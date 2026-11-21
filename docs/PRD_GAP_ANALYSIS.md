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
   output verification) — **resolved**: fixtures for scenarios 1-3 were
   fetched independently per the user's follow-up instruction (CC BY / CC
   BY-SA, license verified from source metadata — see
   `tests/fixtures/README.md`); scenario 4 was already covered by the
   repo's own `demo-openshorts.mp4`. Running them through the pipeline is
   what surfaced the next real finding (model selection, below) — not a
   gap in this document anymore, see `docs/ACCEPTANCE_TESTS.md`.
2. **`schemas/`, `integrations/hyperframes/`, `agent/skills/autonomous-clipper/`
   — explicitly Phase 2+/3+ in the PRD's own layout diagram; not created
   yet in Phase 1, which is correct per the PRD, not a gap.
   `tests/smoke/` was scaffolded with a status README in Phase 0; still not
   populated with a passing automated test, now blocked on the
   model-selection finding below rather than on a fixture.
3. **Feature-gating implementation** — **resolved**: `feature_flags.py`
   plus 26+4 call-site gates across `app.py`/`main.py`/`layout_picker.py`/
   `screencast_layout.py`/`hook_grounding.py`, defense-in-depth (backend
   route refuses regardless of UI state), 47 new tests, full suite green.
   See `docs/ROADMAP.md` Phase 1 for the exact count and file list.
4. **Local-LLM model selection for the moment-scoring stage** —
   **resolved**: `qwen3:4b` timed out (>600s) on this CPU-only machine; a
   second model, `llava:7b` (7B, non-reasoning), succeeded on all three
   fixtures (scenarios 1-3), every time with valid JSON and a title that
   genuinely matched its transcript, every time at $0 cost. See
   `docs/ACCEPTANCE_TESTS.md` "Local-LLM model selection" and the
   per-scenario rows for full evidence.
