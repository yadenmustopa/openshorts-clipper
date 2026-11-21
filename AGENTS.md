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

See `docs/clipper/PRD.md`, `docs/clipper/ARCHITECTURE.md` and
`docs/clipper/ROADMAP.md` for the full product and technical spec. Read all
three before making architectural changes.

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
   dubbing, TTS, or auto-publishing to social platforms. Existing modules
   that implement these (`translate.py`, `social_platforms.py`,
   `social_metrics.py`, `twitch_signals.py`, `saasshorts.py`, parts of
   `free_tools.py`) are feature-flagged or left dormant, not deleted, until a
   dependency audit explicitly approves removal.
3. **Do not delete modules speculatively.** No bulk deletion of upstream
   modules before the dependency audit for that module is complete and
   recorded in `docs/clipper/AUDIT_REPORT.md`. Prefer disabling via
   config/feature flags over deleting code — it keeps the diff reviewable
   against upstream and keeps `git merge upstream/main` viable.
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
8. **Testing honesty.** Report test results as `PASS`, `FAIL`, or `NOT_RUN`.
   Never claim a test passed without having actually executed it in the
   current environment. If the environment lacks GPU/Docker/a dependency
   needed for a test, say so and mark it `NOT_RUN` with the reason.
9. **Document architectural decisions** in `docs/clipper/` as they're made —
   do not let decisions live only in commit messages or chat history.

## Workflow

- Branch naming: `feat/<slug>`, `fix/<slug>`, `chore/<slug>`, `docs/<slug>`.
- Keep `origin` (this fork) and `upstream` (`mutonby/openshorts`) both
  configured; periodically rebase/merge from `upstream/main` rather than
  diverging silently.
- Before large refactors, check `docs/clipper/AUDIT_REPORT.md` for the
  keep/disable/remove classification of the module you're touching.
