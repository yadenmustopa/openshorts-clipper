# Local smoke-test fixtures

Fixtures for `docs/PRD_OpenShorts_Clipper_Claude_Work.md` §L's acceptance
scenarios 1-4. Media is never committed (`tests/fixtures/cache/` is
gitignored); this file plus `fetch_fixtures.sh` are what's checked in, so
anyone can reproduce the same fixtures locally with:

```bash
bash tests/fixtures/fetch_fixtures.sh
```

Requires `yt-dlp`, `ffmpeg`, `curl` (all already project dependencies/
available in this environment). Re-running skips any fixture that already
exists in `cache/`.

## Provenance, per scenario

| Scenario | File | Source | License | Uploader/author | Clip taken |
|---|---|---|---|---|---|
| 1 — single speaker | `cache/scenario1_single_speaker.mp4` | [How to Improve Blender's UI — Andrew Price, Blender Conference 2024](https://www.youtube.com/watch?v=FJRO5wFTEc8) | CC BY (verified via `yt-dlp --dump-json`'s `license` field: *"Creative Commons Attribution license (reuse allowed)"*) | **Blender** (official Blender Foundation channel) | First 90s of a ~20:27 talk |
| 2 — two speakers | `cache/scenario2_two_speakers.mp4` | [Turn the Tables with Dan and Shoshana Jordan \|\| Winning Conversations Podcast](https://www.youtube.com/watch?v=-KbQj_vboOU) | CC BY (verified the same way; also the exact source upstream OpenShorts' own `README.md` names as its demo footage) | **Heritage of Faith CC** | First 90s of a ~26:54 podcast episode |
| 3 — screencast + narration | `cache/scenario3_screencast.mp4` | [File:Basic Introduction to HTML.webm — Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Basic_Introduction_to_HTML.webm) | CC BY-SA 3.0 ([license text](https://creativecommons.org/licenses/by-sa/3.0/)), stated on the file's own Commons description page | Renepick | First 90s of a 15:02 narrated screen recording ("Web Science MOOC") |
| 4 — silent video | `../../demo-openshorts.mp4` (repo root, already present) | Ships with upstream `mutonby/openshorts` as its own demo asset | Covered by the repository's existing terms (not a new fixture added by this project) | — | Used whole (41s); confirmed in Phase 1 testing to have an AAC audio track but 0 detected speech segments (faster-whisper) |

Licenses for scenarios 1 and 2 were confirmed directly from YouTube's own
metadata (`yt-dlp --dump-json <url> | grep license`), not assumed from a
channel's general reputation. Scenario 3's license is Wikimedia Commons'
own stated license on the file page — Commons requires every hosted file
to carry a free license, so this is authoritative by construction.

## Why 90 seconds, and why these specific clips

- Long enough to contain real, continuous speech for the local-LLM
  moment-scoring pipeline to have something to score, short enough that a
  CPU-only run (this machine has no NVIDIA GPU — see `docs/ENVIRONMENT.md`)
  finishes in a reasonable time for iterative testing.
- Re-encoded to H.264/AAC MP4 on download so every fixture matches what
  `main.py`'s pipeline actually expects as input, regardless of the
  source's native container/codec (VP8/Vorbis WebM for scenario 3,
  YouTube's own adaptive formats for 1-2).
- `yt-dlp --download-sections` was tried first to cut the clip during
  download (so only ~90s is ever transferred) but reliably segfaults this
  machine's static ffmpeg 5.1.1 build on the fragmented/m3u8 merge it
  performs internally. The script works around this by downloading the
  full source at a capped resolution (≤480p — small enough to not matter)
  and trimming with a plain, separate `ffmpeg -t 90` call, which does not
  hit that crash. Documented here so a future contributor doesn't waste
  time rediscovering the same crash.

## Rules for adding a new fixture here

1. Verify the license yourself — don't take a secondary source's word for
   it. For YouTube, `yt-dlp --dump-json <url>` and read the `license`
   field. For Wikimedia Commons, read the file's own description page.
2. Record the exact source URL, the license (with a link to its text),
   and the uploader/author in the table above.
3. Never commit the media itself — only this README and the fetch script.
4. Never fabricate a transcript or a result to make a test pass if a
   fixture turns out to be unsuitable (see how scenario 4 was actually
   discovered: a video assumed to have speech turned out not to, and that
   became the scenario-4 fixture instead of being forced into scenario 1).
