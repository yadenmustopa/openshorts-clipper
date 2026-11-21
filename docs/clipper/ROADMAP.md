# Roadmap — OpenShorts Clipper

Status: draft, Phase 0. Phase boundaries may shift once the original PRD
document is reconciled (see `PRD.md` status note).

## Phase 0 — Foundation (this work)

- [x] Audit `mutonby/openshorts` and `heygen-com/hyperframes` at their
      current commits.
- [x] Fork OpenShorts as `yadenmustopa/openshorts-clipper`.
- [x] Configure `origin` (fork) / `upstream` (`mutonby/openshorts`) remotes.
- [x] Branch `chore/phase-0-foundation`.
- [x] Structure/dependency audit; license audit.
- [x] `AGENTS.md`, extended `CLAUDE.md`.
- [x] `PRD.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `ACCEPTANCE_TESTS.md`,
      `AUDIT_REPORT.md`.
- [ ] Baseline tests run in this environment, honestly reported.
- [ ] Commit, push, open Phase 0 PR.
- **Explicitly not done in Phase 0:** no code deleted, no feature disabled,
  no HyperFrames integration started, no agent-orchestration layer started.

## Phase 1 — Local-first hardening (next, not started)

- Reconcile this draft PRD against the user's original
  `PRD_OpenShorts_Clipper_Claude_Work.md`.
- Validate the full text-only pipeline (ingest → transcribe → score →
  cut) runs end-to-end with `LLM_BASE_URL` pointed at a local model and no
  Gemini key present, on real footage, on this machine.
- Decide and implement the "disable, don't delete" mechanism (config flags
  / startup checks) for out-of-scope modules (`translate.py`,
  `social_platforms.py`, `saasshorts.py`, auto-publish paths).
- Document the dependency-install path that avoids the heavy/paid stack
  where possible (CPU-only lock file already exists upstream:
  `requirements-cpu.lock`).

## Phase 2 — HyperFrames rendering integration

- Decide the OpenShorts → HyperFrames handoff contract (see
  `ARCHITECTURE.md` §2.5).
- Decide the fate of the existing `dashboard/` Remotion usage and the
  standalone `remotion/` project relative to HyperFrames (see `PRD.md` open
  question 3).
- Implement the bridge; add acceptance tests (see `ACCEPTANCE_TESTS.md`).

## Phase 3 — Agent orchestration

- Extend `mcp_server.py` / `cli/openshorts_cli.py` (not a parallel API) so
  an agent can: submit a job, poll status, fetch results, adjust pipeline
  parameters.
- Document the exact tool/endpoint contract the agent uses.

## Phase 4 — Optional visual-analysis provider (Gemini Web via Computer Use)

- Only after Phase 1–3 are stable and only if still desired at that point.
- Must implement the same provider contract `gemini_worker.py` exposes
  today for vision stages, with the same graceful-degradation behavior when
  unavailable.

## Phase 5 — Polish and packaging

- Installation docs for a from-scratch self-hosted setup (no cloud
  account required).
- End-to-end acceptance run on representative footage.
