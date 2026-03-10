# OpenTale: Automated Story Workflow Implementation Summary

## Overview

OpenTale now enforces a linear Outline → Scene Planning → Chapter Generation → Validation pipeline where each stage persists the expected artifacts and nothing succeeds without the previous stage completing successfully. The Flask routes, `BookAgents`, `StoryState`, and `ChapterStateManager` collaborate to keep story state, scene plans, and validation reports in lockstep.

---

## Phase 1: Outline & Story-State Capture

**Purpose:** Persist the world, characters, outline, and the baseline story state so downstream automation starts from a known foundation.  
**Key files touched:** `web_app.py`, `prompts.py`, `story_state.py`, `chapter_state_manager.py`, `templates/{world,characters,outline}.html`.  
**Behavior:**  
- World, character, and outline chat endpoints call the corresponding `BookAgents` prompts and write `book_output/world.txt`, `book_output/characters.txt`, `book_output/outline.txt`, and `book_output/chapters.json`.  
- `StoryState.apply_extracted_changes()` remains the integration point that folds agent-derived mutations into `book_output/story_state.json`, `book_output/character_arcs.json`, and `book_output/theme.json`.  
- The outline page uses streaming helpers (e.g., `/finalize_outline_stream`) to flush the completed outline and theme metadata to disk while keeping session state aligned.  
- Startup routines (`_clear_book_output`) reinitialise these files so every new book begins with clean state snapshots.

---

## Phase 2: Required Scene Planning

**Purpose:** Generate a deterministic scene plan for each chapter before any writing begins.  
**Endpoint:** `GET|POST /scenes/<chapter_number>`  
**Implementation highlights:**  
- Validates `book_output/chapters.json`, loads `StoryState`, and calls `BookAgents.plan_chapter_scene_chain()` with the chapter prompt plus the current state summary.  
- Persists the returned plan as `book_output/chapters/chapter_<N>_scene_plan.json`.  
- Seeds chapter-level tracking by creating `book_output/states/chapter_<N>_states.json` through `ChapterStateManager.save_chapter_states`.  
- The Scenes UI (`templates/scenes.html`) shows the generated scenes, allows regeneration, and exposes buttons that redirect users back to the chapter once planning succeeds.

---

## Phase 3: Scene-by-Scene Chapter Generation

**Purpose:** Stream each chapter based on the approved scene plan while streaming state updates.  
**Endpoints:**  
- `GET /chapter/<chapter_number>` – Displays the chapter UI, the scene plan, and redirects to `/scenes/<N>` if no plan exists.  
- `POST /chapter/<chapter_number>` – Captures optional user context/chat and returns the SSE URL.  
- `GET /generate_chapter_stream/<chapter_number>` – Streams every scene sequentially, persists scene files, updates story state, and stitches the final chapter.

**Implementation highlights:**  
1. The SSE generator loads the plan from `book_output/chapters/chapter_<N>_scene_plan.json` and iterates through each scene.  
2. Scenes are generated via `BookAgents.generate_scene_with_state(...)`, which receives our chapter prompt, world/character text, previous chapter excerpt, and the latest `StoryState` summary.  
3. After saving each scene to `book_output/chapters/chapter_<N>_scenes/scene_<M>.txt`, `BookAgents.extract_scene_state_changes()` reads the prose, the extracted deltas mutate `StoryState`, and `ChapterStateManager` records the state transition.  
4. Once all scenes are complete, the SSE stream assembles `book_output/chapters/chapter_<N>.txt`, writes the final `book_output/states/chapter_<N>_states.json`, and emits a `done` event so the UI can move forward.

---

## Phase 4: Validation & Reporting

**Purpose:** Verify that the generated scenes respect timelines, artifacts, world state, and the approved plan before marking the chapter complete.  
**Endpoint:** `POST /validate_chapter/<chapter_number>`  
**Implementation highlights:**  
- Loads scenes from `book_output/chapters/chapter_<N>_scenes/` and the plan JSON from `book_output/chapters/chapter_<N>_scene_plan.json`.  
- Runs `EnhancedStateValidator.validate_chapter_coherence()` plus `generate_validation_report()`, which check character timelines, artifact consistency, world transitions, settings, and character presence.  
- Persists the textual report to `book_output/chapter_<N>_validation.txt` and returns the consolidated JSON summary to the UI for display.

---

## Supporting Infrastructure

- `prompts.py` now exposes the scene planning, scene generation, and state extraction prompts used across the Scenes and Chapter routes.  
- `story_state.py` continues to manage the canonical state store (characters, artifacts, world, plot progress) plus helpers for summaries and applying extracted deltas.  
- `chapter_state_manager.py` wraps file locks around per-chapter state snapshots to keep concurrent SSE writers safe.  
- `enhanced_state_validator.py` provides the layered validation engine invoked by `/validate_chapter/<N>`.  
- UI templates (`templates/scenes.html`, `templates/chapter.html`) reflect the enforced workflow by highlighting the plan and streaming outputs.

---

## Testing & Automation Notes

- Automated suites: `python3 -m pytest tests/test_coherence_validation.py tests/integration_tests.py tests/test_phase5_validation.py` all pass in the current environment, though PytestReturnNotNone warnings persist because the helper classes define constructors and return values instead of asserting.  
- Additional scripts (`tests/integration_tests.py`, `tests/end_to_end_generation_test.py`, `tests/test_phase5_validation.py`) rely on the enriched story state exported via `StoryState` and the new scene-based flows.
