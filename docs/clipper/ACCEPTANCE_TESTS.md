# Acceptance Tests — OpenShorts Clipper

Status: draft, Phase 0. Phase 0's own checklist is verifiable now; later
phases' criteria are stubs to be refined when those phases start.

## Phase 0 acceptance criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Fork `yadenmustopa/openshorts-clipper` exists, public, `isFork=true`, parent `mutonby/openshorts` | PASS | `gh repo view yadenmustopa/openshorts-clipper` |
| 2 | `origin` remote → fork, `upstream` remote → `mutonby/openshorts` | PASS | `git remote -v` in this repo |
| 3 | Branch `chore/phase-0-foundation` created and checked out | PASS | `git status` |
| 4 | `AGENTS.md` present at repo root | PASS | file exists |
| 5 | `CLAUDE.md` extended (not replaced) with fork-specific section | PASS | diff preserves all upstream content |
| 6 | `docs/clipper/{PRD,ARCHITECTURE,ROADMAP,ACCEPTANCE_TESTS,AUDIT_REPORT}.md` present | PASS | files exist |
| 7 | License audit recorded (MIT root, Commercial License `cloud/`, Apache-2.0 HyperFrames, upstream provenance note) | PASS | see `AUDIT_REPORT.md` §License audit |
| 8 | Dependency map recorded (keep / disable-candidate / commercial-excluded) | PASS | see `AUDIT_REPORT.md` §Dependency map |
| 9 | Baseline tests executed where the environment supports them; results reported as PASS/FAIL/NOT_RUN, no unverified claims | see `AUDIT_REPORT.md` §Test results | |
| 10 | No module deleted, no feature removed, no destructive git operation performed | PASS | diff is additive (new files + two doc edits) |
| 11 | No other repository on this machine touched | PASS | all work confined to `clipper/` (its own git repo, independent of the sibling `yadenmustopa` wrapper repo) |
| 12 | Commit(s) structured, pushed to fork, PR opened against the fork's `main` | pending | see final Phase 0 report |

## Phase 1 acceptance criteria (stub, to be refined)

- A real video processed end-to-end (ingest → transcript → scored moments →
  cut → reframed clip) with `LLM_BASE_URL` set to a local model and no
  `GEMINI_API_KEY`/`X-Gemini-Key` present, producing at least one valid
  output clip.
- Out-of-scope modules (`translate.py`, `social_platforms.py`,
  `saasshorts.py`, auto-publish paths) are unreachable in the default
  config without being deleted from the tree.

## Phase 2 acceptance criteria (stub)

- A clip produced by the OpenShorts core pipeline is successfully handed
  off to HyperFrames and rendered with at least one motion-graphics
  treatment applied.

## Phase 3 acceptance criteria (stub)

- An agent (Claude Code or Codex) can submit a job, poll its status, and
  retrieve the finished clip using only the documented API/CLI/MCP surface
  — no direct Python import of pipeline internals.

## Phase 4 acceptance criteria (stub, optional)

- The vision-dependent stages produce a usable result via Gemini Web/
  Computer Use with no Gemini API key configured, and degrade the same way
  the Gemini-API path degrades today when the provider is unavailable.
