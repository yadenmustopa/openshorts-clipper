# HyperFrames integration (Phase 2)

Status: proof-of-concept, built and verified with real renders against
real Phase 1 footage (not a toy/synthetic test). See
`docs/ACCEPTANCE_TESTS.md` for the exact evidence and
`docs/ADR/0002-remotion-vs-hyperframes.md` for the Remotion decision this
unblocks.

## Architecture

```
OpenShorts job (*_metadata.json + clip_N.mp4)
        │
        ▼
timeline_manifest.py          — TimelineManifest schema + validator
        │  (load_manifest_from_job)
        ▼
hyperframes_adapter.py        — the adapter
        │  1. words_for_clip(): source-relative → clip-relative seconds
        │  2. group_words(): caption groups per preset's energy
        │  3. build_index_html(): generates integrations/hyperframes/index.html
        │  4. copies the clip's own video into assets/
        ▼
integrations/hyperframes/     — a HyperFrames project, pinned to
                                 hyperframes@0.9.80 (package.json's scripts)
        │  npx hyperframes@0.9.80 check   (lint/runtime/layout gate)
        │  npx hyperframes@0.9.80 render  (local headless-Chrome render)
        ▼
finished MP4 (1080×1920, H.264/AAC, burned captions + hook overlay)
```

`main.py`'s own clip selection, transcription, cutting, and reframing are
untouched and reused as-is — the adapter only reads what already exists
(per the PRD: "Jangan membuat ulang clip selection atau Whisper; gunakan
hasil existing"). HyperFrames' job is enhancement (captions, hook
overlay, preset-specific motion) on top of a clip OpenShorts already cut
and reframed to 9:16 — not reframing.

## Why a pinned dependency, not vendored code

`integrations/hyperframes/package.json`'s own scripts pin
`npx --yes hyperframes@0.9.80` (not `npx hyperframes`, which would
resolve to whatever is newest at run time) for every command
(`dev`/`check`/`render`/`publish`), and `hyperframes_adapter.py` passes
the same exact version string to its own `subprocess.run` calls. No
HyperFrames source is copied into this repository — see
`docs/ADR/0001-fork-and-worker-boundaries.md` Decision 2 for why
(Apache-2.0 stays independently upgradable, no relicensing risk).

## Local-first, no HeyGen Cloud, no paid API

- Render path used: `npx hyperframes render` (local headless Chrome) —
  never `cloud render`/`lambda render`/`cloudrun render`, which are
  HyperFrames' optional hosted alternatives this project does not use.
- GSAP (the animation runtime HyperFrames compositions use) is **vendored
  locally** at `integrations/hyperframes/assets/vendor/gsap.min.js` — the
  scaffold's default `index.html` loads it from a CDN
  (`cdn.jsdelivr.net`), which the adapter's generated `index.html` does
  not do, and `tests/test_hyperframes_adapter.py::TestBuildIndexHtml::
  test_gsap_is_vendored_locally_not_a_cdn` asserts no `http(s)://` URL
  ever appears in a generated composition.
- One-time setup downloads (not per-render): `npx`'s own package-cache
  fetch of the `hyperframes` npm package, and
  `npx hyperframes browser ensure`'s one-time headless-Chrome download.
  Both are cached afterward, same pattern as this project's own
  Whisper/YOLO model-weight downloads (download once, run offline after).
- **Cache directory gotcha found and fixed:** HyperFrames refuses to
  install/run its browser engine from a group- or other-writable cache
  directory (a real guard, not a bug) — this machine's default
  `~/.cache` resolves to a shared, group-writable location
  (`/mnt/nvme/cache`), so `hyperframes_adapter.py`'s subprocess calls set
  `HYPERFRAMES_CACHE_DIR` to a private `~/.hyperframes-cache` instead of
  disabling the guard.
- Every rendered asset path is relative (`assets/<file>.mp4`, no leading
  `/`) and verified by `test_video_asset_path_has_no_leading_slash`.

## Three presets

| Preset | Caption grouping | Position | Word treatment | Hook style |
|---|---|---|---|---|
| `clean_podcast` | 3-5 words (conversational, per `references/captions.md`) | 640px from bottom | whole group fades as one | simple fade |
| `bold_kinetic` | 2-3 words (high energy) | 700px from bottom | **each word pops in individually** (`back.out(1.4)` scale+opacity, accent color) as it's spoken — verified visually, see `docs/qa/phase2-hyperframes/presets-comparison-t1s.png` | kinetic entrance (blur+scale) |
| `educational_screen` | 4-6 words (calm) | 600px from bottom, smaller font (54px vs 64-76px) | whole group fades | simple fade |

All three stay inside the portrait title-safe guidance from
`references/captions.md` (~600-700px from the bottom), never at exactly
0s (captions open 0.1-0.15s into their window, per the same reference),
and every caption group gets a hard kill (`opacity→0` then
`visibility:hidden`) so a stale group can't linger — the exact pattern
`references/captions.md` documents.

`educational_screen`'s PRD-specified "highlight dan pointer sederhana"
(simple highlight/pointer over screen content) is **not implemented** in
this PoC — it would need knowing *where* on the screencast to point,
which is beyond what OpenShorts' current metadata provides. Recorded as a
known simplification, not a silent gap.

## Rendered proof (not claimed, actually run)

Against `tests/fixtures/cache/scenario1_single_speaker.mp4`'s real Phase 1
output (`scenario1_single_speaker_clip_1.mp4`, 48.22s-75.98s of the
source, the clean pre-subtitle-burn clip — using the subtitled variant
would have double-burned captions, which the PRD explicitly forbids):

| Preset | Output | Resolution | Codec | Duration | Black frames | Audio |
|---|---|---|---|---|---|---|
| `clean_podcast` | `clean_podcast.mp4` | 1080×1920 | H.264/AAC, 30fps | 27.776s | none (`blackdetect`) | mean −18.5dB, max −1.8dB (matches source's −18.4/−1.6dB) |
| `bold_kinetic` | `bold_kinetic.mp4` | 1080×1920 | H.264/AAC, 30fps | 27.776s | none | same |
| `educational_screen` | `educational_screen.mp4` | 1080×1920 | H.264/AAC, 30fps | 27.776s | none | same |

Screenshots: `docs/qa/phase2-hyperframes/presets-comparison-t1s.png`
(all three side by side at t=1s, showing the hook overlay and the three
distinct caption treatments — `bold_kinetic`'s word-by-word pop clearly
visible, mid-word, one word in accent color and two still dim) and
`docs/qa/phase2-hyperframes/educational_screen-contact-sheet.jpg` (7
frames across the full clip, via `npx hyperframes snapshot`).

Rendered MP4s themselves are not committed (same policy as
`tests/fixtures/`: large media stays out of git) — reproduce with:

```bash
python3 -c "
from hyperframes_adapter import load_manifest_from_job, render_clip
m = load_manifest_from_job('<job>_metadata.json', '<source>.mp4', '<job_id>')
render_clip(m, 0, 'clean_podcast', '<job>_clip_1.mp4', 'out.mp4', quality='looks')
"
```

## What this PoC does not cover

- Multi-clip batch rendering (the adapter renders one clip+preset per
  call; nothing prevents looping it, nothing has exercised looping it).
- `render --docker --strict` (the reproducible-container render path) —
  only the plain local `render` was exercised.
- Byte-for-byte render repeatability was not tested (video encoding has
  normal minor nondeterminism); structural repeatability (same
  resolution/codec/duration/no-black-frames on a repeat run) was not
  re-run a second time in this phase — a real gap, not asserted as done.
- The `educational_screen` pointer/highlight feature (see above).
