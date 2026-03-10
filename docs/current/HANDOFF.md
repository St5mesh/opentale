# OpenTale Handoff — March 2026

## Purpose
Capture where the repository stands after the content/workflow overhaul and provide the next engineer with the context, validations, and checklist needed before handing control back to the team.

## What Was Done
- **Documentation and workflow mapping:** Everything that remains active now lives under `docs/current/`, legacy advice sits in `docs/legacy/`, and the README/deployment checklist point at the new paths. The earlier phase‑1 findings, investigation scope, and validation notes remain in the legacy folder for traceability.
- **Test consolidation:** All test scripts were moved into the `tests/` package (with `__init__.py` for convenient imports) and references in docs/deployment scripts now target `tests/…` instead of loose root files.
- **Scene generation flow:** Added the missing `scene_writer` prompt in `agents.py`, ensuring the writer agent exists whenever the UI resumes the scene workflow. This also triggered a full container rebuild so the fresh image includes the additional prompt.

## Investigation Notes
- The UI agent chat continues to orchestrate steps by routing each stage through a dedicated BookAgent, combining stored story state with the latest user messages, and streaming responses via SSE. The new flow keeps that pattern but now routes every scene/chapter request through the extended set of prompt keys.
- During the earlier mapping work we kept an “open mind” checklist (see `docs/legacy/phase1-findings.md`) to distinguish real blockers from cleanup artifacts. Apply the same mindset when validating any “broken pipe” you observe: can it be relegated to archiving, or does it point to a deeper missing signal?

## Tests & Validation
- ✅ `docker compose build` (verifies the updated `scene_writer` prompt is baked into the image).
- ⚠️ Other suites (e.g., `python -m pytest tests`) were not run in this phase. Run them before the next deployment.

## Outstanding Checks
1. `docker compose up` — start the stack after the build to ensure the new agent registration survives runtime loading and the “resuming scene” story path no longer errors.
2. `python -m pytest tests` — confirm the centralized tests still pass in their new location.
3. UI regression: Navigate away from and back to the scene/chapter pages to prove the “Agent not found” error has been eradicated from the stateful workflow.

## Next Steps & Handoff Guidance
- Keep monitoring for any containers that were built before this change, since the missing prompt only manifests when the older image is used.
- Any future work on the mapping should start from `docs/current/IMPLEMENTATION_SUMMARY.md` for the current structure and refer to `docs/legacy/` for historical evidence of deprecated flows.
- Treat every new UI workflow issue as potentially stemming from the agent registration layer—trace it through `agents.py` before assuming business logic needs rewriting.
