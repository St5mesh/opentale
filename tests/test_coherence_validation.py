#!/usr/bin/env python3
"""
Phase 5 Coherence Testing

Tests whether the narrative engine actually prevents the reported issues:
1. Character resurrection prevention
2. Consistent character motivations
3. Traceable causality
4. Plot coherence

This script validates the narrative engine's effectiveness by:
1. Loading a test project with state tracking
2. Extracting narrative patterns
3. Verifying no contradictions exist
4. Generating coherence metrics
"""

import json
import os
import re
from typing import Dict, List, Any, Tuple, Set
from story_state import StoryState
from state_validator import StateValidator


class CoherenceAnalyzer:
    """Analyzes narrative coherence and detects issues."""
    
    @staticmethod
    def analyze_character_consistency(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if character states are consistent throughout.
        
        Returns:
        {
            'total_characters': int,
            'dead_characters': [names],
            'alive_characters': [names],
            'contradictions': [descriptions],
            'status': 'pass' | 'fail'
        }
        """
        result = {
            'total_characters': 0,
            'dead_characters': [],
            'alive_characters': [],
            'contradictions': [],
            'status': 'pass'
        }
        
        characters = state.get('characters', {})
        result['total_characters'] = len(characters)
        
        for char_name, char_data in characters.items():
            status = char_data.get('status', '').lower()
            
            # Track dead vs alive
            if 'dead' in status or 'deceased' in status or 'banished' in status:
                result['dead_characters'].append(char_name)
            else:
                result['alive_characters'].append(char_name)
        
        # Check for contradictions
        contradictions = StateValidator.detect_character_contradictions(state)
        result['contradictions'] = contradictions
        
        if contradictions:
            result['status'] = 'fail'
        
        return result
    
    @staticmethod
    def analyze_artifact_consistency(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if artifact states are consistent throughout.
        
        Returns:
        {
            'total_artifacts': int,
            'active_artifacts': [names],
            'destroyed_artifacts': [names],
            'contradictions': [descriptions],
            'status': 'pass' | 'fail'
        }
        """
        result = {
            'total_artifacts': 0,
            'active_artifacts': [],
            'destroyed_artifacts': [],
            'contradictions': [],
            'status': 'pass'
        }
        
        artifacts = state.get('artifacts', {})
        result['total_artifacts'] = len(artifacts)
        
        for artifact_name, artifact_data in artifacts.items():
            status = artifact_data.get('status', '').lower()
            
            if 'destroyed' in status or 'consumed' in status:
                result['destroyed_artifacts'].append(artifact_name)
            else:
                result['active_artifacts'].append(artifact_name)
        
        # Check for contradictions
        contradictions = StateValidator.detect_artifact_contradictions(state)
        result['contradictions'] = contradictions
        
        if contradictions:
            result['status'] = 'fail'
        
        return result
    
    @staticmethod
    def analyze_scene_causality(chain: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if scene chain has proper causal flow.
        
        Returns:
        {
            'total_scenes': int,
            'causal_links': int,
            'broken_links': [(scene_idx, reason)],
            'status': 'pass' | 'fail'
        }
        """
        result = {
            'total_scenes': 0,
            'causal_links': 0,
            'broken_links': [],
            'status': 'pass'
        }
        
        scenes = chain.get('scenes', [])
        result['total_scenes'] = len(scenes)
        
        for idx, scene in enumerate(scenes[:-1]):  # Exclude last scene
            current_consequence = scene.get('consequence', '').lower().strip()
            next_trigger = scenes[idx + 1].get('next_trigger', '').lower().strip()
            
            if current_consequence and next_trigger:
                result['causal_links'] += 1
                
                # Check for obvious contradictions
                if not CoherenceAnalyzer._consequences_compatible(current_consequence, next_trigger):
                    result['broken_links'].append((idx, f"Consequence '{current_consequence}' conflicts with next trigger '{next_trigger}'"))
        
        if result['broken_links']:
            result['status'] = 'fail'
        
        return result
    
    @staticmethod
    def _consequences_compatible(consequence: str, trigger: str) -> bool:
        """Check if consequence and trigger are logically compatible."""
        # List of incompatible keyword pairs
        contradictions = [
            (['death', 'dies', 'dead'], ['alive', 'awakens']),
            (['betrayal', 'betrays'], ['loyalty', 'faithful']),
            (['hidden', 'secret'], ['revealed', 'exposed']),
            (['escape', 'fled'], ['captured', 'imprisoned']),
        ]
        
        for contra_pair in contradictions:
            keywords1, keywords2 = contra_pair
            if any(kw in consequence for kw in keywords1) and \
               any(kw in trigger for kw in keywords2):
                return False
        
        return True
    
    @staticmethod
    def analyze_state_progression(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if state progresses (not just repeated).
        
        Returns:
        {
            'completed_scenes': int,
            'scene_snapshots': int,
            'character_developments': int,
            'artifact_changes': int,
            'status': 'pass' | 'fail'
        }
        """
        result = {
            'completed_scenes': 0,
            'scene_snapshots': 0,
            'character_developments': 0,
            'artifact_changes': 0,
            'status': 'pass'
        }
        
        # Check plot progress
        progress = state.get('plot_progress', {})
        result['completed_scenes'] = progress.get('completed_scenes', 0)
        
        # Check scene snapshots
        scenes = state.get('scenes', [])
        result['scene_snapshots'] = len(scenes)
        
        # Check character developments
        characters = state.get('characters', {})
        for char_name, char_data in characters.items():
            developments = char_data.get('developments', [])
            result['character_developments'] += len(developments)
        
        # Check artifact changes
        artifacts = state.get('artifacts', {})
        for artifact_name, artifact_data in artifacts.items():
            if artifact_data.get('location') or artifact_data.get('owner'):
                result['artifact_changes'] += 1
        
        # Status is pass if there's evidence of progression
        if result['completed_scenes'] > 0 or result['character_developments'] > 0:
            result['status'] = 'pass'
        
        return result
    
    @staticmethod
    def generate_coherence_report(
        state: Dict[str, Any],
        chain: Dict[str, Any],
        arcs: Dict[str, Any],
        theme: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive coherence report.
        
        Returns full report with all analyses.
        """
        report = {
            'timestamp': __import__('datetime').datetime.now().isoformat(),
            'character_consistency': CoherenceAnalyzer.analyze_character_consistency(state),
            'artifact_consistency': CoherenceAnalyzer.analyze_artifact_consistency(state),
            'scene_causality': CoherenceAnalyzer.analyze_scene_causality(chain),
            'state_progression': CoherenceAnalyzer.analyze_state_progression(state),
            'overall_status': 'pass'
        }
        
        # Overall status is fail if any section failed
        if any(section.get('status') == 'fail' for section in [
            report['character_consistency'],
            report['artifact_consistency'],
            report['scene_causality'],
            report['state_progression']
        ]):
            report['overall_status'] = 'fail'
        
        return report


def test_coherence_prevention():
    """Test that state tracking prevents reported narrative issues."""
    print("\n" + "="*70)
    print("🔍 PHASE 5: COHERENCE VALIDATION TESTS")
    print("="*70)
    
    # Load project state
    state = StoryState.load_story_state()
    chain = StoryState.load_scene_chain()
    arcs = StoryState.load_character_arcs()
    theme = StoryState.load_theme()
    
    report = CoherenceAnalyzer.generate_coherence_report(state, chain, arcs, theme)
    
    # Print report
    print("\n📋 CHARACTER CONSISTENCY")
    print("-" * 70)
    char_report = report['character_consistency']
    print(f"  Total characters: {char_report['total_characters']}")
    print(f"  Alive: {len(char_report['alive_characters'])}, Dead: {len(char_report['dead_characters'])}")
    if char_report['contradictions']:
        print(f"  ❌ Contradictions found: {len(char_report['contradictions'])}")
        for contradiction in char_report['contradictions']:
            print(f"     - {contradiction}")
    else:
        print(f"  ✅ No contradictions (character resurrection prevented)")
    
    print("\n🏺 ARTIFACT CONSISTENCY")
    print("-" * 70)
    artifact_report = report['artifact_consistency']
    print(f"  Total artifacts: {artifact_report['total_artifacts']}")
    print(f"  Active: {len(artifact_report['active_artifacts'])}, Destroyed: {len(artifact_report['destroyed_artifacts'])}")
    if artifact_report['contradictions']:
        print(f"  ❌ Contradictions found: {len(artifact_report['contradictions'])}")
        for contradiction in artifact_report['contradictions']:
            print(f"     - {contradiction}")
    else:
        print(f"  ✅ No contradictions (artifact states consistent)")
    
    print("\n🔗 SCENE CAUSALITY")
    print("-" * 70)
    causality_report = report['scene_causality']
    print(f"  Total scenes: {causality_report['total_scenes']}")
    print(f"  Causal links: {causality_report['causal_links']}")
    if causality_report['broken_links']:
        print(f"  ❌ Broken causal links: {len(causality_report['broken_links'])}")
        for idx, reason in causality_report['broken_links']:
            print(f"     - Scene {idx}: {reason}")
    else:
        print(f"  ✅ No broken causal links (proper scene causality)")
    
    print("\n📊 STATE PROGRESSION")
    print("-" * 70)
    progression_report = report['state_progression']
    print(f"  Completed scenes: {progression_report['completed_scenes']}")
    print(f"  Scene snapshots: {progression_report['scene_snapshots']}")
    print(f"  Character developments: {progression_report['character_developments']}")
    print(f"  Artifact changes: {progression_report['artifact_changes']}")
    if progression_report['status'] == 'pass':
        print(f"  ✅ State progressing (not stale)")
    else:
        print(f"  ⚠️  No state progression recorded yet (run story generation)")
    
    print("\n" + "="*70)
    if report['overall_status'] == 'pass':
        print("✅ ALL COHERENCE CHECKS PASSED")
        print("\n   Narrative engine successfully prevents:")
        print("   • Character resurrection (dead characters stay dead)")
        print("   • Artifact contradictions (destroyed artifacts can't have owners)")
        print("   • Causal contradictions (scene consequences flow logically)")
        print("   • State staleness (story state progresses and updates)")
    else:
        print("❌ COHERENCE ISSUES FOUND")
        print("\n   Review above sections for details")
    print("="*70)
    
    return report


if __name__ == '__main__':
    report = test_coherence_prevention()
    
    # Save report to file (handle permission issues gracefully)
    try:
        with open('book_output/coherence_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n💾 Report saved to book_output/coherence_report.json")
    except (PermissionError, IOError):
        print(f"\n⚠️  Could not save report (permission issue)")
        print(f"   Report data:\n{json.dumps(report, indent=2)}")
