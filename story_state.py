"""
Story state management and persistence for the narrative engine.

This module handles:
- Story state snapshots (character status, artifact status, world changes)
- Scene chain definitions and management
- Character arc tracking
- Theme storage and retrieval
"""

import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime


class StoryState:
    """Manages the persistent story state for a book project."""
    
    STATE_FILE = 'book_output/story_state.json'
    CHAIN_FILE = 'book_output/scene_chain.json'
    ARCS_FILE = 'book_output/character_arcs.json'
    THEME_FILE = 'book_output/theme.json'
    
    @staticmethod
    def initialize_story_state() -> Dict[str, Any]:
        """Create an empty story state structure."""
        return {
            'theme': None,
            'characters': {},  # character_name -> {status, developments}
            'artifacts': {},   # artifact_name -> {status, location, owner}
            'world': {},       # world_element -> {status, details}
            'scenes': [],      # list of scene snapshots
            'plot_progress': {
                'current_chapter': 0,
                'current_scene': 0,
                'completed_scenes': 0
            }
        }
    
    @staticmethod
    def initialize_scene_chain() -> Dict[str, Any]:
        """Create an empty scene chain structure."""
        return {
            'version': '1.0',
            'total_scenes': 0,
            'scenes': [],  # list of scene definitions
            'created_at': datetime.now().isoformat(),
            'approved': False
        }
    
    @staticmethod
    def initialize_character_arcs() -> Dict[str, Any]:
        """Create an empty character arcs structure."""
        return {
            'characters': {}  # character_name -> {arc_stages: [...], current_stage: 0}
        }
    
    @staticmethod
    def initialize_theme() -> Dict[str, Any]:
        """Create an empty theme structure."""
        return {
            'theme_statement': None,
            'core_conflict': None,
            'moral_tension': None,
            'extracted_at': None,
            'approved': False
        }
    
    @staticmethod
    def load_story_state() -> Dict[str, Any]:
        """Load story state from file, or create new if doesn't exist."""
        if os.path.exists(StoryState.STATE_FILE):
            with open(StoryState.STATE_FILE, 'r') as f:
                return json.load(f)
        return StoryState.initialize_story_state()
    
    @staticmethod
    def save_story_state(state: Dict[str, Any]) -> None:
        """Save story state to file."""
        os.makedirs('book_output', exist_ok=True)
        with open(StoryState.STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    
    @staticmethod
    def load_scene_chain() -> Dict[str, Any]:
        """Load scene chain from file, or create new if doesn't exist."""
        if os.path.exists(StoryState.CHAIN_FILE):
            with open(StoryState.CHAIN_FILE, 'r') as f:
                return json.load(f)
        return StoryState.initialize_scene_chain()
    
    @staticmethod
    def save_scene_chain(chain: Dict[str, Any]) -> None:
        """Save scene chain to file."""
        os.makedirs('book_output', exist_ok=True)
        with open(StoryState.CHAIN_FILE, 'w') as f:
            json.dump(chain, f, indent=2)
    
    @staticmethod
    def load_character_arcs() -> Dict[str, Any]:
        """Load character arcs from file, or create new if doesn't exist."""
        if os.path.exists(StoryState.ARCS_FILE):
            with open(StoryState.ARCS_FILE, 'r') as f:
                return json.load(f)
        return StoryState.initialize_character_arcs()
    
    @staticmethod
    def save_character_arcs(arcs: Dict[str, Any]) -> None:
        """Save character arcs to file."""
        os.makedirs('book_output', exist_ok=True)
        with open(StoryState.ARCS_FILE, 'w') as f:
            json.dump(arcs, f, indent=2)
    
    @staticmethod
    def load_theme() -> Dict[str, Any]:
        """Load theme from file, or create new if doesn't exist."""
        if os.path.exists(StoryState.THEME_FILE):
            with open(StoryState.THEME_FILE, 'r') as f:
                return json.load(f)
        return StoryState.initialize_theme()
    
    @staticmethod
    def save_theme(theme: Dict[str, Any]) -> None:
        """Save theme to file."""
        os.makedirs('book_output', exist_ok=True)
        with open(StoryState.THEME_FILE, 'w') as f:
            json.dump(theme, f, indent=2)
    
    @staticmethod
    def add_character_state(state: Dict[str, Any], character_name: str, 
                           status: str, developments: List[str] = None) -> None:
        """Add or update character state in story state."""
        if developments is None:
            developments = []
        state['characters'][character_name] = {
            'status': status,
            'developments': developments,
            'last_updated': datetime.now().isoformat()
        }
    
    @staticmethod
    def add_artifact_state(state: Dict[str, Any], artifact_name: str,
                          status: str, location: str = None, owner: str = None) -> None:
        """Add or update artifact state in story state."""
        state['artifacts'][artifact_name] = {
            'status': status,
            'location': location,
            'owner': owner,
            'last_updated': datetime.now().isoformat()
        }
    
    @staticmethod
    def add_world_state(state: Dict[str, Any], element_name: str,
                       status: str, details: str = None) -> None:
        """Add or update world element state in story state."""
        state['world'][element_name] = {
            'status': status,
            'details': details,
            'last_updated': datetime.now().isoformat()
        }
    
    @staticmethod
    def create_scene_snapshot(scene_num: int, scene_content: str, state_after: Dict[str, Any]) -> Dict[str, Any]:
        """Create a scene snapshot that captures state after scene generation."""
        return {
            'scene_number': scene_num,
            'generated_at': datetime.now().isoformat(),
            'character_states': state_after.get('characters', {}),
            'artifact_states': state_after.get('artifacts', {}),
            'world_states': state_after.get('world', {}),
            'preview': scene_content[:200] + '...' if len(scene_content) > 200 else scene_content
        }
    
    @staticmethod
    def add_scene_to_state(state: Dict[str, Any], scene_snapshot: Dict[str, Any]) -> None:
        """Add scene snapshot to story state."""
        state['scenes'].append(scene_snapshot)
        state['plot_progress']['completed_scenes'] = len(state['scenes'])
    
    @staticmethod
    def create_scene_chain_entry(scene_num: int, title: str, goal: str,
                                 conflict: str, outcome: str, consequence: str,
                                 next_trigger: str) -> Dict[str, Any]:
        """Create a single scene chain entry."""
        return {
            'scene_number': scene_num,
            'title': title,
            'goal': goal,
            'conflict': conflict,
            'outcome': outcome,
            'consequence': consequence,
            'next_trigger': next_trigger,
            'status': 'planned'  # planned, in_progress, completed
        }
    
    @staticmethod
    def add_scene_to_chain(chain: Dict[str, Any], scene_entry: Dict[str, Any]) -> None:
        """Add scene entry to scene chain."""
        chain['scenes'].append(scene_entry)
        chain['total_scenes'] = len(chain['scenes'])
    
    @staticmethod
    def add_character_arc(arcs: Dict[str, Any], character_name: str,
                         arc_stages: List[str]) -> None:
        """Add or update character arc stages."""
        arcs['characters'][character_name] = {
            'arc_stages': arc_stages,
            'current_stage': 0,
            'stage_reached_at': []  # list of scene numbers where each stage was reached
        }
    
    @staticmethod
    def advance_character_stage(arcs: Dict[str, Any], character_name: str,
                               scene_num: int) -> bool:
        """Advance character to next arc stage. Returns True if stage advanced."""
        if character_name not in arcs['characters']:
            return False
        
        char_arc = arcs['characters'][character_name]
        stages = char_arc['arc_stages']
        current = char_arc['current_stage']
        
        if current < len(stages) - 1:
            char_arc['current_stage'] = current + 1
            char_arc['stage_reached_at'].append(scene_num)
            return True
        return False
    
    @staticmethod
    def set_theme(theme: Dict[str, Any], statement: str, core_conflict: str,
                  moral_tension: str) -> None:
        """Set theme properties."""
        theme['theme_statement'] = statement
        theme['core_conflict'] = core_conflict
        theme['moral_tension'] = moral_tension
        theme['extracted_at'] = datetime.now().isoformat()
    
    @staticmethod
    def get_character_state_summary(state: Dict[str, Any]) -> str:
        """Generate a text summary of all character states for use in prompts."""
        lines = ["## Current Character States"]
        for char_name, char_info in state.get('characters', {}).items():
            lines.append(f"\n**{char_name}**")
            lines.append(f"  - Status: {char_info.get('status', 'unknown')}")
            if char_info.get('developments'):
                for dev in char_info['developments']:
                    lines.append(f"    - {dev}")
        return "\n".join(lines)
    
    @staticmethod
    def get_artifact_state_summary(state: Dict[str, Any]) -> str:
        """Generate a text summary of all artifact states for use in prompts."""
        lines = ["## Current Artifact States"]
        for artifact_name, artifact_info in state.get('artifacts', {}).items():
            lines.append(f"\n**{artifact_name}**")
            lines.append(f"  - Status: {artifact_info.get('status', 'unknown')}")
            lines.append(f"  - Location: {artifact_info.get('location', 'unknown')}")
            if artifact_info.get('owner'):
                lines.append(f"  - Owner: {artifact_info['owner']}")
        return "\n".join(lines)
    
    @staticmethod
    def get_world_state_summary(state: Dict[str, Any]) -> str:
        """Generate a text summary of all world states for use in prompts."""
        lines = ["## Current World States"]
        for element_name, element_info in state.get('world', {}).items():
            lines.append(f"\n**{element_name}**")
            lines.append(f"  - Status: {element_info.get('status', 'unknown')}")
            if element_info.get('details'):
                lines.append(f"  - Details: {element_info['details']}")
        return "\n".join(lines)
    
    @staticmethod
    def get_full_state_summary(state: Dict[str, Any]) -> str:
        """Generate a complete text summary of story state for use in prompts."""
        sections = []
        
        if state.get('characters'):
            sections.append(StoryState.get_character_state_summary(state))
        
        if state.get('artifacts'):
            sections.append(StoryState.get_artifact_state_summary(state))
        
        if state.get('world'):
            sections.append(StoryState.get_world_state_summary(state))
        
        return "\n\n".join(sections) if sections else "No story state recorded yet."
