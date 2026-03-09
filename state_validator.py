"""
State validation and integrity checking for the narrative engine.

This module handles:
- Validating story state for consistency and completeness
- Checking scene chain causal integrity
- Verifying character arc validity
- Detecting conflicts and contradictions
- Auto-repairing minor issues
"""

import json
from typing import Dict, List, Tuple, Optional, Any
from story_state import StoryState


class StateValidator:
    """Validates and repairs narrative state for integrity."""
    
    @staticmethod
    def validate_story_state(state: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate story state for structural integrity.
        
        Returns: (is_valid, list_of_issues)
        """
        issues = []
        
        # Check required top-level fields
        required_fields = {'characters', 'artifacts', 'world', 'scenes', 'plot_progress'}
        for field in required_fields:
            if field not in state:
                issues.append(f"Missing required field: {field}")
        
        # Check plot_progress structure
        if 'plot_progress' in state:
            progress = state['plot_progress']
            required_progress = {'current_chapter', 'current_scene', 'completed_scenes'}
            for field in required_progress:
                if field not in progress:
                    issues.append(f"Missing plot_progress field: {field}")
                elif not isinstance(progress[field], int):
                    issues.append(f"plot_progress.{field} must be integer, got {type(progress[field])}")
                elif progress[field] < 0:
                    issues.append(f"plot_progress.{field} cannot be negative: {progress[field]}")
        
        # Check characters
        if 'characters' in state and isinstance(state['characters'], dict):
            for char_name, char_data in state['characters'].items():
                if not isinstance(char_data, dict):
                    issues.append(f"Character '{char_name}' data must be dict, got {type(char_data)}")
                elif 'status' not in char_data:
                    issues.append(f"Character '{char_name}' missing status field")
        
        # Check artifacts
        if 'artifacts' in state and isinstance(state['artifacts'], dict):
            for artifact_name, artifact_data in state['artifacts'].items():
                if not isinstance(artifact_data, dict):
                    issues.append(f"Artifact '{artifact_name}' data must be dict, got {type(artifact_data)}")
                elif 'status' not in artifact_data:
                    issues.append(f"Artifact '{artifact_name}' missing status field")
        
        # Check scenes is list
        if 'scenes' in state and not isinstance(state['scenes'], list):
            issues.append(f"scenes must be list, got {type(state['scenes'])}")
        
        return len(issues) == 0, issues
    
    @staticmethod
    def validate_scene_chain(chain: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate scene chain for causal integrity.
        
        Returns: (is_valid, list_of_issues)
        """
        issues = []
        
        # Check required fields
        required_fields = {'version', 'total_scenes', 'scenes'}
        for field in required_fields:
            if field not in chain:
                issues.append(f"Missing required field: {field}")
        
        # Validate version format
        if 'version' in chain and not isinstance(chain['version'], str):
            issues.append(f"version must be string, got {type(chain['version'])}")
        
        # Validate total_scenes is int
        if 'total_scenes' in chain:
            if not isinstance(chain['total_scenes'], int):
                issues.append(f"total_scenes must be integer, got {type(chain['total_scenes'])}")
            elif chain['total_scenes'] < 0:
                issues.append(f"total_scenes cannot be negative: {chain['total_scenes']}")
        
        # Validate scenes array
        if 'scenes' in chain:
            if not isinstance(chain['scenes'], list):
                issues.append(f"scenes must be list, got {type(chain['scenes'])}")
            else:
                for idx, scene in enumerate(chain['scenes']):
                    if not isinstance(scene, dict):
                        issues.append(f"Scene {idx} must be dict, got {type(scene)}")
                        continue
                    
                    # Check required scene fields
                    required_scene_fields = {'goal', 'conflict', 'outcome', 'consequence', 'next_trigger'}
                    for field in required_scene_fields:
                        if field not in scene:
                            issues.append(f"Scene {idx} missing required field: {field}")
                    
                    # Check if consequence matches next scene's trigger (causal integrity)
                    if idx < len(chain['scenes']) - 1:
                        current_consequence = scene.get('consequence', '').lower().strip()
                        next_trigger = chain['scenes'][idx + 1].get('next_trigger', '').lower().strip()
                        
                        # Allow flexibility: consequence and trigger don't need exact match,
                        # but shouldn't be completely contradictory
                        if current_consequence and next_trigger:
                            # Check for obvious contradictions (e.g., "death" vs "alive")
                            contradiction_pairs = [
                                ('death', 'alive'), ('dead', 'alive'),
                                ('betrayal', 'loyalty'), ('revealed', 'hidden')
                            ]
                            for contradiction in contradiction_pairs:
                                if any(c in current_consequence for c in contradiction) and \
                                   any(c in next_trigger for c in contradiction[::-1]):
                                    issues.append(
                                        f"Scene {idx}-{idx+1} causal contradiction: "
                                        f"consequence '{current_consequence}' conflicts with "
                                        f"next trigger '{next_trigger}'"
                                    )
        
        # Validate total_scenes matches scenes array length
        if 'total_scenes' in chain and 'scenes' in chain:
            if chain['total_scenes'] != len(chain['scenes']):
                issues.append(
                    f"total_scenes mismatch: declared {chain['total_scenes']}, "
                    f"but {len(chain['scenes'])} scenes present"
                )
        
        return len(issues) == 0, issues
    
    @staticmethod
    def validate_character_arcs(arcs: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate character arcs for consistency.
        
        Returns: (is_valid, list_of_issues)
        """
        issues = []
        
        # Check required fields
        if 'characters' not in arcs:
            issues.append("Missing required field: characters")
            return False, issues
        
        if not isinstance(arcs['characters'], dict):
            issues.append(f"characters must be dict, got {type(arcs['characters'])}")
            return False, issues
        
        # Validate each character arc
        for char_name, arc_data in arcs['characters'].items():
            if not isinstance(arc_data, dict):
                issues.append(f"Character '{char_name}' arc must be dict, got {type(arc_data)}")
                continue
            
            # Check arc_stages
            if 'arc_stages' not in arc_data:
                issues.append(f"Character '{char_name}' missing arc_stages field")
            elif not isinstance(arc_data['arc_stages'], list):
                issues.append(f"Character '{char_name}' arc_stages must be list, got {type(arc_data['arc_stages'])}")
            elif len(arc_data['arc_stages']) == 0:
                issues.append(f"Character '{char_name}' arc_stages cannot be empty")
            
            # Check current_stage
            if 'current_stage' not in arc_data:
                issues.append(f"Character '{char_name}' missing current_stage field")
            elif not isinstance(arc_data['current_stage'], int):
                issues.append(f"Character '{char_name}' current_stage must be integer, got {type(arc_data['current_stage'])}")
            elif arc_data['current_stage'] < 0:
                issues.append(f"Character '{char_name}' current_stage cannot be negative: {arc_data['current_stage']}")
            
            # Check current_stage is within valid range
            if 'arc_stages' in arc_data and 'current_stage' in arc_data:
                max_stage = len(arc_data['arc_stages']) - 1
                if arc_data['current_stage'] > max_stage:
                    issues.append(
                        f"Character '{char_name}' current_stage {arc_data['current_stage']} "
                        f"exceeds max stage {max_stage}"
                    )
        
        return len(issues) == 0, issues
    
    @staticmethod
    def validate_theme(theme: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate theme structure.
        
        Returns: (is_valid, list_of_issues)
        """
        issues = []
        
        # Check required fields (can be None/empty initially, but structure must exist)
        required_fields = {'statement', 'core_conflict', 'moral_tension', 'approved'}
        for field in required_fields:
            if field not in theme:
                issues.append(f"Missing required field: {field}")
        
        # Validate types
        if 'statement' in theme and theme['statement'] is not None:
            if not isinstance(theme['statement'], str):
                issues.append(f"statement must be string, got {type(theme['statement'])}")
        
        if 'core_conflict' in theme and theme['core_conflict'] is not None:
            if not isinstance(theme['core_conflict'], str):
                issues.append(f"core_conflict must be string, got {type(theme['core_conflict'])}")
        
        if 'moral_tension' in theme and theme['moral_tension'] is not None:
            if not isinstance(theme['moral_tension'], str):
                issues.append(f"moral_tension must be string, got {type(theme['moral_tension'])}")
        
        if 'approved' in theme and not isinstance(theme['approved'], bool):
            issues.append(f"approved must be boolean, got {type(theme['approved'])}")
        
        return len(issues) == 0, issues
    
    @staticmethod
    def detect_character_contradictions(state: Dict[str, Any]) -> List[str]:
        """
        Detect contradictions in character state.
        
        Returns: list of contradiction descriptions
        """
        contradictions = []
        
        if 'characters' not in state:
            return contradictions
        
        characters = state['characters']
        
        # Check for impossible status combinations
        for char_name, char_data in characters.items():
            if not isinstance(char_data, dict):
                continue
            
            status = char_data.get('status', '').lower()
            
            # Dead characters shouldn't have active development
            if 'dead' in status or 'deceased' in status:
                developments = char_data.get('developments', [])
                if developments and any('lives' in str(d).lower() for d in developments):
                    contradictions.append(
                        f"Character '{char_name}' status is '{status}' "
                        f"but has active developments indicating life"
                    )
        
        return contradictions
    
    @staticmethod
    def detect_artifact_contradictions(state: Dict[str, Any]) -> List[str]:
        """
        Detect contradictions in artifact state.
        
        Returns: list of contradiction descriptions
        """
        contradictions = []
        
        if 'artifacts' not in state:
            return contradictions
        
        artifacts = state['artifacts']
        
        # Check for impossible artifact locations
        for artifact_name, artifact_data in artifacts.items():
            if not isinstance(artifact_data, dict):
                continue
            
            # If status is "destroyed", it shouldn't have an owner or location
            status = artifact_data.get('status', '').lower()
            if 'destroyed' in status or 'consumed' in status:
                if artifact_data.get('owner') or artifact_data.get('location'):
                    contradictions.append(
                        f"Artifact '{artifact_name}' status is '{status}' "
                        f"but still has owner/location assigned"
                    )
        
        return contradictions
    
    @staticmethod
    def repair_state(state: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """
        Attempt to auto-repair minor state issues.
        
        Returns: (repaired_state, list_of_repairs_made)
        """
        repairs = []
        
        # Ensure all top-level fields exist
        if 'characters' not in state:
            state['characters'] = {}
            repairs.append("Created missing 'characters' field")
        
        if 'artifacts' not in state:
            state['artifacts'] = {}
            repairs.append("Created missing 'artifacts' field")
        
        if 'world' not in state:
            state['world'] = {}
            repairs.append("Created missing 'world' field")
        
        if 'scenes' not in state:
            state['scenes'] = []
            repairs.append("Created missing 'scenes' field")
        
        if 'plot_progress' not in state:
            state['plot_progress'] = {
                'current_chapter': 0,
                'current_scene': 0,
                'completed_scenes': 0
            }
            repairs.append("Created missing 'plot_progress' field")
        
        # Ensure plot_progress fields are valid
        if isinstance(state.get('plot_progress'), dict):
            progress = state['plot_progress']
            for field in ['current_chapter', 'current_scene', 'completed_scenes']:
                if field not in progress:
                    progress[field] = 0
                    repairs.append(f"Created missing plot_progress.{field}")
                elif not isinstance(progress[field], int):
                    try:
                        progress[field] = int(progress[field])
                        repairs.append(f"Converted plot_progress.{field} to integer")
                    except (ValueError, TypeError):
                        progress[field] = 0
                        repairs.append(f"Reset invalid plot_progress.{field} to 0")
        
        return state, repairs
    
    @staticmethod
    def repair_scene_chain(chain: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """
        Attempt to auto-repair minor scene chain issues.
        
        Returns: (repaired_chain, list_of_repairs_made)
        """
        repairs = []
        
        # Ensure all top-level fields exist
        if 'version' not in chain:
            chain['version'] = '1.0'
            repairs.append("Created missing 'version' field")
        
        if 'total_scenes' not in chain:
            chain['total_scenes'] = 0
            repairs.append("Created missing 'total_scenes' field")
        
        if 'scenes' not in chain:
            chain['scenes'] = []
            repairs.append("Created missing 'scenes' field")
        
        if 'approved' not in chain:
            chain['approved'] = False
            repairs.append("Created missing 'approved' field")
        
        # Sync total_scenes with actual scenes array
        if chain['total_scenes'] != len(chain['scenes']):
            old_total = chain['total_scenes']
            chain['total_scenes'] = len(chain['scenes'])
            repairs.append(f"Synced total_scenes from {old_total} to {chain['total_scenes']}")
        
        return chain, repairs
    
    @staticmethod
    def full_validation_report(
        state: Dict[str, Any],
        chain: Dict[str, Any],
        arcs: Dict[str, Any],
        theme: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive validation report for all story data.
        
        Returns: validation report dict
        """
        state_valid, state_issues = StateValidator.validate_story_state(state)
        chain_valid, chain_issues = StateValidator.validate_scene_chain(chain)
        arcs_valid, arcs_issues = StateValidator.validate_character_arcs(arcs)
        theme_valid, theme_issues = StateValidator.validate_theme(theme)
        
        char_contradictions = StateValidator.detect_character_contradictions(state)
        artifact_contradictions = StateValidator.detect_artifact_contradictions(state)
        
        return {
            'overall_valid': state_valid and chain_valid and arcs_valid and theme_valid,
            'story_state': {
                'valid': state_valid,
                'issues': state_issues
            },
            'scene_chain': {
                'valid': chain_valid,
                'issues': chain_issues
            },
            'character_arcs': {
                'valid': arcs_valid,
                'issues': arcs_issues
            },
            'theme': {
                'valid': theme_valid,
                'issues': theme_issues
            },
            'contradictions': {
                'character': char_contradictions,
                'artifact': artifact_contradictions
            }
        }
