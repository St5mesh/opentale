"""
Flask web application for OpenTale
"""
import os
import json
import sys
import shutil
import zipfile
import io
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, Response, stream_with_context, flash, redirect, send_file
from config import get_config, get_narrative_config
from agents import BookAgents
from story_state import StoryState
from state_validator import StateValidator
from migration_helper import MigrationHelper
import prompts
import re

app = Flask(__name__)
app.secret_key = 'ai-book-writer-secret-key'  # For session management

# Ensure book_output directory exists
os.makedirs('book_output/chapters', exist_ok=True)
os.makedirs('projects', exist_ok=True)

# Initialize global variables
agent_config = get_config()
narrative_config = get_narrative_config()

# Startup logging
print("[OpenTale] Flask app initializing...", file=sys.stderr)
print(f"[OpenTale] LLM URL: {agent_config.get('base_url', 'http://ollama:11434/v1')}", file=sys.stderr)


# ============================================================================
# PROJECT MANAGEMENT HELPERS
# ============================================================================

BOOK_OUTPUT_DIR = 'book_output'
PROJECTS_DIR = 'projects'
SESSION_KEYS = ['topic', 'world_theme', 'theme', 'characters', 'chapters', 'outline']


def _clear_book_output():
    """Remove all content from book_output/ and reinitialise with empty state files."""
    if os.path.exists(BOOK_OUTPUT_DIR):
        shutil.rmtree(BOOK_OUTPUT_DIR)
    os.makedirs(f'{BOOK_OUTPUT_DIR}/chapters', exist_ok=True)
    os.makedirs(f'{BOOK_OUTPUT_DIR}/states', exist_ok=True)
    # Reinitialise empty narrative state files
    StoryState.save_story_state(StoryState.initialize_story_state())
    StoryState.save_scene_chain(StoryState.initialize_scene_chain())
    StoryState.save_character_arcs(StoryState.initialize_character_arcs())
    StoryState.save_theme(StoryState.initialize_theme())


def _clear_session():
    """Remove all book-related keys from Flask session."""
    for key in SESSION_KEYS:
        session.pop(key, None)
    # Also clear dynamic chapter keys
    dynamic = [k for k in list(session.keys()) if k.startswith('chapter_')]
    for k in dynamic:
        session.pop(k, None)


