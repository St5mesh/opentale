"""
State mutability rules and enforcement for narrative consistency.

This module defines and enforces rules about which state properties can change
between chapters/scenes and which must remain immutable to preserve narrative logic.

Hierarchy of mutability:
1. NEVER_CHANGE: Timeline progression, character deaths, completed quests
2. WARN_ON_CHANGE: Character relationships, key locations
3. ALLOW_CHANGE: Character mood/intent, scene participants, active conflicts
4. HOOK_RULE: Each scene must connect narratively to the previous
"""

from typing import Dict, List, Tuple, Any, Optional
from enum import Enum


class MutabilityLevel(Enum):
    """Levels of state mutability."""
    NEVER_CHANGE = "never_change"  # Immutable across entire story
    WARN_ON_CHANGE = "warn_on_change"  # Flag warnings but allow change
    ALLOW_CHANGE = "allow_change"  # Normal mutations expected
    SCENE_LOCAL = "scene_local"  # Only valid within current scene


class StateMutabilityRules:
    """Defines and validates state mutability rules."""
    
    # Schema defining mutability for each state property
    MUTABILITY_SCHEMA = {
        "characters": {
            "name": MutabilityLevel.NEVER_CHANGE,
            "status": {
                # Sub-schema: different parts of status have different rules
                "alive_status": MutabilityLevel.NEVER_CHANGE,  # Dead/alive transition is one-way
                "dead": MutabilityLevel.NEVER_CHANGE,  # Once dead, always dead
                "mood": MutabilityLevel.ALLOW_CHANGE,
                "intent": MutabilityLevel.ALLOW_CHANGE,
                "location": MutabilityLevel.ALLOW_CHANGE,
                "relationships": MutabilityLevel.WARN_ON_CHANGE,
                "skills": MutabilityLevel.ALLOW_CHANGE,
                "knowledge": MutabilityLevel.ALLOW_CHANGE,
            }
        },
        "artifacts": {
            "name": MutabilityLevel.NEVER_CHANGE,
            "status": {
                "destroyed": MutabilityLevel.NEVER_CHANGE,  # Once destroyed, always destroyed
                "owner": MutabilityLevel.ALLOW_CHANGE,
                "location": MutabilityLevel.ALLOW_CHANGE,
                "condition": MutabilityLevel.ALLOW_CHANGE,
            }
        },
        "world": {
            "timeline": MutabilityLevel.NEVER_CHANGE,  # Time only moves forward
            "locations": {
                "description": MutabilityLevel.WARN_ON_CHANGE,
                "inhabitants": MutabilityLevel.ALLOW_CHANGE,
                "status": MutabilityLevel.ALLOW_CHANGE,
            },
            "events": MutabilityLevel.ALLOW_CHANGE,
        },
        "plot_progress": {
            "current_chapter": MutabilityLevel.ALLOW_CHANGE,
            "current_scene": MutabilityLevel.ALLOW_CHANGE,
            "completed_scenes": MutabilityLevel.NEVER_CHANGE,  # Can only increase
            "completed_quests": MutabilityLevel.NEVER_CHANGE,  # Once done, always done
            "failed_quests": MutabilityLevel.NEVER_CHANGE,  # Once failed, always failed
        },
        "character_arcs": MutabilityLevel.ALLOW_CHANGE,
        "theme": MutabilityLevel.WARN_ON_CHANGE,
    }
    
    @staticmethod
    def check_mutability(
        previous_state: Dict[str, Any],
        new_state: Dict[str, Any],
        change_context: str = "scene_draft"
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Check state mutations against mutability rules.
        
        Args:
            previous_state: State before changes
            new_state: State after changes
            change_context: Context for change ('scene_draft', 'chapter_transition', 'manual_edit')
        
        Returns:
            (is_valid, critical_violations, warnings)
            - critical_violations: Changes that violate immutable rules
            - warnings: Changes that might be problematic
        """
        critical_violations = []
        warnings = []
        
        # Check each top-level state section
        for section_name in ["characters", "artifacts", "world", "plot_progress"]:
            if section_name not in previous_state or section_name not in new_state:
                continue
            
            violations, section_warnings = StateMutabilityRules._check_section_mutability(
                section_name,
                previous_state[section_name],
                new_state[section_name]
            )
            critical_violations.extend(violations)
            warnings.extend(section_warnings)
        
        is_valid = len(critical_violations) == 0
        return is_valid, critical_violations, warnings
    
    @staticmethod
    def _check_section_mutability(
        section_name: str,
        previous_values: Any,
        new_values: Any
    ) -> Tuple[List[str], List[str]]:
        """Check mutability for a specific state section."""
        violations = []
        warnings = []
        
        if section_name == "characters":
            violations, warnings = StateMutabilityRules._check_characters(previous_values, new_values)
        elif section_name == "artifacts":
            violations, warnings = StateMutabilityRules._check_artifacts(previous_values, new_values)
        elif section_name == "world":
            violations, warnings = StateMutabilityRules._check_world(previous_values, new_values)
        elif section_name == "plot_progress":
            violations, warnings = StateMutabilityRules._check_plot_progress(previous_values, new_values)
        
        return violations, warnings
    
    @staticmethod
    def _check_characters(prev_chars: Dict, new_chars: Dict) -> Tuple[List[str], List[str]]:
        """Check character state mutations."""
        violations = []
        warnings = []
        
        for char_name, prev_data in prev_chars.items():
            if char_name not in new_chars:
                continue
            
            new_data = new_chars[char_name]
            
            # Check if character is dead (never resurrect)
            prev_status = prev_data.get("status", "")
            new_status = new_data.get("status", "")
            
            if ("dead" in prev_status.lower() or "deceased" in prev_status.lower()):
                if "dead" not in new_status.lower() and "deceased" not in new_status.lower():
                    violations.append(
                        f"Character '{char_name}' was marked as dead but is now alive. "
                        "Dead characters cannot be resurrected."
                    )
            
            # Warn on relationship changes
            prev_relationships = prev_data.get("relationships", {})
            new_relationships = new_data.get("relationships", {})
            if prev_relationships != new_relationships:
                warnings.append(
                    f"Character '{char_name}' relationships changed. "
                    "Verify this change is narratively consistent."
                )
        
        return violations, warnings
    
    @staticmethod
    def _check_artifacts(prev_artifacts: Dict, new_artifacts: Dict) -> Tuple[List[str], List[str]]:
        """Check artifact state mutations."""
        violations = []
        warnings = []
        
        for artifact_name, prev_data in prev_artifacts.items():
            if artifact_name not in new_artifacts:
                continue
            
            new_data = new_artifacts[artifact_name]
            
            # Check if artifact is destroyed (never undestroys)
            prev_status = prev_data.get("status", "")
            new_status = new_data.get("status", "")
            
            if "destroyed" in prev_status.lower():
                if "destroyed" not in new_status.lower():
                    violations.append(
                        f"Artifact '{artifact_name}' was destroyed but is now undestroyed. "
                        "Destroyed artifacts cannot be restored."
                    )
        
        return violations, warnings
    
    @staticmethod
    def _check_world(prev_world: Dict, new_world: Dict) -> Tuple[List[str], List[str]]:
        """Check world state mutations."""
        violations = []
        warnings = []
        
        # Check timeline never goes backwards
        prev_timeline = prev_world.get("timeline", {})
        new_timeline = new_world.get("timeline", {})
        
        if isinstance(prev_timeline, dict) and isinstance(new_timeline, dict):
            prev_time = prev_timeline.get("current_date")
            new_time = new_timeline.get("current_date")
            
            if prev_time and new_time:
                # Simple string comparison works for ISO format dates
                if new_time < prev_time:
                    violations.append(
                        f"Timeline went backwards: {prev_time} -> {new_time}. "
                        "Time can only move forward."
                    )
        
        return violations, warnings
    
    @staticmethod
    def _check_plot_progress(prev_progress: Dict, new_progress: Dict) -> Tuple[List[str], List[str]]:
        """Check plot progress mutations."""
        violations = []
        warnings = []
        
        # Completed scenes can only increase
        prev_completed = prev_progress.get("completed_scenes", 0)
        new_completed = new_progress.get("completed_scenes", 0)
        if new_completed < prev_completed:
            violations.append(
                f"Completed scenes went backwards: {prev_completed} -> {new_completed}. "
                "Progress can only move forward."
            )
        
        # Completed quests are permanent
        prev_quests = set(prev_progress.get("completed_quests", []))
        new_quests = set(new_progress.get("completed_quests", []))
        removed_quests = prev_quests - new_quests
        if removed_quests:
            violations.append(
                f"Completed quests were removed: {removed_quests}. "
                "Completed quests cannot be uncompleted."
            )
        
        # Failed quests are permanent
        prev_failed = set(prev_progress.get("failed_quests", []))
        new_failed = set(new_progress.get("failed_quests", []))
        removed_failed = prev_failed - new_failed
        if removed_failed:
            violations.append(
                f"Failed quests were removed: {removed_failed}. "
                "Failed quests cannot be unfailed."
            )
        
        return violations, warnings


class StateTransition:
    """Tracks and validates state transitions between scenes."""
    
    def __init__(self):
        """Initialize state transition tracker."""
        self.transition_history: List[Dict[str, Any]] = []
    
    def record_transition(
        self,
        from_state: Dict[str, Any],
        to_state: Dict[str, Any],
        trigger: str = "scene_draft",
        scene_info: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Record and validate a state transition.
        
        Args:
            from_state: State before transition
            to_state: State after transition
            trigger: What caused the transition (scene_draft, chapter_transition, etc.)
            scene_info: Optional info about scene that caused transition
        
        Returns:
            (is_valid, violations, warnings)
        """
        is_valid, violations, warnings = StateMutabilityRules.check_mutability(
            from_state, to_state, trigger
        )
        
        self.transition_history.append({
            "from_state": from_state,
            "to_state": to_state,
            "trigger": trigger,
            "scene_info": scene_info,
            "is_valid": is_valid,
            "violations": violations,
            "warnings": warnings,
        })
        
        return is_valid, violations, warnings
    
    def get_transition_chain(self, scene_number: int) -> List[Dict[str, Any]]:
        """Get transitions up to a specific scene."""
        return self.transition_history[:scene_number]
    
    def validate_narrative_hook(
        self,
        previous_scene_outcome: Dict[str, Any],
        next_scene_premise: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Validate that next scene connects to previous scene outcome.
        
        Each scene's hook must align with the previous scene's consequence.
        
        Args:
            previous_scene_outcome: Outcome/consequence from previous scene
            next_scene_premise: Premise/prerequisite of next scene
        
        Returns:
            (is_connected, issues)
        """
        issues = []
        
        # Check location continuity
        prev_location = previous_scene_outcome.get("final_location")
        next_location = next_scene_premise.get("location")
        
        # Allow location change only if explicitly justified
        if prev_location and next_location and prev_location != next_location:
            # This isn't necessarily a violation, but should be noted
            # The justification should be in the scene content
            pass
        
        # Check character continuity
        prev_characters = set(previous_scene_outcome.get("final_characters", []))
        next_characters = set(next_scene_premise.get("characters_needed", []))
        
        # At least one character should carry forward for continuity
        if not (prev_characters & next_characters):
            issues.append(
                "No character continuity between scenes. "
                "At least one character should carry forward from previous scene."
            )
        
        is_connected = len(issues) == 0
        return is_connected, issues
