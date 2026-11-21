# ADR 0001 — Fork, not rewrite; Python core / Node HyperFrames worker boundary

**Status:** Accepted. **Date:** 2026-11-21.

## Context

The PRD (`docs/PRD_OpenShorts_Clipper_Claude_Work.md`) directs building an
autonomous self-hosted video clipper on top of OpenShorts (clipping) and
HyperFrames (visual composition/rendering), orchestrated by an AI agent.
Two structural questions had to be settled before any code changes: (1)
fork vs. new repo, and (2) how HyperFrames relates to the Python pipeline.

## Decision 1 — Fork `mutonby/openshorts`, do not rewrite or start fresh

Forked as `yadenmustopa/openshorts-clipper` with `upstream` tracking
`mutonby/openshorts`. Phase 0 preserves the original layout completely;
nothing is moved or deleted in bulk. New project-specific material is
added incrementally (`AGENTS.md`, `docs/`, future `schemas/`,
`integrations/hyperframes/`, `agent/skills/autonomous-clipper/`,
`tests/smoke/`) alongside the untouched original tree, per the PRD's
explicit "transitional, not big-bang rewrite" instruction (§I).

**Why:** OpenShorts already implements ~90% of the needed pipeline
(ingest, ASR, scene detection, cut, reframe, subtitles, hook overlays, a
local-LLM moment-scoring path) under a license that permits this. Starting
fresh would re-derive working, tested code for no benefit, and would
violate the explicit instruction not to rebuild from scratch.

## Decision 2 — HyperFrames is a pinned dependency, not vendored code

HyperFrames is referenced at a pinned version/tag and invoked as a
separate Node.js 22+ worker process, installed via its own supported
procedure. It is not forked into this repository's core, and no
HyperFrames source is copied in, "kecuali ada alasan teknis yang jelas"
(PRD §F) — no such reason has arisen yet.

**Why:** Keeps the Apache-2.0 HyperFrames code path independently
upgradable, avoids relicensing/attribution risk from mixing it into the
MIT-licensed OpenShorts tree, and matches the PRD's module boundary:
Python owns media understanding and cut/crop, Node/HyperFrames owns visual
composition and final render (§C "Module boundaries").

## Decision 3 — The existing Remotion usage is not touched by this ADR

`dashboard/`'s `@remotion/*` usage and the standalone top-level
`remotion/` project predate this project's HyperFrames goal. Per the PRD
correction directive, **removing or replacing either requires a HyperFrames
proof-of-concept to exist first** — this ADR does not decide their fate,
and no file in either path is modified, moved, or deleted as a result of
this decision. The actual decision is deferred to a Phase 2 follow-up ADR,
written once a PoC exists to evaluate against.

## Consequences

- `git merge upstream/main` stays viable — the fork has not diverged
  structurally from upstream in Phase 0/1.
- HyperFrames version bumps are a dependency update, not a merge conflict
  inside vendored code.
- Two render paths (upstream's Remotion usage and the future HyperFrames
  worker) coexist until Phase 2 produces evidence to retire one — this is
  accepted as a deliberate, temporary redundancy, not an oversight.
