# Acceptance Tests — OpenShorts Clipper

Scenarios 1-10 are verbatim from `docs/PRD_OpenShorts_Clipper_Claude_Work.md`
§L. Status is updated as real evidence is produced — never marked PASS
without a command/log to point to.

## PRD acceptance scenarios

| # | Scenario | Status | Evidence |
|---|---|---|---|
| 1 | **Single speaker** — horizontal monologue input, 3 relevant candidates, stable face crop, synced subtitles | **NOT_RUN** | Blocked on a fixture: no video in this repo has both real speech and an un-reframed (not-yet-vertical) source shape. `demo-openshorts.mp4` has an audio track but 0 detected speech segments; `dashboard/public/demo/*.mp4` have no audio track at all. Needs a user decision (see `docs/ROADMAP.md` Phase 1). |
| 2 | **Two speakers** — conversation; layout choice doesn't drop a speaker, split/manual fallback available | **NOT_RUN** | Same fixture blocker as #1. |
| 3 | **Screencast/tutorial** — on-screen content not fatally cropped, alternate reframe mode available | **NOT_RUN** | Same fixture blocker as #1; also needs `screencast_layout.py`'s Gemini-vision path or its local fallback, not yet exercised. |
| 4 | **Silent video** — system reports the local-transcript-pipeline limitation; does not fabricate a transcript | **PASS** | `python main.py -i demo-openshorts.mp4 -o <dir>` with `LLM_BASE_URL` set and no `GEMINI_API_KEY`: faster-whisper correctly reported "0 word(s) of speech in 42s," the pipeline switched to the silent-video path, and **failed with an explicit, honest error** ("this video has no usable speech... that needs Gemini... Add a GEMINI_API_KEY for silent videos") instead of inventing a transcript. Exit code 1, `RuntimeError` surfaced cleanly — not masked as success. |
| 5 | **No network mode** — local file + downloaded models + Ollama produces output or a deterministic local error; never calls an external API | **PARTIAL** | The run in scenario #4 made zero calls to Gemini (confirmed by code path: `llm_backend.active()` was true, so `get_viral_clips` never reached the `genai.Client` branch) and zero calls to any other paid API. It did not reach a *successful* local output because the fixture had no speech to score — so "produces output" is unverified, but "never calls an external API when it shouldn't" is verified for every stage that actually ran. |
| 6 | **No keys** — core clipping proceeds without `GEMINI_API_KEY`/`FAL_KEY`/`ELEVENLABS_API_KEY` | **PASS (for the stages reached)** | Same run: no `GEMINI_API_KEY` was set, and the pipeline ran transcription, speech-detection, and the silent-video branch logic without needing one — it only required (and correctly reported needing) a key at the exact point the PRD says a key becomes necessary (vision-only content). `FAL_KEY`/`ELEVENLABS_API_KEY` were never referenced at all in this run (translate.py/AI-UGC paths are not in the default pipeline). |
| 7 | **Render failure** — status/error/retry correct, safe fallback, never leaves a false `COMPLETED` | **NOT_RUN** | No render failure has been deliberately induced yet; the state-machine/retry design in `docs/ARCHITECTURE.md` §4.2 is not yet implemented to test against. |
| 8 | **Restart/resume** — a work item can resume without losing the source manifest | **NOT_RUN** | Depends on the job-state-machine work (Phase 1+), not yet built. |
| 9 | **Security** — path traversal rejected; no secret exposure; git history free of keys | **PARTIAL** | Git history of this fork checked manually: no secrets found (Phase 0 audit). Upstream ships its own path-traversal-guard tests (e.g. `tests/test_account_local_purge.py::TestPathTraversal`, confirmed PASS in the Phase 0 pytest run). A dedicated path-traversal test against *this fork's own* new code has not been written yet, since no new code exists yet. |
| 10 | **Verification** — output MP4 with a defined codec (H.264/AAC or equivalent), 9:16 ratio, valid duration/fps metadata, subtitles not overcropped | **NOT_RUN** | No successful clip render has been produced yet (blocked on #1's fixture) — nothing to verify against. |

No throughput or "commercial quality" claim is made anywhere in this repo
without a benchmark log naming the hardware, input size/duration, model,
per-stage execution time, and result, per the PRD's explicit instruction.

## Phase 0 checklist (internal, supplementary to the PRD's own scenarios)

| # | Criterion | Status |
|---|---|---|
| 1 | Fork exists, public, correct parent | PASS — `gh repo view yadenmustopa/openshorts-clipper` |
| 2 | `origin`/`upstream` remotes correct | PASS — `git remote -v` |
| 3 | Branch `chore/phase-0-foundation`, PR opened | PASS — PR #1 |
| 4 | `AGENTS.md`/`CLAUDE.md` present, upstream content preserved | PASS |
| 5 | `docs/PRD.md`, `ARCHITECTURE.md`, `UPSTREAM_AUDIT.md`, `LICENSE_AUDIT.md`, `ROADMAP.md`, `ACCEPTANCE_TESTS.md`, `ADR/0001-*.md` present | PASS |
| 6 | Baseline upstream tests run, results reported honestly | PASS — see table above and `docs/UPSTREAM_AUDIT.md` |
| 7 | No module deleted, no destructive git operation | PASS — diff is additive plus two in-place doc edits |
| 8 | No other repository touched | PASS — confined to this fork's own working tree |

## Environment distinction (PRD §M requirement: "bedakan test cloud dari local user's PC")

**There is no distinction to draw.** `docs/ENVIRONMENT.md` establishes with
hardware/OS evidence that every command in this document ran directly on
the user's own machine (`pop-os`, bare metal) — not a separate cloud
sandbox standing in for it.
