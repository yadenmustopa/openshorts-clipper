# License Audit — OpenShorts Clipper

Required by `docs/PRD_OpenShorts_Clipper_Claude_Work.md` §J. Module/dependency
disposition is in `docs/UPSTREAM_AUDIT.md`; this file covers license terms
and provenance specifically.

## OpenShorts core

- **License:** MIT (`LICENSE` at repo root).
- **Preserved as-is:** copyright notice, `LICENSE`, `NOTICE` untouched by
  this fork.
- Permits use, modification, self-hosting, and redistribution.

## `cloud/` exception

- **License:** OpenShorts Commercial License (`cloud/LICENSE`), declared in
  root `NOTICE`.
- **Permitted:** view/study/modify; self-host for personal/internal use;
  contribute changes back to the upstream repo.
- **Prohibited without a separate commercial agreement:** offering it as a
  hosted/managed/paid third-party service, reselling/sublicensing it, or
  removing/circumventing its billing/metering/entitlement checks when
  giving third parties access.
- **Import audit (PRD requirement: "Audit import dan dependensinya sebelum
  mencoba eksklusi"):** done. `app.py` imports exactly two `cloud/`
  submodules unconditionally at module load — `cloud.queue_mode` and
  `cloud.owner_cache` — both explicitly documented upstream as having "no
  dependencies beyond the standard library" and being inert without
  `BILLING_ENABLED`. Every other `cloud/` submodule (the ones with real
  paid-service coupling: `managed_keys`, `metering`, `stripe`-backed
  billing code, `emails`, `source_archive`, etc.) is imported only inside
  `if BILLING_ENABLED:` guards. **Conclusion:** the core pipeline runs with
  `BILLING_ENABLED` unset and has no functional dependency on `cloud/`, but
  is not fully import-isolated from it — two lightweight, dependency-free
  submodules load regardless. This project does not set `BILLING_ENABLED`
  and treats `cloud/` as inert, unused baggage, not a dependency to build
  against.

## HyperFrames (external, Phase 2)

- **License:** Apache-2.0.
- Permissive, includes an express patent grant.
- Per the PRD: used as a **pinned dependency** (version/tag-locked), not
  vendored or forked into this repository's core, "kecuali ada alasan
  teknis yang jelas" (unless there's a clear technical reason). If any
  HyperFrames code is ever vendored, its `LICENSE`/`NOTICE` must travel
  with it and must not be relicensed.

## Provenance note (upstream, not actionable by this fork)

`mutonby/openshorts`'s GitHub fork-network lists `kamilstanuch/Autocrop-vertical`
(no declared license on that repository) as the network root. The PRD
explicitly warns against assuming every inherited line is MIT just because
the current root license says so. This fork relies on `mutonby/openshorts`'s
own MIT grant over its *current* tree contents; a file-by-file history audit
of what originated in the unlicensed ancestor was **not performed** — this
is an upstream-inherited risk, recorded, not resolved, and not something
this project can fix by itself.

## Other dependencies

No GPL/AGPL or other copyleft dependency was found in `requirements.txt`,
`requirements-cpu.lock`, `requirements-billing.txt`, or
`dashboard/package.json` at a spot-check level. A full per-package SBOM/
license scan was **not** produced — flagged as a Phase 1+ follow-up if
formal compliance documentation is ever needed.

Model weights pulled at runtime (faster-whisper, YOLOv8n via `ultralytics`,
MediaPipe assets) were not individually re-audited for their own license/
usage terms in this phase — upstream already depends on and ships
instructions for these; using them here carries the same terms upstream
already operates under. Flagged as a Phase 1+ follow-up if commercial
redistribution of outputs (not just self-hosted personal use) is ever
considered.

## Things this fork must never do (hard rules, mirrored in `AGENTS.md`)

- Never relicense, strip, or alter `LICENSE`/`NOTICE` files from any
  component (OpenShorts MIT, `cloud/` Commercial License, HyperFrames
  Apache-2.0).
- Never offer `cloud/` functionality as a hosted service to third parties.
- Never commit demo videos, images, fonts, API tokens, browser cookies, or
  credentials to git without clear rights and need (PRD §J).
