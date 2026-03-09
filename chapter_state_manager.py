"""
Chapter state management for progressive scene drafting.

Manages per-chapter state snapshots and history tracking to ensure
narrative consistency across scenes within a chapter.
"""

import json
import os
import fcntl
import tempfile
from contextlib import contextmanager
from typing import Dict, List, Optional, Any
from datetime import datetime


class ChapterStateManager:
    """Manages chapter-level state persistence and history."""
    
    STATES_DIR = 'book_output/states'
    _lock_files = {}  # In-memory lock file handles
    
    @staticmethod
    @contextmanager
    def _acquire_lock(lock_path: str):
        """Context manager for acquiring a file lock."""
        import logging
        lock_dir = os.path.dirname(lock_path)
        os.makedirs(lock_dir, exist_ok=True)
        
        lock_file = None
        try:
            # Open or create lock file
            lock_file = open(lock_path, 'w')
            # Acquire exclusive lock
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            if lock_file:
                try:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                    lock_file.close()
                except Exception as e:
                    logging.error(f"Error releasing lock {lock_path}: {e}")
    
    @staticmethod
    def _get_lock_path(chapter_number: int) -> str:
        """Get the lock file path for a chapter."""
        return os.path.join(ChapterStateManager.STATES_DIR, f'chapter_{chapter_number}.lock')
    
    @staticmethod
    def ensure_states_directory():
        """Ensure the states directory exists."""
        os.makedirs(ChapterStateManager.STATES_DIR, exist_ok=True)
    
    @staticmethod
    def get_chapter_states_path(chapter_number: int) -> str:
        """Get the file path for a chapter's states."""
        return os.path.join(ChapterStateManager.STATES_DIR, f'chapter_{chapter_number}_states.json')
    
    @staticmethod
    def get_chapter_states_history_path(chapter_number: int) -> str:
        """Get the file path for a chapter's state history."""
        return os.path.join(ChapterStateManager.STATES_DIR, f'chapter_{chapter_number}_history.json')
    
    @staticmethod
    def chapter_states_exist(chapter_number: int) -> bool:
        """Check if states exist for a chapter."""
        return os.path.exists(ChapterStateManager.get_chapter_states_path(chapter_number))
    
    @staticmethod
    def load_chapter_states(chapter_number: int) -> Optional[Dict[str, Any]]:
        """
        Load the current states for a chapter.
        
        Returns:
            Chapter states dict or None if not found
            
        Raises:
            IOError: If file exists but cannot be read
            ValueError: If JSON is invalid
        """
        import logging
        path = ChapterStateManager.get_chapter_states_path(chapter_number)
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                logging.error(f"Invalid JSON in chapter {chapter_number} states: {e}")
                raise ValueError(f"Invalid JSON in chapter {chapter_number} states: {e}")
            except IOError as e:
                logging.error(f"Cannot read chapter {chapter_number} states: {e}")
                raise IOError(f"Cannot read chapter {chapter_number} states: {e}")
        return None
    
    @staticmethod
    def save_chapter_states(chapter_number: int, states: Dict[str, Any]) -> bool:
        """
        Save states for a chapter with file locking.
        
        Args:
            chapter_number: Which chapter
            states: State dict to save
        
        Returns:
            True if successful
            
        Raises:
            IOError: If directory cannot be created or file cannot be written
        """
        import logging
        try:
            ChapterStateManager.ensure_states_directory()
            lock_path = ChapterStateManager._get_lock_path(chapter_number)
            path = ChapterStateManager.get_chapter_states_path(chapter_number)
            
            with ChapterStateManager._acquire_lock(lock_path):
                with open(path, 'w') as f:
                    json.dump(states, f, indent=2)
            return True
        except IOError as e:
            logging.error(f"Cannot save chapter {chapter_number} states: {e}")
            raise IOError(f"Cannot save chapter {chapter_number} states: {e}")
        except Exception as e:
            logging.error(f"Error saving chapter {chapter_number} states: {e}")
            raise
    
    @staticmethod
    def record_scene_state_transition(
        chapter_number: int,
        scene_number: int,
        before_state: Dict[str, Any],
        after_state: Dict[str, Any],
        scene_summary: str = ""
    ) -> bool:
        """
        Record a state transition caused by scene generation with file locking.
        
        This creates a history entry showing how states changed during scene drafting.
        
        Args:
            chapter_number: Which chapter
            scene_number: Which scene within the chapter
            before_state: State before scene generation
            after_state: State after scene generation
            scene_summary: Optional description of scene
        
        Returns:
            True if successful
            
        Raises:
            IOError: If history file cannot be written
        """
        import logging
        try:
            ChapterStateManager.ensure_states_directory()
            lock_path = ChapterStateManager._get_lock_path(chapter_number)
            history_path = ChapterStateManager.get_chapter_states_history_path(chapter_number)
            
            with ChapterStateManager._acquire_lock(lock_path):
                # Load existing history
                history = []
                if os.path.exists(history_path):
                    try:
                        with open(history_path, 'r') as f:
                            history = json.load(f)
                    except (json.JSONDecodeError, IOError) as e:
                        logging.error(f"Error loading state history for chapter {chapter_number}: {e}")
                        raise ValueError(f"Corrupted history file for chapter {chapter_number}: {e}")
                
                # Add new transition
                transition = {
                    'timestamp': datetime.now().isoformat(),
                    'scene_number': scene_number,
                    'scene_summary': scene_summary,
                    'before_state': before_state,
                    'after_state': after_state,
                    'changed_fields': ChapterStateManager._get_changed_fields(before_state, after_state)
                }
                
                history.append(transition)
                
                # Save updated history
                with open(history_path, 'w') as f:
                    json.dump(history, f, indent=2)
            
            return True
        except (IOError, ValueError) as e:
            logging.error(f"Error recording state transition: {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error recording state transition: {e}")
            raise
    
    @staticmethod
    def get_state_history(chapter_number: int) -> List[Dict[str, Any]]:
        """
        Get the full history of state transitions for a chapter.
        
        Returns:
            List of transitions, oldest first
            
        Raises:
            IOError: If history file cannot be read
            ValueError: If history file is corrupted
        """
        import logging
        history_path = ChapterStateManager.get_chapter_states_history_path(chapter_number)
        if os.path.exists(history_path):
            try:
                with open(history_path, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                logging.error(f"Corrupted history file for chapter {chapter_number}: {e}")
                raise ValueError(f"Corrupted history file for chapter {chapter_number}: {e}")
            except IOError as e:
                logging.error(f"Cannot read history file for chapter {chapter_number}: {e}")
                raise IOError(f"Cannot read history file for chapter {chapter_number}: {e}")
        return []
    
    @staticmethod
    def get_state_at_scene(chapter_number: int, scene_number: int) -> Optional[Dict[str, Any]]:
        """
        Reconstruct the state as it was after a specific scene.
        
        Args:
            chapter_number: Which chapter
            scene_number: Which scene (or 0 for initial state)
        
        Returns:
            State at that point in scene progression
        """
        history = ChapterStateManager.get_state_history(chapter_number)
        
        if scene_number == 0:
            # Return initial chapter state
            path = ChapterStateManager.get_chapter_states_path(chapter_number)
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return json.load(f)
        
        # Find the state after the requested scene
        for transition in history:
            if transition['scene_number'] == scene_number:
                return transition['after_state']
        
        # If not found, return last known state
        if history:
            return history[-1]['after_state']
        
        return None
    
    @staticmethod
    def _get_changed_fields(before: Dict, after: Dict) -> Dict[str, Any]:
        """
        Find which fields changed between two states.
        
        Returns a dict showing what changed.
        """
        changed = {}
        
        # Check top-level keys
        all_keys = set(before.keys()) | set(after.keys())
        
        for key in all_keys:
            before_val = before.get(key)
            after_val = after.get(key)
            
            if before_val != after_val:
                changed[key] = {
                    'before': before_val,
                    'after': after_val
                }
        
        return changed
    
    @staticmethod
    def get_chapter_state_summary(chapter_number: int) -> Dict[str, Any]:
        """
        Get a human-readable summary of chapter state.
        
        Useful for UI display and debugging.
        """
        states = ChapterStateManager.load_chapter_states(chapter_number)
        history = ChapterStateManager.get_state_history(chapter_number)
        
        summary = {
            'chapter': chapter_number,
            'has_states': states is not None,
            'total_scenes': len(history),
            'characters': len(states.get('characters', {})) if states else 0,
            'artifacts': len(states.get('artifacts', {})) if states else 0,
            'last_updated': history[-1]['timestamp'] if history else None,
            'total_transitions': len(history)
        }
        
        return summary
    
    @staticmethod
    def export_chapter_states_report(chapter_number: int, output_path: str = None) -> str:
        """
        Export a detailed report of chapter states and transitions.
        
        Args:
            chapter_number: Which chapter
            output_path: Optional path to save report to
        
        Returns:
            Report text
        """
        states = ChapterStateManager.load_chapter_states(chapter_number)
        history = ChapterStateManager.get_state_history(chapter_number)
        
        report = f"=== CHAPTER {chapter_number} STATE REPORT ===\n\n"
        
        if states:
            report += "INITIAL CHAPTER STATES:\n"
            report += json.dumps(states, indent=2) + "\n\n"
        
        if history:
            report += f"STATE TRANSITIONS ({len(history)} scenes):\n"
            report += "=" * 50 + "\n\n"
            
            for i, transition in enumerate(history):
                report += f"SCENE {transition['scene_number']} - {transition.get('scene_summary', 'No description')}\n"
                report += f"Time: {transition['timestamp']}\n"
                report += f"Changed fields:\n"
                
                for field, changes in transition.get('changed_fields', {}).items():
                    report += f"  - {field}\n"
                    report += f"    Before: {changes['before']}\n"
                    report += f"    After: {changes['after']}\n"
                
                report += "\n"
        else:
            report += "No scene transitions recorded yet.\n"
        
        if output_path:
            try:
                with open(output_path, 'w') as f:
                    f.write(report)
            except IOError as e:
                import logging
                logging.error(f"Error exporting report to {output_path}: {e}")
                raise IOError(f"Error exporting report to {output_path}: {e}")
        
        return report
    
    @staticmethod
    def clear_chapter_states(chapter_number: int) -> bool:
        """
        Clear all states and history for a chapter (for regeneration).
        
        Args:
            chapter_number: Which chapter
        
        Returns:
            True if successful
            
        Raises:
            IOError: If files cannot be deleted
        """
        import logging
        try:
            ChapterStateManager.ensure_states_directory()
            
            # Remove states file
            states_path = ChapterStateManager.get_chapter_states_path(chapter_number)
            if os.path.exists(states_path):
                os.remove(states_path)
            
            # Remove history file
            history_path = ChapterStateManager.get_chapter_states_history_path(chapter_number)
            if os.path.exists(history_path):
                os.remove(history_path)
            
            return True
        except IOError as e:
            logging.error(f"Cannot delete chapter {chapter_number} state files: {e}")
            raise IOError(f"Cannot delete chapter {chapter_number} state files: {e}")
