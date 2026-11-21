# Architecture — OpenShorts Clipper

Status: draft, Phase 0/1. Reconciled against
`docs/PRD_OpenShorts_Clipper_Claude_Work.md` (the source PRD). Most of the
"Clipper layer" boxes below do not exist yet — only the OpenShorts core
(inherited from upstream) is implemented so far.

## 1. System overview

```mermaid
flowchart LR
    subgraph Agent["Orchestration (Phase 3)"]
        A[Claude Code / Codex via MCP/CLI/REST]
    end

    subgraph Core["OpenShorts core (Python/FastAPI/FFmpeg, inherited, local-first)"]
        I[Ingest: yt-dlp / upload]
        T[Transcription: faster-whisper]
        S[Scene detection: scenedetect / TransNetV2]
        M[Moment scoring]
        C[Cut: FFmpeg]
        R[Reframe: layout_picker + osrender/ffmpeg]
        Sub[Subtitles / hooks]
    end

    subgraph Providers["Pluggable analysis providers"]
        L[Local LLM\nllm_backend.py\nOllama / vLLM / LM Studio]
        G[Gemini API\n(vision stages only,\ntoday's hard dependency)]
        GW[Gemini Web via Computer Use\n(Phase 4, optional, default OFF,\nexplicit consent per upload)]
    end

    subgraph Render["HyperFrames worker (Node.js 22+, Phase 2, pinned dependency)"]
        H[Visual composition + final render]
    end

    FB[Plain FFmpeg fallback\nif HyperFrames unavailable]

    A -->|create_job / status / render / QA| Core
    I --> T --> S --> M --> C --> R --> Sub
    M -.text scoring.-> L
    R -.vision: layout pick, silent-video.-> G
    R -.optional future.-> GW
    Sub --> H
    H -->|HyperFrames down or failing| FB
    H --> Out[Finished MP4 + editable project + QC report]
    FB --> Out
```

## 2. Module boundaries (PRD §C)

- **Python (OpenShorts core):** media understanding and cut/crop — ingest,
  ASR, scene detection, candidate selection, clip extraction, reframing,
  job API. Owns no visual-composition responsibility.
- **Node/HyperFrames worker:** visual composition and final overlay
  rendering — kinetic captions, hook text, motion overlays, safe-area
  layout. Owns no media-understanding responsibility.
- **AI agent:** decisions and instructions via API/CLI only. Never edits
  binary media directly; never is the sole possible provider (Claude Code
  and Codex must both be able to drive the same surface).
- **Data exchange:** versioned JSON schemas and validated local paths only
  — see §4 below.

## 3. Components

### 3.1 OpenShorts core (inherited from upstream, unchanged in Phase 0/1)

See `docs/UPSTREAM_AUDIT.md` for the full per-file KEEP/DISABLE/REMOVE_LATER/AUDIT
table. Key pieces:

- `main.py` — per-job pipeline (transcribe → scene-detect → score → cut →
  reframe), invocable directly as `python main.py -i <file> -o <dir>` or as
  a child process from `app.py`.
- `app.py` / `front.py` / `front_proxy.py` — FastAPI server, job queue,
  REST API.
- `llm_backend.py` — local-LLM enabler for the two text-only
  moment-scoring passes, via `LLM_BASE_URL`/`LLM_MODEL`/`LLM_API_KEY`/
  `LLM_TIMEOUT`/`LLM_SCORE_BATCH`. This is the PRD's "Local Model Provider"
  component (§C.2).
- `layout_picker.py`, `screencast_layout.py`, `main.get_visual_clips`,
  `gemini_worker.py`, `hook_grounding.py` — the vision-dependent stages;
  still Gemini-only today (see `docs/UPSTREAM_AUDIT.md`, classified
  AUDIT, not KEEP, pending the Phase 4 decision).
- `mcp_server.py` / `mcp_stdio.py` / `cli/openshorts_cli.py` — existing
  agent-callable surface; the base the PRD's "minimal tool API" (§4 below)
  should wrap, not replace.

### 3.2 Local Model Provider (PRD §C.2) — already functional

