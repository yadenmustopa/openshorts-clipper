# AGENTS.md — OpenShorts Clipper

Agent-agnostic rules for any autonomous coding agent (Codex, Claude Code, or
otherwise) working in this repository. `CLAUDE.md` carries the same rules
plus Claude-Code-specific detail; the two must not drift apart on the "Hard
rules" below. When they conflict, this file wins for non-Claude agents and
`CLAUDE.md` wins for Claude Code.

## What this repository is

`openshorts-clipper` is a fork of [mutonby/openshorts](https://github.com/mutonby/openshorts)
(MIT, `cloud/` excepted — see "License boundaries"). It is being adapted into
an **Autonomous AI Video Clipper** that runs self-hosted on a Linux desktop:

- **OpenShorts** supplies ingest, transcription, scene detection, moment
  scoring, cutting, reframing, subtitles and hook overlays.
- **[HyperFrames](https://github.com/heygen-com/hyperframes)** (Apache-2.0,
  referenced — not forked into this repository) supplies HTML-driven
  rendering and motion graphics for finishing clips.
- An AI agent (Claude Code or Codex) orchestrates the pipeline end-to-end.

**Source of truth:** `docs/PRD_OpenShorts_Clipper_Claude_Work.md` (supplied
by the user). `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`,
`docs/UPSTREAM_AUDIT.md`, `docs/LICENSE_AUDIT.md`, `docs/ACCEPTANCE_TESTS.md`
and `docs/ADR/` are the working implementation of that source — read them,
and `docs/PRD_GAP_ANALYSIS.md` for known deltas, before making
architectural changes.

## Hard rules

1. **Local-first, no mandatory paid service.** The primary pipeline must run
   fully offline on the user's own machine with no subscription and no paid
   API key. Do not make Gemini, fal.ai, ElevenLabs, or any HeyGen Cloud
   service a hard dependency of the default path. `llm_backend.py` already
   provides an OpenAI-compatible local-LLM path (Ollama/vLLM/LM
   Studio/llama.cpp) for the text-only moment picker — prefer extending that
   pattern over adding new cloud calls. Vision-dependent stages
   (`layout_picker.py`, `screencast_layout.py`, `main.get_visual_clips`) are
   the one documented gap still requiring Gemini; closing it with a local or
   agent-driven alternative (e.g. Gemini Web via Computer Use) is a
   deliberate later-phase goal, not a Phase 0/1 requirement.
2. **Out of scope, do not build:** AI UGC/avatar generation, AI actors,
   dubbing, TTS, SaaS billing, or auto-publishing to social platforms.
   Existing modules that implement these (`translate.py`,
   `social_platforms.py`, `social_metrics.py`, `twitch_signals.py`,
   `saasshorts.py`, parts of `free_tools.py`, `cloud/`) are feature-flagged
   or left dormant, not deleted, until a dependency audit explicitly
   approves removal. **Gating must be defense-in-depth:** the backend
   endpoint/route itself must refuse the request (not just omit it from a
   response), in addition to the UI not offering the control. Hiding a
   button while leaving the route live is not compliant.
3. **Do not delete modules speculatively.** No bulk deletion of upstream
   modules before the dependency audit for that module is complete and
   recorded in `docs/UPSTREAM_AUDIT.md`. Prefer disabling via
   config/feature flags over deleting code — it keeps the diff reviewable
   against upstream and keeps `git merge upstream/main` viable. This
   explicitly covers `dashboard/`'s `@remotion/*` usage and the top-level
   `remotion/` project: neither is removed or replaced until a HyperFrames
   proof-of-concept exists to justify it (`docs/ADR/0001-fork-and-worker-boundaries.md`).
4. **License boundaries.**
   - Root tree: MIT (see `LICENSE`, `NOTICE`). Free to use, modify, and
     self-host.
   - `cloud/`: OpenShorts Commercial License (see `cloud/LICENSE`). Personal/
     internal self-hosted use is permitted; do NOT offer it as a hosted
     service to third parties, resell it, or strip its metering/entitlement
     checks. This project's local pipeline does not need `cloud/` at all —
     treat it as inert upstream baggage, not a dependency.
   - HyperFrames integration code (when added, e.g. under `integrations/` or
     a vendored subfolder): Apache-2.0. Keep its `LICENSE`/`NOTICE` attached
     and do not relicense it.
   - Never bypass, remove, or weaken license headers/NOTICE files when
     merging upstream changes.
5. **Agent-agnostic, API-first, modular.** New integration points (HyperFrames
   bridge, local-LLM providers, local vision providers) must be exposed
   through a stable internal API/CLI boundary, not hard-wired into `main.py`'s
   control flow. Any agent (Claude Code, Codex, a future one) should be able
   to drive the pipeline through that boundary without reading pipeline
   internals.
6. **Credentials.** Never commit credentials, tokens, or `.env` files. Use
   `.env.example` as the template. If a feature needs a key the user hasn't
   provided, degrade gracefully (as `llm_backend.py` / Gemini fallback
   already does) rather than failing hard or inventing a key.
7. **No destructive git operations** (force-push, history rewrite, branch
   deletion) without explicit user instruction in the current request.
   Always work on a feature/chore branch, never commit directly to `main`.
8. **Testing honesty.** Report test results as `PASS`, `FAIL`, `NOT_RUN`, or
   `PARTIAL`. Never claim a test passed without having actually executed it
   in the current environment, and never claim throughput, quality, or
   "commercial-grade" results without a benchmark log naming the hardware,
   input size/duration, model, and per-stage timing. Before concluding a
   hardware limitation (e.g. "no GPU"), verify whether the current terminal
   is the user's actual target machine or a different sandbox — check
   `systemd-detect-virt`, `/etc/os-release`, `lspci`, not just a tool's
   absence (see `docs/ENVIRONMENT.md` for the standing evidence on this
   machine).
9. **Never fabricate.** No invented durations, virality scores, benchmarks,
   citations, or job statuses — report what was verified, mark the rest
   `NOT_RUN`/unknown.
10. **Non-functional constraints** (PRD §D): concurrency capped at 1 for
   the CPU baseline until a real benchmark justifies raising it; no public
   API exposure without authentication/TLS; Docker ports default to
   localhost, not `0.0.0.0`, for anything sensitive; telemetry is opt-in or
   disabled, and all third-party network egress is documented.
11. **Scope of filesystem/GitHub access.** Never touch the Mabar
   repositories, the global `.agents`/`.claude`/`.codex` config folders, or
   any private file outside this project's working tree without explicit
   user permission for that specific action.
12. **Document architectural decisions** in `docs/` (see `docs/ADR/`) as
   they're made — do not let decisions live only in commit messages or
   chat history.

## Workflow

- Branch naming: `feat/<slug>`, `fix/<slug>`, `chore/<slug>`, `docs/<slug>`.
- Keep `origin` (this fork) and `upstream` (`mutonby/openshorts`) both
  configured; periodically rebase/merge from `upstream/main` rather than
  diverging silently.
- Before large refactors, check `docs/UPSTREAM_AUDIT.md` for the
  KEEP/DISABLE/REMOVE_LATER/AUDIT classification of the module you're
  touching.
