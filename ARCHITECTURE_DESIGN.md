# OpenTale: Automated State Management & Validation Architecture

## Overview

This document describes a comprehensive 4-stage architecture to overcome current limitations in the narrative engine:

### Current Limitations Being Addressed
- ❌ Manual state updates (no automation)
- ❌ No validation of generated content
- ❌ One-way generation flow (can't regenerate easily)
- ❌ Manual merging logic between scenes
- ❌ Scenes lack detailed context about prior events

### Proposed Solution: 4-Stage Process
- ✅ Automated state extraction from generated scenes
- ✅ Multi-level validation (local per-scene, global per-chapter)
- ✅ Per-chapter contextual scene planning (not global)
- ✅ Automatic merging with consistency guarantees
- ✅ Full story state tracking throughout book

---

## Architecture: 4 Stages

### Stage 1: Initial State Generation (Outline Finalization)

**When:** User finalizes the outline on the outline page  
**Goal:** Extract and create baseline story states  
**Outputs:** Initial states that serve as foundation for all chapters

**Generated States:**
- Character states (status, location, knowledge, relationships, inventory)
- Artifact states (location, owner, significance)
- World element states (status, key locations, inhabitants)
- Character arcs (development stages)
- Theme extraction (statement, conflicts, moral tensions)

**Implementation:**
- New endpoint: `POST /finalize_outline_with_states`
- New methods in `BookAgents`:
  - `extract_character_initial_states(char_text) → Dict`
  - `extract_artifacts_from_world(world_text, char_text) → Dict`
  - `extract_world_elements(world_text) → Dict`
  - `extract_theme_from_outline(outline) → Dict`
  - `extract_character_arcs(outline, characters) → Dict`

---

### Stage 2: Per-Chapter Scene Chain (On-Demand Planning)

**When:** User opens a chapter for editing  
**Goal:** Generate chapter-specific scene chains with current context  
**Trigger:** On-demand when user clicks "Edit Chapter X"  
**Key Difference:** NOT global planning upfront, contextual per-chapter

**Generated Scene Chain:**
```json
{
  "chapter_number": 3,
  "from_state": {
    "chapter": 2,
    "scene": 8,
    "snapshot": "Chapter 2 ended with: Alice is confident, has amulet, location: tower"
  },
  "scenes": [
    {
      "scene_number": 9,
      "title": "Tower Ascent",
      "goal": "Alice must reach second floor",
      "conflict": "Guardian spirit blocks entrance",
      "outcome": "She convinces guardian of her purpose",
      "prerequisites": {
        "characters_present": ["Alice", "Guardian Spirit"],
        "character_states": {"Alice": "knows_magic"},
        "artifacts_needed": ["Magic Amulet"],
        "location": "Tower Interior"
      }
    }
  ]
}
```

**Implementation:**
- New endpoint: `POST /generate_chapter_scene_chain/<chapter_num>`
- New method in `BookAgents`:
  - `plan_chapter_scene_chain(outline, world, characters, state, position) → List[Scene]`
- New prompt: `CHAPTER_SCENE_CHAIN_PROMPT`
- Saved as: `book_output/chapter_N_scene_chain.json`

---

### Stage 3: Scene Generation + State Extraction

**When:** User generates individual scenes  
**Goal:** Generate scene content AND automatically extract state changes  
**Process:** 4 sub-phases per scene

**Phase 3A: Generate Scene**
- Input: Scene goal, conflict, outcome, current story state, context
- Output: Generated scene content (~1000 words)

**Phase 3B: Extract State Changes**
- LLM reads generated scene and identifies:
  - Character developments (status changes, knowledge gained)
  - Artifact movements and transformations
  - World state changes
  - New facts learned
- Outputs structured JSON of changes

**Phase 3C: Validate Locally**
- Check for obvious contradictions
- Verify characters mentioned exist
- Verify artifact transitions make sense
- Flag warnings

**Phase 3D: Apply to Story State**
- Auto-update `story_state.json` with extracted changes
- Track timestamps (when/where each change occurred)
- Update character developments, locations, knowledge

**Implementation:**
- Updated endpoint: `POST /generate_scene`
- New method in `BookAgents`:
  - `extract_scene_state_changes(scene_content, scene_goal, state) → Dict`
- New method in `StoryState`:
  - `apply_extracted_changes(state, changes, scene_num) → Dict`
- New prompt: `STATE_EXTRACTION_PROMPT`
- New agent type: "state_extractor"

**Extraction Output Example:**
```json
{
  "characters": [
    {
      "name": "Alice",
      "previous_state": {"status": "learning", "location": "tower_base"},
      "new_state": {"status": "confident", "location": "tower_floor_2"},
      "events": ["convinced guardian", "unlocked new power"]
    }
  ],
  "artifacts": [
    {
      "name": "Magic Amulet",
      "previous_state": {"status": "inert"},
      "new_state": {"status": "glowing"},
      "event": "activated during confrontation"
    }
  ],
  "world": [
    {
      "element": "Tower Interior Floor 2",
      "previous_state": {"status": "sealed"},
      "new_state": {"status": "accessible"},
      "change": "Guardian allows passage"
    }
  ]
}
```

---

### Stage 4: Chapter Coherence Validation & Merging

**When:** User completes all scenes in a chapter  
**Goal:** Validate all scenes together, detect contradictions, merge into final chapter  
**Trigger:** User clicks "Finalize Chapter"

**Validation Checks:**

1. **Character Timelines**
   - No dead characters appearing later
   - Location changes are logical
   - Status changes follow logical progression

2. **Artifact Tracking**
   - No artifact in two places simultaneously
   - Owner changes are consistent
   - Items aren't used after being destroyed

3. **World State**
   - Environmental changes are logical
   - Destroyed locations don't magically repair
   - Settlement descriptions remain consistent

4. **Setting Consistency**
   - All mentioned locations actually exist
   - Context matches between scenes in same location
   - Setting descriptions align across chapter

5. **Character Presence**
   - All mentioned characters are defined
   - Characters present match scene prerequisites
   - No undefined NPCs mentioned

**Implementation:**
- New file: `enhanced_state_validator.py`
- Methods in `EnhancedStateValidator`:
  - `check_character_timeline(scenes, state, chain) → {valid, issues}`
  - `check_artifact_consistency(scenes, state, chain) → {valid, issues}`
  - `check_world_state(scenes, state, chain) → {valid, issues}`
  - `check_setting_consistency(scenes, chain) → {valid, issues}`
  - `check_character_presence(scenes, chain, state) → {valid, issues}`
- New endpoint: `POST /validate_chapter/<chapter_num>`
- New function: `merge_scenes_to_chapter(scenes, chapter_num) → final_text`

---

## Data Flow: Complete Example

```
User creates outline
    ↓
[STAGE 1] User finalizes outline
    ├─ Extract character initial states
    ├─ Extract artifact states
    ├─ Extract world states
    ├─ Extract theme & conflicts
    └─ Save: story_state.json, character_arcs.json, theme.json

    ↓
User clicks "Edit Chapter 3"
    ↓
[STAGE 2] Generate per-chapter scene chain
    ├─ Load: story_state (where we are)
    ├─ Load: chapter 3 outline
    ├─ LLM generates: 4-8 scenes for this chapter
    └─ Save: chapter_3_scene_chain.json

    ↓
User clicks "Generate Scene 9"
    ↓
[STAGE 3A] Generate scene with context
    └─ Output: ~1000 word scene

    ↓
[STAGE 3B] Extract state changes
    ├─ LLM reads scene
    ├─ Identifies: character changes, artifact moves, world updates
    └─ Output: Structured JSON of changes

    ↓
[STAGE 3C] Validate extractions
    └─ Flag any obvious contradictions

    ↓
[STAGE 3D] Apply to story state
    ├─ Update: story_state.json
    └─ Save: updated state

[Repeat for scenes 10, 11, 12]

    ↓
User clicks "Finalize Chapter 3"
    ↓
[STAGE 4] Validate & merge
    ├─ Check: character timelines ✓
    ├─ Check: artifact consistency ✓
    ├─ Check: world state ✓
    ├─ Check: setting consistency ✓
    ├─ Check: character presence ✓
    └─ Merge scenes into chapter_3.txt

    ↓
✅ Chapter complete, state updated, ready for Chapter 4
```

---

## Files to Create/Modify

### New Files
- **enhanced_state_validator.py** - Comprehensive validation logic

### Modified Files
- **story_state.py**
  - Add: `apply_extracted_changes()`
  - Add: `get_story_position()`
  - Add: `validate_character_presence()`
  
- **agents.py**
  - Add: 6 new extraction methods
  - Add: 1 per-chapter scene chain method
  - Add: 1 extraction method
  
- **web_app.py**
  - Add: `/finalize_outline_with_states` endpoint
  - Add: `/generate_chapter_scene_chain/<num>` endpoint
  - Add: `/validate_chapter/<num>` endpoint
  - Update: `/generate_scene` endpoint
  
- **prompts.py**
  - Add: `CHAPTER_SCENE_CHAIN_PROMPT`
  - Add: `STATE_EXTRACTION_PROMPT`
  - Add: `CHARACTER_INITIAL_STATE_PROMPT`
  - Add: `ARTIFACT_EXTRACTION_PROMPT`
  - Add: `THEME_EXTRACTION_PROMPT`
  
- **narrative_parsing.py**
  - Add: `parse_state_extraction()` method

---

## Implementation Phases

### Phase 1: Foundation (Stage 1)
1. Initial state extraction at outline finalization
2. Update StoryState with apply_extracted_changes()
3. Create /finalize_outline_with_states endpoint

### Phase 2: Context (Stage 2)
1. Per-chapter scene chain generation (on-demand)
2. Create enhanced_state_validator.py
3. Add UI visualization for scene chains

### Phase 3: Automation (Stage 3)
1. Scene state extraction agent
2. Add state_extractor agent type
3. Update /generate_scene endpoint with extraction

### Phase 4: Quality (Stage 4)
1. Validation endpoints and logic
2. Scene-to-chapter merging
3. End-to-end testing

---

## Key Benefits

✅ **Fully Automated State Tracking**
- No manual updates
- LLM extracts changes from generated content
- Timestamps track evolution

✅ **Progressive Context Building**
- Each chapter knows current state
- Scenes build naturally on previous events
- Story stays coherent throughout

✅ **Early Error Detection**
- Local validation per scene
- Global validation per chapter
- Issues flagged before committing

✅ **Flexible Regeneration**
- Can regenerate individual scenes
- Can replay from state snapshots
- Not locked into irreversible generations

✅ **Consistency Guarantees**
- Scene chain ensures causality
- State management ensures facts stay consistent
- Validation ensures no contradictions

---

## Success Criteria

- [ ] Stage 1: Initial states generated from outline with all required fields
- [ ] Stage 2: Per-chapter scene chains contextually generated based on current state
- [ ] Stage 3: Scene state changes extracted and auto-applied
- [ ] Stage 4: Contradictions detected and flagged
- [ ] End-to-end: Full book generated with no contradictions
- [ ] Performance: Full chapter generation < 5 minutes
- [ ] Usability: UI shows scene chains and validation results clearly
