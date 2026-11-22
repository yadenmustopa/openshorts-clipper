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

- [x] Centralized `feature_flags.py` (`CLIPPER_ENABLED`, `LOCAL_LLM_ENABLED`
      default on; `UGC_ENABLED`, `TTS_ENABLED`, `DUBBING_ENABLED`,
      `SOCIAL_PUBLISHING_ENABLED`, `GEMINI_VISION_ENABLED`,
      `CLOUD_BILLING_ENABLED` default off). Wired into every backend route
      that reaches UGC/TTS/dubbing/social-publishing/Gemini-vision code
      (26 call sites in `app.py` plus the four Gemini-vision call sites
      inside the `main.py` subprocess: `layout_picker.py`,
      `screencast_layout.py`, `hook_grounding.py`, `main.get_visual_clips`)
      — refusal happens at the route/function itself (`FEATURE_DISABLED`
      structured error), not only by omitting a UI control. MCP and CLI
      inherit the same gate for free since both proxy the same HTTP API.
      Dashboard also hides the corresponding tabs/buttons
      (`App.jsx`, `ResultCard.jsx`) as a convenience, not the actual gate.
      47 new tests in `tests/test_feature_flags.py`; 22 pre-existing
      upstream tests updated to set the flag they now depend on (they test
      behavior that sits behind the new gate, e.g. ownership checks on a
      now-gated route) — full suite: 2578 passed, 56 skipped, 0 failed.
- [x] Fixtures acquired for acceptance scenarios 1-3 (`tests/fixtures/`,
      all CC BY / CC BY-SA, license verified directly from source metadata,
      not assumed) — scenario 4 already covered by the repo's own
      `demo-openshorts.mp4`.
- [x] Headless baseline proven end-to-end, three times, on real footage:
      transcribe → rank (local LLM) → clip → reframe → subtitle → 9:16
      MP4 export. Scenario 1 (single speaker): 1 clip. Scenario 2 (two
      speakers): 3 clips, no speaker dropped from frame. Scenario 3
      (screencast): 2 clips via the local non-Gemini fallback, screen
      content not fatally cropped. All six output files `ffprobe`-verified
      1080×1920 H.264/AAC; all three runs `$0` cost, zero calls to Gemini/
      fal.ai/ElevenLabs. Full detail in `docs/ACCEPTANCE_TESTS.md`.
- [x] Ollama integration validated empirically, not assumed:
      `qwen3:4b` **failed** (timed out past `llm_backend.py`'s 600s
      default — a reasoning model's "thinking" overhead made even one
      small scoring window too slow on CPU). `llava:7b` **succeeded**
      on all three fixtures: valid JSON matching the pydantic schema,
      titles that genuinely reflect each transcript, well under the
      timeout every time. See `docs/ACCEPTANCE_TESTS.md` "Local-LLM model
      selection".
- [x] Passed a local-video smoke test with no Gemini/fal.ai/ElevenLabs —
      three times (scenarios 1, 2, 3 above), not just once.
- [ ] `requirements-cpu.lock` version drift (see `docs/UPSTREAM_AUDIT.md`)
      needs a decision: regenerate the lock, or document
      `requirements.txt`-with-resolution as the supported CPU install path
      on this machine's software stack.

## Phase 2 — HyperFrames Enhanced Rendering (PoC done)

- [x] Versioned timeline schema + validator: `timeline_manifest.py`
      (`TimelineManifest`/`Clip`/`Word`/`Overlay`, pydantic-validated:
      rejects absolute paths, reversed/negative timestamps, out-of-range
      scores, unknown schema versions).
- [x] OpenShorts → HyperFrames adapter: `hyperframes_adapter.py`
      (`load_manifest_from_job`, `words_for_clip` — the explicit
      source-relative→clip-relative transform `docs/ARCHITECTURE.md`
      §4.1 specifies, `group_words`, `build_index_html`, `render_clip`).
      Does not re-run clip selection or Whisper — reads `main.py`'s own
      `*_metadata.json` as-is.
- [x] Three presets (`clean_podcast`, `bold_kinetic`, `educational_screen`)
      — real, visually distinct (word-by-word kinetic pop confirmed in
      `docs/qa/phase2-hyperframes/presets-comparison-t1s.png`), each with
      its own caption grouping/position/size per
      `references/captions.md`'s energy guidance.
- [x] Local CLI render: `npx hyperframes@0.9.80` (pinned in
      `integrations/hyperframes/package.json`'s own scripts and in the
      adapter's subprocess calls) — never HeyGen Cloud, never
      `cloud render`/`lambda`/`cloudrun`.
- [x] At least 3 rendered MP4s — produced against a real Phase 1 clip
      (scenario 1), all 1080×1920 H.264/AAC, no black frames, audio
      preserved within 0.1-0.2dB of source. Full table in
      `docs/architecture/hyperframes-integration.md`.
- [x] Frame screenshots + QA report: `docs/qa/phase2-hyperframes/`,
      `docs/architecture/hyperframes-integration.md`.
- [x] Never double-burn subtitles — the clean, pre-subtitle-burn OpenShorts
      clip is the one fed to HyperFrames, not the `subtitled_*` variant.
- [x] Docs: `docs/architecture/hyperframes-integration.md`.
- [x] Unit/integration tests: `tests/test_timeline_manifest.py` (11),
      `tests/test_hyperframes_adapter.py` (17) — 28 total, pass in a
      minimal environment (pydantic only, no heavy ML stack needed).
- [x] **Remotion decision, gated on this PoC:** `docs/ADR/0002-remotion-vs-hyperframes.md`
      — keep both for now, gradual migration, not a full switch. Neither
      `dashboard/`'s `@remotion/*` usage nor the top-level `remotion/`
      project was touched.
- Not done in this PoC (recorded as known gaps, not silently skipped):
  multi-clip batch rendering, `render --docker --strict`, render
  repeatability re-verified on a second run, `educational_screen`'s
  pointer/highlight feature. See
  `docs/architecture/hyperframes-integration.md` "What this PoC does not
  cover".

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
