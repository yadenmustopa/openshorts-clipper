#!/usr/bin/env bash
# Reproducibly fetch the local smoke-test fixtures documented in
# tests/fixtures/README.md. Downloads a short section of each source
# (never the whole thing) into tests/fixtures/cache/, which is gitignored —
# large media never belongs in git, only this script and the README do.
#
# Requires: yt-dlp (already a project dependency), ffmpeg, curl.
# Safe to re-run: skips a fixture whose output file already exists.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
mkdir -p cache

say() { printf '==> %s\n' "$*"; }

# --- Scenario 1: single speaker (monologue) --------------------------------
# "How to Improve Blender's UI - Andrew Price — Blender Conference 2024"
# https://www.youtube.com/watch?v=FJRO5wFTEc8
# Uploader: Blender (official channel) · License, per YouTube's own metadata
# (`yt-dlp --dump-json`, field "license"): "Creative Commons Attribution
# license (reuse allowed)" == CC BY. Full video ~20:27; we take the first
# 90s only (a single continuous speaker segment near the start).
OUT1=cache/scenario1_single_speaker.mp4
RAW1=cache/_raw1.mp4
if [ ! -f "$OUT1" ]; then
  say "Fetching scenario 1 fixture (single speaker, CC BY, Blender channel)"
  # yt-dlp's own --download-sections segfaults this host's static ffmpeg
  # 5.1.1 build when cutting a fragmented/m3u8 download; download the full
  # video (small at 480p) and trim with our own ffmpeg call instead, which
  # does not hit that crash.
  yt-dlp -f "bv*[height<=480]+ba/b[height<=480]" --merge-output-format mp4 \
    -o "$RAW1" "https://www.youtube.com/watch?v=FJRO5wFTEc8"
  ffmpeg -y -i "$RAW1" -t 90 -c:v libx264 -c:a aac "$OUT1"
  rm -f "$RAW1"
else
  say "Scenario 1 fixture already present: $OUT1"
fi

# --- Scenario 2: two speakers (conversation) --------------------------------
# "Turn the Tables with Dan and Shoshana Jordan || Winning Conversations
# Podcast" — https://www.youtube.com/watch?v=-KbQj_vboOU
# Uploader/channel: "Heritage of Faith CC". License, per YouTube's own
# metadata: "Creative Commons Attribution license (reuse allowed)" == CC BY.
# This is the same source upstream OpenShorts' own README names as its demo
# ("Real OpenShorts output ... licensed CC BY"). Full video ~26:54; first 90s.
OUT2=cache/scenario2_two_speakers.mp4
RAW2=cache/_raw2.mp4
if [ ! -f "$OUT2" ]; then
  say "Fetching scenario 2 fixture (two speakers, CC BY, Heritage of Faith CC)"
  yt-dlp -f "bv*[height<=480]+ba/b[height<=480]" --merge-output-format mp4 \
    -o "$RAW2" "https://www.youtube.com/watch?v=-KbQj_vboOU"
  ffmpeg -y -i "$RAW2" -t 90 -c:v libx264 -c:a aac "$OUT2"
  rm -f "$RAW2"
else
  say "Scenario 2 fixture already present: $OUT2"
fi

# --- Scenario 3: screencast with narration ----------------------------------
# "Basic Introduction to HTML.webm" — Wikimedia Commons:
# https://commons.wikimedia.org/wiki/File:Basic_Introduction_to_HTML.webm
# Author: Renepick. License: CC BY-SA 3.0
# (https://creativecommons.org/licenses/by-sa/3.0/). Full file is a 15m02s
# narrated screen recording ("Web Science MOOC"); we keep only the first 90s.
# Downloaded in full first (Wikimedia's direct file URL doesn't support a
# byte-range that stays a valid webm), then trimmed and the full copy removed.
OUT3=cache/scenario3_screencast.mp4
RAW3=cache/_raw_basic_introduction_to_html.webm
if [ ! -f "$OUT3" ]; then
  say "Fetching scenario 3 fixture (screencast, CC BY-SA 3.0, Wikimedia Commons)"
  curl -sL -o "$RAW3" \
    "https://upload.wikimedia.org/wikipedia/commons/5/58/Basic_Introduction_to_HTML.webm"
  ffmpeg -y -i "$RAW3" -t 90 -c:v libx264 -c:a aac "$OUT3"
  rm -f "$RAW3"
else
  say "Scenario 3 fixture already present: $OUT3"
fi

# --- Scenario 4: silent video ------------------------------------------------
# Already shipped in this repo at the project root (demo-openshorts.mp4,
# upstream's own demo asset) — confirmed in Phase 1 testing to have an AAC
# audio track but 0 detected speech segments (faster-whisper), which is
# exactly the PRD's scenario 4 ("video tanpa ucapan"). Nothing to fetch.
say "Scenario 4 fixture: use ../../demo-openshorts.mp4 (already in the repo, no download needed)"

say "Done. Fixtures in ./cache/ (gitignored, never commit these)."
