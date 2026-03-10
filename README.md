# AI Book Writer

A web-based application that guides you through the process of writing a book with AI assistance. The system uses local AI models to help generate world settings, characters, outlines, and complete chapters.

## Features

- Web-based user interface with no authentication required
- Step-by-step guided book writing process
- Real-time AI generation of:
  - World settings and environments
  - Character profiles and development
  - Book outlines with chapter structure
  - Scene generation for individual chapters
  - Full chapter content
- Local AI model support (compatible with your existing config)
- Progress tracking
- Ability to edit and save generated content
- All content stored in local files for easy access

## Architecture

The application consists of:

- **Flask Web Server**: Provides the user interface and manages the book generation process
- **AI Agents**: Specialized agents for different aspects of book creation:
  - Story planning
  - World building
  - Character development
  - Scene creation
  - Writing and editing
- **Prompt Management**: Centralized prompt templates in `prompts.py`
- **File Storage**: Local storage of all generated content in the `book_output` directory

## Documentation Layout

The project documentation now lives under `docs/` to keep the root focused on runnable code.  
`docs/current/` contains the authoritative architecture, implementation, Docker, and workflow references (e.g., `ARCHITECTURE_DESIGN.md`, `IMPLEMENTATION_SUMMARY.md`, `DOCKER.md`, `SCENE_ANALYSIS_WORKFLOW.txt`), while `docs/legacy/` retains older findings, migration notes, and stability write-ups for auditing.

## Testing

The automated test suites live in the dedicated `tests/` package so the root directory stays uncluttered.  
Run `python3 -m pytest tests/test_coherence_validation.py tests/integration_tests.py tests/test_phase5_validation.py` for the main validation pipelines and use `python3 tests/integration_tests.py` or `python3 tests/end_to_end_generation_test.py` for the longer integration/end-to-end scripts.

## Installation

### Option 1: Docker (Recommended - includes LLM server)

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ai-book-writer.git
cd ai-book-writer
```

2. Start with Docker Compose:
```bash
docker-compose up
```

3. Access the app at `http://localhost:5000`

**That's it!** Docker Compose automatically:
- Starts Ollama LLM server
- Downloads and loads a model
- Launches the Flask app
- Creates persistent volumes for your work

For more details, see [docs/current/DOCKER.md](docs/current/DOCKER.md)

### Option 2: Manual Installation (Local Python)

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ai-book-writer.git
cd ai-book-writer
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Quick Start (Docker)

If you used Docker Compose installation:

```bash
docker-compose up
```

Then open your browser to `http://localhost:5000`

See [docs/current/DOCKER.md](docs/current/DOCKER.md) for Docker commands and troubleshooting.

### Quick Start (Manual Installation)

If you used manual Python installation:

