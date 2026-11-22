"""OpenShorts -> HyperFrames adapter (Phase 2 PoC).

Converts one clip from an OpenShorts job's own ``*_metadata.json`` into a
:class:`timeline_manifest.TimelineManifest`, then into a HyperFrames
project (a generated ``index.html`` inside ``integrations/hyperframes/``)
that the pinned HyperFrames CLI renders locally.

Does **not** re-run clip selection or transcription — this module only
reads what ``main.py`` already produced (per the PRD: "Jangan membuat
ulang clip selection atau Whisper; gunakan hasil existing"). The clip's
own video file (already cut and reframed to 9:16 by OpenShorts) is used
as-is; HyperFrames' job here is enhancement (captions, hook overlay,
preset-specific motion), not reframing.

Three presets (``PRESETS`` below): ``clean_podcast``, ``bold_kinetic``,
``educational_screen`` — see ``docs/architecture/hyperframes-integration.md``
for what each one is for.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import List, Literal, Optional

from timeline_manifest import Clip, Overlay, SourceInfo, TimelineManifest, Word

HYPERFRAMES_VERSION = "0.9.80"
PROJECT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "integrations", "hyperframes")
CANVAS_W, CANVAS_H = 1080, 1920

PresetName = Literal["clean_podcast", "bold_kinetic", "educational_screen"]

# Caption grouping per captions.md's energy guidance: group size and the
# vertical caption-band position (px from the bottom, inside the ~600-700px
# portrait title-safe guidance), per preset.
PRESETS: dict = {
    "clean_podcast": {
        "min_words": 3, "max_words": 5,
        "bottom_px": 640,
        "font_size": 64,
        "ink": "#ffffff",
        "accent": "#ffffff",
        "word_pop": False,
        "hook_style": "simple",
    },
    "bold_kinetic": {
        "min_words": 2, "max_words": 3,
        "bottom_px": 700,
        "font_size": 76,
        "ink": "#ffffff",
        "accent": "#ffd400",
        "word_pop": True,
        "hook_style": "kinetic",
    },
    "educational_screen": {
        "min_words": 4, "max_words": 6,
        "bottom_px": 600,
        "font_size": 54,
        "ink": "#f5f5f5",
        "accent": "#60a5fa",
        "word_pop": False,
        "hook_style": "simple",
    },
}


def load_manifest_from_job(metadata_path: str, source_path: str, job_id: str) -> TimelineManifest:
    """Build a :class:`TimelineManifest` from an OpenShorts job's own
    ``*_metadata.json`` (the exact file ``main.py`` writes — see
    ``main.py``'s ``write_json_atomic(metadata_file, clips_data, ...)``).
    Every clip's rendered video file is expected to sit alongside
    ``metadata_path`` as ``<job_basename>_clip_<n>.mp4`` or the already
    captioned/subtitled variant main.py produced — callers pass the exact
    filename they want via ``video_filename`` on each returned
    :class:`Clip` if main.py's own naming convention doesn't match;
    this function uses the plain ``_clip_N.mp4`` convention.
    """
    with open(metadata_path) as f:
        data = json.load(f)

    transcript = data.get("transcript") or {}
    duration_ms = int(round((transcript.get("segments") or [{}])[-1].get("end", 0) * 1000)) if transcript.get("segments") else 0
    source = SourceInfo(path=os.path.basename(source_path), duration_ms=max(duration_ms, 1))

    clips: List[Clip] = []
    base = os.path.splitext(os.path.basename(metadata_path))[0].replace("_metadata", "")
    for i, short in enumerate(data.get("shorts", [])):
        start_ms = int(round(short["start"] * 1000))
        end_ms = int(round(short["end"] * 1000))
        words = [
            Word(text=w["word"].strip(), start_ms=int(round(w["start"] * 1000)), end_ms=int(round(w["end"] * 1000)))
            for seg in transcript.get("segments", [])
            for w in seg.get("words", [])
            if start_ms <= int(round(w["start"] * 1000)) < end_ms
        ]
        layout_ranges = short.get("layout_ranges") or [{"layout": "general"}]
        mode = layout_ranges[0].get("layout", "general")
        overlays = []
        hook = short.get("viral_hook_text")
        if hook:
            overlays.append(Overlay(type="hook", text=hook, at_ms=0))
        clips.append(Clip(
            clip_id=f"{base}_clip_{i + 1}",
            video_path=f"{base}_clip_{i + 1}.mp4",
            source_in_ms=start_ms,
            source_out_ms=end_ms,
            score=float(short.get("predicted_score", 0)),
            reason=short.get("why", ""),
            layout={"mode": mode if mode in ("track", "general", "split", "screencast") else "general"},
            words=words,
            overlays=overlays,
        ))

    return TimelineManifest(job_id=job_id, source=source, clips=clips)


def words_for_clip(clip: Clip) -> List[dict]:
    """``clip.words`` (source-relative) converted to clip-relative
    seconds — the explicit transform ``docs/ARCHITECTURE.md`` §4.1
    assigns to the render worker, not the manifest."""
    out = []
    for w in clip.words:
        start_s = (w.start_ms - clip.source_in_ms) / 1000.0
        end_s = (w.end_ms - clip.source_in_ms) / 1000.0
        if end_s <= 0:
            continue
        out.append({"text": w.text, "start": max(start_s, 0.0), "end": min(end_s, clip.duration_ms / 1000.0)})
    return out


_WORD_RE = re.compile(r"[A-Za-z0-9'’-]+")


def group_words(words: List[dict], min_words: int, max_words: int) -> List[List[dict]]:
    """Caption groups per ``references/captions.md``: break at a pause of
    150ms+ or the word-count ceiling, never fewer than ``min_words`` words
    unless the clip runs out."""
    groups: List[List[dict]] = []
    current: List[dict] = []
    for i, w in enumerate(words):
        if not _WORD_RE.search(w["text"]):
            continue
        current.append(w)
        is_last = i == len(words) - 1
        gap = (words[i + 1]["start"] - w["end"]) if not is_last else 0.0
        if len(current) >= max_words or (len(current) >= min_words and gap >= 0.15) or is_last:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return groups


def _esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def _caption_group_html(group: List[dict], idx: int, preset: dict) -> tuple[str, str]:
    """Returns (html, js-tween-lines) for one caption group."""
    gid = f"cap{idx}"
    start, end = group[0]["start"], group[-1]["end"]
    # Never land a caption at exactly 0s (reads as pre-existing — captions.md).
    open_at = max(start - 0.15, 0.1 if idx == 0 else 0.0)
    kill_at = end + 0.05

    if preset["word_pop"]:
        spans = "".join(
            f'<span class="w" id="{gid}-w{j}">{_esc(w["text"])}</span> ' for j, w in enumerate(group)
        )
        html = f'<div id="{gid}" class="caption-group" style="opacity:0">{spans}</div>'
        js = [f'tl.set("#{gid}", {{ opacity: 1 }}, {open_at:.3f});']
        for j, w in enumerate(group):
            js.append(
                f'tl.fromTo("#{gid}-w{j}", {{ opacity: 0.35, scale: 0.85 }}, '
                f'{{ opacity: 1, scale: 1, duration: 0.13, ease: "back.out(1.4)" }}, {w["start"]:.3f});'
            )
    else:
        text = _esc(" ".join(w["text"] for w in group))
        html = f'<div id="{gid}" class="caption-group" style="opacity:0">{text}</div>'
        js = [
            f'tl.fromTo("#{gid}", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.12, ease: "power2.out" }}, {open_at:.3f});'
        ]

    js.append(f'tl.to("#{gid}", {{ opacity: 0, duration: 0.12, ease: "power2.in" }}, {max(kill_at - 0.12, open_at):.3f});')
    js.append(f'tl.set("#{gid}", {{ opacity: 0, visibility: "hidden" }}, {kill_at:.3f});')
    return html, "\n      ".join(js)


def build_index_html(manifest: TimelineManifest, clip: Clip, preset_name: PresetName, video_filename: str) -> str:
    preset = PRESETS[preset_name]
    duration_s = clip.duration_ms / 1000.0
    words = words_for_clip(clip)
    groups = group_words(words, preset["min_words"], preset["max_words"])

    caption_html_parts, caption_js_parts = [], []
    for i, g in enumerate(groups):
        html, js = _caption_group_html(g, i, preset)
        caption_html_parts.append(html)
        caption_js_parts.append(js)

    hook_text = next((o.text for o in clip.overlays if o.type == "hook"), None)
    hook_html, hook_js = "", ""
    if hook_text:
        if preset["hook_style"] == "kinetic":
            hook_html = (
                f'<div id="hook" class="hook hook-kinetic" style="opacity:0">{_esc(hook_text)}</div>'
            )
            hook_js = (
                'tl.fromTo("#hook", { opacity: 0, scale: 0.9, filter: "blur(6px)" }, '
                '{ opacity: 1, scale: 1, filter: "blur(0px)", duration: 0.22, ease: "back.out(1.2)" }, 0.1);\n'
                '      tl.to("#hook", { opacity: 0, duration: 0.15, ease: "power2.in" }, 2.4);\n'
                '      tl.set("#hook", { opacity: 0, visibility: "hidden" }, 2.55);'
            )
        else:
            hook_html = f'<div id="hook" class="hook hook-simple" style="opacity:0">{_esc(hook_text)}</div>'
            hook_js = (
                'tl.fromTo("#hook", { opacity: 0 }, { opacity: 1, duration: 0.18, ease: "power2.out" }, 0.1);\n'
                '      tl.to("#hook", { opacity: 0, duration: 0.15, ease: "power2.in" }, 2.3);\n'
                '      tl.set("#hook", { opacity: 0, visibility: "hidden" }, 2.45);'
            )

    bottom_px = preset["bottom_px"]
    font_size = preset["font_size"]
    ink = preset["ink"]
    accent = preset["accent"]

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={CANVAS_W}, height={CANVAS_H}" />
    <script src="assets/vendor/gsap.min.js"></script>
    <style>
      :root {{ --ink: {ink}; --accent: {accent}; }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: {CANVAS_W}px; height: {CANVAS_H}px; overflow: hidden; background: #000; }}
      #root {{ position: relative; width: 100%; height: 100%; font-family: Inter, sans-serif; }}
      #bg {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }}
      .caption-zone {{ position: absolute; left: 6%; right: 6%; bottom: {bottom_px}px;
        display: flex; align-items: center; justify-content: center; overflow: visible; }}
      .caption-group {{ position: absolute; left: 0; right: 0; text-align: center;
        color: var(--ink); font-size: {font_size}px; font-weight: 700; line-height: 1.25;
        text-shadow: 0 2px 10px rgba(0,0,0,0.65); }}
      .caption-group .w {{ display: inline-block; color: var(--accent); }}
      .hook {{ position: absolute; left: 8%; right: 8%; top: 9%; text-align: center;
        color: var(--ink); font-size: 58px; font-weight: 800; line-height: 1.15;
        text-shadow: 0 2px 12px rgba(0,0,0,0.7); }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{duration_s:.3f}"
         data-width="{CANVAS_W}" data-height="{CANVAS_H}">
      <video id="bg" class="clip" data-start="0" data-duration="{duration_s:.3f}"
             data-has-audio="true" playsinline src="assets/{video_filename}"></video>
      {hook_html}
      <div class="caption-zone" data-track-kind="captions">
        {''.join(caption_html_parts)}
      </div>
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      {hook_js}
      {chr(10).join('      ' + j for j in caption_js_parts)}
      window.__timelines["main"] = tl;
      tl.seek(0);
    </script>
  </body>
</html>
"""


@dataclass
class RenderResult:
    ok: bool
    output_path: Optional[str]
    check_output: str
    render_output: str


def render_clip(
    manifest: TimelineManifest,
    clip_index: int,
    preset_name: PresetName,
    clip_video_abspath: str,
    output_mp4_path: str,
    quality: str = "looks",
) -> RenderResult:
    """Generate the HyperFrames project for one clip+preset and render it
    locally with the pinned CLI (``npx hyperframes@{HYPERFRAMES_VERSION}``).
    Never touches the network beyond npx's one-time package-cache fetch —
    the GSAP runtime is vendored (``assets/vendor/gsap.min.js``), the video
    asset is copied in, and `render` runs a local headless Chrome."""
    clip = manifest.clips[clip_index]
    if preset_name not in PRESETS:
        raise ValueError(f"unknown preset {preset_name!r}; choices: {list(PRESETS)}")

    assets_dir = os.path.join(PROJECT_DIR, "assets")
    os.makedirs(assets_dir, exist_ok=True)
    video_filename = os.path.basename(clip_video_abspath)
    shutil.copyfile(clip_video_abspath, os.path.join(assets_dir, video_filename))

    html = build_index_html(manifest, clip, preset_name, video_filename)
    with open(os.path.join(PROJECT_DIR, "index.html"), "w") as f:
        f.write(html)

    def _run(args: list) -> subprocess.CompletedProcess:
        # HyperFrames refuses to install/run its headless-Chrome engine from
        # a group- or other-writable cache dir (a sane guard on a shared
        # machine) — this host's default `~/.cache` resolves to a shared,
        # group-writable location, so point it at a private one instead of
        # disabling the guard.
        env = dict(os.environ)
        env.setdefault("HYPERFRAMES_CACHE_DIR", os.path.expanduser("~/.hyperframes-cache"))
        return subprocess.run(
            ["npx", "--yes", f"hyperframes@{HYPERFRAMES_VERSION}", *args],
            cwd=PROJECT_DIR, capture_output=True, text=True, timeout=300, env=env,
        )

    check = _run(["check", "--json"])
    if check.returncode != 0:
        return RenderResult(ok=False, output_path=None, check_output=check.stdout + check.stderr, render_output="")

    os.makedirs(os.path.dirname(output_mp4_path) or ".", exist_ok=True)
    render = _run(["render", "--quality", quality, "-o", os.path.abspath(output_mp4_path)])
    ok = render.returncode == 0 and os.path.exists(output_mp4_path) and os.path.getsize(output_mp4_path) > 0
    return RenderResult(
        ok=ok,
        output_path=output_mp4_path if ok else None,
        check_output=check.stdout + check.stderr,
        render_output=render.stdout + render.stderr,
    )
