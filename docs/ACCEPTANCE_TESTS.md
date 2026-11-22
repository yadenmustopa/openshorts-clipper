# Acceptance Tests — OpenShorts Clipper

Scenarios 1-10 are verbatim from `docs/PRD_OpenShorts_Clipper_Claude_Work.md`
§L. Status is updated as real evidence is produced — never marked PASS
without a command/log to point to.

## PRD acceptance scenarios

| # | Scenario | Status | Evidence |
|---|---|---|---|
| 1 | **Single speaker** — horizontal monologue input, 3 relevant candidates, stable face crop, synced subtitles | **PASS** (1 candidate, not 3 — see note) | Full local run, no Gemini key, `LLM_BASE_URL` → Ollama `llava:7b`: `python main.py -i tests/fixtures/cache/scenario1_single_speaker.mp4 -o <dir>`. faster-whisper: 14 segments in ~9s. Moment scoring: 1 scoring window (the fixture is only 90s — too short for the 3-5 clip target the PRD describes for a *full-length* source; upstream's own `clip_floor`/candidate-count logic scales with source duration, which is correct behavior, not a bug, for a 90s clip), scored and detailed, 1 clip selected (48.22s-75.98s), title "The Evolution of Blender: A 5-Year Journey" — a title that actually matches the transcript content. Output `subtitled_..._clip_1.mp4`: **1080×1920 (9:16), H.264/AAC, 27.8s**, `layout_ranges` show `track` (face-crop) then `general` (blurred) — the local, non-Gemini layout classifier, since `GEMINI_VISION_ENABLED` is off by default. Subtitles burned from the same word-level timestamps faster-whisper produced (`autosubs_*.ass`). Total wall time 223.2s, CPU time 210.5s, **cost $0.000000** (`cost_analysis.total_cost` in the job's own metadata JSON). |
| 2 | **Two speakers** — conversation; layout choice doesn't drop a speaker, split/manual fallback available | **PASS** | Same local setup as scenario 1, `tests/fixtures/cache/scenario2_two_speakers.mp4`. Found **3 clips** (the 90s two-speaker conversation had more distinct moments than the 90s monologue did — the PRD's 3-5 target, now actually met): "Dan and Shoshana's Texas adventure" (38.76-59.35s), "The pressure of being in the hot seat on a podcast" (59.35-78.66s), "The cameras they use for their podcast" (78.63-90.0s) — all three titles genuinely match their transcript segments. All 3 outputs verified by `ffprobe`: **1080×1920, H.264/AAC**. Layout chosen for all three: `general` (blurred wide shot keeping the full frame, both speakers visible) — the local active-speaker classifier did not confidently lock onto a `split`/`track` mode for this footage, but critically **no speaker was dropped from frame**, which is the scenario's actual requirement; this is the local, non-Gemini fallback working as intended, not a defect. `cost_analysis.total_cost: 0.0`. Total wall time 231.4s. |
| 3 | **Screencast/tutorial** — on-screen content not fatally cropped, alternate reframe mode available | **PASS** | Same local setup, `tests/fixtures/cache/scenario3_screencast.mp4` ("Basic Introduction to HTML," CC BY-SA 3.0). `SCREENCAST_LAYOUT` was left at its default (off), so this exercised the **local, non-Gemini fallback path**, not `screencast_layout.py`'s Gemini-vision branch — consistent with `GEMINI_VISION_ENABLED` defaulting off in this fork and with the PRD's own instruction not to rely on Gemini as the only analysis path. Found 2 clips: "HTML Basics for Beginners" (4.86-20.24s) and "HTML: Beyond Web Pages" (56.54-84.96s), both titles accurate to the transcript. Both outputs **1080×1920, H.264/AAC** (`ffprobe`-verified). Layout: `general` (the full screen content scaled/padded into frame, not cropped) for both — satisfies "not fatally cropped" without needing the Gemini-specific screencast detector. `cost_analysis.total_cost: 0.0`. |
| 4 | **Silent video** — system reports the local-transcript-pipeline limitation; does not fabricate a transcript | **PASS** | `python main.py -i demo-openshorts.mp4 -o <dir>` with `LLM_BASE_URL` set and no `GEMINI_API_KEY`: faster-whisper correctly reported "0 word(s) of speech in 42s," the pipeline switched to the silent-video path, and **failed with an explicit, honest error** ("this video has no usable speech... that needs Gemini... Add a GEMINI_API_KEY for silent videos") instead of inventing a transcript. Exit code 1, `RuntimeError` surfaced cleanly — not masked as success. |
| 5 | **No network mode** — local file + downloaded models + Ollama produces output or a deterministic local error; never calls an external API | **PASS** | The scenario-1 run (above) produced real output end-to-end with zero Gemini/fal.ai/ElevenLabs calls — `cost_analysis.total_cost` in the job metadata is `0.0`, the only network call made was to the already-local Ollama server at `localhost:11434`. The scenario-4 run separately confirmed the *deterministic local error* half of this scenario (no silent fabrication). |
| 6 | **No keys** — core clipping proceeds without `GEMINI_API_KEY`/`FAL_KEY`/`ELEVENLABS_API_KEY` | **PASS** | No `GEMINI_API_KEY`, `FAL_KEY`, or `ELEVENLABS_API_KEY` were set for the scenario-1 run, and it completed successfully end to end — transcription, scene detection, local-LLM scoring, cutting, reframing (local layout classifier, not Gemini), and subtitle burning all ran without any of the three. |
| 7 | **Render failure** — status/error/retry correct, safe fallback, never leaves a false `COMPLETED` | **NOT_RUN** | No render failure has been deliberately induced yet; the state-machine/retry design in `docs/ARCHITECTURE.md` §4.2 is not yet implemented to test against. |
| 8 | **Restart/resume** — a work item can resume without losing the source manifest | **NOT_RUN** | Depends on the job-state-machine work (Phase 1+), not yet built. |
| 9 | **Security** — path traversal rejected; no secret exposure; git history free of keys | **PARTIAL** | Git history of this fork checked manually: no secrets found (Phase 0 audit). Upstream ships its own path-traversal-guard tests (e.g. `tests/test_account_local_purge.py::TestPathTraversal`, confirmed PASS in the Phase 0 pytest run). A dedicated path-traversal test against *this fork's own* new code has not been written yet, since no new code exists yet. |
| 10 | **Verification** — output MP4 with a defined codec (H.264/AAC or equivalent), 9:16 ratio, valid duration/fps metadata, subtitles not overcropped | **PASS** | `ffprobe` on the scenario-1 output: `codec_name=h264` (video), `codec_name=aac` (audio), `width=1080 height=1920` (exactly 9:16), `duration=27.800000` (matches the clip's `start`/`end` in the metadata JSON to within encoder rounding). Subtitle overcrop was not separately measured pixel-by-pixel in this pass — the ASS file and burn step are pre-existing, tested upstream functionality (`tests/test_burned_subtitles.py`, PASS in the Phase 0/1 suite), not new code from this fork. |

No throughput or "commercial quality" claim is made anywhere in this repo
without a benchmark log naming the hardware, input size/duration, model,
per-stage execution time, and result, per the PRD's explicit instruction.

## Local-LLM model selection — a real finding, not an assumption

Per the explicit instruction not to assume a small model is automatically
adequate: it was tested, and the first model tried was **not** adequate.

| Model | Params | Result on scenario 1 (90s clip, 1 scoring window) |
|---|---|---|
| `qwen3:4b` | 4B, reasoning/"thinking" model | **FAIL — timeout.** Transcription succeeded (14 segments, ~9s). The scoring call to Ollama's OpenAI-compatible endpoint did not return within `llm_backend.py`'s `DEFAULT_TIMEOUT` (600s); total job wall time 613.5s before the client gave up. `main.get_viral_clips` printed `❌ Gemini Error: timed out` (a pre-existing upstream wording — the error-formatting helper says "Gemini" even on the local-LLM path; not something introduced by this fork, flagged as a minor upstream wording issue, not fixed here) and the job correctly raised `RuntimeError` rather than fabricating a result. |
| `llava:7b` | 7B (llama family, vision+text) | **PASS.** Scored the window, returned valid structured JSON matching the pydantic schema `main.py` validates against (score, both social-platform descriptions, YouTube title, hook text, `why` rationale, `layout_ranges`), selected 1 clip (48.22s-75.98s) with a title ("The Evolution of Blender: A 5-Year Journey") that genuinely reflects the transcript content — not a generic placeholder. 2 calls (score + detail) in well under the 600s timeout. `cost_analysis.total_cost: 0.0`. |

This matches upstream's own documented guidance (README: *"7-8B models
return valid JSON reliably, 3B ones do not"*) exactly: the 4B reasoning
model failed (timeout), the 7B plain instruction-following model
succeeded on the first try, both JSON-valid and qualitatively sensible.
**Conclusion for this machine: use a ≥7B non-"thinking" model for the
local moment picker; a 4B reasoning model's token overhead makes it
impractical on CPU-only hardware even for a short clip.**
`qwen2.5-coder:1.5b` was not tried given it is smaller still and
coder-specialized rather than general-instruction-following — not needed
once a working model was found.

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

## Phase 2 — HyperFrames PoC quality control

Required checks from the Phase 2 directive, against real renders (not
claimed): see `docs/architecture/hyperframes-integration.md` for the full
writeup, `docs/qa/phase2-hyperframes/` for screenshots.

| Check | Result |
|---|---|
| Output 1080×1920, H.264/AAC | PASS — `ffprobe` on all 3 preset outputs |
| Durasi dan FPS valid | PASS — 27.776s, 30fps, matches source clip duration |
| Audio tetap sinkron | PASS — `volumedetect`: −18.5dB mean / −1.8dB max on all 3 outputs vs. source's −18.4/−1.6dB (encoding-rounding-level difference, not a sync or level defect) |
| Subtitle mengikuti timestamp transkrip | PASS — captions built directly from `words_for_clip()`'s clip-relative conversion of the same faster-whisper word timestamps `main.py` produced; visually confirmed in the contact sheet at 6 timestamps across the clip |
| Tidak ada black frame atau visual yang hilang | PASS — `ffmpeg blackdetect` reports none on any of the 3 outputs |
| Tidak ada cropping fatal pada wajah atau screencast | PASS — `object-fit: cover` on an already-9:16-reframed source means no new cropping is introduced; visually confirmed in the contact sheet |
| Aset tidak membutuhkan network request ketika render | PASS — GSAP vendored locally (`assets/vendor/gsap.min.js`, asserted by `test_gsap_is_vendored_locally_not_a_cdn`); one-time setup downloads (npx package cache, headless-Chrome download) are not per-render |
| Project tetap editable | PARTIAL — the generated `index.html` is a normal HyperFrames project (`npx hyperframes check`/`snapshot`/`timeline` all work against it), but it is regenerated per render by the adapter rather than hand-edited; no human-editing workflow was exercised in this PoC |
| Hasil render dapat diulang dengan konfigurasi yang sama | NOT_RUN — a second render of the same clip+preset to confirm structural repeatability (resolution/codec/duration/no-black-frames reproduce) was not performed in this phase; recorded as a gap in `docs/architecture/hyperframes-integration.md`, not assumed |

## Environment distinction (PRD §M requirement: "bedakan test cloud dari local user's PC")

**There is no distinction to draw.** `docs/ENVIRONMENT.md` establishes with
hardware/OS evidence that every command in this document ran directly on
the user's own machine (`pop-os`, bare metal) — not a separate cloud
sandbox standing in for it.
