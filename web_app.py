"""
Flask web application for OpenTale
"""
import os
import json
import sys
from flask import Flask, render_template, request, jsonify, session, Response, stream_with_context, flash, redirect
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

# Initialize global variables
agent_config = get_config()
narrative_config = get_narrative_config()

# Startup logging
print("[OpenTale] Flask app initializing...", file=sys.stderr)
print(f"[OpenTale] LLM URL: {agent_config.get('base_url', 'http://ollama:11434/v1')}", file=sys.stderr)


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
    
    return render_template('world.html', world_theme=world_theme, topic=session.get('topic', ''))

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
    
    data = request.json
    topic = data.get('topic', session.get('topic', ''))
    
    # Load world theme from file or session
    world_theme = ''
    if os.path.exists('book_output/world.txt'):
        with open('book_output/world.txt', 'r') as f:
            world_theme = f.read().strip()
    else:
        world_theme = session.get('world_theme', '')
    
    if not world_theme:
        return jsonify({'error': 'World theme not available'}), 400
    
    try:
        book_agents = BookAgents(agent_config)
        theme_data = book_agents.extract_theme(topic, world_theme)
        
        # Save theme to file
        theme_file_data = StoryState.initialize_theme()
        StoryState.set_theme(
            theme_file_data,
            theme_data.get('theme_statement', ''),
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
        return jsonify({'error': str(e)}), 500

@app.route('/plan_scene_chain', methods=['POST'])
def plan_scene_chain():
    """Plan scene chain from outline (if feature enabled)"""
    if not narrative_config.get('scene_chain_enabled', True):
        return jsonify({'error': 'Scene chain planning not enabled'}), 400
    
    data = request.json
    
    # Load outline from file
    if not os.path.exists('book_output/outline.txt'):
        return jsonify({'error': 'Outline not available'}), 400
    
    with open('book_output/outline.txt', 'r') as f:
        outline = f.read().strip()
    
    try:
        book_agents = BookAgents(agent_config)
        book_agents.create_agents("", 10)  # Initialize agents with empty prompt and default chapters
        scenes = book_agents.plan_scene_chain(outline)
        
        # Save scene chain to file
        chain_data = StoryState.initialize_scene_chain()
        for scene in scenes:
            StoryState.add_scene_to_chain(chain_data, scene)
        StoryState.save_scene_chain(chain_data)
        
        session['scene_chain'] = scenes
        
        return jsonify({
            'success': True,
            'total_scenes': len(scenes),
            'scenes': scenes[:5]  # Return preview of first 5 scenes
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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

@app.route('/finalize_outline_with_states', methods=['POST'])
def finalize_outline_with_states():
    """
    Finalize outline and generate initial story states (Phase 1, Stage 1).
    
    This endpoint:
    1. Takes the current outline, characters, and world
    2. Extracts initial character states
    3. Extracts artifact states
    4. Extracts world element states
    5. Extracts theme
    6. Extracts character arcs
    7. Saves all to story state files
    
    Returns: JSON with success/error and extracted state summary
    """
    try:
        # Get required files
        if not os.path.exists('book_output/outline.txt'):
            return jsonify({'error': 'Outline not found'}), 400
        if not os.path.exists('book_output/characters.txt'):
            return jsonify({'error': 'Characters not found'}), 400
        if not os.path.exists('book_output/world.txt'):
            return jsonify({'error': 'World not found'}), 400
        
        # Load content
        with open('book_output/outline.txt', 'r') as f:
            outline = f.read()
        with open('book_output/characters.txt', 'r') as f:
            characters = f.read()
        with open('book_output/world.txt', 'r') as f:
            world_theme = f.read()
        
        # Initialize BookAgents for extraction
        book_agents = BookAgents(agent_config)
        book_agents.create_agents('', 10)
        
        # Extract all story elements (in parallel would be better, but doing sequentially for now)
        extracted_chars = book_agents.extract_character_initial_states(characters, "Story theme")
        extracted_artifacts = book_agents.extract_artifacts_from_world(world_theme, characters)
        extracted_world = book_agents.extract_world_elements(world_theme, outline)
        extracted_theme = book_agents.extract_theme_from_outline(outline)
        extracted_arcs = book_agents.extract_character_arcs(outline, characters)
        
        # Combine all extractions
        all_extracted = {
            **extracted_chars,
            **extracted_artifacts,
            **extracted_world,
            **extracted_theme,
            **extracted_arcs
        }
        
        # Initialize and apply to story state
        story_state = StoryState.initialize_story_state()
        story_state = StoryState.apply_extracted_changes(story_state, all_extracted, source="outline_finalization")
        
        # Save story state
        StoryState.save_story_state(story_state)
        
        # Save character arcs if extracted
        if "character_arcs" in all_extracted:
            arcs_data = StoryState.initialize_character_arcs()
            for arc in all_extracted["character_arcs"]:
                StoryState.add_character_arc(
                    arcs_data,
                    arc.get("name", "Unknown"),
                    arc.get("arc_stages", [])
                )
            StoryState.save_character_arcs(arcs_data)
        
        # Save theme if extracted
        if "theme" in all_extracted and all_extracted["theme"]:
            theme_data = StoryState.initialize_theme()
            theme_info = all_extracted["theme"]
            StoryState.set_theme(
                theme_data,
                theme_info.get("statement", ""),
                theme_info.get("core_conflict", ""),
                theme_info.get("moral_tension", "")
            )
            StoryState.save_theme(theme_data)
        
        return jsonify({
            'success': True,
            'message': 'Outline finalized and initial states generated',
            'extracted': {
                'characters': len(all_extracted.get('characters', [])),
                'artifacts': len(all_extracted.get('artifacts', [])),
                'world_elements': len(all_extracted.get('world_elements', [])),
                'has_theme': bool(all_extracted.get('theme')),
                'has_arcs': bool(all_extracted.get('character_arcs'))
            }
        })
    
    except Exception as e:
        print(f"Error finalizing outline with states: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to finalize outline: {str(e)}'}), 500

@app.route('/generate_chapter_scene_chain/<int:chapter_number>', methods=['POST'])
def generate_chapter_scene_chain(chapter_number):
    """
    Generate per-chapter scene chain on-demand (Phase 2, Stage 2).
    
    This is called when a user opens a chapter for editing. It:
    1. Loads current story state
    2. Loads the chapter outline
    3. Generates a contextual scene chain for that chapter
    4. Saves the scene chain
    
    Returns: JSON with scene chain or error
    """
    try:
        # Load current story state
        story_state = StoryState.load_story_state()
        state_summary = StoryState.get_full_state_summary(story_state)
        
        # Load chapters to get this chapter's outline
        if not os.path.exists('book_output/chapters.json'):
            return jsonify({'error': 'No chapters found'}), 400
        
        with open('book_output/chapters.json', 'r') as f:
            chapters = json.load(f)
        
        # Find the chapter
        chapter_data = None
        for ch in chapters:
            if ch['chapter_number'] == chapter_number:
                chapter_data = ch
                break
        
        if not chapter_data:
            return jsonify({'error': f'Chapter {chapter_number} not found'}), 404
        
        # Initialize BookAgents for scene chain planning
        book_agents = BookAgents(agent_config)
        book_agents.create_agents('', 10)
        
        # Generate scene chain for this chapter
        scene_chain = book_agents.plan_chapter_scene_chain(
            chapter_number,
            chapter_data['prompt'],  # The chapter outline
            state_summary
        )
        
        # Save scene chain to file
        scene_chain_file = f'book_output/chapter_{chapter_number}_scene_chain.json'
        with open(scene_chain_file, 'w') as f:
            json.dump(scene_chain, f, indent=2)
        
        return jsonify({
            'success': True,
            'chapter': chapter_number,
            'scenes': scene_chain.get('scenes', []),
            'scene_count': len(scene_chain.get('scenes', []))
        })
    
    except Exception as e:
        print(f"Error generating scene chain for chapter {chapter_number}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to generate scene chain: {str(e)}'}), 500

@app.route('/chapter/<int:chapter_number>', methods=['GET', 'POST'])
def chapter(chapter_number):
    """Generate or display a specific chapter"""
    chapters = []
    
    # Always load from disk first to get latest outline
    if os.path.exists('book_output/chapters.json'):
        with open('book_output/chapters.json', 'r') as f:
            chapters = json.load(f)
            session['chapters'] = chapters
    # Fall back to session if disk doesn't exist
    elif session.get('chapters'):
        chapters = session.get('chapters', [])
    
    # Check if chapter exists
    chapter_data = None
    for ch in chapters:
        if ch['chapter_number'] == chapter_number:
            chapter_data = ch
            break
    
    if not chapter_data:
        return render_template('error.html', message=f"Chapter {chapter_number} not found")
    
    if request.method == 'POST':
        # Get any additional context from the chat interface
        additional_context = request.form.get('additional_context', '')
        
        # Generate chapter content
        world_theme = session.get('world_theme', '')
        if not world_theme and os.path.exists('book_output/world.txt'):
            with open('book_output/world.txt', 'r') as f:
                world_theme = f.read().strip()
                session['world_theme'] = world_theme
                
        characters = session.get('characters', '')
        if not characters and os.path.exists('book_output/characters.txt'):
            with open('book_output/characters.txt', 'r') as f:
                characters = f.read().strip()
                session['characters'] = characters
                
        outline = session.get('outline', '')
        if not outline and os.path.exists('book_output/outline.txt'):
            with open('book_output/outline.txt', 'r') as f:
                outline = f.read().strip()
                session['outline'] = outline
        
        # Get previous chapters context
        previous_context = ""
        if chapter_number > 1:
            prev_chapter_path = f'book_output/chapters/chapter_{chapter_number-1}.txt'
            if os.path.exists(prev_chapter_path):
                with open(prev_chapter_path, 'r') as f:
                    # Get a summary or the last few paragraphs
                    content = f.read()
                    previous_context = content[-1000:] if len(content) > 1000 else content
        
        # Initialize agents for chapter generation
        book_agents = BookAgents(agent_config, chapters)
        agents = book_agents.create_agents(world_theme, len(chapters))
        
        # Add the additional context from chat to the chapter prompt
        chapter_prompt = f"{chapter_data['prompt']}\n\n{additional_context}" if additional_context else chapter_data['prompt']
        
        # Generate the chapter
        chapter_content = book_agents.generate_content(
            "writer",
            prompts.CHAPTER_GENERATION_PROMPT.format(
                chapter_number=chapter_number,
                chapter_title=chapter_data['title'],
                chapter_outline=chapter_prompt,
                world_theme=world_theme,
                relevant_characters=characters,  # You might want to filter for relevant characters only
                scene_details="",  # This would be filled if scenes were generated first
                previous_context=previous_context
            )
        )
        
        # Clean and save chapter content
        chapter_content = chapter_content.strip()
        chapter_path = f'book_output/chapters/chapter_{chapter_number}.txt'
        with open(chapter_path, 'w') as f:
            f.write(chapter_content)
        
        return jsonify({'chapter_content': chapter_content})
    
    # GET request - show chapter page with existing content if available
    chapter_content = ''
    chapter_path = f'book_output/chapters/chapter_{chapter_number}.txt'
    if os.path.exists(chapter_path):
        with open(chapter_path, 'r') as f:
            chapter_content = f.read().strip()
    
    return render_template('chapter.html', 
                           chapter=chapter_data,
                           chapter_content=chapter_content,
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
        
        # Initialize agents
        book_agents = BookAgents(agent_config, chapters)
        agents = book_agents.create_agents(world_theme, len(chapters) if chapters else 1)
        
        # Generate the scene
        scene_content = book_agents.generate_content(
            "writer",
            prompts.SCENE_GENERATION_PROMPT.format(
                chapter_number=chapter_number,
                chapter_title=chapter_data.get('title', f"Chapter {chapter_number}"),
                chapter_outline=chapter_data.get('prompt', ""),
                world_theme=world_theme,
                relevant_characters=characters,
                previous_context=previous_context
            )
        )
        
        # Save scene to a file
        scene_dir = f'book_output/chapters/chapter_{chapter_number}_scenes'
        os.makedirs(scene_dir, exist_ok=True)
        
        # Count existing scenes and create a new one
        scene_count = len([f for f in os.listdir(scene_dir) if f.endswith('.txt')])
        scene_path = f'{scene_dir}/scene_{scene_count + 1}.txt'
        
        with open(scene_path, 'w') as f:
            f.write(scene_content)
        
        # [PHASE 3] Extract state changes from the generated scene
        try:
            story_state = StoryState.load_story_state()
            state_summary = StoryState.get_full_state_summary(story_state)
            
            # Extract state changes from scene
            state_changes = book_agents.extract_scene_state_changes(scene_content, state_summary)
            
            # Apply extracted changes to story state
            if state_changes and (state_changes.get('characters') or state_changes.get('artifacts') or state_changes.get('world')):
                story_state = StoryState.apply_extracted_changes(
                    story_state,
                    state_changes,
                    source=f"scene_{chapter_number}_{scene_count + 1}"
                )
                StoryState.save_story_state(story_state)
                print(f"Applied state changes from scene {scene_count + 1}")
        except Exception as e:
            print(f"Warning: Failed to extract state changes from scene: {e}")
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

if __name__ == '__main__':
    print("[OpenTale] Starting Flask server on http://0.0.0.0:5000", file=sys.stderr)
    app.run(host='0.0.0.0', debug=False, port=5000, use_reloader=False, threaded=True) 