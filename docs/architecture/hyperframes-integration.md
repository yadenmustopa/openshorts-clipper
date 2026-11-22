# HyperFrames integration (Phase 2)

Status: hardened past proof-of-concept (Step A). The PoC proved the
architecture; Step A hardening (this pass) is what makes concurrent,
multi-job production use actually safe — the two are not the same claim,
and the PoC was explicitly **not** treated as automatic proof of the
latter. Built and verified with real renders against real Phase 1 footage
(not a toy/synthetic test). See `docs/ACCEPTANCE_TESTS.md` for the exact
evidence and `docs/ADR/0002-remotion-vs-hyperframes.md` for the Remotion
decision this unblocks.

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

## Workspace isolation (Step A.1/A.3, hardening)

The PoC rendered every clip into the single shared
`integrations/hyperframes/` template directory — fine for one render at a
time by hand, unsafe the moment two clips (or two jobs) render
concurrently, since `main.py`'s `ThreadPoolExecutor` (`CLIP_WORKERS`)
already does exactly that for a job's own clips.

`render_clip()` now takes a required `job_output_dir` argument and calls
`_prepare_workspace(job_output_dir, clip_id, preset_name)`, which builds a
fresh `<job_output_dir>/hyperframes_render/<clip_id>/<preset>/` directory
per call — wiping (`shutil.rmtree`) any stale content before copying the
template files and vendored assets in, so a previous failed/aborted
render's leftovers are never silently merged into a new one. Every path
the adapter touches (template files, the clip's own video, the generated
`index.html`) is resolved through `resolve_within(base_dir, *parts)`,
which uses `os.path.realpath` to reject both `..`-traversal and a
symlink that resolves outside the workspace (`WorkspaceEscapeError`).

Verified in `tests/test_hyperframes_adapter.py`: different `clip_id` →
different workspace, different `preset` → different workspace, different
`job_output_dir` with the same `clip_id` → different workspace, a stale
workspace's content is wiped not merged, and a real `os.symlink` pointed
outside `base_dir` is rejected by `resolve_within` (a symlink pointing
*inside* `base_dir` is correctly allowed).

## Hardened output validation (Step A.4)

The PoC's validation was "process exit code 0 and output file size > 0" —
real risk: ffmpeg/Chrome can exit 0 and still produce a corrupt, silent,
or wrong-resolution file. `validate_rendered_output()` now runs real
`ffprobe -show_format -show_streams` (`probe_output()`: codec, resolution,
duration, audio/video stream presence) plus an `ffmpeg blackdetect` sweep
(`detect_black_frames()`) and returns a `ValidationReport` with every
mismatch spelled out, not just a boolean. `render_clip(..., validate=True)`
(the default) calls this automatically after a successful process exit
and attaches the report to `RenderResult.validation`.

## Structural repeatability (Step A.5, hardening)

Not re-run in the PoC (flagged there as a real gap). Hardening pass: the
identical `clip_video_abspath` + preset was rendered twice back-to-back
into two separate job-output directories; both runs passed
`validate_rendered_output()` and, stronger than what was required,
produced **byte-for-byte identical** output (same MD5 checksum, same file
size) — the per-job/per-clip workspace isolation did not introduce any
cross-run nondeterminism.

## Real-footage preset tests (Step A.6, hardening)

The PoC exercised only the single-speaker fixture against all three
presets. Hardening pass adds genuinely different content types per
preset, both through the hardened `render_clip()` (isolated workspace +
full validation):

- `clean_podcast` against the real two-speaker fixture
  (`scenario2_two_speakers_clip_1.mp4`) — passed `ffprobe`/black-frame
  validation with neither speaker dropped from frame.
- `educational_screen` against the real screencast fixture
  (`scenario3_screencast_clip_1.mp4`) — passed the same validation against
  screen-content footage, not talking-head footage.

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
render_clip(m, 0, 'clean_podcast', '<job>_clip_1.mp4', 'out.mp4',
            job_output_dir='<job_output_dir>', quality='looks')
"
```

## What Step A hardening still does not cover (open gaps — explicit, not assumed closed)

The user's directive was explicit: do not treat the PoC as automatic
proof the worker is safe for concurrent production jobs. Workspace
isolation, hardened validation, and structural repeatability are now
verified (above); the following are genuinely still open:

- **No live concurrent-job test against the full `app.py`/job-queue
  stack.** `tests/test_hyperframes_adapter.py::TestPrepareWorkspace`
  proves two workspaces never collide at the filesystem level (unit
  test, synthetic job dirs); it does not exercise two real `main.py` job
  processes rendering through HyperFrames at the same moment on this
  machine. That end-to-end concurrency proof is deferred to Phase 3's
  MVP acceptance test (PRD §L item explicitly calling for "two
  concurrent jobs").
- Multi-clip batch rendering (the adapter renders one clip+preset per
  call; nothing prevents looping it, nothing has exercised looping it
  under load).
- `render --docker --strict` (the reproducible-container render path) —
  only the plain local `render` was exercised.
- The `educational_screen` pointer/highlight feature (see above) —
  unimplemented, not a hardening regression.
- The residual outbound-connection investigation (`ultralytics/utils/
  events.py`'s analytics pinger) is tracked in `docs/UPSTREAM_AUDIT.md`
  §6, not here — it is a dependency-telemetry finding, not a HyperFrames
  integration gap, but it affects the same "no internet required" claim
  this document makes about the render path itself (the render path's
  own zero-network behavior, headless Chrome + node only talking over
  127.0.0.1 CDP, is independently verified and unaffected by that
  finding).
