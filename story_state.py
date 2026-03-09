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
            'statement': None,
            'core_conflict': None,
            'moral_tension': None,
            'extracted_at': None,
            'approved': False
        }
    
    @staticmethod
    def load_story_state() -> Dict[str, Any]:
        """Load story state from file, or create new if doesn't exist."""
        if not os.path.exists(StoryState.STATE_FILE):
            return StoryState.initialize_story_state()
        
        try:
            with open(StoryState.STATE_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # Corrupted or unreadable file; return default
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
        if not os.path.exists(StoryState.CHAIN_FILE):
            return StoryState.initialize_scene_chain()
        
        try:
            with open(StoryState.CHAIN_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
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
        if not os.path.exists(StoryState.ARCS_FILE):
            return StoryState.initialize_character_arcs()
        
        try:
            with open(StoryState.ARCS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
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
        if not os.path.exists(StoryState.THEME_FILE):
            return StoryState.initialize_theme()
        
        try:
            with open(StoryState.THEME_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return StoryState.initialize_theme()
    
    @staticmethod
    def save_theme(theme: Dict[str, Any]) -> None:
        """Save theme to file."""
        os.makedirs('book_output', exist_ok=True)
        with open(StoryState.THEME_FILE, 'w') as f:
            json.dump(theme, f, indent=2)
    
    @staticmethod
    def add_character_state(state: Dict[str, Any], character_name: str,
                            status: str, developments: List[str] = None,
                            location: str = None, companions: List[str] = None,
                            faction: str = None, goals: List[str] = None,
                            inventory: List[str] = None,
                            relationships: Dict[str, str] = None,
                            knowledge: List[str] = None,
                            abilities: List[str] = None) -> None:
        """Add or update character state in story state.

        Preserves existing extra fields when updating an existing entry so that
        a status-only update does not wipe location/goals/etc.
        """
        if developments is None:
            developments = []
        existing = state['characters'].get(character_name, {})
        state['characters'][character_name] = {
            'status': status,
            'developments': developments,
            'location': location if location is not None else existing.get('location'),
            'companions': companions if companions is not None else existing.get('companions', []),
            'faction': faction if faction is not None else existing.get('faction'),
            'goals': goals if goals is not None else existing.get('goals', []),
            'inventory': inventory if inventory is not None else existing.get('inventory', []),
            'relationships': relationships if relationships is not None else existing.get('relationships', {}),
            'knowledge': knowledge if knowledge is not None else existing.get('knowledge', []),
            'abilities': abilities if abilities is not None else existing.get('abilities', []),
            'last_updated': datetime.now().isoformat()
        }

    @staticmethod
    def add_artifact_state(state: Dict[str, Any], artifact_name: str,
                           status: str, location: str = None, owner: str = None,
                           is_location_known: bool = None, known_by: List[str] = None,
                           significance: str = None, properties: List[str] = None) -> None:
        """Add or update artifact state in story state."""
        existing = state['artifacts'].get(artifact_name, {})
        state['artifacts'][artifact_name] = {
            'status': status,
            'location': location if location is not None else existing.get('location'),
            'owner': owner if owner is not None else existing.get('owner'),
            'is_location_known': is_location_known if is_location_known is not None else existing.get('is_location_known', True),
            'known_by': known_by if known_by is not None else existing.get('known_by', []),
            'significance': significance if significance is not None else existing.get('significance'),
            'properties': properties if properties is not None else existing.get('properties', []),
            'last_updated': datetime.now().isoformat()
        }

    @staticmethod
    def add_world_state(state: Dict[str, Any], element_name: str,
                        status: str, details: str = None,
                        element_type: str = None, inhabitants: List[str] = None,
                        political_status: str = None, current_events: List[str] = None,
                        key_occupants: List[str] = None, trend: str = None,
                        public_opinion: str = None) -> None:
        """Add or update world element state in story state."""
        existing = state['world'].get(element_name, {})
        state['world'][element_name] = {
            'status': status,
            'details': details if details is not None else existing.get('details'),
            'type': element_type if element_type is not None else existing.get('type'),
            'inhabitants': inhabitants if inhabitants is not None else existing.get('inhabitants', []),
            'political_status': political_status if political_status is not None else existing.get('political_status'),
            'current_events': current_events if current_events is not None else existing.get('current_events', []),
            'key_occupants': key_occupants if key_occupants is not None else existing.get('key_occupants', []),
            'trend': trend if trend is not None else existing.get('trend'),
            'public_opinion': public_opinion if public_opinion is not None else existing.get('public_opinion'),
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
        theme['statement'] = statement
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
            if char_info.get('location'):
                lines.append(f"  - Location: {char_info['location']}")
            if char_info.get('faction'):
                lines.append(f"  - Faction: {char_info['faction']}")
            if char_info.get('companions'):
                lines.append(f"  - With: {', '.join(char_info['companions'])}")
            if char_info.get('goals'):
                lines.append(f"  - Goals: {'; '.join(char_info['goals'])}")
            if char_info.get('inventory'):
                lines.append(f"  - Carrying: {', '.join(char_info['inventory'])}")
            if char_info.get('relationships'):
                for other, rel in char_info['relationships'].items():
                    lines.append(f"  - {other}: {rel}")
            if char_info.get('knowledge'):
                for fact in char_info['knowledge']:
                    lines.append(f"  - Knows: {fact}")
            if char_info.get('developments'):
                for dev in char_info['developments']:
                    lines.append(f"  - Development: {dev}")
        return "\n".join(lines)

    @staticmethod
    def get_artifact_state_summary(state: Dict[str, Any]) -> str:
        """Generate a text summary of all artifact states for use in prompts."""
        lines = ["## Current Artifact States"]
        for artifact_name, artifact_info in state.get('artifacts', {}).items():
            lines.append(f"\n**{artifact_name}**")
            lines.append(f"  - Status: {artifact_info.get('status', 'unknown')}")
            if artifact_info.get('location'):
                lines.append(f"  - Location: {artifact_info['location']}")
            loc_known = artifact_info.get('is_location_known')
            if loc_known is not None:
                lines.append(f"  - Location known: {'yes' if loc_known else 'no'}")
            if artifact_info.get('known_by'):
                lines.append(f"  - Known by: {', '.join(artifact_info['known_by'])}")
            if artifact_info.get('owner'):
                lines.append(f"  - Owner: {artifact_info['owner']}")
            if artifact_info.get('significance'):
                lines.append(f"  - Significance: {artifact_info['significance']}")
            if artifact_info.get('properties'):
                lines.append(f"  - Properties: {', '.join(artifact_info['properties'])}")
        return "\n".join(lines)

    @staticmethod
    def get_world_state_summary(state: Dict[str, Any]) -> str:
        """Generate a text summary of all world states for use in prompts."""
        lines = ["## Current World States"]
        for element_name, element_info in state.get('world', {}).items():
            lines.append(f"\n**{element_name}**")
            lines.append(f"  - Status: {element_info.get('status', 'unknown')}")
            if element_info.get('type'):
                lines.append(f"  - Type: {element_info['type']}")
            if element_info.get('details'):
                lines.append(f"  - Details: {element_info['details']}")
            if element_info.get('political_status'):
                lines.append(f"  - Political status: {element_info['political_status']}")
            if element_info.get('trend'):
                lines.append(f"  - Trend: {element_info['trend']}")
            if element_info.get('public_opinion'):
                lines.append(f"  - Public opinion: {element_info['public_opinion']}")
            if element_info.get('key_occupants'):
                lines.append(f"  - Key occupants: {', '.join(element_info['key_occupants'])}")
            if element_info.get('inhabitants'):
                lines.append(f"  - Inhabitants: {', '.join(element_info['inhabitants'])}")
            if element_info.get('current_events'):
                for event in element_info['current_events']:
                    lines.append(f"  - Event: {event}")
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
    
    @staticmethod
    def load_with_validation(filepath: str, default_factory, validator_func=None) -> Dict[str, Any]:
        """
        Load JSON file with validation. Falls back to default if invalid.
        
        Args:
            filepath: Path to JSON file
            default_factory: Function that returns default structure
            validator_func: Optional validation function returning (is_valid, issues)
        
        Returns: Loaded or default data structure
        
        Raises:
            ValueError: If validation fails with an invalid state
        """
        import logging
        
        if not os.path.exists(filepath):
            return default_factory()
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Validate if validator provided
            if validator_func and callable(validator_func):
                is_valid, issues = validator_func(data)
                if not is_valid:
                    logging.error(f"Validation failed for {filepath}: {issues}")
                    raise ValueError(f"State validation failed for {filepath}: {issues}")
            
            return data
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error in {filepath}: {e}")
            return default_factory()
        except IOError as e:
            logging.error(f"IO error reading {filepath}: {e}")
            return default_factory()
    
    @staticmethod
    def save_with_backup(filepath: str, data: Dict[str, Any]) -> bool:
        """
        Save JSON file with automatic backup of existing file.
        
        Args:
            filepath: Path to save to
            data: Data to save
        
        Returns: True if save successful, False otherwise
        """
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Create backup if file exists
            if os.path.exists(filepath):
                backup_path = filepath + '.backup'
                try:
                    with open(filepath, 'r') as f:
                        backup_data = json.load(f)
                    with open(backup_path, 'w') as f:
                        json.dump(backup_data, f, indent=2)
                except (IOError, json.JSONDecodeError):
                    pass  # Skip backup if current file is corrupted
            
            # Write new file atomically (write to temp, then rename)
            temp_path = filepath + '.tmp'
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Rename temp to target
            if os.path.exists(filepath):
                os.remove(filepath)
            os.rename(temp_path, filepath)
            
            return True
        except IOError as e:
            print(f"Error saving {filepath}: {e}")
            return False
    
    @staticmethod
    def apply_extracted_changes(state: Dict[str, Any], extracted_data: Dict[str, Any],
                                source: str = "extraction") -> Dict[str, Any]:
        """
        Apply extracted story elements to story state (Phase 1 & 3).

        Handles two input formats:
        1. Flat format (from initial state bootstrap):
           {"name": "X", "status": "...", "location": "...", ...}
        2. Scene-delta format (from STATE_EXTRACTION_PROMPT):
           {"name": "X", "old_state": {...}, "new_state": {"status": "...", "location": "..."}, "events": [...]}

        Args:
            state: Current story state
            extracted_data: Extracted data with keys: characters, artifacts, world_elements/world, theme, arcs
            source: Source of extraction (outline, scene, etc.) for tracking

        Returns:
            Updated story state
        """
        def _flatten_char(char: Dict) -> Dict:
            """Normalise scene-delta or flat character dict to flat form."""
            if "new_state" in char:
                flat = dict(char.get("new_state", {}))
                flat["name"] = char.get("name", flat.get("name"))
                if "events" in char:
                    flat["developments"] = char["events"]
                return flat
            return char

        def _flatten_artifact(artifact: Dict) -> Dict:
            if "new_state" in artifact:
                flat = dict(artifact.get("new_state", {}))
                flat["name"] = artifact.get("name", flat.get("name"))
                return flat
            return artifact

        def _flatten_world(element: Dict) -> Dict:
            if "new_state" in element:
                flat = {"status": element.get("new_state", element.get("old_state", "unknown"))}
                if isinstance(flat["status"], dict):
                    flat = dict(flat["status"])
                flat["name"] = element.get("element", element.get("name", ""))
                flat["details"] = element.get("event", element.get("details"))
                return flat
            # World elements sometimes use "element" as the name key
            if "element" in element and "name" not in element:
                element = dict(element)
                element["name"] = element.pop("element")
            return element

        # Apply character states
        if "characters" in extracted_data:
            for raw_char in extracted_data["characters"]:
                char = _flatten_char(raw_char)
                if char.get("name"):
                    StoryState.add_character_state(
                        state,
                        char["name"],
                        char.get("status", "unknown"),
                        char.get("developments", char.get("knowledge", [])),
                        location=char.get("location"),
                        companions=char.get("companions"),
                        faction=char.get("faction"),
                        goals=char.get("goals"),
                        inventory=char.get("inventory"),
                        relationships=char.get("relationships"),
                        knowledge=char.get("knowledge"),
                        abilities=char.get("abilities"),
                    )

        # Apply artifact states
        if "artifacts" in extracted_data:
            for raw_artifact in extracted_data["artifacts"]:
                artifact = _flatten_artifact(raw_artifact)
                if artifact.get("name"):
                    StoryState.add_artifact_state(
                        state,
                        artifact["name"],
                        artifact.get("status", "unknown"),
                        location=artifact.get("location"),
                        owner=artifact.get("owner"),
                        is_location_known=artifact.get("is_location_known"),
                        known_by=artifact.get("known_by"),
                        significance=artifact.get("significance"),
                        properties=artifact.get("properties"),
                    )

        # Apply world element states (key may be "world_elements" or "world")
        for key in ("world_elements", "world"):
            if key in extracted_data and isinstance(extracted_data[key], list):
                for raw_element in extracted_data[key]:
                    element = _flatten_world(raw_element)
                    if element.get("name"):
                        StoryState.add_world_state(
                            state,
                            element["name"],
                            element.get("status", "unknown"),
                            details=element.get("details", element.get("description")),
                            element_type=element.get("type"),
                            inhabitants=element.get("inhabitants"),
                            political_status=element.get("political_status"),
                            current_events=element.get("current_events"),
                            key_occupants=element.get("key_occupants"),
                            trend=element.get("trend"),
                            public_opinion=element.get("public_opinion"),
                        )

        # Apply theme
        if "theme" in extracted_data and extracted_data["theme"]:
            theme_data = extracted_data["theme"]
            state["theme"] = {
                "statement": theme_data.get("statement"),
                "core_conflict": theme_data.get("core_conflict"),
                "moral_tension": theme_data.get("moral_tension"),
                "character_conflict": theme_data.get("character_conflict"),
                "world_conflict": theme_data.get("world_conflict"),
                "extracted_at": datetime.now().isoformat()
            }

        # Apply character arcs
        if "character_arcs" in extracted_data:
            if "arcs" not in state:
                state["arcs"] = {}
            for arc in extracted_data["character_arcs"]:
                if arc.get("name"):
                    state["arcs"][arc["name"]] = {
                        "starting_state": arc.get("starting_state"),
                        "arc_stages": arc.get("arc_stages", []),
                        "final_state": arc.get("final_state"),
                        "key_moments": arc.get("key_moments", []),
                        "current_stage": 0
                    }

        # Update metadata
        state["last_extraction"] = {
            "source": source,
            "timestamp": datetime.now().isoformat()
        }

        return state
    
    @staticmethod
    def get_story_position() -> Dict[str, Any]:
        """
        Get the current position in the story (current chapter and scene).
        
        Returns:
            Dict with current_chapter and current_scene
        """
        state = StoryState.load_story_state()
        progress = state.get("plot_progress", {})
        return {
            "current_chapter": progress.get("current_chapter", 0),
            "current_scene": progress.get("current_scene", 0),
            "completed_scenes": progress.get("completed_scenes", 0)
        }
    
    @staticmethod
    def validate_character_presence(state: Dict[str, Any], character_names: List[str]) -> bool:
        """
        Validate that all mentioned characters exist in story state.
        
        Args:
            state: Story state
            character_names: List of character names to validate
        
        Returns:
            True if all characters exist, False otherwise
        """
        existing_chars = set(state.get("characters", {}).keys())
        required_chars = set(character_names)
        return required_chars.issubset(existing_chars)
