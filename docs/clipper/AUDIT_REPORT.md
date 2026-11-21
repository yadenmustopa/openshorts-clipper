# Phase 0 Audit Report — OpenShorts Clipper

Date: 2026-11-21. Environment: local Linux workstation (this machine),
Python 3.11.4, Node 22.23.1, Docker 29.1.2, ffmpeg 5.1.1-static, git 2.34.1.

## 1. Source provenance

| Repo | Role | Default branch | Commit SHA audited | License |
|---|---|---|---|---|
| [`mutonby/openshorts`](https://github.com/mutonby/openshorts) | Forked (this repository's upstream) | `main` | `5da5b839d3231e3b2152250fa83aa17d40c91e64` | MIT, except `cloud/` (Commercial License) |
| [`heygen-com/hyperframes`](https://github.com/heygen-com/hyperframes) | Referenced only, **not forked** | `main` | `63d1bb5596d0a307b3efa4290a7a3cf3848e090e` | Apache-2.0 |

`mutonby/openshorts` at audit time: public, 9,527 stargazers, 2,003 forks,
not archived, pushed 2026-11-20. Its own GitHub fork-network lists
`kamilstanuch/Autocrop-vertical` (no declared license) as the ultimate
network root. This is noted as an upstream provenance fact, not a blocker:
the current `mutonby/openshorts` tree carries its own MIT grant
(`LICENSE`, `NOTICE`) over its present contents, which is what this fork
relies on.

## 2. Fork created

- **URL:** https://github.com/yadenmustopa/openshorts-clipper
- Created via `gh repo fork mutonby/openshorts` then renamed via the GitHub
  API (the installed `gh` CLI, v2.4.0, predates the `--fork-name` flag).
- **Public.** GitHub does not allow a private fork of a public repository on
  a personal account. Confirmed before creation and accepted per the user's
  explicit Phase 0 instructions.
- `origin` → `git@github.com:yadenmustopa/openshorts-clipper.git`
- `upstream` → `git@github.com:mutonby/openshorts.git`
- Working branch: `chore/phase-0-foundation`, both remotes at
  `5da5b83` at branch-creation time (no drift).

## 3. License audit

| Path | License | Notes |
|---|---|---|
| Repository root (everything outside `cloud/`) | MIT (`LICENSE`) | Permissive: use, modify, self-host, redistribute. |
| `cloud/` | OpenShorts Commercial License (`cloud/LICENSE`), declared in `NOTICE` | Permits personal/internal self-hosted use and contributing changes back. Forbids offering it as a hosted/managed/paid third-party service, reselling it, or stripping its billing/metering/entitlement checks. **This project does not use `cloud/` at all** — the local pipeline has no runtime dependency on it, so the restriction is moot in practice, but the boundary is recorded in `AGENTS.md`/`CLAUDE.md` so no future change accidentally wires a local flow through it. |
| HyperFrames (external, referenced) | Apache-2.0 | Permissive, patent grant included. Must preserve `LICENSE`/`NOTICE` if/when any HyperFrames code is vendored in a later phase. |

No GPL/AGPL or other copyleft dependency was found in `requirements.txt`,
`requirements-cpu.lock`, `requirements-billing.txt`, or
`dashboard/package.json` at a spot-check level (full per-package license
scan was not run — flagged as a Phase 1 follow-up if a formal SBOM is
wanted).

## 4. Dependency / module map

Classification legend: **KEEP** (needed, local-capable, unchanged in
Phase 0) · **KEEP-GATED** (needed but has a cloud dependency that must stay
optional/local-first) · **DISABLE-CANDIDATE** (out of scope per the PRD,
kept dormant, not deleted) · **COMMERCIAL-EXCLUDED** (under `cloud/`,
never used by this project's local pipeline).

| Module/dir | Classification | Why |
|---|---|---|
| `main.py`, `app.py`, `front.py`, `front_proxy.py`, `api_role.py`, `serve.py` | KEEP | Core job/API orchestration. |
| `clip_selection.py`, `scene_detection.py`, `frame_sampler.py`, `active_speaker.py` | KEEP | Local, CPU/GPU-only (`scenedetect`, `transnetv2-pytorch`, `mediapipe`). |
| `reframe_v2.py`, `split_layout.py`, `screencast_layout.py`, `camera_inset.py`, `panel_layout.py`, `layout_ranges.py`, `gpu_render.py`, `gpu_decode.py`, `osrender/` | KEEP | Reframing + GPU render path; local GPU (user's own), no cloud call except the vision pick below. |
| `transcribe_backends.py` | KEEP | faster-whisper, fully local. |
| `llm_backend.py` | KEEP | **The local-first enabler** — OpenAI-compatible local LLM for the two text-only moment-scoring passes (Ollama/vLLM/LM Studio/llama.cpp). No cloud key required when `LLM_BASE_URL` is set. |
| `layout_picker.py`, `screencast_layout.py` (vision call), `main.get_visual_clips` | KEEP-GATED | Still call Gemini for frame/video understanding — the one real cloud dependency left in the default pipeline. Degrades to "none"/clear failure without a key; not a hard crash. Candidate for the Phase 4 optional Gemini-Web-via-Computer-Use provider. |
| `gemini_worker.py` | KEEP-GATED | Gemini API client backing the above. |
| `editor.py`, `hooks.py`, `hook_placement.py`, `hook_grounding.py`, `subtitles.py`, `burned_subtitles.py`, `thumbnail.py`, `recut.py`, `watermarked.py`, `punch_in.py`, `quality_probe.py`, `restoring_static.py`, `pro_mode.py` | KEEP | Post-cut effects/captions/hooks; local. (`hook_grounding.py` also touches Gemini for grounding — same KEEP-GATED caveat as above.) |
| `yt_account.py`, `yt_clients.py`, `source_cache.py` | KEEP | Ingest (yt-dlp), local. |
| `worker.py`, `remote_worker.py` | KEEP | Job execution; `remote_worker.py` is an optional second local/owned host, not a managed cloud service. |
| `security_utils.py`, `ssrf_guard.py`, `media_auth.py` | KEEP | Existing security guards; unmodified. |
| `mcp_server.py`, `mcp_stdio.py`, `cli/openshorts_cli.py` | KEEP | Existing agent-callable surface; the natural extension point for Phase 3 orchestration. |
| `s3_uploader.py`, `file_hosts.py` | KEEP (optional) | Optional backup/export; not required for the core local pipeline, not disabled either. |
| `translate.py` | DISABLE-CANDIDATE | ElevenLabs dubbing/TTS — explicitly out of scope. |
| `social_platforms.py`, `social_metrics.py`, `twitch_signals.py`, `saasshorts.py` | DISABLE-CANDIDATE | Auto-publishing / social-platform integration — explicitly out of scope. |
| `free_tools.py` | DISABLE-CANDIDATE (partial) | Bundles public SEO/free-tool pages with some auto-publish-adjacent logic; needs a closer read in Phase 1 before deciding what, if anything, to gate. |
| `cloud/*` (41 files: `billing.py`, `stripe` usage, `oauth.py`, `metering.py`, `autopilot.py`, etc.) | COMMERCIAL-EXCLUDED | Commercial License; SaaS-only; zero runtime dependency from the local pipeline. |
| `dashboard/` (React + Vite + `@remotion/*`) | KEEP (pending Phase 2 decision) | Existing web UI; already uses Remotion (not HyperFrames) for in-browser preview/render. Disposition relative to HyperFrames is PRD open question 2. |
| top-level `remotion/` | KEEP (pending Phase 2 decision) | Separate standalone Remotion render project; disposition relative to HyperFrames is PRD open question 3. |
| `docs/`, `design.md`, `skills/openshorts/` | KEEP | Existing upstream documentation/design-system/agent-skill content; left untouched. |

### Dependency manifest highlights

- `requirements.txt` (base/BYOK): `scenedetect`, `transnetv2-pytorch`,
  `ultralytics`, `torch`/`torchvision`, `yt-dlp`, `faster-whisper`,
  `py3langid`, `google-genai` (the one paid-API client in the base
  manifest), `python-dotenv`, `mediapipe`, `boto3`, `fastapi`, `uvicorn`,
  `httpx`, `Pillow`, `beautifulsoup4`. All local/CPU-or-own-GPU except
  `google-genai`.
- `requirements-billing.txt`: only pulled in when `BILLING_ENABLED`
  (cloud/SaaS mode) — `sqlalchemy[asyncio]`, `stripe`, `PyJWT`,
  `email-validator`, `maxminddb`, etc. **Not needed** for this project's
  local-first pipeline.
- `requirements-cpu.lock` / `requirements-gpu.lock`: full pinned
  transitive lock for reproducible installs; CPU lock is the right default
  for a no-dedicated-inference-GPU host, GPU lock for a host with one.
- `dashboard/package.json`: `@remotion/*` (media/player/web-renderer),
  `mediabunny`, `react`, `zod`. `npm audit` reports 15 known
  vulnerabilities (1 low / 3 moderate / 11 high) in the current dependency
  tree — inherited from upstream, not introduced by this fork; recorded
  here as a Phase 1+ follow-up (`npm audit` / `npm audit fix` review), not
  fixed in Phase 0 since it touches dependency versions outside this
  phase's scope.

## 5. Security notes (spot-check only, not a full security review)

- Upstream already ships `ssrf_guard.py` and `media_auth.py`, suggesting
  SSRF and media-access protections are a known concern already addressed
  for fetched URLs — not re-verified line-by-line in Phase 0.
- No secrets, API keys, or credentials were found committed in the cloned
  tree; `.env.example` is a template with no real values.
- `npm audit` on `dashboard/` reports 15 vulnerabilities (see above) —
  dependency-version issue, not a code issue introduced here.
- A full security review (e.g. the project's own `security-review` skill)
  was **not run** in Phase 0 — out of scope for a foundation/audit phase;
  recommended before any internet-facing deployment.

## 6. Test results (Phase 0 baseline)

Commands run exactly as upstream's `.github/workflows/ci.yml` runs them,
in a throwaway virtualenv (`.venv-ci`, deleted after the run — not
committed).

| Suite | Command | Result |
|---|---|---|
| Backend unit/integration tests | `pip install pytest pillow httpx pydantic sqlalchemy greenlet numpy opencv-python-headless python-dotenv google-genai fastapi boto3 PyJWT email-validator python-multipart asyncpg` then `pytest tests/ -v` | **PASS** — 2412 passed, 103 skipped, 0 failed, exit code 0 (36–42s). Skips are the same ones CI documents: tests needing a real Postgres (`TEST_DATABASE_URL`) or Stripe sandbox state, which this environment doesn't provision. |
| Frontend build | `cd dashboard && npm ci && npm run build` | **PASS** — `npm ci` installed 230 packages cleanly; `vite build` completed, exit code 0 (warns about a few >500kB chunks — a build-size advisory, not a failure). |
| Frontend lint (`npm run lint`) | — | **NOT_RUN** — not part of upstream CI's own gate (CI only runs `build` for the frontend job), so not run here either, to avoid reporting against a bar upstream itself doesn't enforce. |
| Heavy-ML-dependent code paths (torch/ultralytics/mediapipe/faster-whisper-backed scene detection, face tracking, transcription accuracy) | — | **NOT_RUN** — upstream's own CI deliberately excludes this stack from its install for the same reason (see `ci.yml` comment: "WITHOUT the heavy ML stack ... the pipeline modules import those lazily behind their feature gates"). Installing/running it is a multi-GB download and GPU-tuned step appropriate for Phase 1's real end-to-end validation, not Phase 0's foundation audit. |
| `docker compose up --build` full-stack smoke test | — | **NOT_RUN** — not attempted in Phase 0; Docker is available on this machine (v29.1.2) but a full-stack boot (Postgres, backend, frontend, GPU passthrough) is a Phase 1 end-to-end concern, not a foundation-audit one. |
| Live job run on real video (ingest → transcribe → score → cut → reframe) | — | **NOT_RUN** — requires the heavy ML stack and a real local-LLM or Gemini key; this is Phase 1's acceptance criterion (`ACCEPTANCE_TESTS.md`), not Phase 0's. |

No test result above is claimed without having actually been executed in
this session; everything marked `NOT_RUN` is explicitly a scope decision
for Phase 0, not an unreported failure.

## 7. Risks and open issues carried into Phase 1

1. **Missing original PRD.** The user's referenced
   `PRD_OpenShorts_Clipper_Claude_Work.md` was never received. `PRD.md` in
   this repo is a reconstruction from the chat brief and must be reconciled
   once the real file is available.
2. **Vision-stage cloud dependency.** `layout_picker.py`,
   `screencast_layout.py`, and the silent-video path still require Gemini.
   This is the single concrete gap between "runs fully local today" and the
   goal; Phase 4 (optional) is the currently planned answer.
3. **Two competing render paths already in the tree**
   (`dashboard`'s `@remotion/*` usage and the standalone top-level
   `remotion/` project) that both predate the HyperFrames integration goal
   — needs a Phase 2 design decision, not a Phase 0 one.
4. **`npm audit` reports 15 vulnerabilities** in `dashboard/`'s current
   dependency tree (inherited from upstream) — unaddressed, tracked for
   Phase 1+.
5. **No formal SBOM / full per-package license scan** was produced; the
   license audit above is a manual spot-check of the declared licenses and
   the top-level dependency manifests.
6. **Heavy-ML and full-stack paths are unverified** in this environment
   (see §6) — Phase 1's job is to actually exercise them end-to-end.
