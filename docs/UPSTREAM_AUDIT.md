# Upstream Audit — OpenShorts Clipper

Covers source provenance and the module/dependency map. License specifics
are in `docs/LICENSE_AUDIT.md`; environment evidence is in
`docs/ENVIRONMENT.md`. Classification legend follows the PRD's first-run
report format (`docs/PRD_OpenShorts_Clipper_Claude_Work.md` §M): **KEEP**,
**DISABLE**, **REMOVE_LATER**, **AUDIT**.

## 1. Source provenance

| Repo | Role | Default branch | Commit SHA audited |
|---|---|---|---|
| [`mutonby/openshorts`](https://github.com/mutonby/openshorts) | Forked (this repository's upstream) | `main` | `5da5b839d3231e3b2152250fa83aa17d40c91e64` |
| [`heygen-com/hyperframes`](https://github.com/heygen-com/hyperframes) | Referenced as a pinned dependency (Phase 2), **not forked/vendored** | `main` | `63d1bb5596d0a307b3efa4290a7a3cf3848e090e` |

`mutonby/openshorts` at audit time: public, 9,527 stargazers, 2,003 forks,
not archived, pushed 2026-11-20. Its GitHub fork-network lists
`kamilstanuch/Autocrop-vertical` (no declared license on that repo) as the
network root — recorded per the PRD's explicit instruction not to assume
every inherited line is MIT just because the current root license says so.
No attempt was made in Phase 0 to audit file-by-file which lines trace back
to that ancestor; this is flagged as a residual provenance risk, not
resolved.

## 2. Fork created

- **URL:** https://github.com/yadenmustopa/openshorts-clipper
- Created via `gh repo fork mutonby/openshorts`, then renamed via the
  GitHub API (installed `gh` v2.4.0 predates the `--fork-name` flag).
- **Public.** GitHub does not allow a private fork of a public repo on a
  personal account — confirmed before creation, accepted per the user's
  explicit Phase 0 instructions and PRD §A.2.
- `origin` → `git@github.com:yadenmustopa/openshorts-clipper.git`
- `upstream` → `git@github.com:mutonby/openshorts.git`
- Working branch: `chore/phase-0-foundation`, both remotes at `5da5b83` at
  branch-creation time (no drift).

## 3. Module / dependency map

| Module/dir | Classification | Why |
|---|---|---|
| `main.py`, `app.py`, `front.py`, `front_proxy.py`, `api_role.py`, `serve.py` | KEEP | Core job/API orchestration. |
| `clip_selection.py`, `scene_detection.py`, `frame_sampler.py`, `active_speaker.py` | KEEP | Local, CPU/GPU-only (`scenedetect`, `transnetv2-pytorch`, `mediapipe`). |
| `reframe_v2.py`, `split_layout.py`, `screencast_layout.py`, `camera_inset.py`, `panel_layout.py`, `layout_ranges.py`, `gpu_render.py`, `gpu_decode.py`, `osrender/` | KEEP | Reframing + render path; CPU path confirmed working on this machine (no NVIDIA GPU — see `ENVIRONMENT.md`), GPU path is for a user with an NVIDIA card. |
| `transcribe_backends.py` | KEEP | faster-whisper, fully local. |
| `llm_backend.py` | KEEP | The local-first enabler for text moment-scoring — OpenAI-compatible local LLM (Ollama/vLLM/LM Studio/llama.cpp) via `LLM_BASE_URL`. |
| `layout_picker.py`, `screencast_layout.py` (vision call), `main.get_visual_clips`, `gemini_worker.py`, `hook_grounding.py` (vision grounding) | AUDIT | Still call Gemini for frame/video understanding — the one real cloud dependency left in the default pipeline. Degrades to "none"/clear failure without a key, never a hard crash or a fabricated result (matches PRD acceptance scenario #4). Disposition depends on the Phase 4 Gemini-Web-via-Computer-Use decision — not disabled, not kept as a permanent dependency either; genuinely pending. |
| `editor.py`, `hooks.py`, `hook_placement.py`, `subtitles.py`, `burned_subtitles.py`, `thumbnail.py`, `recut.py`, `watermarked.py`, `punch_in.py`, `quality_probe.py`, `restoring_static.py`, `pro_mode.py` | KEEP | Post-cut effects/captions/hooks; local. |
| `yt_account.py`, `yt_clients.py`, `source_cache.py` | KEEP | Ingest (yt-dlp), local; URL ingest needs internet and must respect content rights per PRD FR-01. |
| `worker.py`, `remote_worker.py` | KEEP | Job execution; `remote_worker.py` is an optional second host the user owns, not a managed cloud service. |
| `security_utils.py`, `ssrf_guard.py`, `media_auth.py` | KEEP | Existing security guards; unmodified. |
| `mcp_server.py`, `mcp_stdio.py`, `cli/openshorts_cli.py` | KEEP | Existing agent-callable surface; the extension point for Phase 3 orchestration (PRD §E "Minimal tool API" should wrap these, not replace them). |
| `s3_uploader.py`, `file_hosts.py` | AUDIT | PRD vision is local-artifact-store-first ("file lokal terlebih dahulu, S3 tidak diperlukan" — §C.7); not required by the core pipeline. Not disabled outright since self-hosters may still want optional backup, but default config should not require it. |
| `translate.py` | DISABLE | ElevenLabs dubbing/TTS — explicit PRD non-goal. Gating must cover the backend endpoint, not just the UI (PRD correction directive; see `AGENTS.md` rule 2). |
| `social_platforms.py`, `social_metrics.py`, `twitch_signals.py`, `saasshorts.py` | DISABLE | Auto-publishing / social-platform / AI-UGC-adjacent — explicit PRD non-goals (§B "Non-goals"). |
| `free_tools.py` | AUDIT | Bundles public SEO/free-tool pages with some auto-publish-adjacent logic; needs a closer read before classifying definitively as DISABLE or KEEP (partial). |
| `cloud/*` (41 files: `billing.py`, `stripe` usage, `oauth.py`, `metering.py`, `autopilot.py`, etc.) | AUDIT | OpenShorts Commercial License, SaaS-only — see `docs/LICENSE_AUDIT.md`. The PRD explicitly requires auditing the actual import graph before assuming it is fully excludable, not just asserting "no dependency." **That audit was done** (this phase): `app.py` unconditionally imports two specific submodules, `cloud.queue_mode` and `cloud.owner_cache`, at module load time — both are explicitly documented upstream as "no dependencies beyond the standard library, importable with billing off," and both are functionally inert unless billing-specific state is configured. Every other `cloud/` submodule (`managed_keys`, `metering`, `stripe`-backed code, `emails`, etc.) is imported only inside `if BILLING_ENABLED:` blocks in `app.py`. Net finding: **not zero import-time coupling, but zero functional/runtime dependency with billing off** — the earlier Phase 0 claim of "zero dependency" is corrected to this more precise statement. |
| `dashboard/` (React + Vite + `@remotion/*`) | AUDIT | Existing web UI; already uses Remotion (not HyperFrames) for in-browser preview/render. Per the PRD correction directive: **do not remove or replace until a HyperFrames proof-of-concept backs that architectural decision.** Not REMOVE_LATER yet — that reclassification happens only after the Phase 2 PoC. |
| top-level `remotion/` | AUDIT | Same PoC-gated disposition as `dashboard/`'s Remotion usage. |
| `docs/architecture/*`, `design.md`, `skills/openshorts/` | KEEP | Existing upstream documentation/design-system/agent-skill content; left untouched. |

### Dependency manifest highlights

- `requirements.txt` (base/BYOK): `scenedetect`, `transnetv2-pytorch`,
  `ultralytics`, `torch`/`torchvision`, `yt-dlp`, `faster-whisper`,
  `py3langid`, `google-genai` (the one paid-API client in the base
  manifest), `python-dotenv`, `mediapipe`, `boto3`, `fastapi`, `uvicorn`,
  `httpx`, `Pillow`, `beautifulsoup4`. All local/CPU-or-own-GPU except
  `google-genai`.
- `requirements-billing.txt`: only pulled in when `BILLING_ENABLED` —
  `sqlalchemy[asyncio]`, `stripe`, `PyJWT`, `email-validator`,
  `maxminddb`, etc. Not needed for the local-first pipeline.
- `requirements-cpu.lock` / `requirements-gpu.lock`: full pinned transitive
  lock for reproducible installs. **Known issue found in Phase 1 (not
  Phase 0):** several exact pins in `requirements-cpu.lock` (e.g.
  `soupsieve==4.0.1`) are no longer resolvable against live PyPI in this
  dated environment (2026-11-21) — the lock has drifted from what PyPI
  actually serves. The Phase 1 local pipeline install used
  `requirements.txt` with normal dependency resolution instead (see
  `docs/ROADMAP.md` Phase 1 notes) and got a working environment, but this
  means the lock file can no longer be trusted for a bit-for-bit
  reproducible install on this machine without regenerating it.
- `dashboard/package.json`: `@remotion/*`, `mediabunny`, `react`, `zod`.
  `npm audit` reports 15 known vulnerabilities (1 low / 3 moderate / 11
  high) in the current dependency tree — inherited from upstream, not
  introduced by this fork.

## 4. Security notes (spot-check only, not a full security review)

- Upstream already ships `ssrf_guard.py` and `media_auth.py` — SSRF and
  media-access protections for fetched URLs appear to already be a known
  concern upstream; not re-verified line-by-line here.
- No secrets, API keys, or credentials were found committed in the cloned
  tree; `.env.example` is a template with no real values.
- `npm audit` on `dashboard/` reports 15 vulnerabilities (see above).
- A full security review (secret scanning, dependency scanning beyond
  `npm audit`, path-traversal testing per PRD acceptance scenario #9) was
  **not run** in Phase 0/1 — recommended before any internet-facing
  deployment, and explicitly required before Phase 3 exposes any API
  surface to an agent running outside this machine.

## 5. Feature gating (Phase 1)

`feature_flags.py` (new, root) is the single source of truth for whether
UGC generation, TTS, dubbing, social publishing, and Gemini vision are
reachable. Default: all off except `CLIPPER_ENABLED`/`LOCAL_LLM_ENABLED`.
Gated at the route/function itself (`app.py`: 26 call sites via a
`require_feature()` helper returning a structured `{"error":
"FEATURE_DISABLED", "feature": <name>, "message": ...}` 403 — same shape
as the existing `payment_required` convention; `main.py`'s subprocess-side
Gemini-vision call sites — `layout_picker.pick`, `screencast_layout.detect_content_ranges`,
`hook_grounding.reground`, `main.get_visual_clips` — via a direct
`feature_flags.enabled("GEMINI_VISION_ENABLED")` check, independent of
whether a Gemini key happens to be present). MCP (`mcp_server.py`) and the
CLI (`cli/openshorts_cli.py`) both proxy the same HTTP API, so they
inherit every gate without separate code. The dashboard additionally hides
the corresponding tabs/buttons (`App.jsx`, `ResultCard.jsx`) as a UX
convenience — not the actual enforcement point. `cloud/` itself was not
modified (its own `BILLING_ENABLED` gate is a stronger, route-doesn't-exist
gate already). Tests: `tests/test_feature_flags.py` (47 new), plus 22
pre-existing upstream tests updated to set the flag their tested behavior
now sits behind (e.g. an ownership check on a route that's gated off by
default needs the gate opened first to reach the code under test).

## 6. No-outbound-internet test (Phase 1 Step A.5)

Tested, not assumed: ran the scenario-1 pipeline twice with
`ss -tnp` sampled every second against the exact PID, once plain and once
with `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1` set, distinguishing
localhost (`127.0.0.1:11434`, Ollama — expected, this is the local model
server) and the machine's own LAN address (`192.168.1.12`, the source
address of outbound sockets, not a destination) from genuine public
internet.

| Run | External (public-internet) hosts contacted | Job outcome |
|---|---|---|
| Plain (no offline flags) | `13.35.202.121:443` (AWS CloudFront, reverse-resolves to `*.sin2.r.cloudfront.net` — Hugging Face Hub's CDN) and `20.184.175.4:443` (Microsoft/Azure ASN, unidentified) | Succeeded (3 clips) |
| `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1` | Only `20.184.175.14:443` (same Azure ASN block, unidentified) | Succeeded (2 clips) |

**Finding:** the Hugging Face Hub freshness check `faster_whisper.utils.
download_model` triggers via `huggingface_hub.snapshot_download` (called
from `transcribe_backends.py`'s model loader, which does not pass
`local_files_only=True` or otherwise force offline mode) is real and is
fixed by setting `HF_HUB_OFFLINE=1`/`TRANSFORMERS_OFFLINE=1` once models
are cached — the job succeeds identically with or without it, confirming
the check was non-essential (the already-cached model is used in both
cases).

**Not fully resolved:** a second, smaller external connection (Azure ASN)
persisted even with both offline env vars set. Investigated but not
conclusively identified: `ultralytics`' built-in Sentry telemetry was
checked and ruled out (`set_sentry()`'s own guard clause requires
`sys.argv[0]` to be literally `"yolo"` — the CLI binary name — which is
never true when `ultralytics` is imported as a library from `main.py`, so
it short-circuits before `sentry_sdk.init()`). The exact source among
`mediapipe`/`onnxruntime`/`ctranslate2`/`transnetv2-pytorch` was not
pinned down within this phase's time budget. **The job's actual output
was byte-for-byte unaffected** by this connection existing or not (same
success, same clip count class of outcome) — it is best-effort/telemetry-
shaped, not a functional dependency, but it is an honest open item, not a
closed one. A self-hoster wanting airtight zero-egress should block it at
the OS level (e.g. `/etc/hosts` or a firewall rule once its exact hostname
is identified) rather than rely on an application-level fix that isn't
confirmed to exist yet.

**Recommendation for the default config:** set `HF_HUB_OFFLINE=1` and
`TRANSFORMERS_OFFLINE=1` by default once a self-hosted install's models
are known to be cached (e.g. in `.env.example`, commented, with the
instruction to uncomment after first run) — not done in this phase since
it changes first-run (cold cache) behavior and deserves its own decision,
not a side effect of an audit.

## 7. Local-LLM performance on this machine (Phase 1 finding)

A 4B "thinking"/reasoning model (`qwen3:4b`) timed out (>600s,
`llm_backend.py`'s default) scoring a single transcript window from a 90s
clip — CPU-only, no NVIDIA GPU (see `docs/ENVIRONMENT.md`). A 7B
non-reasoning model (`llava:7b`) succeeded on all three local-footage
fixtures tried (single speaker, two speakers, screencast — see
`docs/ACCEPTANCE_TESTS.md`), every time well under the timeout, with valid
JSON and a qualitatively sensible, transcript-accurate result. This
matches upstream's own README guidance ("7-8B models return valid JSON
reliably, 3B ones do not") and extends it with a CPU-specific data point:
parameter count alone doesn't predict practicality on CPU-only hardware —
a reasoning model's token overhead matters as much as its size. Full
evidence in `docs/ACCEPTANCE_TESTS.md` "Local-LLM model selection".
