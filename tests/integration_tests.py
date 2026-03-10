#!/usr/bin/env python3
"""
Phase 6: Integration Testing Framework

Tests the complete narrative engine pipeline:
1. Theme extraction and validation
2. Character arc generation
3. Scene chain planning with causality
4. Full story state initialization
5. Scene coherence validation

This framework verifies that all components work together correctly
and that the narrative engine solves all reported coherence issues.
"""

import json
import os
import sys
import time
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

# Import narrative engine components
from story_state import StoryState
from state_validator import StateValidator
from tests.test_coherence_validation import CoherenceAnalyzer
from migration_helper import MigrationHelper


@dataclass
class TestResult:
    """Container for a single test result."""
    test_name: str
    passed: bool
    message: str
    duration: float
    details: Dict[str, Any] = None


class IntegrationTestFramework:
    """Framework for integration testing the narrative engine."""
    
    def __init__(self, test_name: str = "Integration Test"):
        self.test_name = test_name
        self.results: List[TestResult] = []
        self.start_time = None
        self.end_time = None
    
    def run_test(self, test_func, test_name: str) -> TestResult:
        """
        Run a single test and capture results.
        
        Args:
            test_func: Function to run (should return (passed, message, details))
            test_name: Name of the test
        
        Returns:
            TestResult with pass/fail status
        """
        start = time.time()
        try:
            passed, message, details = test_func()
            duration = time.time() - start
            result = TestResult(test_name, passed, message, duration, details)
            self.results.append(result)
            return result
        except Exception as e:
            duration = time.time() - start
            result = TestResult(
                test_name, 
                False, 
                f"Exception: {str(e)}", 
                duration,
                {'exception': str(e)}
            )
            self.results.append(result)
            return result
    
    def print_result(self, result: TestResult):
        """Print a test result in readable format."""
        status = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"{status} | {result.test_name} ({result.duration:.2f}s)")
        if result.message:
            print(f"      {result.message}")
        if result.details:
            for key, value in result.details.items():
                if key != 'exception':
                    print(f"      {key}: {value}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all test results."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        total_time = sum(r.duration for r in self.results)
        
        return {
            'total_tests': total,
            'passed': passed,
            'failed': failed,
            'pass_rate': f"{100 * passed / total:.1f}%" if total > 0 else "N/A",
            'total_duration': f"{total_time:.2f}s",
            'timestamp': datetime.now().isoformat()
        }
    
    def print_summary(self):
        """Print test summary."""
        summary = self.get_summary()
        print("\n" + "="*70)
        print("📊 TEST SUMMARY")
        print("="*70)
        print(f"Total tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Pass rate: {summary['pass_rate']}")
        print(f"Total duration: {summary['total_duration']}")
        print("="*70)
        
        return summary['failed'] == 0


class IntegrationTests:
    """Integration tests for narrative engine."""
    
    @staticmethod
    def test_state_file_initialization() -> Tuple[bool, str, Dict]:
        """Test that state files initialize correctly."""
        try:
            # Check that all state files can be loaded/created
            state = StoryState.load_story_state()
            chain = StoryState.load_scene_chain()
            arcs = StoryState.load_character_arcs()
            theme = StoryState.load_theme()
            
            # Verify structure
            assert 'characters' in state, "Missing characters in state"
            assert 'scenes' in chain, "Missing scenes in chain"
            assert 'characters' in arcs, "Missing characters in arcs"
            assert 'theme_statement' in theme, "Missing theme_statement"
            
            details = {
                'state_keys': list(state.keys()),
                'chain_keys': list(chain.keys()),
                'arcs_keys': list(arcs.keys()),
                'theme_keys': list(theme.keys())
            }
            
            return True, "All state files initialized correctly", details
        except Exception as e:
            return False, f"State initialization failed: {e}", {}
    
    @staticmethod
    def test_state_validation() -> Tuple[bool, str, Dict]:
        """Test that state validation works correctly."""
        try:
            state = StoryState.load_story_state()
            chain = StoryState.load_scene_chain()
            arcs = StoryState.load_character_arcs()
            theme = StoryState.load_theme()
            
            # Validate all components
            state_valid, state_issues = StateValidator.validate_story_state(state)
            chain_valid, chain_issues = StateValidator.validate_scene_chain(chain)
            arcs_valid, arcs_issues = StateValidator.validate_character_arcs(arcs)
            theme_valid, theme_issues = StateValidator.validate_theme(theme)
            
            all_valid = state_valid and chain_valid and arcs_valid and theme_valid
            
            details = {
                'state_valid': state_valid,
                'chain_valid': chain_valid,
                'arcs_valid': arcs_valid,
                'theme_valid': theme_valid,
                'issues': (state_issues + chain_issues + arcs_issues + theme_issues)[:3]
            }
            
            if not all_valid:
                return False, f"Validation found {len(details['issues'])} issues", details
            
            return True, "All state files pass validation", details
        except Exception as e:
            return False, f"Validation test failed: {e}", {}
    
    @staticmethod
    def test_character_arc_structure() -> Tuple[bool, str, Dict]:
        """Test that character arcs have proper structure."""
        try:
            arcs = StoryState.load_character_arcs()
            
            # Create test character arcs
            test_char_arcs = {
                'characters': {
                    'TestCharacter': {
                        'arc_stages': ['Stage 1', 'Stage 2', 'Stage 3'],
                        'current_stage': 0
                    }
                }
            }
            
            # Validate test arcs
            valid, issues = StateValidator.validate_character_arcs(test_char_arcs)
            
            if not valid:
                return False, f"Character arc validation failed: {issues}", {}
            
            details = {
                'test_character': 'TestCharacter',
                'stages': test_char_arcs['characters']['TestCharacter']['arc_stages'],
                'current_stage': test_char_arcs['characters']['TestCharacter']['current_stage']
            }
            
            return True, "Character arc structure is valid", details
        except Exception as e:
            return False, f"Character arc test failed: {e}", {}
    
    @staticmethod
    def test_scene_chain_causality() -> Tuple[bool, str, Dict]:
        """Test that scene chains maintain causal integrity."""
        try:
            # Create test scene chain
            test_chain = {
                'version': '1.0',
                'total_scenes': 3,
                'scenes': [
                    {
                        'goal': 'Hero learns of danger',
                        'conflict': 'Threat is overwhelming',
                        'outcome': 'Hero gains courage',
                        'consequence': 'Hero is motivated to act',
                        'next_trigger': 'Hero prepares for battle'
                    },
                    {
                        'goal': 'Hero prepares for battle',
                        'conflict': 'Preparation is incomplete',
                        'outcome': 'Hero finds an ally',
                        'consequence': 'Hero has backup for fight',
                        'next_trigger': 'Final battle begins'
                    },
                    {
                        'goal': 'Final battle with enemy',
                        'conflict': 'Enemy is powerful',
                        'outcome': 'Heroes work together',
                        'consequence': 'Enemy is defeated',
                        'next_trigger': 'Victory and aftermath'
                    }
                ],
                'approved': True
            }
            
            # Validate causal chain
            valid, issues = StateValidator.validate_scene_chain(test_chain)
            
            if not valid:
                return False, f"Scene chain validation failed: {issues}", {}
            
            # Verify causal flow
            causality_result = CoherenceAnalyzer.analyze_scene_causality(test_chain)
            
            if causality_result['status'] != 'pass':
                return False, f"Causal flow broken: {causality_result['broken_links']}", {}
            
            details = {
                'total_scenes': test_chain['total_scenes'],
                'causal_links': causality_result['causal_links'],
                'status': causality_result['status']
            }
            
            return True, "Scene chain causality is intact", details
        except Exception as e:
            return False, f"Scene chain test failed: {e}", {}
    
    @staticmethod
    def test_contradiction_detection() -> Tuple[bool, str, Dict]:
        """Test that contradictions are properly detected."""
        try:
            # Create state with deliberate contradictions
            test_state = {
                'characters': {
                    'DeadHero': {
                        'status': 'dead',
                        'developments': ['DeadHero returns and saves the day']  # Contradiction!
                    }
                },
                'artifacts': {
                    'DestroyedSword': {
                        'status': 'destroyed',
                        'owner': 'DeadHero',  # Contradiction!
                        'location': 'Vault'
                    }
                },
                'world': {},
                'scenes': [],
                'plot_progress': {'current_chapter': 0, 'current_scene': 0, 'completed_scenes': 0}
            }
            
            # Check contradictions are detected
            char_contradictions = StateValidator.detect_character_contradictions(test_state)
            artifact_contradictions = StateValidator.detect_artifact_contradictions(test_state)
            
            found_contradictions = len(char_contradictions) > 0 or len(artifact_contradictions) > 0
            
            if not found_contradictions:
                return False, "Failed to detect contradictions in test state", {}
            
            details = {
                'character_contradictions': len(char_contradictions),
                'artifact_contradictions': len(artifact_contradictions),
                'total': len(char_contradictions) + len(artifact_contradictions)
            }
            
            return True, f"Successfully detected {details['total']} contradictions", details
        except Exception as e:
            return False, f"Contradiction detection test failed: {e}", {}
    
    @staticmethod
    def test_coherence_scoring() -> Tuple[bool, str, Dict]:
        """Test coherence scoring on realistic narrative."""
        try:
            # Create realistic test narrative
            state = {
                'theme': 'Courage in face of darkness',
                'characters': {
                    'Kai': {
                        'status': 'alive',
                        'developments': [
                            'Kai is a skilled warrior',
                            'Kai discovers her inner power',
                            'Kai becomes a legend'
                        ]
                    },
                    'Sage': {
                        'status': 'alive',
                        'developments': [
                            'Sage provides wisdom',
                            'Sage sacrifices knowledge for victory'
                        ]
                    }
                },
                'artifacts': {
                    'Sword of Legends': {
                        'status': 'active',
                        'owner': 'Kai',
                        'location': 'In Kai\'s hands'
                    }
                },
                'world': {'realm': {'status': 'peaceful', 'details': 'Realm is at peace'}},
                'scenes': [
                    {'title': 'Beginning', 'chapter': 1},
                    {'title': 'Discovery', 'chapter': 2},
                    {'title': 'Victory', 'chapter': 3}
                ],
                'plot_progress': {
                    'current_chapter': 3,
                    'current_scene': 3,
                    'completed_scenes': 3
                }
            }
            
            chain = {
                'version': '1.0',
                'total_scenes': 3,
                'scenes': [
                    {
                        'goal': 'Introduce Kai',
                        'conflict': 'Darkness threatens',
                        'outcome': 'Kai is called to action',
                        'consequence': 'Journey begins',
                        'next_trigger': 'Sage appears'
                    },
                    {
                        'goal': 'Sage trains Kai',
                        'conflict': 'Power is overwhelming',
                        'outcome': 'Kai gains control',
                        'consequence': 'Kai is ready',
                        'next_trigger': 'Final confrontation'
                    },
                    {
                        'goal': 'Kai defeats darkness',
                        'conflict': 'Final battle is fierce',
                        'outcome': 'Good prevails',
                        'consequence': 'Peace is restored',
                        'next_trigger': 'Story concludes'
                    }
                ]
            }
            
            arcs = {
                'characters': {
                    'Kai': {
                        'arc_stages': ['Ordinary', 'Called to Adventure', 'Transformed', 'Champion'],
                        'current_stage': 3
                    }
                }
            }
            
            theme = {
                'theme_statement': 'Courage in face of darkness',
                'core_conflict': 'Good vs. Evil',
                'moral_tension': 'Is sacrifice necessary?',
                'approved': True
            }
            
            # Generate coherence report
            report = CoherenceAnalyzer.generate_coherence_report(state, chain, arcs, theme)
            
            if report['overall_status'] != 'pass':
                return False, f"Coherence check failed: {report}", {}
            
            details = {
                'character_consistency': report['character_consistency']['status'],
                'artifact_consistency': report['artifact_consistency']['status'],
                'scene_causality': report['scene_causality']['status'],
                'state_progression': report['state_progression']['status'],
                'overall': report['overall_status']
            }
            
            return True, "Narrative coherence verified", details
        except Exception as e:
            return False, f"Coherence scoring test failed: {e}", {}
    
    @staticmethod
    def test_persistence_across_restarts() -> Tuple[bool, str, Dict]:
        """Test that state persists across save/load cycles."""
        try:
            import tempfile
            import shutil
            
            # Use temporary directory to avoid permission issues
            test_dir = tempfile.mkdtemp()
            original_state_file = StoryState.STATE_FILE
            
            try:
                # Override state file location
                StoryState.STATE_FILE = os.path.join(test_dir, 'story_state.json')
                
                # Create test state
                original_state = StoryState.initialize_story_state()
                original_state['characters']['TestChar'] = {
                    'status': 'alive',
                    'developments': ['Test development']
                }
                original_state['plot_progress']['completed_scenes'] = 5
                
                # Save
                StoryState.save_story_state(original_state)
                
                # Load
                loaded_state = StoryState.load_story_state()
                
                # Verify integrity
                if loaded_state != original_state:
                    return False, "State changed after save/load cycle", {}
                
                if loaded_state['characters']['TestChar']['status'] != 'alive':
                    return False, "Character status not preserved", {}
                
                if loaded_state['plot_progress']['completed_scenes'] != 5:
                    return False, "Progress not preserved", {}
                
                details = {
                    'characters_preserved': 'TestChar' in loaded_state['characters'],
                    'status_preserved': loaded_state['characters']['TestChar']['status'] == 'alive',
                    'progress_preserved': loaded_state['plot_progress']['completed_scenes'] == 5
                }
                
                return True, "State correctly preserved across cycles", details
            finally:
                # Restore original file path and cleanup
                StoryState.STATE_FILE = original_state_file
                shutil.rmtree(test_dir)
        except Exception as e:
            return False, f"Persistence test failed: {e}", {}
    
    @staticmethod
    def test_backward_compatibility() -> Tuple[bool, str, Dict]:
        """Test backward compatibility with existing projects."""
        try:
            # Check migration status
            status = MigrationHelper.get_migration_status()
            
            # Test basic file detection
            has_basic = MigrationHelper.project_has_basic_files()
            has_state = MigrationHelper.project_has_state_files()
            
            details = {
                'has_basic_files': has_basic,
                'has_state_files': has_state,
                'recommended_actions': status['recommended_actions'],
                'chapters': status['chapters_count']
            }
            
            # Backward compatibility means old projects should work
            # Either they have state files or they can be migrated
            compatible = has_state or (has_basic and status['recommended_actions'])
            
            if not compatible:
                return False, "Project not backward compatible", details
            
            return True, "Backward compatibility maintained", details
        except Exception as e:
            return False, f"Backward compatibility test failed: {e}", {}


def run_integration_tests():
    """Run all integration tests."""
    print("\n" + "="*70)
    print("🧪 PHASE 6: INTEGRATION TESTING")
    print("="*70)
    
    framework = IntegrationTestFramework("Narrative Engine Integration Tests")
    
    # Run all tests
    tests = [
        (IntegrationTests.test_state_file_initialization, "State file initialization"),
        (IntegrationTests.test_state_validation, "State validation"),
        (IntegrationTests.test_character_arc_structure, "Character arc structure"),
        (IntegrationTests.test_scene_chain_causality, "Scene chain causality"),
        (IntegrationTests.test_contradiction_detection, "Contradiction detection"),
        (IntegrationTests.test_coherence_scoring, "Coherence scoring"),
        (IntegrationTests.test_persistence_across_restarts, "Persistence across restarts"),
        (IntegrationTests.test_backward_compatibility, "Backward compatibility"),
    ]
    
    print("\nRunning integration tests...\n")
    
    for test_func, test_name in tests:
        result = framework.run_test(test_func, test_name)
        framework.print_result(result)
    
    # Print summary
    success = framework.print_summary()
    
    return framework.get_summary(), success


if __name__ == '__main__':
    summary, success = run_integration_tests()
    
    # Print detailed summary
    print("\n📊 INTEGRATION TEST REPORT")
    print("="*70)
    print(f"Tests run: {summary['total_tests']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Success rate: {summary['pass_rate']}")
    print(f"Duration: {summary['total_duration']}")
    print("="*70)
    
    if success:
        print("\n✅ ALL INTEGRATION TESTS PASSED")
        print("\nThe narrative engine is ready for production deployment!")
    else:
        print("\n❌ SOME INTEGRATION TESTS FAILED")
        print("\nReview failures above before deployment")
    
    exit(0 if success else 1)
