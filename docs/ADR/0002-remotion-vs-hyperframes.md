# ADR 0002 — Remotion vs. HyperFrames, after the Phase 2 PoC

**Status:** Accepted (recommendation only — no code removed by this ADR).
**Date:** 2026-11-22. Supersedes nothing; narrows
`docs/ADR/0001-fork-and-worker-boundaries.md` Decision 3, which explicitly
deferred this comparison until a HyperFrames PoC existed to evaluate
against. It now does — see `docs/architecture/hyperframes-integration.md`
for what was actually built and rendered.

## Context

This fork inherited two things that both touch "render a video from
structured data":

1. **Remotion**, already wired into `dashboard/`'s `@remotion/*` React
   components (in-browser preview/render) and a standalone top-level
   `remotion/` project.
2. **HyperFrames**, the PRD's chosen target for "enhanced visual
   composition and rendering" (Phase 2), now proven with a real adapter
   (`hyperframes_adapter.py`, `timeline_manifest.py`) and three rendered
   presets against real Phase 1 footage.

Per the correction directive that gated this ADR: *"Jangan memutuskan
penghapusan Remotion sebelum proof-of-concept HyperFrames berhasil."*
The PoC succeeded (`docs/ACCEPTANCE_TESTS.md`), so this is the comparison
that unblocks a decision — not yet an instruction to delete anything.

## Comparison

| Axis | Remotion (as used in `dashboard/`) | HyperFrames (Phase 2 PoC) |
|---|---|---|
| **What it is** | React components compose a video; Remotion's own renderer (`@remotion/media`, `@remotion/web-renderer`) runs in-browser for live preview and server-side for final render. | Plain HTML/CSS + GSAP timelines, seeked frame-by-frame by a pinned CLI (`npx hyperframes@0.9.80`) through a local headless Chrome. |
| **Where it already lives** | `dashboard/src` — deeply integrated into the existing clip editor/preview UI (`ClipEditor.jsx`, `RemotionPreview.jsx` per `docs/UPSTREAM_AUDIT.md`'s module map). Removing it means rebuilding that UI surface. | `integrations/hyperframes/` — a new, separate project. Zero existing UI depends on it yet. |
| **Feature fit for this project's actual need** (captions, hook overlays, preset-driven motion over an already-cut-and-reframed clip) | Capable in principle (it's a full React renderer) but the existing wiring is for *preview*, not for the specific "burn captions/hook/preset motion onto a finished 9:16 clip" job — would need new components built for that, same amount of new work as the HyperFrames adapter took. | Purpose-fits what was built: the PoC's three presets (`clean_podcast`, `bold_kinetic`, `educational_screen`) are exactly this job, already rendering real output. |
| **Rendering quality observed** | Not evaluated in Phase 2 — no comparable Remotion composition was built to render against the same footage, so this ADR makes no quality claim for Remotion. | Verified: 1080×1920 H.264/AAC, correct duration, no black frames, audio preserved within 0.1-0.2dB of source, captions correctly synced and positioned, word-level kinetic emphasis working (`docs/qa/phase2-hyperframes/`). |
| **Performance** | Unmeasured in this phase. | ~85-100s wall time per preset render (`draft` quality) for a 27.8s clip on this CPU-only machine (no NVIDIA GPU) — acceptable for this project's "a few clips per job" scale; not benchmarked at `delivery` quality or in bulk. |
| **Maintenance complexity** | Tied to React/npm's whole dependency tree already in `dashboard/` (and its own known issues — `npm audit`: 15 vulnerabilities, `docs/UPSTREAM_AUDIT.md`). Any change touches the same codebase as the rest of the dashboard. | A separate Node project with its own pinned CLI version (`hyperframes@0.9.80` in every script) — isolated from the dashboard's dependency tree entirely; upgrades are a version-bump decision made independently. |
| **Agent integration** | No programmatic/CLI contract for "render this JSON into that MP4" exists today — it's wired for a human using the dashboard. | Built for exactly this: `hyperframes_adapter.render_clip()` is a plain Python function an agent (Claude Code, Codex, the future Phase 3 orchestrator) calls with a manifest and a preset name — no UI involved, matches the PRD's "agent-agnostic" requirement directly. |
| **Compatibility with the existing editor** | Already compatible — it *is* the existing editor's preview tech. | Not integrated with `ClipEditor.jsx` at all yet; a HyperFrames-rendered clip is a finished MP4, not something the existing word-level editor can re-open and adjust the way it adjusts an OpenShorts clip today. |
| **License** | MIT-compatible (Remotion itself; check its own license for commercial redistribution terms not assessed here). | Apache-2.0, pinned dependency, not vendored (`docs/ADR/0001`). |

## Decision

**Keep both, for now — a gradual migration, not a full switch.**

Specifically:

1. **Do not remove `dashboard/`'s Remotion usage or the top-level
   `remotion/` project.** It is the live editor-preview path for every
   existing OpenShorts feature (`ClipEditor.jsx`, word-level trims,
   framing changes) that this PoC did not touch and does not replace.
2. **HyperFrames becomes the path for the specific job it was built and
   proven for:** turning a finished OpenShorts clip into a
   captioned/hook-overlaid/preset-styled final render, callable
   programmatically (CLI/adapter), for agent-driven workflows (Phase 3)
   and any future "apply a preset" feature — not for the interactive
   word-level editing Remotion/the dashboard already does well.
3. **Re-evaluate full migration only after**: (a) HyperFrames gains a
   batch/bulk render benchmark at `delivery` quality, (b) a decision is
   made about whether the dashboard's interactive editor should also move
   to HyperFrames (a materially bigger project than this PoC — it would
   mean rebuilding `ClipEditor.jsx`'s live-preview interactivity on
   HyperFrames' seek-based model), and (c) the `npm audit` findings in
   Remotion's dependency tree are judged against HyperFrames' own
   (unaudited in this phase) dependency tree.

## Consequences

- Two render paths exist in the codebase simultaneously, by design, not
  oversight — documented here so a future contributor doesn't "clean up"
  one assuming the other was a mistake.
- Phase 3 (agent orchestration) should target the HyperFrames adapter's
  function-call contract for anything that fits "render a finished,
  styled clip" — not attempt to drive the dashboard's Remotion preview
  programmatically, which isn't built for that.
- If a future phase decides to migrate the interactive editor to
  HyperFrames too, that is a new ADR, not an extension of this one — it's
  a materially different, larger decision than what this PoC answered.
