"""
Backward compatibility and migration utilities for the narrative engine.

This module provides tools for:
- Checking if a project uses the new narrative engine
- Migrating existing projects to enable state tracking
- Generating state retroactively from existing outline/chapters
"""

import json
import os
from typing import Dict, List, Any, Tuple, Optional
from story_state import StoryState
from narrative_parsing import NarrativeParser


class MigrationHelper:
    """Helps existing projects use the new narrative engine."""
    
    @staticmethod
    def project_has_state_files() -> bool:
        """Check if current project already has state tracking enabled."""
        return all(os.path.exists(f) for f in [
            StoryState.STATE_FILE,
            StoryState.CHAIN_FILE,
            StoryState.ARCS_FILE,
            StoryState.THEME_FILE
        ])
    
    @staticmethod
    def project_has_basic_files() -> bool:
        """Check if project has basic OpenTale files (world, characters, outline)."""
        return all(os.path.exists(f) for f in [
            'book_output/world.txt',
            'book_output/characters.txt',
            'book_output/outline.txt'
        ])
    
    @staticmethod
    def load_world() -> Optional[str]:
        """Load world.txt content if it exists."""
        path = 'book_output/world.txt'
        if os.path.exists(path):
            with open(path, 'r') as f:
                return f.read()
        return None
    
    @staticmethod
    def load_characters() -> Optional[str]:
        """Load characters.txt content if it exists."""
        path = 'book_output/characters.txt'
        if os.path.exists(path):
            with open(path, 'r') as f:
                return f.read()
        return None
    
    @staticmethod
    def load_outline() -> Optional[str]:
        """Load outline.txt content if it exists."""
        path = 'book_output/outline.txt'
        if os.path.exists(path):
            with open(path, 'r') as f:
                return f.read()
        return None
    
    @staticmethod
    def load_chapters() -> List[str]:
        """Load all chapter files."""
        chapters = []
        chapter_dir = 'book_output/chapters'
        if os.path.exists(chapter_dir):
            for filename in sorted(os.listdir(chapter_dir)):
                if filename.startswith('chapter_') and filename.endswith('.txt'):
                    with open(os.path.join(chapter_dir, filename), 'r') as f:
                        chapters.append(f.read())
        return chapters
    
    @staticmethod
    def generate_character_arcs_from_characters(characters_text: str) -> Dict[str, Any]:
        """
        Generate character arcs from characters.txt content.
        
        Creates basic arc structure for each character found.
        Real arcs should be extracted via AI, but this provides fallback.
        """
        arcs = StoryState.initialize_character_arcs()
        
        # Simple extraction: look for character names (assumes "Character: Name" format)
        lines = characters_text.split('\n')
        current_char = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Try to identify character entries (simple heuristic)
            if line.endswith(':') and len(line) < 50:
                current_char = line.rstrip(':').strip()
                if current_char and len(current_char) > 1:
                    # Create basic arc (will need AI extraction for real stages)
                    arcs['characters'][current_char] = {
                        'arc_stages': [
                            'introduction',
                            'development',
                            'climax',
                            'resolution'
                        ],
                        'current_stage': 0
                    }
        
        return arcs
    
    @staticmethod
    def generate_initial_state_from_outline(outline_text: str) -> Dict[str, Any]:
        """
        Generate initial story state from outline.
        
        Extracts character names and world elements mentioned in outline
        to create a starting point for state tracking.
        """
        state = StoryState.initialize_story_state()
        
        # Simple extraction: look for common names/terms
        outline_lower = outline_text.lower()
        
        # Extract potential character names (capitalized words)
        import re
        potential_names = re.findall(r'\b[A-Z][a-z]+\b', outline_text)
        
        for name in set(potential_names):
            if len(name) > 2 and name not in ['The', 'And', 'Or', 'Chapter']:
                if name not in state['characters']:
                    state['characters'][name] = {
                        'status': 'alive',
                        'developments': []
                    }
        
        return state
    
    @staticmethod
    def migrate_existing_project(verbose: bool = True) -> Tuple[bool, str]:
        """
        Migrate an existing project to enable state tracking.
        
        This function:
        1. Checks if state files already exist
        2. If not, creates default state files
        3. Generates character arcs from characters.txt if available
        4. Generates initial state from outline.txt if available
        5. Saves all files for future use
        
        Args:
            verbose: If True, print migration steps
        
        Returns:
            (success, message)
        """
        log = []
        
        def print_step(msg: str):
            log.append(msg)
            if verbose:
                print(msg)
        
        # Check if already migrated
        if MigrationHelper.project_has_state_files():
            msg = "✅ Project already has state tracking enabled"
            print_step(msg)
            return True, msg
        
        # Check if project has basic files
        if not MigrationHelper.project_has_basic_files():
            msg = "⚠️  Project missing required files (world.txt, characters.txt, outline.txt)"
            print_step(msg)
            return False, msg
        
        print_step("🔄 Migrating existing project to enable state tracking...")
        
        try:
            # Initialize base state files
            print_step("  • Creating story_state.json...")
            state = StoryState.initialize_story_state()
            
            # Try to generate initial state from outline
            outline = MigrationHelper.load_outline()
            if outline:
                initial_state = MigrationHelper.generate_initial_state_from_outline(outline)
                state['characters'].update(initial_state['characters'])
                print_step(f"    Found {len(state['characters'])} characters in outline")
            
            StoryState.save_story_state(state)
            
            # Initialize scene chain
            print_step("  • Creating scene_chain.json...")
            chain = StoryState.initialize_scene_chain()
            StoryState.save_scene_chain(chain)
            
            # Initialize character arcs
            print_step("  • Creating character_arcs.json...")
            characters_text = MigrationHelper.load_characters()
            if characters_text:
                arcs = MigrationHelper.generate_character_arcs_from_characters(characters_text)
                print_step(f"    Generated arcs for {len(arcs['characters'])} characters")
            else:
                arcs = StoryState.initialize_character_arcs()
            
            StoryState.save_character_arcs(arcs)
            
            # Initialize theme (empty until extracted via AI)
            print_step("  • Creating theme.json...")
            theme = StoryState.initialize_theme()
            StoryState.save_theme(theme)
            
            print_step("✅ Migration complete! State tracking enabled for this project.")
            print_step("   Next: Extract theme via /extract_theme endpoint")
            print_step("   Then: Plan scene chain via /plan_scene_chain endpoint")
            
            success_msg = "\n".join(log)
            return True, success_msg
            
        except Exception as e:
            error_msg = f"❌ Migration failed: {str(e)}"
            log.append(error_msg)
            print_step(error_msg)
            return False, "\n".join(log)
    
    @staticmethod
    def get_migration_status() -> Dict[str, Any]:
        """
        Get detailed migration status for a project.
        
        Returns dict with:
        - has_state_files: Whether state tracking is enabled
        - has_basic_files: Whether project has fundamental files
        - characters_count: Number of characters in project
        - chapters_count: Number of chapters written
        - recommended_actions: Next steps for user
        """
        status = {
            'has_state_files': MigrationHelper.project_has_state_files(),
            'has_basic_files': MigrationHelper.project_has_basic_files(),
            'characters': MigrationHelper.load_characters() is not None,
            'outline': MigrationHelper.load_outline() is not None,
            'chapters_count': len(MigrationHelper.load_chapters()),
            'recommended_actions': []
        }
        
        if not status['has_state_files']:
            if status['has_basic_files']:
                status['recommended_actions'].append('Run migration: POST /migrate_project')
            else:
                status['recommended_actions'].append('Create world, characters, and outline first')
        else:
            if not StoryState.load_theme().get('approved'):
                status['recommended_actions'].append('Extract and approve theme')
            
            chain = StoryState.load_scene_chain()
            if not chain.get('approved') or not chain.get('scenes'):
                status['recommended_actions'].append('Plan and approve scene chain')
        
        return status


