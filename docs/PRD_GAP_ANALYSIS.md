# PRD Gap Analysis

**Supersedes an earlier version of this file** that was written before the
actual `docs/PRD_OpenShorts_Clipper_Claude_Work.md` reached this agent (it
had been referenced twice but its content didn't arrive until the user's
third message in this thread; `find / -iname "*PRD_OpenShorts*"` had
turned up nothing until then — it appeared at
`/mnt/nvme/Downloads/PRD_OpenShorts_Clipper_Claude_Work.md` and was moved
into this repo at `docs/PRD_OpenShorts_Clipper_Claude_Work.md`). This
version compares against the **real document**, not a reconstruction.

## Where Phase 0/1 work was already aligned

Everything in `docs/PRD.md`'s original draft (OpenShorts core, Ollama for
text moment-scoring, HyperFrames as a Phase 2 separate worker, MCP/CLI/REST
orchestration for Codex/Claude Code, Gemini-via-Computer-Use as optional
Phase 4, no UGC/TTS/dubbing/billing/auto-publish) turned out to match the
real PRD's §B/§C/§H directly. No redesign was needed on those points.

## Gaps found and corrected

| Gap | Real PRD source | Correction applied |
|---|---|---|
| Doc file layout didn't match | §I: `docs/PRD.md`, `ARCHITECTURE.md`, `UPSTREAM_AUDIT.md`, `LICENSE_AUDIT.md`, `ROADMAP.md`, `ACCEPTANCE_TESTS.md`, `ADR/0001-*.md` at `docs/` top level | Moved everything out of `docs/clipper/` into `docs/`; split the combined audit doc into `UPSTREAM_AUDIT.md` + `LICENSE_AUDIT.md`; added `docs/ADR/0001-fork-and-worker-boundaries.md`. |
| Dependency classification scheme didn't match | §M.3: `KEEP`/`DISABLE`/`REMOVE_LATER`/`AUDIT` | Remapped from the earlier `KEEP`/`KEEP-GATED`/`DISABLE-CANDIDATE`/`COMMERCIAL-EXCLUDED` scheme in `docs/UPSTREAM_AUDIT.md`. |
| `cloud/` claimed "zero dependency" without checking the import graph | §J: "Audit import dan dependensinya sebelum mencoba eksklusi" | Actually traced `app.py`'s imports: `cloud.queue_mode` and `cloud.owner_cache` load unconditionally (both explicitly dependency-free/inert upstream); everything else is `BILLING_ENABLED`-gated. Corrected claim now in `docs/LICENSE_AUDIT.md`. |
| No formal data contract / job state machine / tool API documented | §E | Added to `docs/ARCHITECTURE.md` §4 (manifest JSON shape, `CREATED→...→COMPLETED` state machine, the 9-function tool API) as a design target — not yet implemented, correctly marked so. |
| HyperFrames integration spec was a vague "Phase 2, TBD" | §F: pinned dependency (not vendored), 3 named presets, specific CLI commands, caching rule, no-double-burn-subtitle rule | Added to `docs/ARCHITECTURE.md` §3.3 verbatim. |
| Agent skill spec (`autonomous-clipper`) didn't exist anywhere | §G | Added to `docs/ARCHITECTURE.md` §3.4 as a Phase 3 design target. |
| Gemini-via-Computer-Use constraints were under-specified | §H: explicit per-upload consent, provenance logging fields, never store cookies/tokens, no ToS bypass | Added to `docs/ARCHITECTURE.md` §3.5. |
| Feature-gating depth was underspecified ("disable via config") | Correction directive (restating PRD intent): gate the backend endpoint, not just hide a UI button | `AGENTS.md` rule 2 now states this explicitly; not yet implemented in code (Phase 1 pending work). |
| Acceptance tests were generic phase checkboxes | §L: 10 concrete numbered scenarios | `docs/ACCEPTANCE_TESTS.md` rewritten to the PRD's exact 10 scenarios with real PASS/FAIL/NOT_RUN/PARTIAL status per scenario. |
| "Target environment" said "Ubuntu" without verifying bare-metal vs. sandbox | Correction directive: verify explicitly, don't assume CPU-only from a GPU-detection miss | `docs/ENVIRONMENT.md` created with hardware/OS evidence; `docs/PRD.md` §4 corrected. |
| `demo-openshorts.mp4` assumed usable as a fixture without checking | PRD §L scenario #4 actually anticipates a silent-video case | Checked: it has audio but 0 detected speech — reclassified as the correct fixture for scenario #4 (silent video), not scenario #1 (single speaker). A different fixture is still needed for #1-3; tracked as an open item, not resolved by assumption. |

## Still open

1. **Fixture for PRD acceptance scenarios #1-3, #7, #8, #10** (single
   speaker, two speakers, screencast, render failure, restart/resume,
   output verification) — all need either a real speech-bearing local
   video or a decision to defer them. Not resolved yet; was asked about
   once and the question was dismissed without a choice being made, so it
   is asked again, more narrowly, alongside this report.
2. **`schemas/`, `integrations/hyperframes/`, `agent/skills/autonomous-clipper/`,
   `tests/smoke/`** — all explicitly Phase 1+/2+/3+ in the PRD's own
   layout diagram; not created yet in Phase 0/1, which is correct per the
   PRD, not a gap.
3. **Feature-gating implementation** (backend + UI, not just UI) for
   `translate.py`, `social_platforms.py`, `social_metrics.py`,
   `twitch_signals.py`, `saasshorts.py` — designed (see `AGENTS.md` rule 2,
   `docs/ROADMAP.md` Phase 1) but not yet coded.
