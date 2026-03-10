# Phase 1 Findings (2026-03-10)

## Flow map
- **World building**: `/world`, `/world_chat`, `/world_chat_stream`, `/finalize_world`, and the streaming counterparts all rely on `BookAgents` (via `agents.create_agents` → `world_builder_chat`/`world_builder` prompts) to turn freeform chat into `book_output/world.txt` and in-memory session state.
- **Theme extraction**: `/extract_theme` reads `book_output/world.txt`, reuses `BookAgents.theme_extractor`, writes `theme.json`, and stores the LLM output in session; the flow is gated by the `theme_extraction_enabled` toggle in `config.get_narrative_config`.
- **Character creation**: `/characters`, `/characters_chat`/`_stream`, and `/finalize_characters_stream` require a saved world theme, call the `character_generator` prompt, and persist to `book_output/characters.txt`.
- **Outline generation**: `/outline` ensures world+characters exist, loads `world.txt`, `characters.txt`, and `chapters.json`, then `parse_outline_to_chapters` (supported by `outline_creator` prompts) populates `session['chapters']` plus `book_output/chapters.json`; streaming/finalize endpoints call the same `BookAgents` prompts to save final outline text.
- **Scene planning & chapter workflow**: `/scenes/<N>` reads `chapters.json`, uses `StoryState` summaries and `BookAgents.plan_chapter_scene_chain`, saves `book_output/chapters/chapter_{N}_scene_plan.json`, and seeds `ChapterStateManager`. `/chapter/<N>` enforces that plan, `/generate_chapter_stream/<N>` runs through each planned scene while streaming results, and `/validate_chapter/<N>` now loads that scene plan plus the generated scenes before calling `EnhancedStateValidator` for timeline/artifact/world/setting/presence checks.
- **State tracking**: `StoryState` continues to manage `story_state.json`, `character_arcs.json`, and `theme.json`, while `ChapterStateManager` writes `book_output/states/chapter_{N}_states.json`. The global scene-chain code exists for backwards compatibility, but the active pipeline persists per-chapter scene plans and transitions.

## Blockers & Inferred Links
- **No active blockers** – The Outline → Scene Planning → Chapter Generation → Validation pipeline now runs through `/scenes/<N>` and `/generate_chapter_stream/<N>`, so the retired `/generate_chapter_scene_chain/<N>` and `/finalize_outline_with_states` endpoints are no longer part of the workflow. The remaining investigations focus on verifying that the concrete metadata files and validators behave as documented.

## Methods & Investigation Scope
- **Documentation reviewed**: `README.md`, `docs/current/ARCHITECTURE_DESIGN.md`, `docs/current/IMPLEMENTATION_SUMMARY.md`, `docs/legacy/FRESH_START_GUIDE.md`, `docs/legacy/NARRATIVE_ENGINE_DEPLOYMENT.md`, `docs/current/SCENE_ANALYSIS_WORKFLOW.txt`, `docs/legacy/COMPLETION_CHECKLIST.md`.
- **Code inspected**: `web_app.py`, `agents.py`, `prompts.py`, `story_state.py`, `state_validator.py`, `enhanced_state_validator.py`, `chapter_state_manager.py`, `narrative_parsing.py`, `state_mutability.py`, `migration_helper.py`, `narrative_orchestrator.py`.
- **Version history consulted**: `git log --since=2026-01-01` (notably commits `f72b9e4`, `6eef027`, `a024ec8`, `48541a7`, `709ff17`, `3a7b246`) to align findings with documented intentions.
- **State of artifacts**: Confirmed `book_output` structure and `StoryState` helpers describe persistent flows; `BookAgents` prompts (world/characters/outline/scene/writer) align with each route.
- This investigation thus maps the intended and observed flows, recognizes dead ends, and flags which connections still rely on inferred behaviors pending runtime verification.
