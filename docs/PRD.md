# PRD — OpenShorts Clipper (working copy)

> **Source of truth:** [`docs/PRD_OpenShorts_Clipper_Claude_Work.md`](PRD_OpenShorts_Clipper_Claude_Work.md),
> v1.0, 2026-11-21, supplied by the user. This file is a working summary and
> implementation cross-reference, not a replacement — where the two
> disagree, the source document wins. `docs/PRD_GAP_ANALYSIS.md` tracks the
> reconciliation between this project's actual state and that document.

## 1. Vision

**OpenShorts Clipper** is a self-hosted, local-first system that takes one
source video, detects interesting moments, produces 3–5 vertical (9:16)
clips, composes subtitles/overlays via HyperFrames, QA-checks the result,
and hands back finished MP4s plus an editable project and a QC report —
assembled from existing open-source projects, not built from scratch:

- **[OpenShorts](https://github.com/mutonby/openshorts)** (MIT, forked as
  this repository) — ingest, transcription, scene detection, moment
  scoring, cutting, reframing, subtitles, hook overlays, job API.
- **[HyperFrames](https://github.com/heygen-com/hyperframes)** (Apache-2.0,
  pinned dependency, Node.js 22+ worker, **not** forked/vendored into this
  repo except for a clear technical reason) — HTML/CSS/GSAP-driven visual
  composition and final rendering.
- An **AI coding agent** (Claude Code or Codex) orchestrating the pipeline
  through CLI/REST/MCP, not by editing pipeline internals per run.

## 2. Primary goals

1. Transcript-based clipping runs fully locally after models/dependencies
   are installed — no Gemini API key, fal.ai, ElevenLabs, or subscription
   required for the core pipeline.
2. Output clips are visually clean, audio-synced, correctly subtitled, and
   reproducible (same input + config → same manifest/output).
3. The whole process is controllable via CLI, REST API, and MCP, usable by
   either Claude Code or Codex — no tight coupling to one agent provider.
4. Google Gemini Web via Computer Use is available **only** as an optional,
   default-off, explicit-consent visual-analysis provider (Phase 4).
5. This project is not wired into Mabar or any other unrelated repository
   at this stage; the API design must not preclude that integration later.

## 3. Non-goals (explicitly out of scope for MVP)

- AI UGC video generation, AI actors, text-to-video, image-to-video,
  generative lip-sync.
- ElevenLabs, voice cloning, dubbing, TTS.
- SaaS monetization, billing, subscriptions, cloud accounts, third-party
  hosted rendering.
- Auto-publishing to TikTok/Instagram/YouTube (future extension, not MVP).
- Replacing Google Flow/Veo-style AI video generation.
- Relying on the Gemini browser as the *only* analysis path.

Modules implementing these in upstream OpenShorts
(`translate.py`, `social_platforms.py`, `social_metrics.py`,
`twitch_signals.py`, `saasshorts.py`, `cloud/`) are disabled via
config/route-level gating, not deleted — see `docs/UPSTREAM_AUDIT.md` for
per-module disposition and `AGENTS.md` rule 2 for the gating requirement
(backend endpoint *and* UI, not just a hidden button).

## 4. Target environment — verified, not assumed

Self-hosted on the user's own Linux desktop. This is the same bare-metal
machine this agent has executed on throughout Phase 0/1: `pop-os`, Pop!_OS
22.04 LTS, MSI MS-7C52, AMD Ryzen 5 5600G (12 threads, integrated Radeon
graphics, **no NVIDIA GPU**), 54 GiB RAM, Docker + ffmpeg + Python 3.11 +
Node 22 available, Ollama already running locally with several models
pulled. Full evidence in `docs/ENVIRONMENT.md`.

OpenShorts' GPU-accelerated path (`osrender/`, NVENC, CUDA
torch/ultralytics/mediapipe) is NVIDIA-specific per upstream's own docs and
does not apply to this machine's AMD iGPU — the CPU path
(`requirements-cpu.lock`/`requirements.txt`) is correct here, with a
graceful NVIDIA-optional fallback for any user who does have one (PRD
non-functional requirements, §D).

## 5. Where to find the rest of the spec

The source PRD is organized by section; rather than duplicate it here,
this table maps each section to where it's implemented/tracked in this
repo:

| Source PRD section | Covered in |
|---|---|
| C. System design (components, pipeline, module boundaries) | `docs/ARCHITECTURE.md` |
| D. Functional + non-functional requirements | `docs/ARCHITECTURE.md` §Requirements traceability |
| E. Data contract (timeline manifest, job states, tool API) | `docs/ARCHITECTURE.md` §Data contract |
| F. HyperFrames integration | `docs/ARCHITECTURE.md` §HyperFrames integration (Phase 2) |
| G. Agent skill `autonomous-clipper` | `docs/ARCHITECTURE.md` §Agent orchestration (Phase 3) |
| H. Gemini via Use Computer | `docs/ARCHITECTURE.md` §Optional vision provider (Phase 4) |
| I. Repository structure | this repo's actual layout, see `docs/ADR/0001-fork-and-worker-boundaries.md` |
| J. License/upstream/security audit | `docs/LICENSE_AUDIT.md`, `docs/UPSTREAM_AUDIT.md` |
| K. Milestones & DoD | `docs/ROADMAP.md` |
| L. Acceptance test scenarios | `docs/ACCEPTANCE_TESTS.md` |
| M. First-run report format | delivered in chat at the end of each phase; archived nowhere else by design (it's a report, not a spec) |