def _project_meta(project_name: str) -> dict:
    """Load project.json for a saved project, or return empty dict."""
    meta_path = os.path.join(PROJECTS_DIR, project_name, 'project.json')
    if os.path.exists(meta_path):
        try:
            with open(meta_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {'name': project_name}


def _list_projects() -> list:
    """Return sorted list of saved project metadata dicts."""
    if not os.path.exists(PROJECTS_DIR):
        return []
    projects = []
    for name in sorted(os.listdir(PROJECTS_DIR)):
        project_dir = os.path.join(PROJECTS_DIR, name)
        if os.path.isdir(project_dir):
            meta = _project_meta(name)
            meta['name'] = name
            projects.append(meta)
    return projects


def ensure_state_files_exist():
    """
    Ensure all narrative state files exist. Creates defaults if missing.
    Enables backward compatibility with existing projects without state files.
    """
    # Ensure directories exist
    os.makedirs('book_output/chapters', exist_ok=True)
    
    if not os.path.exists(StoryState.STATE_FILE):
        state = StoryState.initialize_story_state()
        StoryState.save_story_state(state)
    
    if not os.path.exists(StoryState.CHAIN_FILE):
        chain = StoryState.initialize_scene_chain()
        StoryState.save_scene_chain(chain)
    
    if not os.path.exists(StoryState.ARCS_FILE):
        arcs = StoryState.initialize_character_arcs()
        StoryState.save_character_arcs(arcs)
    
    if not os.path.exists(StoryState.THEME_FILE):
        theme = StoryState.initialize_theme()
        StoryState.save_theme(theme)


def validate_all_state_files():
    """
    Validate all state files for integrity. Attempt repairs if issues found.
    
    Returns: (all_valid, validation_report)
    """
    state = StoryState.load_story_state()
    chain = StoryState.load_scene_chain()
    arcs = StoryState.load_character_arcs()
    theme = StoryState.load_theme()
    
    report = StateValidator.full_validation_report(state, chain, arcs, theme)
    
    # Auto-repair if issues found
    if not report['story_state']['valid']:
        state, repairs = StateValidator.repair_state(state)
        StoryState.save_story_state(state)
    
    if not report['scene_chain']['valid']:
        chain, repairs = StateValidator.repair_scene_chain(chain)
        StoryState.save_scene_chain(chain)
    
    return report['overall_valid'], report

@app.before_request
def startup_check():
    """Initialize state files and log startup"""
    if not hasattr(app, 'startup_done'):
        print("[OpenTale] First request - initializing...", file=sys.stderr)
        try:
            if narrative_config.get('state_tracking_enabled', False):
                ensure_state_files_exist()
            print("[OpenTale] ✓ State files initialized", file=sys.stderr)
        except Exception as e:
            print(f"[OpenTale] ⚠ State initialization warning: {e}", file=sys.stderr)
        app.startup_done = True
        print("[OpenTale] ✓ Flask app ready on http://0.0.0.0:5000", file=sys.stderr)

@app.route('/')
def index():
    """Render the home page"""
    # Ensure state files exist (backward compatibility)
    if narrative_config.get('state_tracking_enabled', False):
        ensure_state_files_exist()
    
    return render_template('index.html')

@app.route('/world', methods=['GET'])
def world():
    """Display world theme or chat interface"""
    # GET request - show world page with existing theme if available
    world_theme = ''
    if os.path.exists('book_output/world.txt'):
        with open('book_output/world.txt', 'r') as f:
            world_theme = f.read().strip()
        session['world_theme'] = world_theme
    
    # Load saved theme if it exists so the world page can display it on reload
    saved_theme = None
    if os.path.exists('book_output/theme.json'):
        try:
            saved_theme = StoryState.load_theme()
        except Exception:
            pass

    return render_template('world.html', world_theme=world_theme, topic=session.get('topic', ''), saved_theme=saved_theme)

@app.route('/world_chat', methods=['POST'])
def world_chat():
    """Handle ongoing chat for world building"""
    data = request.json
    user_message = data.get('message', '')
    chat_history = data.get('chat_history', [])
    topic = data.get('topic', '')
    
    # Save topic to session if available
    if topic:
        session['topic'] = topic
    
    # Initialize agents for world building
    book_agents = BookAgents(agent_config)
    agents = book_agents.create_agents(topic, 0)
    
    # Generate response using the direct chat method
    ai_response = book_agents.generate_chat_response(chat_history, topic, user_message)
    
    # Clean the response
    ai_response = ai_response.strip()
    
    return jsonify({
        'message': ai_response
    })

@app.route('/world_chat_stream', methods=['POST'])
def world_chat_stream():
    """Handle ongoing chat for world building with streaming response"""
    data = request.json
    user_message = data.get('message', '')
    chat_history = data.get('chat_history', [])
    topic = data.get('topic', '')
    
    # Save topic to session if available
    if topic:
        session['topic'] = topic
    
    # Initialize agents for world building
    book_agents = BookAgents(agent_config)
    agents = book_agents.create_agents(topic, 0)
    
    # Generate streaming response
    stream = book_agents.generate_chat_response_stream(chat_history, topic, user_message)
    
    def generate():
        # Send a heartbeat to establish the connection
        yield "data: {\"content\": \"\"}\n\n"
        
        # Iterate through the stream to get each chunk
        for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta and chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                # Send each token as it arrives
                yield f"data: {json.dumps({'content': content})}\n\n"
        
        # Send completion marker
        yield f"data: {json.dumps({'content': '[DONE]'})}\n\n"
    
    return Response(stream_with_context(generate()), 
                   mimetype='text/event-stream',
                   headers={
                       'Cache-Control': 'no-cache',
                       'X-Accel-Buffering': 'no'  # Disable buffering in Nginx if used
                   })

@app.route('/finalize_world', methods=['POST'])
def finalize_world():
    """Finalize the world setting based on chat history"""
    data = request.json
    chat_history = data.get('chat_history', [])
    topic = data.get('topic', '')
    
    # Initialize agents for world building
    book_agents = BookAgents(agent_config)
    agents = book_agents.create_agents(topic, 0)
    
    # Generate the final world setting using the direct method
    world_theme = book_agents.generate_final_world(chat_history, topic)
    
    # Clean and save world theme to session and file
    world_theme = world_theme.strip()
    world_theme = re.sub(r'\n+', '\n', world_theme.strip())
    
    session['world_theme'] = world_theme
    with open('book_output/world.txt', 'w') as f:
        f.write(world_theme)
    
    return jsonify({
        'world_theme': world_theme
    })

@app.route('/finalize_world_stream', methods=['POST'])
def finalize_world_stream():
    """Finalize the world setting based on chat history with streaming response"""
    data = request.json
    chat_history = data.get('chat_history', [])
    topic = data.get('topic', '')
    
    # Initialize agents for world building
    book_agents = BookAgents(agent_config)
    agents = book_agents.create_agents(topic, 0)
    
    # Generate the final world setting using streaming
    stream = book_agents.generate_final_world_stream(chat_history, topic)
    
    def generate():
        # Send a heartbeat to establish the connection
        yield "data: {\"content\": \"\"}\n\n"
        
        # Collect all chunks to save the complete response
        collected_content = []
        
        # Iterate through the stream to get each chunk
        for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta and chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                collected_content.append(content)
                # Send each token as it arrives
                yield f"data: {json.dumps({'content': content})}\n\n"
        
        # Combine all chunks for the complete content
        complete_content = ''.join(collected_content)
        
        # Clean and save world theme to session and file once streaming is complete
        world_theme = complete_content.strip()
        world_theme = re.sub(r'\n+', '\n', world_theme)
        
        session['world_theme'] = world_theme
        with open('book_output/world.txt', 'w') as f:
            f.write(world_theme)
        
        # Send completion marker
        yield f"data: {json.dumps({'content': '[DONE]'})}\n\n"
    
    return Response(stream_with_context(generate()), 
                   mimetype='text/event-stream',
                   headers={
                       'Cache-Control': 'no-cache',
                       'X-Accel-Buffering': 'no'
                   })

@app.route('/save_world', methods=['POST'])
def save_world():
    """Save edited world theme"""
    world_theme = request.form.get('world_theme')
    world_theme = world_theme.replace('\r\n', '\n')
    world_theme = re.sub(r'\n{2,}', '\n\n', world_theme)
    
    # Strip extra newlines at the beginning and normalize newlines
    world_theme = world_theme.strip()
    world_theme = re.sub(r'\n+', '\n', world_theme.strip())
    
    # Save to session
    session['world_theme'] = world_theme
    
    # Save to file
    with open('book_output/world.txt', 'w') as f:
        f.write(world_theme)
    
    return jsonify({'success': True})

# ============================================================================
# NARRATIVE ENGINE ROUTES (Phase 3)
# ============================================================================

@app.route('/extract_theme', methods=['POST'])
def extract_theme():
    """Extract story theme from world and topic (if feature enabled)"""
    if not narrative_config.get('theme_extraction_enabled', True):
        return jsonify({'error': 'Theme extraction not enabled'}), 400
    
    data = request.json or {}
    topic = data.get('topic', session.get('topic', ''))
    
    # Load world theme from file or session
    world_theme = ''
    if os.path.exists('book_output/world.txt'):
        try:
            with open('book_output/world.txt', 'r') as f:
                world_theme = f.read().strip()
        except Exception as e:
            return jsonify({'error': f'Failed to read world.txt: {str(e)}'}), 500
    else:
        world_theme = session.get('world_theme', '')
    
    if not world_theme:
        return jsonify({'error': 'World theme not available'}), 400
    
    try:
        book_agents = BookAgents(agent_config)
        book_agents.create_agents(topic, 0)  # Initialize system prompts
        theme_data = book_agents.extract_theme(topic, world_theme)
        
        # Save theme to file
        theme_file_data = StoryState.initialize_theme()
        StoryState.set_theme(
            theme_file_data,
            theme_data.get('statement', ''),
            theme_data.get('core_conflict', ''),
            theme_data.get('moral_tension', '')
        )
        StoryState.save_theme(theme_file_data)
        
        session['theme'] = theme_data
        
        return jsonify({
            'success': True,
            'theme': theme_data
        })
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[extract_theme] DETAILED ERROR:\n{tb}", file=sys.stderr)
        return jsonify({'error': str(e), 'details': tb}), 500

@app.route('/scenes/<int:chapter_number>', methods=['GET', 'POST'])
def plan_chapter_scenes(chapter_number):
    """
    Plan scenes for a specific chapter (NEW REQUIRED WORKFLOW).
    
    GET: Show scene planning UI with chapter outline and suggested scenes
    POST: Generate and save scene plan for chapter
    """
    from chapter_state_manager import ChapterStateManager
    
    # Load chapters
    if not os.path.exists('book_output/chapters.json'):
        return render_template('error.html', message="Outline not found"), 400
    
    with open('book_output/chapters.json', 'r') as f:
        chapters = json.load(f)
    
    chapter_data = None
    for ch in chapters:
        if ch['chapter_number'] == chapter_number:
            chapter_data = ch
            break
    
    if not chapter_data:
        return render_template('error.html', message=f"Chapter {chapter_number} not found"), 404
    
    scene_plan_file = f'book_output/chapters/chapter_{chapter_number}_scene_plan.json'
    scene_plan = None
    
    if os.path.exists(scene_plan_file):
        with open(scene_plan_file, 'r') as f:
            scene_plan = json.load(f)
    if scene_plan:
        scene_plan = _prepare_scene_plan_for_display(scene_plan)
    
    if request.method == 'POST':
        # Generate new scene plan
        try:
            story_state = StoryState.load_story_state()
            state_summary = StoryState.get_full_state_summary(story_state)
            
            book_agents = BookAgents(agent_config)
            book_agents.create_agents('', len(chapters))
            
            # Generate chapter scene plan
            scene_plan_data = book_agents.plan_chapter_scene_chain(
                chapter_number,
                chapter_data['prompt'],
                state_summary
            )
            
            # Save scene plan
            os.makedirs('book_output/chapters', exist_ok=True)
            with open(scene_plan_file, 'w') as f:
                json.dump(scene_plan_data, f, indent=2)
            
            # Initialize chapter state tracking
            ChapterStateManager.ensure_states_directory()
            initial_state = StoryState.load_story_state()
            ChapterStateManager.save_chapter_states(chapter_number, {
                'chapter': chapter_number,
                'current_scene': 0,
                'initial_state': initial_state,
                'scenes_completed': 0
            })
            
            return jsonify({
                'success': True,
                'scene_plan': scene_plan_data,
                'message': f"Scene plan created with {len(scene_plan_data.get('scenes', []))} scenes"
            })
        except Exception as e:
            import traceback
            print(f"Error generating scene plan: {e}\n{traceback.format_exc()}", file=sys.stderr)
            return jsonify({'error': str(e)}), 500
    
    # GET - show scene planning page
    return render_template('scenes.html',
                         chapter=chapter_data,
                         chapter_number=chapter_number,
                         scene_plan=scene_plan,
                         chapters=chapters)


@app.route('/save_scene_plan/<int:chapter_number>', methods=['POST'])
def save_scene_plan(chapter_number):
    """Persist user-edited scene plans for a chapter."""
    data = request.get_json(silent=True)
    if not data or 'scenes' not in data:
        return jsonify({'error': 'Missing scenes payload'}), 400

    scenes_payload = data['scenes']
    normalized = _normalize_scene_plan_payload(scenes_payload)
    if not normalized:
        return jsonify({'error': 'No valid scenes to save'}), 400

    os.makedirs('book_output/chapters', exist_ok=True)
    scene_plan_file = f'book_output/chapters/chapter_{chapter_number}_scene_plan.json'
    scene_plan_data = {
        'chapter': chapter_number,
        'scenes': normalized
    }
    try:
        with open(scene_plan_file, 'w') as f:
            json.dump(scene_plan_data, f, indent=2)
    except IOError as err:
        return jsonify({'error': f'Unable to write scene plan: {err}'}), 500

    return jsonify({'success': True})


def _prepare_scene_plan_for_display(scene_plan):
    """Ensure each scene has text-friendly fallbacks for the UI."""
    scenes = scene_plan.get('scenes', [])
    for idx, scene in enumerate(scenes):
        scene_number = _safe_scene_number(scene.get('scene_number'), idx + 1)
        scene['scene_number'] = scene_number
        scene.setdefault('title', f"Scene {scene_number}")
        scene.setdefault('goal', '')
        scene.setdefault('conflict', '')
        scene.setdefault('outcome', '')
        scene.setdefault('consequence', '')
        scene.setdefault('summary', '')
        scene.setdefault('key_events', [])
        characters = scene.get('characters_present')
        scene['characters_present_text'] = '\n'.join(characters) if isinstance(characters, (list, tuple)) else (characters or '')
        scene['prerequisites_text'] = _prerequisites_to_text(scene.get('prerequisites'))
    return scene_plan


def _normalize_scene_plan_payload(scenes_payload):
    normalized = []
    for idx, scene in enumerate(scenes_payload):
        scene_number = _safe_scene_number(scene.get('scene_number'), idx + 1)
        title = (scene.get('title') or f"Scene {scene_number}").strip()
        goal = (scene.get('goal') or '').strip()
        conflict = (scene.get('conflict') or '').strip()
        outcome = (scene.get('outcome') or '').strip()
        consequence = (scene.get('consequence') or '').strip()
        summary = (scene.get('summary') or '').strip()
        characters = _split_lines(scene.get('characters_present'))
        prerequisites_desc = (scene.get('prerequisites') or '').strip()

        normalized.append({
            'scene_number': scene_number,
            'title': title,
            'goal': goal,
            'conflict': conflict,
            'outcome': outcome,
            'consequence': consequence,
            'characters_present': characters,
            'prerequisites': {'description': prerequisites_desc},
            'summary': summary,
            'key_events': _derive_key_events({'goal': goal, 'conflict': conflict, 'outcome': outcome, 'consequence': consequence, 'summary': summary})
        })
    return normalized


def _derive_key_events(scene_data):
    events = []
    for field in ['goal', 'conflict', 'outcome', 'consequence', 'summary']:
        value = scene_data.get(field)
        if isinstance(value, str) and value.strip():
            events.append(value.strip())
    return events


def _split_lines(raw_value):
    if not raw_value:
        return []
    if isinstance(raw_value, (list, tuple)):
        return [str(v).strip() for v in raw_value if str(v).strip()]
    return [line.strip() for line in str(raw_value).splitlines() if line.strip()]


def _prerequisites_to_text(prerequisites):
    if not prerequisites:
        return ''
    if isinstance(prerequisites, str):
        return prerequisites.strip()
    if isinstance(prerequisites, dict):
        entries = []
        for key, value in prerequisites.items():
            if not value:
                continue
            formatted = value
            if isinstance(value, (list, tuple)):
                formatted = ', '.join(str(item) for item in value if str(item).strip())
            entries.append(f"{key}: {formatted}")
        return '\n'.join(entries)
    return str(prerequisites)


def _safe_scene_number(value, fallback):
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback

@app.route('/get_story_state', methods=['GET'])
def get_story_state():
    """Retrieve current story state"""
    try:
        state = StoryState.load_story_state()
        theme = StoryState.load_theme()
        
        return jsonify({
            'success': True,
            'state': state,
            'theme': theme,
            'state_summary': StoryState.get_full_state_summary(state)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/validate_state', methods=['GET'])
def validate_state():
    """
    Validate all state files for integrity.
    
    Returns validation report with any issues found.
    Attempts auto-repair for fixable issues.
    """
    try:
        all_valid, report = validate_all_state_files()
        
        return jsonify({
            'success': True,
            'valid': all_valid,
            'report': report
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/migration_status', methods=['GET'])
def migration_status():
    """
    Get migration status for current project.
    
    Returns information about whether project has state tracking enabled
    and what actions are recommended.
    """
    try:
        status = MigrationHelper.get_migration_status()
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/migrate_project', methods=['POST'])
def migrate_project():
    """
    Migrate an existing project to enable state tracking.
    
    This creates state files and initializes them with data extracted
    from existing world, characters, and outline files.
    
    Enables backward compatibility for projects created before the
    narrative engine was added.
    """
    try:
        success, message = MigrationHelper.migrate_existing_project(verbose=False)
        
        return jsonify({
            'success': success,
            'message': message
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/characters', methods=['GET'])
def characters():
    """Display characters or character creation chat interface"""
    # GET request - show characters page with existing characters if available
    characters_content = ''
    if os.path.exists('book_output/characters.txt'):
        with open('book_output/characters.txt', 'r') as f:
            characters_content = f.read().strip()
        session['characters'] = characters_content
    
    # Load world theme from file if it exists
    world_theme = ''
    if os.path.exists('book_output/world.txt'):
        with open('book_output/world.txt', 'r') as f:
            world_theme = f.read().strip()
    # If not available from file, try from session
    else:
        world_theme = session.get('world_theme', '')
    
    return render_template('characters.html', 
                           characters=characters_content, 
                           world_theme=world_theme)

@app.route('/save_characters', methods=['POST'])
def save_characters():
    """Save edited characters"""
    characters_content = request.form.get('characters')
    characters_content = characters_content.replace('\r\n', '\n')
    characters_content = re.sub(r'\n{2,}', '\n\n', characters_content)
    
    # Strip extra newlines at the beginning and normalize newlines
    characters_content = characters_content.strip()
    
    # Save to session
    session['characters'] = characters_content
    
    # Save to file
    with open('book_output/characters.txt', 'w') as f:
        f.write(characters_content)
    
    return jsonify({'success': True})

@app.route('/outline', methods=['GET', 'POST'])
def outline():
    # Check if world theme and characters exist
    if not os.path.exists('book_output/world.txt'):
        flash('You need to create a world setting first.', 'warning')
        return redirect('/world')
    
    if not os.path.exists('book_output/characters.txt'):
        flash('You need to create characters first.', 'warning')
        return redirect('/characters')
    
    # Get world theme and characters
    with open('book_output/world.txt', 'r') as f:
        world_theme = f.read()
    
    with open('book_output/characters.txt', 'r') as f:
        characters = f.read()
    
    # GET request - just show the page
    outline_content = ''
    if os.path.exists('book_output/outline.txt'):
        with open('book_output/outline.txt', 'r') as f:
            outline_content = f.read()
    
    # Get chapter list if it exists
    chapters = []
    if os.path.exists('book_output/chapters.json'):
        with open('book_output/chapters.json', 'r') as f:
            chapters = json.load(f)
    
    return render_template('outline.html', 
                          world_theme=world_theme, 
                          characters=characters,
                          outline=outline_content,
                          chapters=chapters)

@app.route('/generate_chapters', methods=['POST'])
def generate_chapters():
    """Generate chapters structure from existing outline"""
    # Check if we have an outline
    if not os.path.exists('book_output/outline.txt'):
        return jsonify({'error': 'Outline not found. Please create an outline first.'})
    
    # Get the outline content
    with open('book_output/outline.txt', 'r') as f:
        outline_content = f.read()
    
    # Get the desired number of chapters
    num_chapters = int(request.form.get('num_chapters', 10))
    
    # Parse the outline into chapters
    chapters = parse_outline_to_chapters(outline_content, num_chapters)
    
    # Save chapters to session and file
    session['chapters'] = chapters
    with open('book_output/chapters.json', 'w') as f:
        json.dump(chapters, f, indent=2)
    
    return jsonify({'success': True, 'num_chapters': len(chapters)})

@app.route('/save_outline', methods=['POST'])
def save_outline():
    """Save edited outline and generate chapters structure"""
    outline_content = request.form.get('outline')
    outline_content = outline_content.replace('\r\n', '\n')
    outline_content = re.sub(r'\n{2,}', '\n\n', outline_content)
    
    # Strip extra newlines at the beginning and normalize newlines
    outline_content = outline_content.strip()
    
    # Save to session
    session['outline'] = outline_content
    
    # Save to file
    with open('book_output/outline.txt', 'w') as f:
        f.write(outline_content)
    
    # Generate and save chapters
    num_chapters = int(request.form.get('num_chapters', 10))
    chapters = parse_outline_to_chapters(outline_content, num_chapters)
    
    # Save chapters to session and file
    session['chapters'] = chapters
    with open('book_output/chapters.json', 'w') as f:
        json.dump(chapters, f, indent=2)
    
    return jsonify({'success': True, 'num_chapters': len(chapters)})

@app.route('/chapter/<int:chapter_number>', methods=['GET', 'POST'])
def chapter(chapter_number):
    """
    Generate or display a specific chapter using planned scenes.
    NOW REQUIRES SCENE PLAN (enforced workflow).
    """
    from chapter_state_manager import ChapterStateManager
    
    chapters = []
    
    # Load chapters from disk
    if os.path.exists('book_output/chapters.json'):
        with open('book_output/chapters.json', 'r') as f:
            chapters = json.load(f)
            session['chapters'] = chapters
    elif session.get('chapters'):
        chapters = session.get('chapters', [])
    
    # Find chapter
    chapter_data = None
    for ch in chapters:
        if ch['chapter_number'] == chapter_number:
            chapter_data = ch
            break
    
    if not chapter_data:
        return render_template('error.html', message=f"Chapter {chapter_number} not found")
    
    # CHECK SCENE PLAN EXISTS (HARD REQUIREMENT)
    scene_plan_file = f'book_output/chapters/chapter_{chapter_number}_scene_plan.json'
    if not os.path.exists(scene_plan_file):
        # Redirect to scene planning
        return redirect(f'/scenes/{chapter_number}')
    
    with open(scene_plan_file, 'r') as f:
        scene_plan = json.load(f)
    
    if request.method == 'POST':
        # Store generation context in session and return stream URL.
        # Actual generation happens via SSE at /generate_chapter_stream/<N>.
        additional_context = request.form.get('additional_context', '')
        chat_history_json = request.form.get('chat_history', '[]')
        try:
            chat_history = json.loads(chat_history_json)
        except (json.JSONDecodeError, ValueError):
            chat_history = []

        session[f'chapter_{chapter_number}_additional_context'] = additional_context
        session[f'chapter_{chapter_number}_chat_history'] = chat_history
        return jsonify({'stream_url': f'/generate_chapter_stream/{chapter_number}'})
    
    # GET - show chapter page
    chapter_content = ''
    chapter_path = f'book_output/chapters/chapter_{chapter_number}.txt'
    if os.path.exists(chapter_path):
        with open(chapter_path, 'r') as f:
            chapter_content = f.read().strip()
    
    return render_template('chapter.html', 
                         chapter=chapter_data,
                         chapter_content=chapter_content,
                         chapter_number=chapter_number,
                         scene_plan=scene_plan,
                         chapters=chapters)

@app.route('/save_chapter/<int:chapter_number>', methods=['POST'])
def save_chapter(chapter_number):
    """Save edited chapter content"""
    chapter_content = request.form.get('chapter_content')
    
    # Strip extra newlines at the beginning and normalize newlines
    chapter_content = chapter_content.strip()
    
    chapter_path = f'book_output/chapters/chapter_{chapter_number}.txt'
    with open(chapter_path, 'w') as f:
        f.write(chapter_content)
    
    return jsonify({'success': True})


@app.route('/chapter_chat/<int:chapter_number>', methods=['POST'])
def chapter_chat(chapter_number):
    """Real LLM chat for chapter development discussion."""
    data = request.get_json(silent=True) or {}
    user_message = data.get('message', '').strip()
    chat_history = data.get('chat_history', [])

    if not user_message:
        return jsonify({'error': 'No message provided'}), 400

    # Load chapter data
    chapters = []
    if os.path.exists('book_output/chapters.json'):
        with open('book_output/chapters.json', 'r') as f:
            chapters = json.load(f)

    chapter_data = next((ch for ch in chapters if ch['chapter_number'] == chapter_number), None)
    if not chapter_data:
        return jsonify({'error': f'Chapter {chapter_number} not found'}), 404

    # Load scene plan
    scene_plan_file = f'book_output/chapters/chapter_{chapter_number}_scene_plan.json'
    scene_plan = {}
    if os.path.exists(scene_plan_file):
        with open(scene_plan_file, 'r') as f:
            scene_plan = json.load(f)

    world_theme = ''
    characters = ''
    if os.path.exists('book_output/world.txt'):
        with open('book_output/world.txt', 'r') as f:
            world_theme = f.read().strip()
    if os.path.exists('book_output/characters.txt'):
        with open('book_output/characters.txt', 'r') as f:
            characters = f.read().strip()

    # Build chapter context for the advisor system prompt
    scene_summary = ""
    if scene_plan.get('scenes'):
        scene_lines = [f"  Scene {s['scene_number']}: {s['title']} — {s.get('summary', s.get('goal', ''))}"
                       for s in scene_plan['scenes']]
        scene_summary = "Planned Scenes:\n" + "\n".join(scene_lines)

    chapter_context = (
        f"CHAPTER BEING DEVELOPED: Chapter {chapter_number}: {chapter_data['title']}\n\n"
        f"Chapter outline:\n{chapter_data.get('prompt', '')}\n\n"
        f"{scene_summary}\n\n"
        f"WORLD SETTING (summary):\n{world_theme[:800]}\n\n"
        f"CHARACTERS:\n{characters[:800]}"
    )

    try:
        book_agents = BookAgents(agent_config, chapters)
        book_agents.create_agents(world_theme, len(chapters))
        response_text = book_agents.generate_chapter_chat_response(
            chat_history, chapter_context, user_message
        )
        return jsonify({'response': response_text})
    except Exception as e:
        import traceback
        print(f"Error in chapter_chat: {e}\n{traceback.format_exc()}", file=sys.stderr)
        return jsonify({'error': str(e)}), 500


@app.route('/generate_chapter_stream/<int:chapter_number>')
def generate_chapter_stream(chapter_number):
    """SSE endpoint: generate chapter scene-by-scene with state updates between each scene."""
    from chapter_state_manager import ChapterStateManager

    additional_context = session.pop(f'chapter_{chapter_number}_additional_context', '')
    chat_history = session.pop(f'chapter_{chapter_number}_chat_history', [])

    def _send(payload: dict) -> str:
        return f"data: {json.dumps(payload)}\n\n"

    def generate():
        try:
            # ── Load all needed context ──────────────────────────────────────
            chapters = []
            if os.path.exists('book_output/chapters.json'):
                with open('book_output/chapters.json', 'r') as f:
                    chapters = json.load(f)

            chapter_data = next(
                (ch for ch in chapters if ch['chapter_number'] == chapter_number), None
            )
            if not chapter_data:
                yield _send({'type': 'error', 'message': f'Chapter {chapter_number} not found'})
                return

            scene_plan_file = f'book_output/chapters/chapter_{chapter_number}_scene_plan.json'
            if not os.path.exists(scene_plan_file):
                yield _send({'type': 'error', 'message': 'Scene plan not found. Plan scenes first.'})
                return

            with open(scene_plan_file, 'r') as f:
                scene_plan = json.load(f)

            scenes = scene_plan.get('scenes', [])
            if not scenes:
                yield _send({'type': 'error', 'message': 'Scene plan is empty.'})
                return

            world_theme = ''
            characters = ''
            if os.path.exists('book_output/world.txt'):
                with open('book_output/world.txt', 'r') as f:
                    world_theme = f.read().strip()
            if os.path.exists('book_output/characters.txt'):
                with open('book_output/characters.txt', 'r') as f:
                    characters = f.read().strip()

            previous_context = ""
            if chapter_number > 1:
                prev_path = f'book_output/chapters/chapter_{chapter_number - 1}.txt'
                if os.path.exists(prev_path):
                    with open(prev_path, 'r') as f:
                        content = f.read()
                        previous_context = content[-1500:] if len(content) > 1500 else content

            # Build chat history context for the writer
            chat_context = ""
            if chat_history:
                user_notes = [m['content'] for m in chat_history if m.get('role') == 'user']
                if user_notes:
                    chat_context = (
                        "\n\nAUTHOR REQUIREMENTS FOR THIS CHAPTER (must be respected):\n"
                        + "\n".join(f"- {note}" for note in user_notes)
                    )

            chapter_prompt_base = chapter_data['prompt']
            if additional_context:
                chapter_prompt_base += f"\n\n{additional_context}"
            chapter_prompt_base += chat_context

            book_agents = BookAgents(agent_config, chapters)
            book_agents.create_agents(world_theme, len(chapters))

            # ── Load or create chapter state ─────────────────────────────────
            chapter_state = ChapterStateManager.load_chapter_states(chapter_number)
            if not chapter_state:
                story_state = StoryState.load_story_state()
                if chapter_number > 1:
                    prev_cs = ChapterStateManager.load_chapter_states(chapter_number - 1)
                    if prev_cs and 'final_state' in prev_cs:
                        story_state = prev_cs['final_state']
                chapter_state = {
                    'chapter': chapter_number,
                    'current_scene': 0,
                    'initial_state': story_state,
                    'scenes_completed': 0,
                    'state_transitions': []
                }
            else:
                story_state = StoryState.load_story_state()

            total_scenes = len(scenes)
            all_scene_contents = []
            os.makedirs(f'book_output/chapters/chapter_{chapter_number}_scenes', exist_ok=True)

            # ── Generate each scene ──────────────────────────────────────────
            for i, scene in enumerate(scenes):
                scene_num = i + 1
                scene_title = scene.get('title', f'Scene {scene_num}')

                yield _send({
                    'type': 'progress',
                    'message': f'Generating Scene {scene_num} of {total_scenes}: {scene_title}',
                    'scene': scene_num,
                    'total': total_scenes,
                    'percent': int((i / total_scenes) * 80)
                })

                state_summary = StoryState.get_full_state_summary(story_state)

                scene_goal = scene.get('goal', scene.get('summary', chapter_prompt_base))
                scene_conflict = scene.get('conflict', '')
                scene_outcome = scene.get('outcome', '')

                story_context = (
                    f"Chapter {chapter_number}: {chapter_data['title']}\n"
                    f"Chapter outline: {chapter_prompt_base}\n\n"
                    f"Previous chapter context:\n{previous_context}"
                )

                scene_content = book_agents.generate_scene_with_state(
                    scene_goal=scene_goal,
                    scene_conflict=scene_conflict,
                    scene_outcome=scene_outcome,
                    story_context=story_context,
                    world_theme=world_theme,
                    characters=characters,
                    current_state=state_summary
                )

                # Save scene to disk
                scene_path = f'book_output/chapters/chapter_{chapter_number}_scenes/scene_{scene_num}.txt'
                with open(scene_path, 'w') as f:
                    f.write(scene_content)

                all_scene_contents.append(f"## {scene_title}\n\n{scene_content}")

                yield _send({
                    'type': 'scene_complete',
                    'message': f'Scene {scene_num} written. Updating story state...',
                    'scene': scene_num,
                    'total': total_scenes,
                    'percent': int(((i + 0.7) / total_scenes) * 80)
                })

                # ── Extract and apply state changes ──────────────────────────
                try:
                    state_changes = book_agents.extract_scene_state_changes(
                        scene_content, state_summary
                    )
                    if state_changes and any(
                        state_changes.get(k) for k in ('characters', 'artifacts', 'world')
                    ):
                        story_state = StoryState.apply_extracted_changes(
                            story_state, state_changes,
                            source=f"chapter_{chapter_number}_scene_{scene_num}"
                        )
                        StoryState.save_story_state(story_state)
                        chapter_state.setdefault('state_transitions', []).append({
                            'scene': scene_num,
                            'changes': state_changes
                        })
                        yield _send({
                            'type': 'state_updated',
                            'message': f'Story state updated after Scene {scene_num}',
                            'scene': scene_num,
                            'percent': int(((i + 0.9) / total_scenes) * 80)
                        })
                except Exception as state_err:
                    print(f"Warning: state extraction failed for scene {scene_num}: {state_err}",
                          file=sys.stderr)

            # ── Assemble final chapter ────────────────────────────────────────
            yield _send({
                'type': 'progress',
                'message': 'Assembling final chapter...',
                'percent': 85
            })

            chapter_content = (
                f"# Chapter {chapter_number}: {chapter_data['title']}\n\n"
                + "\n\n---\n\n".join(all_scene_contents)
            )
            chapter_content = chapter_content.strip()

            chapter_path = f'book_output/chapters/chapter_{chapter_number}.txt'
            with open(chapter_path, 'w') as f:
                f.write(chapter_content)

            # ── Finalise chapter state ────────────────────────────────────────
            chapter_state['final_state'] = StoryState.load_story_state()
            chapter_state['scenes_completed'] = total_scenes
            chapter_state['plot_progress'] = {
                'current_chapter': chapter_number,
                'completed_scenes': story_state.get('plot_progress', {}).get('completed_scenes', 0)
            }
            ChapterStateManager.save_chapter_states(chapter_number, chapter_state)

            yield _send({
                'type': 'done',
                'message': f'Chapter {chapter_number} complete! ({total_scenes} scenes)',
                'chapter_content': chapter_content,
                'percent': 100
            })

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"Error in generate_chapter_stream {chapter_number}: {e}\n{tb}", file=sys.stderr)
            yield _send({'type': 'error', 'message': str(e)})

    return Response(
        stream_with_context(generate()),
        content_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )

@app.route('/scene/<int:chapter_number>', methods=['GET', 'POST'])
def scene(chapter_number):
    """Generate a scene for a specific chapter"""
    # Load chapters data - always load from disk first to get latest
    chapters = []
    
    # Always load from disk first to get latest outline
    if os.path.exists('book_output/chapters.json'):
        try:
            with open('book_output/chapters.json', 'r') as f:
                chapters = json.load(f)
                session['chapters'] = chapters
        except Exception as e:
            print(f"Error loading chapters.json: {e}")
    # Fall back to session if disk doesn't exist
    elif session.get('chapters'):
        chapters = session.get('chapters', [])
    
    # Print diagnostic info
    print(f"Number of chapters loaded: {len(chapters)}")
    print(f"Looking for chapter: {chapter_number}")
    if chapters:
        print(f"Available chapter numbers: {[ch.get('chapter_number') for ch in chapters]}")
    
    # Find chapter data
    chapter_data = None
    for ch in chapters:
        if ch.get('chapter_number') == chapter_number:
            chapter_data = ch
            break
    
    if not chapter_data:
        print(f"Chapter {chapter_number} not found in loaded data")
        # Try alternate approaches to find the chapter
        
        # Approach 1: Direct file check
        chapter_path = f'book_output/chapters/chapter_{chapter_number}.txt'
        if os.path.exists(chapter_path):
            # Chapter exists but data isn't in memory
            chapter_data = {
                'chapter_number': chapter_number,
                'title': f"Chapter {chapter_number}",
                'prompt': "Chapter content from file"
            }
            print(f"Found chapter file, creating basic chapter data")
        else:
            # Approach 2: Create stub data if no chapters exist yet
            chapter_data = {
                'chapter_number': chapter_number,
                'title': f"Chapter {chapter_number}",
                'prompt': "No chapter outline available"
            }
            print(f"Creating stub chapter data")
    
    if request.method == 'POST':
        scene_description = request.form.get('scene_description', '')
        
        # Generate the scene
        world_theme = ''
        characters = ''
        
        # Load world and character data
        if os.path.exists('book_output/world.txt'):
            with open('book_output/world.txt', 'r') as f:
                world_theme = f.read().strip()
        else:
            world_theme = session.get('world_theme', '')
            
        if os.path.exists('book_output/characters.txt'):
            with open('book_output/characters.txt', 'r') as f:
                characters = f.read().strip()
        else:
            characters = session.get('characters', '')
        
        # Get previous context
        previous_context = ""
        if chapter_number > 1:
            prev_chapter_path = f'book_output/chapters/chapter_{chapter_number-1}.txt'
            if os.path.exists(prev_chapter_path):
                with open(prev_chapter_path, 'r') as f:
                    content = f.read()
                    previous_context = content[-1000:] if len(content) > 1000 else content
        
        # [ENHANCED] Load current chapter states for context-aware scene generation
        chapter_states = None
        states_file = f'book_output/states/chapter_{chapter_number}_states.json'
        if os.path.exists(states_file):
            try:
                with open(states_file, 'r') as f:
                    chapter_states = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load chapter states: {e}")
        
        # Initialize agents
        book_agents = BookAgents(agent_config, chapters)
        agents = book_agents.create_agents(world_theme, len(chapters) if chapters else 1)
        
        # [ENHANCED] Include chapter states in scene generation prompt for continuity
        state_context = ""
        if chapter_states:
            state_context = f"\n\nCurrent Chapter State:\n{json.dumps(chapter_states, indent=2)}"
        
        # Generate the scene with state context
        scene_content = book_agents.generate_content(
            "writer",
            prompts.SCENE_GENERATION_PROMPT.format(
                chapter_number=chapter_number,
                chapter_title=chapter_data.get('title', f"Chapter {chapter_number}"),
                chapter_outline=chapter_data.get('prompt', ""),
                world_theme=world_theme,
                relevant_characters=characters,
                previous_context=previous_context
            ) + state_context
        )
        
        # Save scene to a file
        scene_dir = f'book_output/chapters/chapter_{chapter_number}_scenes'
        os.makedirs(scene_dir, exist_ok=True)
        
        # Count existing scenes and create a new one
        scene_count = len([f for f in os.listdir(scene_dir) if f.endswith('.txt')])
        scene_path = f'{scene_dir}/scene_{scene_count + 1}.txt'
        
        with open(scene_path, 'w') as f:
            f.write(scene_content)
        
        # [PHASE 3] Extract state changes from the generated scene with mutability validation
        try:
            from state_mutability import StateMutabilityRules
            
            story_state = StoryState.load_story_state()
            state_summary = StoryState.get_full_state_summary(story_state)
            
            # Extract state changes from scene
            state_changes = book_agents.extract_scene_state_changes(scene_content, state_summary)
            
            # Apply extracted changes to story state
            if state_changes and (state_changes.get('characters') or state_changes.get('artifacts') or state_changes.get('world')):
                # [ENHANCED] Validate state mutations before applying
                previous_state = story_state.copy()
                story_state_new = StoryState.apply_extracted_changes(
                    story_state,
                    state_changes,
                    source=f"scene_{chapter_number}_{scene_count + 1}"
                )
                
                # Check mutability rules
                is_valid, violations, warnings = StateMutabilityRules.check_mutability(
                    previous_state,
                    story_state_new,
                    'scene_draft'
                )
                
                if violations:
                    print(f"State Mutation Violations in Chapter {chapter_number}, Scene {scene_count + 1}:")
                    for v in violations:
                        print(f"  ✗ {v}")
                
                if warnings:
                    print(f"State Mutation Warnings in Chapter {chapter_number}, Scene {scene_count + 1}:")
                    for w in warnings:
                        print(f"  ⚠ {w}")
                
                # Save the updated state regardless of warnings (but not if critical violations)
                story_state = story_state_new
                StoryState.save_story_state(story_state)
                print(f"Applied state changes from scene {scene_count + 1}")
                
                # [ENHANCED] Update chapter-specific states file
                if chapter_states:
                    # Merge scene changes into chapter states (optional - tracks chapter-level progression)
                    chapter_states['last_updated_scene'] = scene_count + 1
                    chapter_states['state_transitions'] = chapter_states.get('state_transitions', []) + [{
                        'scene': scene_count + 1,
                        'changes': state_changes
                    }]
                    with open(states_file, 'w') as f:
                        json.dump(chapter_states, f, indent=2)
        
        except Exception as e:
            print(f"Warning: Failed to extract state changes from scene: {e}")
            import traceback
            traceback.print_exc()
            # Don't fail scene generation if extraction fails
        
        return jsonify({'scene_content': scene_content})
    
    # GET request - load existing scenes for this chapter
    scenes = []
    scene_dir = f'book_output/chapters/chapter_{chapter_number}_scenes'
    
    if os.path.exists(scene_dir):
        scene_files = [f for f in os.listdir(scene_dir) if f.endswith('.txt')]
        scene_files.sort(key=lambda f: int(f.split('_')[1].split('.')[0]))  # Sort by scene number
        
        for scene_file in scene_files:
            scene_path = os.path.join(scene_dir, scene_file)
            scene_number = int(scene_file.split('_')[1].split('.')[0])
            
            with open(scene_path, 'r') as f:
                content = f.read()
                
                # Extract a title from the first line or first few words
                lines = content.split('\n')
                if lines:
                    title = lines[0][:30] + '...' if len(lines[0]) > 30 else lines[0]
                else:
                    title = f"Scene {scene_number}"
                
                scenes.append({
                    'number': scene_number,
                    'title': title,
                    'content': content
                })
    
    # Return the template with loaded scenes
    return render_template('scene.html', 
                           chapter=chapter_data,
                           scenes=scenes)

@app.route('/get_or_create_chapter_states/<int:chapter_number>', methods=['GET', 'POST'])
def get_or_create_chapter_states(chapter_number):
    """
    Get or lazily create initial story states for a specific chapter.
    
    Called when user first enters a chapter for drafting.
    If states don't exist, generate them from outline, world, and previous chapter states.
    """
    try:
        from state_mutability import StateMutabilityRules
        
        # Check if chapter states already exist
        states_file = f'book_output/states/chapter_{chapter_number}_states.json'
        
        if os.path.exists(states_file):
            with open(states_file, 'r') as f:
                chapter_states = json.load(f)
            return jsonify({'success': True, 'states': chapter_states, 'is_new': False})
        
        # States don't exist, generate them
        # Load required data
        chapters = []
        if os.path.exists('book_output/chapters.json'):
            with open('book_output/chapters.json', 'r') as f:
                chapters = json.load(f)
        
        # Find chapter outline
        chapter_data = None
        for ch in chapters:
            if ch.get('chapter_number') == chapter_number:
                chapter_data = ch
                break
        
        if not chapter_data:
            return jsonify({'error': f'Chapter {chapter_number} not found'}), 404
        
        # Load world and characters
        world_theme = ''
        characters = ''
        if os.path.exists('book_output/world.txt'):
            with open('book_output/world.txt', 'r') as f:
                world_theme = f.read()
        if os.path.exists('book_output/characters.txt'):
            with open('book_output/characters.txt', 'r') as f:
                characters = f.read()
        
        # Load previous chapter states if this isn't chapter 1
        previous_states = None
        if chapter_number > 1:
            prev_states_file = f'book_output/states/chapter_{chapter_number-1}_states.json'
            if os.path.exists(prev_states_file):
                with open(prev_states_file, 'r') as f:
                    previous_states = json.load(f)
        
        # Load global story state for context
        story_state = StoryState.load_story_state()
        completed_quests = story_state.get('plot_progress', {}).get('completed_quests', [])
        pending_quests = story_state.get('plot_progress', {}).get('pending_quests', [])
        
        # Generate chapter states
        book_agents = BookAgents(agent_config)
        chapter_states = book_agents.generate_chapter_initial_states(
            chapter_number=chapter_number,
            chapter_outline=chapter_data.get('prompt', ''),
            world_theme=world_theme,
            characters=characters,
            previous_chapter_states=previous_states,
            completed_quests=completed_quests,
            pending_quests=pending_quests
        )
        
        # Validate that states follow mutability rules
        if previous_states:
            is_valid, violations, warnings = StateMutabilityRules.check_mutability(
                previous_states,
                chapter_states,
                'chapter_transition'
            )
            if violations:
                print(f"Warning: State mutability violations in chapter {chapter_number}:")
                for violation in violations:
                    print(f"  - {violation}")
        
        # Save chapter states
        os.makedirs('book_output/states', exist_ok=True)
        with open(states_file, 'w') as f:
            json.dump(chapter_states, f, indent=2)
        
        return jsonify({
            'success': True,
            'states': chapter_states,
            'is_new': True,
            'message': f'Generated initial states for chapter {chapter_number}'
        })
    
    except Exception as e:
        print(f"Error getting/creating chapter states: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/validate_chapter/<int:chapter_number>', methods=['POST'])
def validate_chapter(chapter_number):
    """
    Validate a completed chapter for consistency (Phase 4, Stage 4).
    
    This endpoint:
    1. Loads all scenes for the chapter
    2. Loads the scene chain for the chapter
    3. Loads current story state
    4. Runs comprehensive validation checks
    5. Returns validation report
    
    Returns: JSON with validation results and report
    """
    try:
        from enhanced_state_validator import EnhancedStateValidator
        
        # Load scene chain for this chapter
        scene_chain_file = f'book_output/chapter_{chapter_number}_scene_chain.json'
        if not os.path.exists(scene_chain_file):
            return jsonify({'error': f'No scene chain found for chapter {chapter_number}'}), 404
        
        with open(scene_chain_file, 'r') as f:
            scene_chain = json.load(f)
        
        # Load all scenes for this chapter
        scene_dir = f'book_output/chapters/chapter_{chapter_number}_scenes'
        scenes = []
        
        if os.path.exists(scene_dir):
            scene_files = [f for f in os.listdir(scene_dir) if f.endswith('.txt')]
            scene_files.sort(key=lambda f: int(f.split('_')[1].split('.')[0]))
            
            for scene_file in scene_files:
                scene_path = os.path.join(scene_dir, scene_file)
                scene_number = int(scene_file.split('_')[1].split('.')[0])
                
                with open(scene_path, 'r') as f:
                    content = f.read()
                    scenes.append({
                        'scene_number': scene_number,
                        'content': content,
                        'characters_present': [],  # Would need to extract from content
                        'prerequisites': {}  # Would need from scene chain
                    })
        
        if not scenes:
            return jsonify({'error': f'No scenes found for chapter {chapter_number}'}), 404
        
        # Load story state
        story_state = StoryState.load_story_state()
        
        # Run validation
        validation_results = EnhancedStateValidator.validate_chapter_coherence(
            scenes, scene_chain, story_state
        )
        
        # Generate report
        report = EnhancedStateValidator.generate_validation_report(validation_results)
        
        # Save report to file
        report_file = f'book_output/chapter_{chapter_number}_validation.txt'
        with open(report_file, 'w') as f:
            f.write(report)
        
        return jsonify({
            'success': True,
            'chapter': chapter_number,
            'is_valid': validation_results['is_valid'],
            'total_issues': validation_results['total_issues'],
            'checks': {name: check['valid'] for name, check in validation_results['checks'].items()},
            'report': report
        })
    
    except Exception as e:
        print(f"Error validating chapter {chapter_number}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to validate chapter: {str(e)}'}), 500

@app.route('/characters_chat', methods=['POST'])
def characters_chat():
    """Handle ongoing chat for character creation"""
    data = request.json
    user_message = data.get('message', '')
    chat_history = data.get('chat_history', [])
    world_theme = session.get('world_theme', '')
    
    # Ensure we have a world theme
    if not world_theme:
        if os.path.exists('book_output/world.txt'):
            with open('book_output/world.txt', 'r') as f:
                world_theme = f.read().strip()
            session['world_theme'] = world_theme
        else:
            return jsonify({'error': 'World theme not found. Please complete world building first.'})
    
    # Initialize agents for character creation
    book_agents = BookAgents(agent_config)
    agents = book_agents.create_agents(world_theme, 0)
    
    # Generate response using the direct chat method
    ai_response = book_agents.generate_chat_response_characters(chat_history, world_theme, user_message)
    
    # Clean the response
    ai_response = ai_response.strip()
    
    return jsonify({
        'message': ai_response
    })

@app.route('/characters_chat_stream', methods=['POST'])
def characters_chat_stream():
    """Handle ongoing chat for character creation with streaming response"""
    data = request.json
    user_message = data.get('message', '')
    chat_history = data.get('chat_history', [])
    world_theme = session.get('world_theme', '')
    
    # Ensure we have a world theme
    if not world_theme:
        if os.path.exists('book_output/world.txt'):
            with open('book_output/world.txt', 'r') as f:
                world_theme = f.read().strip()
            session['world_theme'] = world_theme
        else:
            return jsonify({'error': 'World theme not found. Please complete world building first.'})
    
    # Initialize agents for character creation
    book_agents = BookAgents(agent_config)
    agents = book_agents.create_agents(world_theme, 0)
    
    # Generate streaming response
    stream = book_agents.generate_chat_response_characters_stream(chat_history, world_theme, user_message)
    
    def generate():
        # Send a heartbeat to establish the connection
        yield "data: {\"content\": \"\"}\n\n"
        
        # Iterate through the stream to get each chunk
        for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta and chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                # Send each token as it arrives
                yield f"data: {json.dumps({'content': content})}\n\n"
        
        # Send completion marker
        yield f"data: {json.dumps({'content': '[DONE]'})}\n\n"
    
    return Response(stream_with_context(generate()), 
                   mimetype='text/event-stream',
                   headers={
                       'Cache-Control': 'no-cache',
                       'X-Accel-Buffering': 'no'
                   })

@app.route('/finalize_characters_stream', methods=['POST'])
def finalize_characters_stream():
    """Finalize the characters based on chat history with streaming response"""
    data = request.json
    chat_history = data.get('chat_history', [])
    num_characters = data.get('num_characters', 3)
    world_theme = session.get('world_theme', '')
    
    # Ensure we have a world theme
    if not world_theme:
        if os.path.exists('book_output/world.txt'):
            with open('book_output/world.txt', 'r') as f:
                world_theme = f.read().strip()
            session['world_theme'] = world_theme
        else:
            return jsonify({'error': 'World theme not found. Please complete world building first.'})
    
    # Initialize agents for character creation
    book_agents = BookAgents(agent_config)
    agents = book_agents.create_agents(world_theme, 0)
    
    # Generate the final characters using streaming
    stream = book_agents.generate_final_characters_stream(chat_history, world_theme, num_characters)
    
    def generate():
        # Send a heartbeat to establish the connection
        yield "data: {\"content\": \"\"}\n\n"
        
        # Collect all chunks to save the complete response
        collected_content = []
        
        # Iterate through the stream to get each chunk
        for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta and chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                collected_content.append(content)
                # Send each token as it arrives
                yield f"data: {json.dumps({'content': content})}\n\n"
        
        # Combine all chunks for the complete content
        complete_content = ''.join(collected_content)
        
        # Clean and save characters to session and file once streaming is complete
        characters_content = complete_content.strip()
        
        session['characters'] = characters_content
        with open('book_output/characters.txt', 'w') as f:
            f.write(characters_content)
        
        # Send completion marker
        yield f"data: {json.dumps({'content': '[DONE]'})}\n\n"
    
    return Response(stream_with_context(generate()), 
                   mimetype='text/event-stream',
                   headers={
                       'Cache-Control': 'no-cache',
                       'X-Accel-Buffering': 'no'
                   })

@app.route('/outline_chat', methods=['POST'])
def outline_chat():
    """Handle ongoing chat for outline creation"""
    data = request.json
    user_message = data.get('message', '')
    chat_history = data.get('chat_history', [])
    num_chapters = data.get('num_chapters', 10)
    
    # Get world_theme and characters for context
    world_theme = session.get('world_theme', '')
    characters = session.get('characters', '')
    
    # Ensure we have world and characters
    if not world_theme or not characters:
        # Try to load from files
        if os.path.exists('book_output/world.txt'):
            with open('book_output/world.txt', 'r') as f:
                world_theme = f.read().strip()
            session['world_theme'] = world_theme
        
        if os.path.exists('book_output/characters.txt'):
            with open('book_output/characters.txt', 'r') as f:
                characters = f.read().strip()
            session['characters'] = characters
            
        if not world_theme or not characters:
            return jsonify({'error': 'World theme or characters not found. Please complete previous steps first.'})
    
    # Initialize agents for outline creation
    book_agents = BookAgents(agent_config)
    agents = book_agents.create_agents(world_theme, num_chapters)
    
    # Generate response using the direct chat method
    ai_response = book_agents.generate_chat_response_outline(chat_history, world_theme, characters, user_message)
    
    # Clean the response
    ai_response = ai_response.strip()
    
    return jsonify({
        'message': ai_response
    })

@app.route('/outline_chat_stream', methods=['POST'])
def outline_chat_stream():
    """Handle ongoing chat for outline creation with streaming response"""
    data = request.json
    user_message = data.get('message', '')
    chat_history = data.get('chat_history', [])
    num_chapters = data.get('num_chapters', 10)
    
    # Get world_theme and characters for context
    world_theme = session.get('world_theme', '')
    characters = session.get('characters', '')
    
    # Ensure we have world and characters
    if not world_theme or not characters:
        # Try to load from files
        if os.path.exists('book_output/world.txt'):
            with open('book_output/world.txt', 'r') as f:
                world_theme = f.read().strip()
            session['world_theme'] = world_theme
        
        if os.path.exists('book_output/characters.txt'):
            with open('book_output/characters.txt', 'r') as f:
                characters = f.read().strip()
            session['characters'] = characters
            
        if not world_theme or not characters:
            return jsonify({'error': 'World theme or characters not found. Please complete previous steps first.'})
    
    # Initialize agents for outline creation
    book_agents = BookAgents(agent_config)
    agents = book_agents.create_agents(world_theme, num_chapters)
    
    # Generate streaming response
    stream = book_agents.generate_chat_response_outline_stream(chat_history, world_theme, characters, user_message)
    
    def generate():
        # Send a heartbeat to establish the connection
        yield "data: {\"content\": \"\"}\n\n"
        
        # Iterate through the stream to get each chunk
        for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta and chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                # Send each token as it arrives
                yield f"data: {json.dumps({'content': content})}\n\n"
        
        # Send completion marker
        yield f"data: {json.dumps({'content': '[DONE]'})}\n\n"
    
    return Response(stream_with_context(generate()), 
                   mimetype='text/event-stream',
                   headers={
                       'Cache-Control': 'no-cache',
                       'X-Accel-Buffering': 'no'
                   })

@app.route('/finalize_outline_stream', methods=['POST'])
def finalize_outline_stream():
    """Finalize the outline based on chat history with streaming response"""
    data = request.json
    chat_history = data.get('chat_history', [])
    num_chapters = data.get('num_chapters', 10)
    
    # Get world_theme and characters for context
    world_theme = session.get('world_theme', '')
    characters = session.get('characters', '')
    
    # Ensure we have world and characters
    if not world_theme or not characters:
        # Try to load from files
        if os.path.exists('book_output/world.txt'):
            with open('book_output/world.txt', 'r') as f:
                world_theme = f.read().strip()
            session['world_theme'] = world_theme
        
        if os.path.exists('book_output/characters.txt'):
            with open('book_output/characters.txt', 'r') as f:
                characters = f.read().strip()
            session['characters'] = characters
            
        if not world_theme or not characters:
            return jsonify({'error': 'World theme or characters not found. Please complete previous steps first.'})
    
    # Initialize agents for outline creation
    book_agents = BookAgents(agent_config)
    agents = book_agents.create_agents(world_theme, num_chapters)
    
    # Generate the final outline using streaming
    stream = book_agents.generate_final_outline_stream(chat_history, world_theme, characters, num_chapters)
    
    def generate():
        # Send a heartbeat to establish the connection
        yield "data: {\"content\": \"\"}\n\n"
        
        # Collect all chunks to save the complete response
        collected_content = []
        
        # Iterate through the stream to get each chunk
        for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta and chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                collected_content.append(content)
                # Send each token as it arrives
                yield f"data: {json.dumps({'content': content})}\n\n"
        
        # Combine all chunks for the complete content
        complete_content = ''.join(collected_content)
        
        # Clean and save outline to session and file once streaming is complete
        outline_content = complete_content.strip()
        
        session['outline'] = outline_content
        
        # Save to file
        with open('book_output/outline.txt', 'w') as f:
            f.write(outline_content)
        
        # Try to parse chapters
        chapters = parse_outline_to_chapters(outline_content, num_chapters)
        session['chapters'] = chapters
        
        # Save structured outline for later use
        with open('book_output/chapters.json', 'w') as f:
            json.dump(chapters, f, indent=2)
        
        # Send completion marker
        yield f"data: {json.dumps({'content': '[DONE]'})}\n\n"
    
    return Response(stream_with_context(generate()), 
                   mimetype='text/event-stream',
                   headers={
                       'Cache-Control': 'no-cache',
                       'X-Accel-Buffering': 'no'
                   })

def parse_outline_to_chapters(outline_content, num_chapters):
    """Helper function to parse outline content into structured chapter format"""
    chapters = []
    try:
        # Extract just the outline content (between OUTLINE: and END OF OUTLINE)
        start_idx = outline_content.find('OUTLINE:')
        end_idx = outline_content.find('END OF OUTLINE')
        if start_idx != -1 and end_idx != -1:
            outline_text = outline_content[start_idx + len('OUTLINE:'):end_idx].strip()
        else:
            outline_text = outline_content
        
        seen_chapters = set()
        
        # First, handle range entries like "Chapters 10-19: Description"
        range_matches = re.finditer(r'Chapters\s+(\d+)\s*-\s*(\d+):\s+([^\n]+)', outline_text)
        for match in range_matches:
            start_num = int(match.group(1))
            end_num = int(match.group(2))
            range_description = match.group(3).strip()
            
            # Extract content for the range
            start_pos = match.start()
            next_chapter_match = re.search(r'Chapter[s]?\s+(\d+)', outline_text[start_pos + 1:])
            if next_chapter_match:
                end_pos = start_pos + 1 + next_chapter_match.start()
                range_content = outline_text[start_pos:end_pos].strip()
            else:
                range_content = outline_text[start_pos:].strip()
            
            # Create individual chapter entries for each chapter in the range
            for chapter_num in range(start_num, end_num + 1):
                if chapter_num not in seen_chapters:
                    seen_chapters.add(chapter_num)
                    chapters.append({
                        'chapter_number': chapter_num,
                        'title': f"Part {chapter_num}: {range_description}",
                        'prompt': range_content
                    })
        
        # Then, handle standard chapter entries "Chapter N: Title"
        chapter_matches = re.finditer(r'Chapter\s+(\d+):\s+([^\n]+)', outline_text)
        
        for match in chapter_matches:
            chapter_num = int(match.group(1))
            chapter_title = match.group(2).strip()
            
            # Skip duplicate chapter numbers
            if chapter_num in seen_chapters:
                continue
            
            seen_chapters.add(chapter_num)
            
            # Find the end of this chapter's content (start of next chapter or end of text)
            start_pos = match.start()
            next_chapter_match = re.search(r'Chapter[s]?\s+(\d+)', outline_text[start_pos + 1:])
            
            if next_chapter_match:
                end_pos = start_pos + 1 + next_chapter_match.start()
                chapter_content = outline_text[start_pos:end_pos].strip()
            else:
                chapter_content = outline_text[start_pos:].strip()
            
            # Extract just the content part, not including the chapter title line
            content_lines = chapter_content.split('\n')
            chapter_description = '\n'.join(content_lines[1:]) if len(content_lines) > 1 else ""
            
            chapters.append({
                'chapter_number': chapter_num,
                'title': chapter_title,
                'prompt': chapter_description
            })
        
        # Sort chapters by chapter number to ensure correct order
        chapters.sort(key=lambda x: x['chapter_number'])
        
        # Only use num_chapters as a fallback if no chapters are found
        if not chapters:
            print(f"No chapters found in outline, creating {num_chapters} default chapters")
            for i in range(1, num_chapters + 1):
                chapters.append({
                    'chapter_number': i,
                    'title': f"Chapter {i}",
                    'prompt': f"Content for chapter {i}"
                })
                
    except Exception as e:
        # Fallback if parsing fails
        print(f"Error parsing outline: {e}")
        for i in range(1, num_chapters + 1):
            chapters.append({
                'chapter_number': i,
                'title': f"Chapter {i}",
                'prompt': f"Content for chapter {i}"
            })
    
    # Print diagnostic info
    print(f"Found {len(chapters)} chapters in the outline")
    
    # Save to the correct filename
    with open('book_output/chapters.json', 'w') as f:
        json.dump(chapters, f, indent=2)
    
    return chapters


# ============================================================================
# PROJECT MANAGEMENT ROUTES
# ============================================================================

@app.route('/api/projects', methods=['GET'])
def list_projects():
    """Return list of saved projects as JSON."""
    return jsonify({'projects': _list_projects()})


@app.route('/api/projects/save', methods=['POST'])
def save_project():
    """Save current book_output/ as a named project snapshot."""
    data = request.json or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Project name is required'}), 400

    # Sanitise: only allow alphanumeric, spaces, hyphens, underscores
    safe_name = re.sub(r'[^\w\s\-]', '', name).strip().replace(' ', '_')
    if not safe_name:
        return jsonify({'error': 'Invalid project name'}), 400

    dest = os.path.join(PROJECTS_DIR, safe_name)
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(BOOK_OUTPUT_DIR, dest)

    # Write metadata
    topic = session.get('topic', '')
    chapter_count = 0
    chapters_file = os.path.join(BOOK_OUTPUT_DIR, 'chapters.json')
    if os.path.exists(chapters_file):
        try:
            with open(chapters_file) as f:
                chapter_count = len(json.load(f))
        except Exception:
            pass

    meta = {
        'name': safe_name,
        'display_name': name,
        'topic': topic,
        'chapter_count': chapter_count,
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat(),
    }
    # Preserve original created_at if updating an existing save
    existing_meta_path = os.path.join(dest, 'project.json')
    if os.path.exists(existing_meta_path):
        try:
            with open(existing_meta_path) as f:
                existing = json.load(f)
            meta['created_at'] = existing.get('created_at', meta['created_at'])
        except Exception:
            pass

    with open(os.path.join(dest, 'project.json'), 'w') as f:
        json.dump(meta, f, indent=2)

    session['project_name'] = safe_name
    return jsonify({'success': True, 'project': meta})


@app.route('/api/projects/load', methods=['POST'])
def load_project():
    """Load a saved project into book_output/ and restore Flask session."""
    data = request.json or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Project name is required'}), 400

    src = os.path.join(PROJECTS_DIR, name)
    if not os.path.exists(src):
        return jsonify({'error': f'Project "{name}" not found'}), 404

    # Replace book_output with the project snapshot (exclude project.json)
    if os.path.exists(BOOK_OUTPUT_DIR):
        shutil.rmtree(BOOK_OUTPUT_DIR)
    shutil.copytree(src, BOOK_OUTPUT_DIR, ignore=shutil.ignore_patterns('project.json'))
    os.makedirs(f'{BOOK_OUTPUT_DIR}/chapters', exist_ok=True)
    os.makedirs(f'{BOOK_OUTPUT_DIR}/states', exist_ok=True)

    _clear_session()

    # Restore session from project files
    meta = _project_meta(name)
    if meta.get('topic'):
        session['topic'] = meta['topic']

    world_file = os.path.join(BOOK_OUTPUT_DIR, 'world.txt')
    if os.path.exists(world_file):
        with open(world_file) as f:
            session['world_theme'] = f.read()

    chars_file = os.path.join(BOOK_OUTPUT_DIR, 'characters.txt')
    if os.path.exists(chars_file):
        with open(chars_file) as f:
            session['characters'] = f.read()

    outline_file = os.path.join(BOOK_OUTPUT_DIR, 'outline.txt')
    if os.path.exists(outline_file):
        with open(outline_file) as f:
            session['outline'] = f.read()

    chapters_file = os.path.join(BOOK_OUTPUT_DIR, 'chapters.json')
    if os.path.exists(chapters_file):
        try:
            with open(chapters_file) as f:
                session['chapters'] = json.load(f)
        except Exception:
            pass

    session['project_name'] = name
    return jsonify({'success': True, 'project': meta})


@app.route('/api/projects/new', methods=['POST'])
def new_project():
    """Clear current book data and session for a fresh project."""
    _clear_book_output()
    _clear_session()
    session.pop('project_name', None)
    return jsonify({'success': True})


@app.route('/api/projects/export', methods=['GET'])
def export_project():
    """Download current book_output/ as a ZIP archive."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(BOOK_OUTPUT_DIR):
            for fname in files:
                fpath = os.path.join(root, fname)
                arcname = os.path.relpath(fpath, BOOK_OUTPUT_DIR)
                zf.write(fpath, arcname)
    buf.seek(0)
    project_name = session.get('project_name', 'opentale_export')
    download_name = f"{project_name}.zip"
    return send_file(buf, mimetype='application/zip', as_attachment=True, download_name=download_name)


@app.route('/api/projects/import', methods=['POST'])
def import_project():
    """Accept a ZIP upload and extract it into book_output/."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    uploaded = request.files['file']
    if not uploaded.filename.endswith('.zip'):
        return jsonify({'error': 'Only .zip files are supported'}), 400

    try:
        with zipfile.ZipFile(uploaded.stream, 'r') as zf:
            # Safety check: reject paths that escape the target directory
            for member in zf.namelist():
                if member.startswith('/') or '..' in member:
                    return jsonify({'error': 'Invalid ZIP contents'}), 400
            if os.path.exists(BOOK_OUTPUT_DIR):
                shutil.rmtree(BOOK_OUTPUT_DIR)
            os.makedirs(BOOK_OUTPUT_DIR, exist_ok=True)
            zf.extractall(BOOK_OUTPUT_DIR)
    except zipfile.BadZipFile:
        return jsonify({'error': 'Invalid ZIP file'}), 400

    os.makedirs(f'{BOOK_OUTPUT_DIR}/chapters', exist_ok=True)
    os.makedirs(f'{BOOK_OUTPUT_DIR}/states', exist_ok=True)

    _clear_session()

    world_file = os.path.join(BOOK_OUTPUT_DIR, 'world.txt')
    if os.path.exists(world_file):
        with open(world_file) as f:
            session['world_theme'] = f.read()

    chars_file = os.path.join(BOOK_OUTPUT_DIR, 'characters.txt')
    if os.path.exists(chars_file):
        with open(chars_file) as f:
            session['characters'] = f.read()

    outline_file = os.path.join(BOOK_OUTPUT_DIR, 'outline.txt')
    if os.path.exists(outline_file):
        with open(outline_file) as f:
            session['outline'] = f.read()

    chapters_file = os.path.join(BOOK_OUTPUT_DIR, 'chapters.json')
    if os.path.exists(chapters_file):
        try:
            with open(chapters_file) as f:
                session['chapters'] = json.load(f)
        except Exception:
            pass

    session.pop('project_name', None)
    return jsonify({'success': True})


@app.route('/api/projects/<project_name>', methods=['DELETE'])
def delete_project(project_name):
    """Delete a saved project snapshot."""
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    if not os.path.exists(project_dir):
        return jsonify({'error': 'Project not found'}), 404
    shutil.rmtree(project_dir)
    return jsonify({'success': True})


if __name__ == '__main__':
    print("[OpenTale] Starting Flask server on http://0.0.0.0:5000", file=sys.stderr)
    app.run(host='0.0.0.0', debug=False, port=5000, use_reloader=False, threaded=True) 
