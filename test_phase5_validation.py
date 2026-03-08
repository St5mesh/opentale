#!/usr/bin/env python3
"""
Phase 5 Validation Tests

Tests for:
1. Data structure integrity (story state, scene chain, character arcs, theme)
2. Persistence (save/load cycles)
3. Backward compatibility (loading projects without state files)
4. Auto-repair functionality
"""

import json
import os
import tempfile
import shutil
from story_state import StoryState
from state_validator import StateValidator


class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def add_pass(self, test_name, details=""):
        self.passed += 1
        self.tests.append(("PASS", test_name, details))
        print(f"✅ {test_name}")
        if details:
            print(f"   {details}")
    
    def add_fail(self, test_name, error):
        self.failed += 1
        self.tests.append(("FAIL", test_name, error))
        print(f"❌ {test_name}")
        print(f"   Error: {error}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"Test Summary: {self.passed}/{total} passed")
        print(f"{'='*60}")
        return self.failed == 0


def test_story_state_validation():
    """Test story state validation logic"""
    results = TestResults()
    
    print("\n📋 STORY STATE VALIDATION TESTS")
    print("-" * 60)
    
    # Test 1: Valid state passes validation
    valid_state = StoryState.initialize_story_state()
    is_valid, issues = StateValidator.validate_story_state(valid_state)
    if is_valid:
        results.add_pass("Valid state passes validation", f"No issues found")
    else:
        results.add_fail("Valid state passes validation", f"Issues: {issues}")
    
    # Test 2: Missing required fields detected
    invalid_state = {'characters': {}}  # Missing required fields
    is_valid, issues = StateValidator.validate_story_state(invalid_state)
    if not is_valid and len(issues) > 0:
        results.add_pass("Missing fields detected", f"Found {len(issues)} issues")
    else:
        results.add_fail("Missing fields detected", "No issues reported for incomplete state")
    
    # Test 3: Invalid data types detected
    bad_state = StoryState.initialize_story_state()
    bad_state['plot_progress']['current_chapter'] = "not_an_int"
    is_valid, issues = StateValidator.validate_story_state(bad_state)
    if not is_valid:
        results.add_pass("Invalid data types detected", f"Found {len(issues)} issues")
    else:
        results.add_fail("Invalid data types detected", "Type errors not caught")
    
    # Test 4: Negative values detected
    bad_state = StoryState.initialize_story_state()
    bad_state['plot_progress']['completed_scenes'] = -5
    is_valid, issues = StateValidator.validate_story_state(bad_state)
    if not is_valid:
        results.add_pass("Negative values detected", f"Found {len(issues)} issues")
    else:
        results.add_fail("Negative values detected", "Negative values not caught")
    
    # Test 5: Auto-repair creates missing fields
    repair_state = {'characters': {}}
    repaired, repairs = StateValidator.repair_state(repair_state)
    if 'plot_progress' in repaired and 'artifacts' in repaired:
        results.add_pass("Auto-repair creates missing fields", f"Made {len(repairs)} repairs")
    else:
        results.add_fail("Auto-repair creates missing fields", "Repair incomplete")
    
    return results


def test_scene_chain_validation():
    """Test scene chain validation logic"""
    results = TestResults()
    
    print("\n🔗 SCENE CHAIN VALIDATION TESTS")
    print("-" * 60)
    
    # Test 1: Valid chain passes validation
    valid_chain = StoryState.initialize_scene_chain()
    valid_chain['scenes'] = [
        {
            'goal': 'Meet the mentor',
            'conflict': 'Mentor is suspicious',
            'outcome': 'Mentor agrees to help',
            'consequence': 'Hero gains knowledge',
            'next_trigger': 'Hero ready to face challenge'
        }
    ]
    valid_chain['total_scenes'] = 1
    is_valid, issues = StateValidator.validate_scene_chain(valid_chain)
    if is_valid:
        results.add_pass("Valid chain passes validation", "No issues found")
    else:
        results.add_fail("Valid chain passes validation", f"Issues: {issues}")
    
    # Test 2: Missing required scene fields detected
    bad_chain = StoryState.initialize_scene_chain()
    bad_chain['scenes'] = [{'goal': 'Test'}]  # Missing fields
    is_valid, issues = StateValidator.validate_scene_chain(bad_chain)
    if not is_valid:
        results.add_pass("Missing scene fields detected", f"Found {len(issues)} issues")
    else:
        results.add_fail("Missing scene fields detected", "Missing fields not caught")
    
    # Test 3: total_scenes mismatch detected
    bad_chain = StoryState.initialize_scene_chain()
    bad_chain['total_scenes'] = 5
    bad_chain['scenes'] = []  # No scenes but total_scenes=5
    is_valid, issues = StateValidator.validate_scene_chain(bad_chain)
    if not is_valid:
        results.add_pass("total_scenes mismatch detected", f"Found {len(issues)} issues")
    else:
        results.add_fail("total_scenes mismatch detected", "Mismatch not caught")
    
    # Test 4: Auto-repair fixes total_scenes
    repair_chain = StoryState.initialize_scene_chain()
    repair_chain['total_scenes'] = 10
    repair_chain['scenes'] = [{'goal': 'x'} for _ in range(3)]  # Mismatch
    repaired, repairs = StateValidator.repair_scene_chain(repair_chain)
    if repaired['total_scenes'] == 3:
        results.add_pass("Auto-repair fixes total_scenes", f"Corrected to {repaired['total_scenes']}")
    else:
        results.add_fail("Auto-repair fixes total_scenes", f"Still {repaired['total_scenes']}")
    
    return results


def test_character_arcs_validation():
    """Test character arcs validation logic"""
    results = TestResults()
    
    print("\n👤 CHARACTER ARCS VALIDATION TESTS")
    print("-" * 60)
    
    # Test 1: Valid arcs pass validation
    valid_arcs = StoryState.initialize_character_arcs()
    valid_arcs['characters']['Kai'] = {
        'arc_stages': ['reluctant', 'awakening', 'corrupted', 'redeemed'],
        'current_stage': 1
    }
    is_valid, issues = StateValidator.validate_character_arcs(valid_arcs)
    if is_valid:
        results.add_pass("Valid arcs pass validation", "No issues found")
    else:
        results.add_fail("Valid arcs pass validation", f"Issues: {issues}")
    
    # Test 2: Missing arc_stages detected
    bad_arcs = StoryState.initialize_character_arcs()
    bad_arcs['characters']['Kai'] = {'current_stage': 0}  # Missing arc_stages
    is_valid, issues = StateValidator.validate_character_arcs(bad_arcs)
    if not is_valid:
        results.add_pass("Missing arc_stages detected", f"Found {len(issues)} issues")
    else:
        results.add_fail("Missing arc_stages detected", "Missing field not caught")
    
    # Test 3: Empty arc_stages detected
    bad_arcs = StoryState.initialize_character_arcs()
    bad_arcs['characters']['Kai'] = {
        'arc_stages': [],  # Empty
        'current_stage': 0
    }
    is_valid, issues = StateValidator.validate_character_arcs(bad_arcs)
    if not is_valid:
        results.add_pass("Empty arc_stages detected", f"Found {len(issues)} issues")
    else:
        results.add_fail("Empty arc_stages detected", "Empty array not caught")
    
    # Test 4: current_stage out of range detected
    bad_arcs = StoryState.initialize_character_arcs()
    bad_arcs['characters']['Kai'] = {
        'arc_stages': ['stage1', 'stage2'],
        'current_stage': 5  # Out of range
    }
    is_valid, issues = StateValidator.validate_character_arcs(bad_arcs)
    if not is_valid:
        results.add_pass("Out-of-range stage detected", f"Found {len(issues)} issues")
    else:
        results.add_fail("Out-of-range stage detected", "Invalid stage not caught")
    
    return results


def test_contradiction_detection():
    """Test detection of contradictions in state"""
    results = TestResults()
    
    print("\n⚠️  CONTRADICTION DETECTION TESTS")
    print("-" * 60)
    
    # Test 1: Dead character with active developments
    state = StoryState.initialize_story_state()
    state['characters']['Silas'] = {
        'status': 'dead',
        'developments': ['Silas learns magic and lives on']
    }
    contradictions = StateValidator.detect_character_contradictions(state)
    if len(contradictions) > 0:
        results.add_pass("Dead character contradiction detected", f"Found {len(contradictions)} contradictions")
    else:
        results.add_fail("Dead character contradiction detected", "Contradiction not detected")
    
    # Test 2: Destroyed artifact with owner
    state = StoryState.initialize_story_state()
    state['artifacts']['Sword'] = {
        'status': 'destroyed',
        'owner': 'Kai',
        'location': 'Castle'
    }
    contradictions = StateValidator.detect_artifact_contradictions(state)
    if len(contradictions) > 0:
        results.add_pass("Destroyed artifact contradiction detected", f"Found {len(contradictions)} contradictions")
    else:
        results.add_fail("Destroyed artifact contradiction detected", "Contradiction not detected")
    
    return results


def test_persistence_cycle():
    """Test save/load persistence cycles"""
    results = TestResults()
    
    print("\n💾 PERSISTENCE CYCLE TESTS")
    print("-" * 60)
    
    # Create temporary directory for testing
    test_dir = tempfile.mkdtemp()
    original_state_file = StoryState.STATE_FILE
    original_chain_file = StoryState.CHAIN_FILE
    
    try:
        # Override file paths for testing
        StoryState.STATE_FILE = os.path.join(test_dir, 'story_state.json')
        StoryState.CHAIN_FILE = os.path.join(test_dir, 'scene_chain.json')
        
        # Test 1: Save and load state cycle
        original_state = StoryState.initialize_story_state()
        original_state['characters']['Kai'] = {'status': 'alive'}
        original_state['plot_progress']['completed_scenes'] = 5
        
        StoryState.save_story_state(original_state)
        loaded_state = StoryState.load_story_state()
        
        if loaded_state == original_state:
            results.add_pass("Save/load state cycle", "State preserved exactly")
        else:
            results.add_fail("Save/load state cycle", "State changed after cycle")
        
        # Test 2: Save/load with backup
        modified_state = loaded_state.copy()
        modified_state['plot_progress']['completed_scenes'] = 10
        
        success = StoryState.save_with_backup(StoryState.STATE_FILE, modified_state)
        if success and os.path.exists(StoryState.STATE_FILE + '.backup'):
            results.add_pass("Save with backup created", "Backup file exists")
        else:
            results.add_fail("Save with backup created", "Backup not created")
        
        # Test 3: Persistence across multiple saves
        states = []
        for i in range(3):
            state = StoryState.initialize_story_state()
            state['plot_progress']['completed_scenes'] = i
            states.append(state)
            StoryState.save_story_state(state)
        
        final_loaded = StoryState.load_story_state()
        if final_loaded['plot_progress']['completed_scenes'] == 2:
            results.add_pass("Multiple save cycles", "Last saved state preserved")
        else:
            results.add_fail("Multiple save cycles", "State not preserved correctly")
        
    finally:
        # Restore original file paths and cleanup
        StoryState.STATE_FILE = original_state_file
        StoryState.CHAIN_FILE = original_chain_file
        shutil.rmtree(test_dir)
    
    return results


def test_backward_compatibility():
    """Test backward compatibility with existing projects"""
    results = TestResults()
    
    print("\n🔄 BACKWARD COMPATIBILITY TESTS")
    print("-" * 60)
    
    # Test 1: Load nonexistent state creates defaults
    test_dir = tempfile.mkdtemp()
    original_state_file = StoryState.STATE_FILE
    
    try:
        StoryState.STATE_FILE = os.path.join(test_dir, 'story_state.json')
        
        # Load from nonexistent file
        state = StoryState.load_story_state()
        
        if state and 'characters' in state and 'plot_progress' in state:
            results.add_pass("Nonexistent state creates defaults", "Default structure created")
        else:
            results.add_fail("Nonexistent state creates defaults", "Invalid default structure")
        
    finally:
        StoryState.STATE_FILE = original_state_file
        shutil.rmtree(test_dir)
    
    # Test 2: Corrupted JSON file falls back to default
    test_dir = tempfile.mkdtemp()
    StoryState.STATE_FILE = os.path.join(test_dir, 'story_state.json')
    
    try:
        # Create corrupted JSON file
        with open(StoryState.STATE_FILE, 'w') as f:
            f.write("{ invalid json content ]}")
        
        state = StoryState.load_story_state()
        
        if state and 'characters' in state:
            results.add_pass("Corrupted JSON falls back to default", "Recovered gracefully")
        else:
            results.add_fail("Corrupted JSON falls back to default", "Did not recover")
        
    finally:
        StoryState.STATE_FILE = original_state_file
        shutil.rmtree(test_dir)
    
    # Test 3: Validation report generation
    state = StoryState.initialize_story_state()
    chain = StoryState.initialize_scene_chain()
    arcs = StoryState.initialize_character_arcs()
    theme = StoryState.initialize_theme()
    
    report = StateValidator.full_validation_report(state, chain, arcs, theme)
    
    if report and 'overall_valid' in report and 'story_state' in report:
        results.add_pass("Validation report generation", f"Report has all sections")
    else:
        results.add_fail("Validation report generation", "Report incomplete")
    
    return results


def main():
    """Run all Phase 5 validation tests"""
    print("\n" + "="*60)
    print("🔍 PHASE 5: PERSISTENCE & VALIDATION TESTS")
    print("="*60)
    
    all_results = []
    
    # Run test suites
    all_results.append(test_story_state_validation())
    all_results.append(test_scene_chain_validation())
    all_results.append(test_character_arcs_validation())
    all_results.append(test_contradiction_detection())
    all_results.append(test_persistence_cycle())
    all_results.append(test_backward_compatibility())
    
    # Print summary
    print("\n" + "="*60)
    total_passed = sum(r.passed for r in all_results)
    total_failed = sum(r.failed for r in all_results)
    total_tests = total_passed + total_failed
    
    print(f"📊 OVERALL RESULTS: {total_passed}/{total_tests} tests passed")
    if total_failed == 0:
        print("✅ ALL TESTS PASSED - Phase 5 validation layer ready!")
    else:
        print(f"❌ {total_failed} tests failed - review above for details")
    print("="*60)
    
    return total_failed == 0


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
