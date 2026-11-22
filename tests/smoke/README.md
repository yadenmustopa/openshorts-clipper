# Clipper smoke tests (Phase 1+)

This directory is scaffolded per
`docs/PRD_OpenShorts_Clipper_Claude_Work.md` §I's repository layout. It is
meant to hold this project's own end-to-end smoke tests for the local-first
clipper pipeline — distinct from upstream's existing `tests/` suite (unit/
integration tests for OpenShorts itself, run via `pytest tests/ -v`, see
`docs/UPSTREAM_AUDIT.md`).

**Status: scaffolded, not yet populated with a passing smoke test.**

What exists so far (see `docs/ACCEPTANCE_TESTS.md` for the authoritative,
up-to-date status table):

- A manual run of `main.py -i demo-openshorts.mp4 -o <dir>` with
  `LLM_BASE_URL` pointed at a local Ollama model and no `GEMINI_API_KEY`
  set, confirming PRD acceptance scenario #4 (silent video → explicit
  error, no fabricated transcript) and partially confirming #5/#6
  (no-network, no-keys for the stages actually reached).
- No automated smoke test script exists here yet, and PRD scenarios #1-3,
  #7, #8, #10 have not been exercised at all — they are blocked on a
  speech-bearing local video fixture (see `docs/ROADMAP.md` Phase 1 and
  `docs/PRD_GAP_ANALYSIS.md` "Still open" #1).

**Do not add a smoke test here that silently skips when a fixture is
missing and reports green.** Per `AGENTS.md` rule 8/9, a blocked test must
report `NOT_RUN` with its blocker, never a false `PASS`.