1. **Configure your LLM server** (see [Configuration](#configuration) section)

2. **Start the local AI model server** (e.g., LM Studio, Ollama, text-generation-webui)
   - Ensure a model is loaded and the server is running
   - Default expects: `http://localhost:1234/v1`

3. **Run the Flask application**:
```bash
python web_app.py
```
You should see: `* Running on http://127.0.0.1:5000`

4. **Open your browser** and navigate to:
```
http://localhost:5000
```

5. **Follow the step-by-step process**:
    - **World Building**: Describe your story's setting and world
    - **Characters**: Generate main characters for your world
    - **Outline**: Create a chapter-by-chapter outline
    - **Chapter Writing**: Generate scenes and full chapters iteratively
    - **Editing**: Refine and save your content locally

## Book Writing Workflow

The application guides you through a logical book creation process:

1. **World Building**: Define the setting, time period, and environment for your story
2. **Character Creation**: Generate the main characters for your book
3. **Outline Generation**: Create a chapter-by-chapter outline of your story
4. **Chapter Writing**:
   - Generate individual scenes for a chapter
   - Generate a complete chapter
   - Edit and save your chapters
   - Proceed to the next chapter

## Output Structure

All generated content is saved in the `book_output` directory:
```
book_output/
├── world.txt                # World setting
├── characters.txt           # Character profiles
├── outline.txt              # Full book outline
├── outline.json             # Structured outline data
├── chapters/
│   ├── chapter_1.txt
│   ├── chapter_2.txt
│   └── ...
│   └── chapter_1_scenes/    # Generated scenes for chapters
│       ├── scene_1.txt
│       └── ...
```

## Requirements

- Python 3.8+
- Flask 2.2.0+
- AutoGen 0.2.0+
- Local AI model (as configured in your existing `config.py`)
- Other dependencies listed in requirements.txt

## Configuration

### Prerequisites: Setting up a Local AI Model Server

This application requires a local LLM (Large Language Model) server running before you start the Flask app. The server must provide an OpenAI-compatible API endpoint.

**Choose one of the following options:**

#### Option 1: LM Studio (Recommended for beginners)
1. Download LM Studio from [lmstudio.ai](https://lmstudio.ai)
2. Install and launch the application
3. Go to the "Local Server" tab
4. Select a model (e.g., `gemma-3-12b-it` to match defaults)
5. Click "Start Server"
6. Server will run on `http://localhost:1234/v1` (default)

#### Option 2: Ollama
1. Download Ollama from [ollama.ai](https://ollama.ai)
2. Install and run `ollama serve` in a terminal
3. In another terminal, pull a model: `ollama pull gemma:latest`
4. Server runs on `http://localhost:11434/v1` by default

#### Option 3: text-generation-webui
1. Clone the repository: `git clone https://github.com/oobabooga/text-generation-webui`
2. Follow their setup instructions
3. Run with OpenAI API enabled: `python server.py --openai-api`
4. Server typically runs on `http://localhost:5000/v1`

---

### Configuring `config.py`

Edit `config.py` to match your local model server settings:

```python
"""Configuration for the book generation system"""
import os
from typing import Dict, List

def get_config(local_url: str = "http://localhost:1234/v1") -> Dict:
    """Get the configuration for the agents
    
    Args:
        local_url: The base URL of your local LLM server's OpenAI-compatible API endpoint
    """
    
    # Basic config for local LLM
    config_list = [{
        'model': 'gemma-3-12b-it',        # Model name as shown in your LLM server
        'base_url': local_url,             # URL of your LLM server (e.g., http://localhost:1234/v1)
        'api_key': "not-needed"            # Can be any value; local servers typically don't need real keys
    }]

    # Common configuration for all agents
    agent_config = {
        "seed": 42,                        # Random seed for reproducibility
        "temperature": 0.7,                # 0.0 = deterministic, 1.0 = creative (0.5-0.8 recommended for writing)
        "config_list": config_list,
        "timeout": 600,                    # Timeout in seconds (600 = 10 minutes per request)
        "cache_seed": None
    }
    
    return agent_config
```

#### Configuration Examples

**Example 1: Using LM Studio (default)**
- No changes needed! LM Studio runs on `http://localhost:1234/v1` by default
- Ensure you've selected `gemma-3-12b-it` (or similar) in LM Studio and started the server

**Example 2: Using Ollama with a different model**
```python
def get_config(local_url: str = "http://localhost:11434/v1") -> Dict:
    config_list = [{
        'model': 'gemma:latest',           # Use your Ollama model name here
        'base_url': local_url,
        'api_key': "not-needed"
    }]
    # ... rest of config
```

**Example 3: Using text-generation-webui on a different port**
```python
def get_config(local_url: str = "http://localhost:8000/v1") -> Dict:
    config_list = [{
        'model': 'your-model-name',        # Your model name from webui
        'base_url': local_url,
        'api_key': "not-needed"
    }]
    # ... rest of config
```

**Example 4: Remote server (not localhost)**
```python
def get_config(local_url: str = "http://192.168.1.100:1234/v1") -> Dict:
    config_list = [{
        'model': 'gemma-3-12b-it',
        'base_url': local_url,
        'api_key': "not-needed"
    }]
    # ... rest of config
```

#### Configuration Parameters Explained

| Parameter | Purpose | Default | Notes |
|-----------|---------|---------|-------|
| `base_url` | LLM server API endpoint | `http://localhost:1234/v1` | Must end with `/v1` for OpenAI compatibility |
| `model` | Model identifier | `gemma-3-12b-it` | Must match a model available on your server |
| `temperature` | Output creativity | `0.7` | Lower (0.3-0.5) = focused, Higher (0.8-1.0) = creative |
| `seed` | Reproducibility | `42` | Same seed + temp produces consistent results |
| `timeout` | Request timeout | `600` seconds | Increase if generations are timing out on slower hardware |

#### Finding Your Server Settings

**How to find the correct `base_url`:**
1. Start your LLM server
2. Look for a message like: "Server running on http://localhost:XXXX"
3. The API endpoint is typically: `http://localhost:XXXX/v1`

**How to find the correct `model` name:**
- **LM Studio**: See the model name in the "Local Server" tab
- **Ollama**: Run `ollama list` to see available models
- **text-generation-webui**: Check your loaded model in the UI

---

### Optional: Customizing Prompts

You can also fine-tune generation behavior by editing `prompts.py`:
- Modify prompt templates to change how the AI approaches world-building, character creation, etc.
- All prompt templates are defined as strings with `{placeholders}` for context insertion

---

### Troubleshooting Connection Issues

**Error: "Connection refused" or "Network error"**
- Verify your LLM server is actually running
- Check that the `base_url` in `config.py` matches your server's actual address
- Ensure the URL ends with `/v1`

**Error: "Model not found" or "Invalid model"**
- The model name in `config.py` doesn't exist on your server
- Check your server UI to see available models
- Verify you've downloaded/pulled the model in your LLM server

**Timeout errors**
- Your hardware is too slow for the model
- Try a smaller model (e.g., `mistral-7b` instead of `gemma-3-12b-it`)
- Increase `timeout` in `config.py` to `900` or `1200` seconds

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
