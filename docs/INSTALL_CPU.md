# Reproducible CPU install

For a machine with no NVIDIA GPU (confirmed the right path on this
machine — see `docs/ENVIRONMENT.md`). This is what `requirements-cpu.lock`
is for, and what the Dockerfile's `GPU=0` build does; the steps below are
the same thing outside Docker, for local development.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip

# torch/torchvision from the PyTorch CPU index first — from PyPI directly
# they bundle ~16 CUDA/triton wheels (several GB) even on a CPU-only box.
pip install --index-url https://download.pytorch.org/whl/cpu \
  torch==2.11.0 torchvision==0.26.0

# Everything else, pinned, with --no-deps so nothing unpinned sneaks in.
pip install --no-deps -r requirements-cpu.lock

pip check   # must say "No broken requirements found."
```

Add `-r requirements-billing.txt`'s packages too (already included in
`requirements-cpu.lock`) only if you intend to run with `BILLING_ENABLED`
— this fork doesn't.

## Why this file exists

The `requirements-cpu.lock` shipped at the start of Phase 1 pinned exact
versions (e.g. `soupsieve==4.0.1`) that are no longer resolvable against
live PyPI as of 2026-11-21 — `pip install --no-deps -r requirements-cpu.lock`
failed outright with *"Could not find a version that satisfies the
requirement."* This is normal lock-file drift (PyPI serves what's
currently published, a lock file freezes a point in time), not a defect
introduced by this fork.

**Fixed by regenerating the lock** using the exact procedure its own
header already documents:

```bash
pip install -r requirements.txt -r requirements-billing.txt   # plain resolution
pip check                                                      # confirm no conflicts
pip freeze --all --exclude pip --exclude torch --exclude torchvision > requirements-cpu.lock
```

Verified, not just regenerated and assumed good:

1. `pip check` after the plain-resolution install: *"No broken
   requirements found."*
2. The new lock re-installed cleanly with `--no-deps` into a fresh venv
   (the exact command the Dockerfile uses).
3. `pip install --no-index --no-deps -r requirements.txt -r requirements-billing.txt`
   against that same venv — the Dockerfile's own post-lock sanity check —
   exited 0.
4. The full `pytest tests/ -v` suite (2578 passed, 56 skipped, 0 failed)
   and three real end-to-end pipeline jobs (see
   `docs/ACCEPTANCE_TESTS.md`) ran successfully against a venv built this
   way.

Three packages present in the prior lock are intentionally absent from
the regenerated one — explained in the lock file's own updated header,
not repeated here to avoid the two going out of sync:
`httptools`/`uvloop` (uvicorn's optional `[standard]` extras — not pulled
in by a plain, un-extras `uvicorn==0.46.0` resolution) and `onnx-asr`
(backs GPU-only Parakeet transcription; belongs in
`requirements-gpu.lock`, not here).

## When to regenerate again

Any time `pip install --no-deps -r requirements-cpu.lock` fails to
resolve a pin, or `requirements.txt`/`requirements-billing.txt` changes.
Same three commands as above. Keep the lock file's header comment intact
(it documents its own regeneration procedure) and add a dated note like
this file's, same as this fork's convention.
