# Roadmap — OpenShorts Clipper

Milestones mirror `docs/PRD_OpenShorts_Clipper_Claude_Work.md` §K exactly;
status reflects actual work done, not intent.

## Phase 0 — GitHub Repository + Forensic Audit + Baseline (DONE)

- [x] Fork `yadenmustopa/openshorts-clipper` created, public, `origin`/
      `upstream` correct, baseline SHA `5da5b83` recorded.
- [x] Working branch `chore/phase-0-foundation`; PR #1 opened against the
      fork's own `main`.
- [x] `AGENTS.md`, `CLAUDE.md` (extended, upstream content preserved),
      `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/UPSTREAM_AUDIT.md`,
      `docs/LICENSE_AUDIT.md`, `docs/ROADMAP.md`, `docs/ACCEPTANCE_TESTS.md`,
      `docs/ADR/0001-fork-and-worker-boundaries.md`.
- [x] Module/dependency inventory with KEEP/DISABLE/REMOVE_LATER/AUDIT
      classification (`docs/UPSTREAM_AUDIT.md`).
- [x] Upstream smoke tests run where the environment supports them
      (`pytest tests/ -v`: 2412 passed/103 skipped; `dashboard` build:
      passed) — see `docs/ACCEPTANCE_TESTS.md`. Nothing claimed PASS
      without a log.
- [x] License/upstream audit, including the `cloud/` exception and the
      `kamilstanuch/Autocrop-vertical` provenance note.
- **Explicitly not done in Phase 0:** no pipeline code changed, no feature
  disabled, no HyperFrames integration started, no agent-orchestration
  layer started.

## Phase 1 — Clipper-Only + Local Models (in progress)

- [ ] Disable UGC/TTS/dubbing/publishing/billing/cloud-gallery in **both**
      the UI and the backend route (defense in depth — a hidden button
      with a live endpoint behind it does not satisfy this).
- [ ] Headless baseline: transcribe → rank → clip → 9:16 export using a
      local LLM (`LLM_BASE_URL`), with per-stage logging and acceptance
      checks.
- [ ] Ollama integration validated empirically: JSON validity and
      selection-quality checked against what's actually installed
      (`qwen3:4b`, `qwen2.5-coder:1.5b`, `llava:7b`), not assumed adequate
      just because upstream supports the mechanism.
- [ ] Pass a one-local-video smoke test with no Gemini/fal.ai/ElevenLabs —
      **blocked on a usable fixture**: `demo-openshorts.mp4` has audio but
      0 detected speech segments (it correctly exercises PRD acceptance
      scenario #4, "silent video," not scenario #1, "single speaker");
      none of `dashboard/public/demo/*.mp4` have an audio track at all. A
      real speech-bearing fixture is needed and is a pending decision with
      the user (download a short section of a clearly-licensed source vs.
      a user-supplied local file vs. deferring).
- [ ] `requirements-cpu.lock` version drift (see `docs/UPSTREAM_AUDIT.md`)
      needs a decision: regenerate the lock, or document
      `requirements.txt`-with-resolution as the supported CPU install path
      on this machine's software stack.

## Phase 2 — HyperFrames Enhanced Rendering (not started)

- Implement the versioned timeline schema and the Python → Node worker
  boundary (`docs/ARCHITECTURE.md` §4.1).
- Three presets (`clean_podcast`, `bold_kinetic`, `educational_screen`),
  word-aligned subtitles, motion overlays, render logs, editable output.
- Never double-burn subtitles. Must pass QA for all three presets on a
  fixture.
- **Gates the Remotion decision:** only after this phase's proof-of-concept
  exists does `docs/ADR/0001-fork-and-worker-boundaries.md` get revisited
  for whether `dashboard/`'s `@remotion/*` usage and the top-level
  `remotion/` project are kept, replaced, or removed.

## Phase 3 — Autonomous Agent + MCP/CLI (not started)

- `autonomous-clipper` skill for both Codex and Claude Code
  (`docs/ARCHITECTURE.md` §3.4).
- Multi-stage workflow with retry/idempotency, a decision log, QA
  pass/fail, and a review gate.
- Acceptance: the agent processes one video into 3–5 results and writes
  the final manifest, without fabricating any score, duration, or status.

## Phase 4 — Optional Gemini Browser Vision (not started, optional)

- Browser provider with explicit per-upload consent, limited availability,
  real error handling (not bypassing CAPTCHA/ToS/rate limits), and a
  fallback that never blocks the local-only pipeline's success.

## Future (explicitly out of scope)

Mass batch processing, scheduling, Mabar integration, social publishing,
multi-user SaaS.