Ollama (or any OpenAI-compatible server) via `LLM_BASE_URL`. Confirmed
available on this machine: Ollama 0.31.1 running locally with `qwen3:4b`,
`qwen2.5-coder:1.5b`, `llava:7b`, `nomic-embed-text` already pulled (see
`docs/ENVIRONMENT.md`). Upstream's own guidance: 7-8B+ models return valid
JSON reliably, 3B models do not — none of the locally available models
clear that bar, so JSON-validity and selection-quality must be verified
empirically (PRD correction directive), not assumed either way.

### 3.3 HyperFrames worker (PRD §C.3, §F) — Phase 2, not yet built

- Node.js 22+, separate worker process from the Python core.
- Installed/updated via HyperFrames' own supported procedure (e.g.
  `npx hyperframes skills update`) after a dependency/security audit of
  that procedure — not hand-rolled.
- Renders compositions from local inputs only: clipped footage, transcript
  word timestamps, a style JSON, the audio/video source. No CDN required
  at render time.
- **Minimum three presets required:** `clean_podcast`, `bold_kinetic`,
  `educational_screen`.
- Use `npx hyperframes lint` / `npx hyperframes check` / the render CLI —
  version-checked before assuming exact command availability, since the
  PRD explicitly warns these may not be identical across HyperFrames
  releases.
- Output per clip: `composition/index.html`, local assets, a manifest, a
  render log, and the final MP4.
- **Caching:** re-render only the stage that changed. Never re-run
  transcription just to change a font or overlay.
- **Subtitle ownership:** OpenShorts produces word timestamps; HyperFrames
  is the final subtitle *renderer* when enhanced mode is active. Never burn
  subtitles twice.
- **Fallback:** if HyperFrames is unavailable or fails but the base
  clipper is healthy, the system must still emit a plain FFmpeg MP4, with
  an explicit `NEEDS_REVIEW` (or equivalently explicit) status — never a
  silent degrade presented as a full success.

### 3.4 Agent Orchestrator (PRD §C.4, §G) — Phase 3, not yet built

Claude Code / Codex drive the pipeline via the tool API in §4 below,
implemented as a thin, safe wrapper over the existing OpenShorts
API/CLI/MCP surface (`mcp_server.py`, `cli/openshorts_cli.py`) — not a
reimplementation, and never with unrestricted shell access handed to a
browser or remote caller.

The PRD names a specific skill, `autonomous-clipper` (provider-agnostic,
usable by both Claude Code and Codex), with:

- SOP: `inspect → transcribe → rank → verify → clip → compose → render →
  QA → deliver`.
- A decision rubric: preserve context, opening hook strength, speech
  clarity, crop quality, subtitle readability, stated user objective.
- Quality gates, a tool-use policy, a maximum retry count, and a path to
  request human approval when needed.
- A safe fallback when the optional Gemini-Web provider is offline, the
  browser session expired, or upload consent wasn't given.
- A hard rule against fabricating duration, scores, benchmarks, citations,
  or job status — the agent reports what it verified, nothing more.

Not implemented yet; recorded here so Phase 3 work starts from this spec
rather than re-deriving it.

### 3.5 Optional Gemini Browser Analyzer (PRD §C.5, §H) — Phase 4, optional

- **Default OFF.** Not a dependency for the MVP under any phase before 4.
- Only a legitimate, human-authenticated browser session; only
  computer-use capability the agent's environment officially provides.
- The agent must get **explicit, specific consent** before uploading a
  private/sensitive/unpublished video — a standing "yes" is not assumed to
  cover every future upload.
- Scope of what it's asked to analyze: visual hook, on-screen context,
  scene type, active speaker, layout recommendation — returned as a JSON
  recommendation that is verified locally before use, never trusted blind.
- Must not bypass UI changes, upload limits, login walls, CAPTCHAs, rate
  limits, or Terms of Service when the browser flow hits them — fail
  visibly instead.
- A Gemini subscription is never treated as unlimited/automatic
  permission; the actual ToS and limits are checked when this phase
  actually starts, not assumed now.
- **Provenance logging required:** video hash, clip start/end, analysis
  timestamp, model/provider (if known), the raw response text, parse
  status, and human-approval status. **Never** store browser cookies or
  session tokens.

### 3.6 Local Artifact Store (PRD §C.7)

Local files and project manifests first; S3/R2 is optional, not required.
`.gitignore` must exclude `output/`, raw footage, `.env`, model weights,
browser profiles, temporary renders, and caches (verified against the
existing `.gitignore` — see `docs/UPSTREAM_AUDIT.md`).

