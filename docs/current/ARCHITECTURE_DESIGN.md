# OpenTale: Automated Story Workflow Architecture

## Overview

This document describes how the current OpenTale application coordinates the staged, AI-assisted story-building process. The goal of the latest architecture is to keep state consistent, keep scene planning in the critical path, and provide validation safeguards before a chapter is considered complete.

### Current Limitations Being Addressed
- ❌ Manual state updates scattered across pages.
- ❌ Scene planning either optional or disconnected from writing.
- ❌ Chapter generation that ignores the planned scenes and state.
- ❌ Lack of comprehensive, contextual validation before publishing a chapter.

### Proposed Solution: 4-Stage Pipeline
- ✅ Stage 1: Outline completion captures the base world, characters, chapters, and story-state files.
- ✅ Stage 2: Every chapter receives a dedicated scene plan that is required before writing.
- ✅ Stage 3: Chapters are generated scene-by-scene, streaming the results while extracting state changes and locking progress with `ChapterStateManager`.
- ✅ Stage 4: Each chapter goes through `EnhancedStateValidator` checks using the plan + scene output to produce a validation report.

---

## Architecture: Process Stages

### Stage 1: Outline & Story-State Capture

**When:** The user finishes world building, characters, and the chapter outline.  
**Goal:** Persist the foundation of the book (world, characters, chapters, theme, and initial state) so the later stages have a reliable baseline.

**Routes involved:**  
- `GET /outline` / `POST /outline`: Save outline, split it into `book_output/chapters.json`, and persist `book_output/outline.txt`.  
- `/outline_chat*` + `/world_chat*` / `/characters_chat*`: Drive the UI conversations that help compose the new content.  
- `/finalize_outline_stream`: (Streaming helper) writes `book_output/story_state.json`, `book_output/characters.txt`, `book_output/world.txt`, and `book_output/theme.json` once the outline is stable.

**Artifacts written:**  
- `book_output/world.txt`, `book_output/characters.txt`, `book_output/outline.txt`, `book_output/theme.json`  
- `book_output/chapters.json` (list of chapter prompts)  
- `book_output/story_state.json` & `book_output/character_arcs.json` (StoryState captures locations, artifacts, relationships, and progress).  

**Notes:**  
The explicit `/finalize_outline_with_states` endpoint mentioned in earlier documentation no longer exists; the outline page now relies on streaming helpers and manual `StoryState.apply_extracted_changes()` calls to keep the global state in sync.

---

### Stage 2: Required Scene Planning

**When:** The user clicks “Plan Scenes” on a chapter card.  
**Route:** `GET/POST /scenes/<chapter_number>`

**Process:**  
1. Validate that `book_output/chapters.json` exists and that the requested chapter is defined.  
2. Load the current `StoryState` summary for context.  
3. Call `BookAgents.plan_chapter_scene_chain()` (the same planning model that drove the old `scene_chain` feature) with the chapter prompt and state.  
4. Save the resulting JSON to `book_output/chapters/chapter_<chapter_number>_scene_plan.json`.  
5. Initialize chapter-level tracking with `ChapterStateManager.save_chapter_states(...)`, which creates `book_output/states/chapter_<chapter_number>_states.json`.

**Outputs:**  
- `book_output/chapters/chapter_<N>_scene_plan.json` (scene metadata: titles, goals, conflicts, prerequisites).  
- `book_output/states/chapter_<N>_states.json` (initial state snapshot, scene counters, empty transitions).  

**Goal:** Stage 2 is now mandatory. `/chapter/<N>` refuses to run until a plan exists, so the scene plan is the deterministic handoff from outline to writing.

---

### Stage 3: Scene-by-Scene Chapter Generation

**Routes:**  
- `GET /chapter/<chapter_number>`: Display the chapter UI, surface the scene plan, and redirect to `/scenes/<N>` if the plan is missing.  
- `POST /chapter/<chapter_number>`: Kick off the SSE stream via `/generate_chapter_stream/<chap_num>`.  
- `GET /generate_chapter_stream/<chapter_number>`: Streams the chapter generation one scene at a time while updating story state.

**Process:**  
1. The SSE endpoint loads the plan from `book_output/chapters/chapter_<N>_scene_plan.json`.  
2. Each scene is generated through `BookAgents.generate_scene_with_state(...)`, which receives the chapter prompt, world/character text, previous chapter content, and the latest `StoryState` summary.  
3. After writing the scene file, `BookAgents.extract_scene_state_changes()` reads the generated content, identifies character/artifact/world updates, and `StoryState.apply_extracted_changes()` merges the mutations back into `book_output/story_state.json`.  
4. `ChapterStateManager` records each transition and, when all scenes complete, saves the final snapshot (final state + scene count) back to `book_output/states/chapter_<N>_states.json`.  
5. Individual scenes appear in `book_output/chapters/chapter_<N>_scenes/scene_<M>.txt` and the assembled chapter is emitted to `book_output/chapters/chapter_<N>.txt`.

**Additional notes:**  
- SSE events emit `progress`, `scene_complete`, `state_updated`, and `done` messages so the front end shows streaming output.  
- The per-scene workflow ensures chapter generation is constrained by the approved plan and the latest shared state before validation runs.

---

### Stage 4: Validation & Consistency Checking

**Route:** `POST /validate_chapter/<chapter_number>`

**Process:**  
1. Load all scenes from `book_output/chapters/chapter_<N>_scenes/`.  
2. Load the plan JSON produced in Stage 2 from `book_output/chapters/chapter_<N>_scene_plan.json`.  
3. Pass the scenes, plan, and `StoryState.load_story_state()` into `EnhancedStateValidator.validate_chapter_coherence()` and `generate_validation_report()`.  
4. Persist the human-readable report to `book_output/chapter_<N>_validation.txt` and return the JSON summary to the UI.

**Validation checks:** Character timelines, artifact consistency, world state, setting consistency, character presence.

---

## Data Persistence at a Glance

- `book_output/story_state.json` – central story state (characters, artifacts, plot progress).  
- `book_output/characters.txt`, `book_output/world.txt`, `book_output/theme.json` – user-entered lore.  
- `book_output/chapters.json` – chapter prompts extracted from the outline.  
- `book_output/chapters/chapter_<N>_scene_plan.json` – required scene definitions used by `/generate_chapter_stream`.  
- `book_output/chapters/chapter_<N>_scenes/scene_<M>.txt` – each generated scene.  
- `book_output/chapters/chapter_<N>.txt` – compiled chapter content.  
- `book_output/states/chapter_<N>_states.json` – `ChapterStateManager` snapshot for the chapter, including `initial_state`, `final_state`, and `state_transitions`.  
- `book_output/chapter_<N>_validation.txt` – validator report for the chapter.  

## Concurrency & Safety

- `ChapterStateManager` uses file locking to avoid overwriting states when multiple actors interact with the same chapter.  
- `StoryState.save_story_state()` writes only after each scene’s extraction succeeds, so downstream generators always read the latest state.
