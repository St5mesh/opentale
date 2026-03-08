# Copilot Instructions for OpenTale

## Project Overview

OpenTale is a Flask web application that guides users through AI-assisted book writing. It uses local LLM models (via OpenAI-compatible APIs) to generate world settings, characters, outlines, and complete chapters through an iterative process.

## Setup & Running

### Development Setup
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Running the Application
1. Start your local AI model server (configured to serve on `http://localhost:1234/v1` by default)
2. Run the Flask app:
   ```bash
   python web_app.py
   ```
3. Access the web UI at `http://localhost:5000`

### Code Quality & Testing
```bash
# Linting
flake8 .

# Type checking
mypy .

# Code formatting
black .

# Run tests (when available)
pytest
```

## Architecture

### Core Components

**web_app.py** (Flask application)
- Main Flask server with routes for each book creation step
- Manages Flask sessions and persists user progress
- Handles both standard HTTP responses and Server-Sent Events (SSE) for streaming responses
- Routes follow the book workflow: `/`, `/world`, `/characters`, `/outline`, `/chapter`

**agents.py** (BookAgents class)
- Wraps OpenAI-compatible API calls
- Manages specialized agent system prompts (memory_keeper, world_architect, character_specialist, scene_generator, chapter_writer)
- Tracks context: book outline, character developments, world elements
- Provides methods for different generation stages: world building, character creation, outline, scenes, chapters
- Supports both non-streaming (`generate_chat_response`) and streaming (`generate_chat_response_stream`) responses

**config.py** (Configuration)
- Centralized LLM configuration
- Returns agent_config with model, base_url, api_key, temperature (0.7), seed (42), and timeout (600s)
- Currently hardcoded to use `gemma-3-12b-it` model via localhost:1234

**prompts.py** (Prompt templates)
- Contains all prompt templates used throughout the book generation process
- Templates include placeholders for context (world, characters, chapter info, etc.)
- Key templates: WORLD_THEME_PROMPT, CHARACTER_CREATION_PROMPT, OUTLINE_GENERATION_PROMPT, SCENE_GENERATION_PROMPT, CHAPTER_GENERATION_PROMPT

### Frontend

**templates/** (Jinja2 templates)
- `base.html` - Base template with navigation
- `index.html` - Home page with topic entry
- `world.html` - World building chat interface
- `characters.html` - Character generation interface
- `outline.html` - Outline display and management
- `scene.html` - Scene generation interface
- `chapter.html` - Full chapter generation and editing

**static/** (Frontend assets)
- `scripts.js` - Client-side logic for form submission, streaming responses, and session management
- `styles.css` - Application styling

### Data Persistence

Generated content is stored in `book_output/` directory:
- `world.txt` - World setting description
- `characters.txt` - Character profiles
- `outline.txt` - Full outline text
- `outline.json` - Structured outline data
- `chapters/chapter_N.txt` - Individual chapter content
- `chapters/chapter_N_scenes/scene_M.txt` - Individual scene content

## Key Conventions

### Agent Interaction Pattern
- All AI interactions use `BookAgents` class
- Agents are initialized with `agent_config` from `config.py`
- Context (outline, previous chapters) is passed to agents to maintain narrative consistency
- Memory tracking is built into the `memory_keeper` agent system prompt

### Response Handling
- Streaming responses use Server-Sent Events (SSE) format: `data: {json}\n\n`
- Non-streaming responses return JSON: `{"message": "content"}`
- Client-side JavaScript handles streaming response parsing and DOM updates

### File Storage
- All file I/O uses relative paths from project root
- File existence checks determine whether to load existing content (e.g., `os.path.exists('book_output/world.txt')`)
- Content is written to disk after generation (not shown in code snippets but follow this pattern)

### Session Management
- Flask session stores `topic`, `world_theme`, and other progress state
- Session data is checked on page load to determine what content to display
- Client-side state (chat history) is maintained in JavaScript and sent to server on requests

## Workflow

The user experience follows a linear workflow:

1. **Home** - Enter book topic
2. **World** - Chat-based world building with AI
3. **Characters** - Generate character profiles based on the world
4. **Outline** - Generate chapter outline
5. **Chapter** - Iteratively generate and edit chapters
   - Generate scenes for a chapter
   - Generate full chapter content
   - Edit content
   - Move to next chapter

Each step builds on the previous steps, with context being passed to maintain consistency.
