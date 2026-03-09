"""
Narrative engine orchestration for web application integration.

This module coordinates the narrative engine components with the web app,
handling the full pipeline of theme extraction, scene planning, and state tracking.
"""

from typing import Dict, Optional, List
from agents import BookAgents
from story_state import StoryState
from config import get_config


class NarrativeOrchestrator:
    """Orchestrates the narrative engine workflow for book generation."""
    
    def __init__(self):
        """Initialize the orchestrator with agent config."""
        self.agent_config = get_config()
        self.story_state = StoryState.load_story_state()
        self.scene_chain = StoryState.load_scene_chain()
        self.character_arcs = StoryState.load_character_arcs()
        self.theme = StoryState.load_theme()
    
    def initialize_new_book(self, topic: str, world_theme: str, 
                           characters: str, outline: str) -> None:
        """Initialize all narrative structures for a new book."""
        # Initialize fresh state
        self.story_state = StoryState.initialize_story_state()
        self.scene_chain = StoryState.initialize_scene_chain()
        self.character_arcs = StoryState.initialize_character_arcs()
        self.theme = StoryState.initialize_theme()
        
        # Save to disk
        StoryState.save_story_state(self.story_state)
        StoryState.save_scene_chain(self.scene_chain)
        StoryState.save_character_arcs(self.character_arcs)
        StoryState.save_theme(self.theme)
    
    def extract_and_save_theme(self, topic: str, world_theme: str) -> Dict:
        """Extract theme from topic and world, save it."""
        agents = BookAgents(self.agent_config)
        theme_data = agents.extract_theme(topic, world_theme)
        
        # Update theme structure
        StoryState.set_theme(
            self.theme,
            theme_data.get('statement', ''),
            theme_data.get('core_conflict', ''),
            theme_data.get('moral_tension', '')
        )
        self.theme['approved'] = False  # Require user approval
        StoryState.save_theme(self.theme)
        
        return theme_data
    
    def extract_and_save_character_arcs(self, characters: str) -> Dict[str, List[str]]:
        """Extract character arc stages, save them."""
        agents = BookAgents(self.agent_config)
        arcs = agents.extract_character_arcs(characters, self.theme)
        
        # Update character arcs structure
        for char_name, arc_stages in arcs.items():
            StoryState.add_character_arc(self.character_arcs, char_name, arc_stages)
        
        StoryState.save_character_arcs(self.character_arcs)
        
        return arcs
    
    def plan_and_save_scene_chain(self, outline: str) -> List[Dict]:
        """Plan scene chain from outline, save it."""
        agents = BookAgents(self.agent_config)
        scenes = agents.plan_scene_chain(outline)
        
        # Update scene chain structure
        self.scene_chain = StoryState.initialize_scene_chain()
        for scene in scenes:
            StoryState.add_scene_to_chain(self.scene_chain, scene)
        
        self.scene_chain['approved'] = False  # Require user approval
        StoryState.save_scene_chain(self.scene_chain)
        
        return scenes
    
    def plan_next_scene_generation(self) -> Dict:
        """Plan the next scene to generate given current state."""
        agents = BookAgents(self.agent_config)
        
        # Need outline and other context - would normally load from file
        # This is a simplified version
        scene_plan = agents.plan_next_scene(
            self.story_state,
            '',  # outline - would load from file
            self.scene_chain.get('scenes', []),
            len(self.story_state.get('scenes', []))
        )
        
        return scene_plan
    
    def generate_scene(self, scene_goal: str, scene_conflict: str,
                      scene_outcome: str, world_theme: str,
                      characters: str, story_context: str = '') -> str:
        """Generate a single scene respecting story state."""
        agents = BookAgents(self.agent_config)
        
        # Get current state summary
        state_summary = StoryState.get_full_state_summary(self.story_state)
        
        # Generate scene
        scene_content = agents.generate_scene_with_state(
            scene_goal,
            scene_conflict,
            scene_outcome,
            story_context,
            world_theme,
            characters,
            state_summary
        )
        
        return scene_content
    
    def extract_and_apply_state_updates(self, scene_content: str) -> Dict:
        """Extract state changes from generated scene and apply them."""
        agents = BookAgents(self.agent_config)
        
        # Extract state updates
        updates = agents.extract_state_updates(scene_content)
        
        # Apply character changes
        for char_name, changes in updates.get('character_changes', {}).items():
            summary = changes.get('summary', '')
            details = changes.get('details', [])
            StoryState.add_character_state(
                self.story_state,
                char_name,
                summary,
                details
            )
        
        # Apply artifact changes
        for artifact_name, changes in updates.get('artifact_changes', {}).items():
            summary = changes.get('summary', '')
            details = changes.get('details', [])
            if len(details) > 0:
                location = details[0] if 'Location' in str(details[0]) else None
                owner = details[1] if len(details) > 1 and 'Owner' in str(details[1]) else None
            else:
                location = None
                owner = None
            
            StoryState.add_artifact_state(
                self.story_state,
                artifact_name,
                summary,
                location=location,
                owner=owner
            )
        
        # Apply world changes
        for element_name, changes in updates.get('world_changes', {}).items():
            summary = changes.get('summary', '')
            details = changes.get('details', [])
            details_str = ' '.join(details) if details else None
            
            StoryState.add_world_state(
                self.story_state,
                element_name,
                summary,
                details=details_str
            )
        
        # Add scene snapshot
        scene_snapshot = StoryState.create_scene_snapshot(
            len(self.story_state.get('scenes', [])) + 1,
            scene_content,
            self.story_state
        )
        StoryState.add_scene_to_state(self.story_state, scene_snapshot)
        
        # Save updated state
        StoryState.save_story_state(self.story_state)
        
        return updates
    
    def get_state_summary(self) -> str:
        """Get a text summary of current story state."""
        return StoryState.get_full_state_summary(self.story_state)
    
    def get_scene_chain_preview(self, num_scenes: int = 5) -> List[Dict]:
        """Get a preview of upcoming scenes in the chain."""
        scenes = self.scene_chain.get('scenes', [])
        completed = len(self.story_state.get('scenes', []))
        
        # Return next N scenes
        return scenes[completed:completed + num_scenes]
    
    def approve_theme(self) -> None:
        """Mark theme as approved by user."""
        self.theme['approved'] = True
        StoryState.save_theme(self.theme)
    
    def approve_scene_chain(self) -> None:
        """Mark scene chain as approved by user."""
        self.scene_chain['approved'] = True
        StoryState.save_scene_chain(self.scene_chain)
    
    def reset_story_state(self) -> None:
        """Reset story state (useful for restarting generation)."""
        self.story_state = StoryState.initialize_story_state()
        StoryState.save_story_state(self.story_state)
    
    def export_story_bible(self) -> Dict:
        """Export complete story bible for reference."""
        return {
            'theme': self.theme,
            'character_arcs': self.character_arcs,
            'scene_chain': self.scene_chain,
            'current_state': self.story_state,
            'state_summary': self.get_state_summary()
        }
