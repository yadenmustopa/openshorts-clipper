# Architecture — OpenShorts Clipper

Status: draft, Phase 0. Describes the target shape; most of the "Clipper
layer" boxes below do not exist yet — only the OpenShorts core (inherited
from upstream) is currently implemented.

## 1. System overview

```mermaid
flowchart LR
    subgraph Agent["Orchestration (Phase 3)"]
        A[Claude Code / Codex]
    end

    subgraph Core["OpenShorts core (inherited, local-first)"]
        I[Ingest: yt-dlp / upload]
        T[Transcription: faster-whisper]
        S[Scene detection: scenedetect / TransNetV2]
        M[Moment scoring]
        C[Cut: FFmpeg]
        R[Reframe: layout_picker + osrender GPU]
        Sub[Subtitles / hooks]
    end

    subgraph Providers["Pluggable analysis providers"]
        L[Local LLM\nllm_backend.py\nOllama / vLLM / LM Studio]
        G[Gemini API\n(vision stages only,\ntoday's hard dependency)]
        GW[Gemini Web via Computer Use\n(Phase 4, optional)]
    end

    subgraph Render["Rendering / motion graphics (Phase 2)"]
        H[HyperFrames bridge]
    end

    A -->|drives via API/CLI| Core
    I --> T --> S --> M --> C --> R --> Sub
    M -.text scoring.-> L
    R -.vision: layout pick, silent-video.-> G
    R -.optional future.-> GW
    Sub --> H
    H --> Out[Finished vertical clip]
```

## 2. Components

### 2.1 OpenShorts core (inherited from upstream, unchanged in Phase 0)

- `main.py` — per-job pipeline: transcription → scene detection → moment
  scoring → cut → reframe.
- `app.py` / `front.py` / `front_proxy.py` — FastAPI server, job queue, REST
  API, multiprocess front/engine split.
- `clip_selection.py`, `layout_picker.py`, `reframe_v2.py`,
  `split_layout.py`, `screencast_layout.py`, `camera_inset.py`,
  `panel_layout.py`, `layout_ranges.py` — moment picking and reframing
  layouts.
- `gpu_render.py`, `gpu_decode.py`, `osrender/` (Rust/CUDA) — the GPU render
  pass that composites a scene's layout graph in one pass.
- `editor.py`, `hooks.py`, `hook_placement.py`, `hook_grounding.py`,
  `subtitles.py`, `burned_subtitles.py`, `thumbnail.py` — post-cut effects,
  hook overlays, captions, thumbnails.
- `transcribe_backends.py` — faster-whisper, fully local.
- `llm_backend.py` — **the local-first enabler**: routes the two
  *text-only* transcript-scoring passes in `main.get_viral_clips` to any
  OpenAI-compatible server (Ollama, vLLM, LM Studio, llama.cpp) when
  `LLM_BASE_URL` is set, bypassing Gemini for that stage.
- `gemini_worker.py` — direct Gemini API client. Still required today for
  the stages `llm_backend.py` explicitly does not cover: `layout_picker.py`
  (frame-based layout choice), `screencast_layout.py` (on-screen content
  detection), `main.get_visual_clips` (silent-video path). This is the one
  documented hard dependency on a paid API in the default pipeline.
- `mcp_server.py` / `mcp_stdio.py` — existing MCP tool surface; relevant
  prior art for "agent-callable pipeline", likely the right place to extend
  for Phase 3 orchestration rather than inventing a parallel API.
- `cli/openshorts_cli.py` — existing Python CLI entry point.
- `yt_account.py`, `yt_clients.py`, `source_cache.py` — ingest/download.
- `worker.py`, `remote_worker.py` — job execution, optional second-host CPU
  worker.
- `security_utils.py`, `ssrf_guard.py`, `media_auth.py` — existing security
  guards (SSRF protection on fetched media URLs, media auth tokens). Not
  modified in Phase 0; worth reviewing in a later security pass.

### 2.2 Out-of-scope modules (present, dormant by design)

Not built on, not removed yet (see `AUDIT_REPORT.md` for disposition):
`translate.py` (ElevenLabs dubbing/TTS), `social_platforms.py`,
`social_metrics.py`, `twitch_signals.py`, `saasshorts.py`, the auto-publish
parts of `free_tools.py`.

### 2.3 Commercial-licensed, untouched

`cloud/` — billing, managed API keys, SaaS account lifecycle. Under the
OpenShorts Commercial License, not MIT. The local pipeline has zero runtime
dependency on it; it stays in the tree only because it ships with upstream.

### 2.4 Existing frontend (reference, not yet decided — see PRD open question 2)

`dashboard/` (React + Vite) already renders previews via `@remotion/*`
packages. A separate top-level `remotion/` directory is a standalone
Remotion render project. Neither is HyperFrames; both predate this fork's
goal of using HyperFrames for rendering/motion graphics. Phase 2 must decide
whether HyperFrames replaces this Remotion usage, sits alongside it, or only
takes over the "finishing" step after OpenShorts' own cut/reframe/subtitle
stages.

### 2.5 New: HyperFrames bridge (Phase 2, not yet built)

Planned integration point: OpenShorts produces a cut-and-reframed clip
(with burned or soft subtitles and hook overlays already applied, per
today's pipeline order); HyperFrames takes that clip plus any motion-graphics
spec and renders the finished output. Exact handoff format (file path
convention vs. a small HTTP call vs. a HyperFrames CLI invocation) is a
Phase 2 design decision, to be recorded here once made — do not invent it
silently inside pipeline code.

### 2.6 New: agent orchestration layer (Phase 3, not yet built)

Claude Code / Codex drives the pipeline by calling the existing (or
lightly extended) `mcp_server.py` / REST API / `cli/openshorts_cli.py`
surface — not by directly importing and calling internal pipeline
functions. Keeps the agent interface stable even as pipeline internals
change.

### 2.7 New: optional local/agent-driven vision provider (Phase 4, optional)

A provider implementing the same contract `gemini_worker.py` exposes for
vision stages, backed by Gemini Web driven through Computer Use instead of
the paid Gemini API. Explicitly optional and explicitly later-phase per the
PRD; must degrade the same way an absent Gemini key degrades today
(`layout_picker`/`screencast_layout` return "none", `get_visual_clips` fails
the job with a clear message) when unavailable.

## 3. Data flow (today, unchanged by Phase 0)

Ingest (yt-dlp or upload) → transcription (word timestamps, faster-whisper)
→ scene detection → moment scoring (local LLM if `LLM_BASE_URL` set, else
Gemini) → FFmpeg cut → vertical reframing (Gemini for layout choice today) →
effects/subtitles → hook overlay → [Phase 2: HyperFrames finishing] →
output.

## 4. Integration principles

- API-first: every new capability (HyperFrames bridge, local vision
  provider) is reachable through the existing HTTP/MCP/CLI surface, so the
  orchestrating agent never needs pipeline-internal knowledge.
- Agent-agnostic: nothing in the new integration layer assumes "Claude Code"
  specifically; Codex or any other agent must be able to drive the same
  surface.
- Config-gated, not code-forked: new providers are selected via environment
  variables / config (mirroring `llm_backend.py`'s `LLM_PROVIDER`/
  `LLM_BASE_URL` pattern), not via maintaining parallel copies of pipeline
  files.