class StateGenerator:
    """Generates narrative state from existing project content."""
    
    @staticmethod
    def extract_characters_from_chapters(chapters: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Extract character mentions and status from existing chapters.
        
        Returns dict mapping character_name -> {status, last_seen_chapter, mentions_count}
        """
        characters = {}
        
        for chapter_idx, chapter in enumerate(chapters):
            chapter_lower = chapter.lower()
            
            # Look for common status indicators
            if 'dead' in chapter_lower or 'died' in chapter_lower:
                # Extract character names near death mentions
                import re
                death_patterns = [
                    r'(\w+)\s+(?:fell|dropped|died|was dead|killed)',
                    r'(?:dead|death|died)\s+(?:of|was)\s+(\w+)',
                ]
                for pattern in death_patterns:
                    matches = re.findall(pattern, chapter_lower)
                    for name in matches:
                        if name not in characters:
                            characters[name] = {'status': 'dead', 'first_mention': chapter_idx}
        
        return characters
    
    @staticmethod
    def detect_artifacts_from_chapters(chapters: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Extract artifact mentions and status from existing chapters.
        
        Returns dict mapping artifact_name -> {status, location, owner}
        """
        artifacts = {}
        
        # This is a simple heuristic; real extraction would use NLP
        common_artifacts = ['sword', 'ring', 'amulet', 'crown', 'crystal', 'book', 'scroll']
        
        for chapter in chapters:
            for artifact in common_artifacts:
                if artifact in chapter.lower():
                    if artifact not in artifacts:
                        artifacts[artifact] = {
                            'status': 'unknown',
                            'location': 'unknown',
                            'owner': 'unknown'
                        }
        
        return artifacts


if __name__ == '__main__':
    # Example usage
    print("\n" + "="*60)
    print("OpenTale Migration Helper")
    print("="*60)
    
    status = MigrationHelper.get_migration_status()
    print("\nProject Status:")
    print(f"  State files: {'✅' if status['has_state_files'] else '❌'}")
    print(f"  Basic files: {'✅' if status['has_basic_files'] else '❌'}")
    print(f"  Chapters: {status['chapters_count']}")
    print(f"\nRecommended actions:")
    for action in status['recommended_actions']:
        print(f"  • {action}")
    
    if not status['has_state_files'] and status['has_basic_files']:
        print("\nRunning migration...")
        success, message = MigrationHelper.migrate_existing_project(verbose=True)
        if success:
            print("\n✅ Migration successful!")
        else:
            print(f"\n❌ Migration failed:\n{message}")