## 4. Data contract (PRD §E)

### 4.1 Canonical timeline manifest (draft, not yet implemented — schemas/ is Phase 1+)

```json
{
  "schema_version": "1.0.0",
  "job_id": "<uuid>",
  "source": {
    "path": "assets/source.mp4",
    "sha256": "<sha256>",
    "duration_ms": 1800000
  },
  "clips": [
    {
      "clip_id": "clip_001",
      "source_in_ms": 91000,
      "source_out_ms": 133000,
      "score": 0.82,
      "score_type": "model_estimate",
      "reason": "Strong opening statement with complete context",
      "layout": { "mode": "face_track", "aspect_ratio": "9:16" },
      "caption_style": "kinetic_clean",
      "words": [{ "start_ms": 91000, "end_ms": 91350, "text": "Contoh" }],
      "overlays": [{ "type": "hook", "text": "Contoh judul", "at_ms": 0 }]
    }
  ]
}
```

Decisions still required before this is final (per the PRD itself, this
example is explicitly "belum final"):

- **Timestamp frame of reference.** PRD recommendation: `words[].start_ms`/
  `end_ms` are **source-relative** in the manifest; the HyperFrames render
  worker does the explicit transform to clip-relative. This must be
  encoded in the JSON Schema (Phase 1+, under `schemas/`), with negative-
  timestamp, offset, and overlap cases tested.
- **No absolute filesystem paths** in a manifest that may move between
  machines — use paths relative to the job root.
- `score`/`score_type: "model_estimate"` must never be presented as a
  guarantee of virality — the field name says so on purpose.

### 4.2 Job state machine (PRD §E)

```
CREATED -> INGESTING -> TRANSCRIBING -> ANALYZING -> SELECTING -> CLIPPING -> COMPOSING -> RENDERING -> QA -> COMPLETED
```

Terminal/alternate states: `FAILED`, `CANCELED`, `NEEDS_REVIEW`. Each job
record persists `stage`, `error_code`, `attempt`, timestamps, and
`artifacts`. Retry policy: up to 3 attempts per stage for recoverable
errors; **never** auto-retry a CAPTCHA, an unauthorized/billing error, or
an invalid-source error.

Not yet implemented as a formal state machine — today's `main.py`/`app.py`
job tracking is less granular. This is explicitly a Phase 1+ deliverable,
not retrofitted in Phase 0.

### 4.3 Minimal tool API (design target, to wrap existing endpoints)

```
create_job(input_path, settings) -> job_id
process_job(job_id) -> accepted
get_job_status(job_id) -> stage/progress/errors
list_clip_candidates(job_id) -> ranked clips
update_clip(job_id, clip_id, decisions) -> updated manifest
render_clip(job_id, clip_id, preset) -> output_id
inspect_output(job_id, clip_id) -> QA report
get_artifacts(job_id) -> output paths
cancel_job(job_id) -> canceled
```

Implemented as a thin, safe wrapper over the existing OpenShorts
API/CLI/MCP functions (§3.1) — not a parallel reimplementation. No
unrestricted shell tool is ever exposed to a browser or remote caller.

## 5. Requirements traceability (PRD §D)

Functional requirements FR-01 through FR-16 and the non-functional
requirements (local-first, no mandatory paid key, CPU-only path with
graceful NVIDIA-optional acceleration, concurrency capped at 1 for the CPU
baseline until benchmarked, no public API exposure without auth/TLS,
opt-in/disabled telemetry, documented network egress, no credentials in
logs/git, idempotent restartable jobs) are tracked against the actual
codebase per-module in `docs/UPSTREAM_AUDIT.md` rather than duplicated
here. `docs/ACCEPTANCE_TESTS.md` carries the PRD's 10 acceptance scenarios
with their current PASS/FAIL/NOT_RUN status.

## 6. Open items

1. `remotion/` (top-level) and `dashboard/`'s `@remotion/*` usage: per the
   PRD correction directive, **not removed** until a HyperFrames
   proof-of-concept backs that decision (see `docs/ADR/0001-fork-and-worker-boundaries.md`).
2. The exact HyperFrames pin (version/tag) is not yet chosen — Phase 2
   work.
3. Formal JSON Schema for the timeline manifest, and the job-state-machine
   implementation, are Phase 1+ deliverables, not yet built.
