# PRD — OpenShorts Clipper (Autonomous AI Video Clipper)

> **Status: DRAFT, derived from the chat-provided brief.**
> The user's original brief referenced an attached file,
> `PRD_OpenShorts_Clipper_Claude_Work.md`, as the authoritative source
> specification. That file was never actually received by the agent that
> wrote this document (not present in the working directory or the
> conversation). This PRD is reconstructed from the detailed instructions
> given directly in chat for Phase 0. **It must be reconciled against the
> original file once the user supplies it**, before Phase 1 planning is
> treated as final. Until then, treat every requirement below as
> provisional.

## 1. Vision

Build an autonomous AI video clipper that turns long-form video into short
vertical clips, running entirely self-hosted on the user's own Linux
machine, with no subscription and no mandatory paid API. The system is
assembled from existing open-source projects rather than built from
scratch:

- **[OpenShorts](https://github.com/mutonby/openshorts)** (MIT, forked as
  this repository) — ingest, transcription, scene detection, moment
  scoring, cutting, reframing, subtitles, hook overlays.
- **[HyperFrames](https://github.com/heygen-com/hyperframes)** (Apache-2.0,
  referenced as an external dependency/integration target, not forked) —
  HTML-driven rendering and motion graphics for finishing clips.
- An **AI coding agent** (Claude Code or Codex) as the orchestrator that
  drives the pipeline end-to-end, rather than a human operating a GUI for
  every step.

## 2. Goals

1. The core clipping pipeline (ingest → transcribe → detect scenes → score
   moments → cut → reframe → subtitle) must run fully locally, with no
   required subscription or paid API key.
2. Rendering and motion-graphics finishing is handed off to HyperFrames.
3. An AI agent can orchestrate the whole pipeline (trigger jobs, inspect
   results, adjust parameters) through a stable API/CLI surface — not by
   reading or rewriting pipeline internals per run.
4. The project stays legally clean: MIT core respected, the `cloud/`
   Commercial License boundary respected, HyperFrames' Apache-2.0 respected.
5. Changes are made incrementally and reviewably against upstream
   `mutonby/openshorts`, so the fork can keep merging upstream fixes.

## 3. Non-goals (explicitly out of scope)

- AI UGC/avatar generation.
- AI actors.
- Dubbing / voice translation (upstream's `translate.py`, ElevenLabs-based).
- TTS (text-to-speech) generation.
- Auto-publishing to social platforms (upstream's `social_platforms.py`,
  `saasshorts.py`, related auto-publish flows).
- Any cloud/SaaS billing surface (`cloud/`, `BILLING_ENABLED`) — present in
  the codebase for license/provenance reasons, never operated.

These are not deleted outright in Phase 0 (see
`docs/clipper/AUDIT_REPORT.md` and `AGENTS.md` rule 3 — no speculative bulk
deletion before a module-by-module dependency audit). They are tracked as
"disable/keep-dormant" candidates for a later phase.

## 4. Target environment

- Self-hosted on the user's own Linux desktop (this environment: Ubuntu,
  `/mnt/nvme` storage, Docker + ffmpeg + Python 3.11 + Node 22 available
  locally — see `docs/clipper/AUDIT_REPORT.md` for the exact baseline).
- No requirement on GPU cloud rental, managed Postgres, or any other paid
  infrastructure for the primary pipeline. (`osrender/`'s GPU path is for
  the user's own local GPU, not a cloud GPU rental — see
  `docs/architecture/jobs-and-deploys.md` upstream.)

## 5. Optional / future providers

- **Gemini Web via Computer Use** is an explicitly *optional* visual-analysis
  provider for a *later* phase (not Phase 0 or Phase 1). It is intended to
  stand in for the vision-dependent stages that currently require the paid
  Gemini API (`layout_picker.py`, `screencast_layout.py`,
  `main.get_visual_clips`) — see `llm_backend.py` and
  `docs/architecture/clip-selection.md` for what already runs on a local
  LLM today (the *text*-only moment-scoring passes) versus what still
  requires a vision model.

## 6. Constraints carried over from the engineering rules

- Do not rebuild OpenShorts from scratch; keep existing functionality that
  is still needed.
- Do not remove many modules before the dependency audit is complete.
- Do not touch any other repository (e.g. unrelated `Mabar` repos on this
  machine).
- Modular, local-first, API-first, agent-agnostic design.
- No credentials committed to git.
- Structured commits; document architectural decisions.
- No destructive git operations (force-push, hard reset, branch deletion)
  without explicit instruction.
- No claiming a test passed without having actually run it in this
  environment.

## 7. Open questions (blocking Phase 1 finalization)

1. What does the original `PRD_OpenShorts_Clipper_Claude_Work.md` specify
   that isn't captured above? (format/resolution targets, clip length
   targets, which HyperFrames version/branch, specific CLI/API contract
   between the agent and the pipeline, UI requirements, etc.)
2. Is the existing OpenShorts dashboard (React + Remotion,
   `dashboard/`) kept as the UI, replaced, or run alongside a new
   agent-driven CLI/API-only mode?
3. How should the top-level `remotion/` project (a separate Remotion render
   app already in this repo, distinct from HyperFrames) relate to the
   HyperFrames integration — coexist, get superseded, or get removed once
   HyperFrames covers its role?
