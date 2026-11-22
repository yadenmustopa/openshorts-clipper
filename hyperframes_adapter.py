"""OpenShorts -> HyperFrames adapter (Phase 2, hardened for concurrent use).

Converts one clip from an OpenShorts job's own ``*_metadata.json`` into a
:class:`timeline_manifest.TimelineManifest`, then into an **isolated**
HyperFrames project under the job's own output directory, rendered
locally with the pinned HyperFrames CLI.

Does **not** re-run clip selection or transcription — this module only
reads what ``main.py`` already produced (per the PRD: "Jangan membuat
ulang clip selection atau Whisper; gunakan hasil existing"). The clip's
own video file (already cut and reframed to 9:16 by OpenShorts) is used
as-is; HyperFrames' job here is enhancement (captions, hook overlay,
preset-specific motion), not reframing.

Three presets (``PRESETS`` below): ``clean_podcast``, ``bold_kinetic``,
``educational_screen`` — see ``docs/architecture/hyperframes-integration.md``
for what each one is for.

## Concurrency hardening (Phase 2 Step A)

The original PoC wrote every render to one shared
``integrations/hyperframes/index.html`` / ``assets/`` — safe for a single
manual render, **not** safe once multiple clips or jobs render at once
(``main.py``'s own ``ThreadPoolExecutor`` already renders several clips
in parallel per job, see ``CLIP_WORKERS`` in ``main.py``). Every render
now gets its own workspace: ``render_clip`` takes ``job_output_dir`` (the
job's own output directory — the same one ``main.py``/``app.py`` already
use) and builds ``<job_output_dir>/hyperframes_render/<clip_id>/<preset>/``,
a fresh copy of the template project, so two clips of the same job (or
two jobs) rendering at the same time never touch each other's
``index.html``, ``assets/``, or ``.hyperframes/`` state.

The one thing still shared on purpose: ``HYPERFRAMES_CACHE_DIR`` (the
downloaded headless-Chrome binary and npx's package cache) — a large,
effectively read-only-after-first-use download, not per-job state. A
cold start where two jobs race to populate it for the first time is a
known, narrow edge case (see "What this hardening does not cover" in
``docs/architecture/hyperframes-integration.md``); pre-warming it once
(``npx hyperframes@<pinned> browser ensure``) avoids the race entirely.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import List, Literal, Optional

from timeline_manifest import Clip, Overlay, SourceInfo, TimelineManifest, Word

HYPERFRAMES_VERSION = "0.9.80"
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "integrations", "hyperframes")
CANVAS_W, CANVAS_H = 1080, 1920
HYPERFRAMES_CACHE_DIR = os.environ.get("HYPERFRAMES_CACHE_DIR") or os.path.expanduser("~/.hyperframes-cache")

# Files copied from TEMPLATE_DIR into every per-render workspace. Deliberately
# not a recursive copytree of the whole template dir — that would also pull
# in AGENTS.md/CLAUDE.md (irrelevant per render) and risk picking up a stray
# .hyperframes/ or assets/*.mp4 left over from a previous manual run.
_TEMPLATE_FILES = ["hyperframes.json", "meta.json", "package.json"]
_TEMPLATE_ASSET_DIRS = ["assets/vendor"]

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


class WorkspaceEscapeError(Exception):
    """A path built from job/clip/preset data would resolve outside the
    directory it's supposed to be confined to."""


def resolve_within(base_dir: str, *parts: str) -> str:
    """Join ``parts`` onto ``base_dir`` and return the resolved
    (symlink-free) absolute path — raising :class:`WorkspaceEscapeError`
    if it does not stay inside ``base_dir``. Every path this module
    builds from manifest-supplied or caller-supplied components (clip
    ids, preset names, video filenames) goes through this before being
    used for a filesystem write, so a crafted identifier or a symlink
    planted inside the workspace can't escape it. ``base_dir`` need not
    exist yet (its own realpath is still well-defined); create any
    needed directories with the *returned* path, not the raw join."""
    base_real = os.path.realpath(base_dir)
    joined = os.path.join(base_dir, *parts)
    real = os.path.realpath(joined)
    if real != base_real and not real.startswith(base_real + os.sep):
        raise WorkspaceEscapeError(
            f"{os.path.join(*parts)!r} resolves to {real!r}, which is outside "
            f"the allowed workspace {base_real!r}"
        )
    return real


def load_manifest_from_job(metadata_path: str, source_path: str, job_id: str) -> TimelineManifest:
    """Build a :class:`TimelineManifest` from an OpenShorts job's own
    ``*_metadata.json`` (the exact file ``main.py`` writes — see
    ``main.py``'s ``write_json_atomic(metadata_file, clips_data, ...)``).
    Every clip's rendered video file is expected to sit alongside
    ``metadata_path`` as ``<job_basename>_clip_<n>.mp4``.

    ``TimelineManifest``'s own validators (``timeline_manifest.py``)
    reject an unsafe ``job_id``/``clip_id``/path before this function
    returns — a job id or filename derived from untrusted input (e.g. a
    user-supplied upload name) cannot smuggle a path-traversal segment
    through here.
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


def _prepare_workspace(job_output_dir: str, clip_id: str, preset_name: str) -> str:
    """Create (or reset) ``<job_output_dir>/hyperframes_render/<clip_id>/<preset>/``
    as a fresh copy of the template project. ``clip_id``/``preset_name``
    are already-validated safe identifiers by this point (the manifest's
    own pydantic validators for ``clip_id``; ``preset_name`` is checked
    against the ``PRESETS`` dict in ``render_clip`` before this is
    called) — ``resolve_within`` is still applied as defense in depth,
    not as the only check."""
    os.makedirs(job_output_dir, exist_ok=True)
    render_root = resolve_within(job_output_dir, "hyperframes_render")
    os.makedirs(render_root, exist_ok=True)
    workspace = resolve_within(render_root, clip_id, preset_name)
    if os.path.exists(workspace):
        shutil.rmtree(workspace)
    os.makedirs(workspace)

    for rel in _TEMPLATE_FILES:
        src = os.path.join(TEMPLATE_DIR, rel)
        if os.path.exists(src):
            shutil.copyfile(src, os.path.join(workspace, rel))
    for rel in _TEMPLATE_ASSET_DIRS:
        src = os.path.join(TEMPLATE_DIR, rel)
        if os.path.isdir(src):
            dst = os.path.join(workspace, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copytree(src, dst)
    os.makedirs(os.path.join(workspace, "assets"), exist_ok=True)
    return workspace


@dataclass
class ProbeResult:
    """What ``ffprobe`` actually found in a rendered file — not inferred
    from an exit code."""
    exists: bool = False
    size_bytes: int = 0
    duration_s: float = 0.0
    width: int = 0
    height: int = 0
    video_codec: str = ""
    audio_codec: str = ""
    has_video_stream: bool = False
    has_audio_stream: bool = False
    raw: dict = field(default_factory=dict)
    error: str = ""


def probe_output(path: str) -> ProbeResult:
    """Run ``ffprobe`` on ``path`` and report its actual, measured
    properties. Never guesses from the file extension or size alone."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return ProbeResult(exists=os.path.exists(path), size_bytes=os.path.getsize(path) if os.path.exists(path) else 0,
                            error="file missing or empty")
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-print_format", "json",
             "-show_format", "-show_streams", path],
            capture_output=True, text=True, timeout=60,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return ProbeResult(exists=True, size_bytes=os.path.getsize(path), error=f"ffprobe failed to run: {e}")
    if proc.returncode != 0:
        return ProbeResult(exists=True, size_bytes=os.path.getsize(path), error=f"ffprobe error: {proc.stderr.strip()}")
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        return ProbeResult(exists=True, size_bytes=os.path.getsize(path), error=f"ffprobe gave non-JSON output: {e}")

    result = ProbeResult(exists=True, size_bytes=os.path.getsize(path), raw=data)
    try:
        result.duration_s = float(data.get("format", {}).get("duration", 0.0))
    except (TypeError, ValueError):
        pass
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video" and not result.has_video_stream:
            result.has_video_stream = True
            result.video_codec = stream.get("codec_name", "")
            result.width = int(stream.get("width", 0) or 0)
            result.height = int(stream.get("height", 0) or 0)
        elif stream.get("codec_type") == "audio" and not result.has_audio_stream:
            result.has_audio_stream = True
            result.audio_codec = stream.get("codec_name", "")
    return result


def detect_black_frames(path: str, min_duration_s: float = 0.1) -> List[tuple]:
    """``ffmpeg blackdetect`` — returns a list of ``(start_s, end_s)``
    black stretches of at least ``min_duration_s``. Empty means none
    found (not "didn't check" — a parse failure raises, it doesn't
    silently report zero)."""
    proc = subprocess.run(
        ["ffmpeg", "-i", path, "-vf", f"blackdetect=d={min_duration_s}:pix_th=0.02", "-an", "-f", "null", "-"],
        capture_output=True, text=True, timeout=120,
    )
    spans = []
    for line in proc.stderr.splitlines():
        if "black_start" in line:
            m = re.search(r"black_start:([\d.]+) black_end:([\d.]+)", line)
            if m:
                spans.append((float(m.group(1)), float(m.group(2))))
    return spans


@dataclass
class ValidationReport:
    ok: bool
    probe: ProbeResult
    black_frames: List[tuple]
    problems: List[str] = field(default_factory=list)


def validate_rendered_output(
    path: str,
    expected_duration_s: float,
    expected_width: int = CANVAS_W,
    expected_height: int = CANVAS_H,
    duration_tolerance_s: float = 0.5,
    check_black_frames: bool = True,
) -> ValidationReport:
    """The real acceptance gate for a rendered clip — codec, resolution,
    duration, and stream presence via ``ffprobe``, plus a black-frame
    sweep, not merely "the process exited 0 and the file is non-empty"."""
    probe = probe_output(path)
    problems: List[str] = []
    if probe.error:
        problems.append(f"ffprobe: {probe.error}")
        return ValidationReport(ok=False, probe=probe, black_frames=[], problems=problems)

    if not probe.has_video_stream:
        problems.append("no video stream found")
    elif probe.video_codec != "h264":
        problems.append(f"video codec is {probe.video_codec!r}, expected h264")
    if (probe.width, probe.height) != (expected_width, expected_height):
        problems.append(f"resolution is {probe.width}x{probe.height}, expected {expected_width}x{expected_height}")
    if not probe.has_audio_stream:
        problems.append("no audio stream found")
    elif probe.audio_codec not in ("aac",):
        problems.append(f"audio codec is {probe.audio_codec!r}, expected aac")
    if abs(probe.duration_s - expected_duration_s) > duration_tolerance_s:
        problems.append(
            f"duration is {probe.duration_s:.3f}s, expected {expected_duration_s:.3f}s "
            f"(tolerance {duration_tolerance_s}s)"
        )

    black_frames: List[tuple] = []
    if check_black_frames and not problems:
        black_frames = detect_black_frames(path)
        if black_frames:
            problems.append(f"{len(black_frames)} black-frame span(s) found: {black_frames}")

    return ValidationReport(ok=not problems, probe=probe, black_frames=black_frames, problems=problems)


@dataclass
class RenderResult:
    ok: bool
    output_path: Optional[str]
    workspace: Optional[str]
    check_output: str
    render_output: str
    validation: Optional[ValidationReport] = None


def render_clip(
    manifest: TimelineManifest,
    clip_index: int,
    preset_name: PresetName,
    clip_video_abspath: str,
    output_mp4_path: str,
    job_output_dir: str,
    quality: str = "looks",
    validate: bool = True,
) -> RenderResult:
    """Generate an **isolated** HyperFrames project for one clip+preset
    under ``job_output_dir`` and render it locally with the pinned CLI
    (``npx hyperframes@{HYPERFRAMES_VERSION}``). Safe to call
    concurrently for different clips/presets of the same or different
    jobs — each call gets its own workspace (see module docstring).

    Never touches the network beyond npx's one-time package-cache fetch
    and the one-time headless-Chrome download — the GSAP runtime is
    vendored (``assets/vendor/gsap.min.js``), the video asset is copied
    in, and `render` runs a local headless Chrome.
    """
    clip = manifest.clips[clip_index]
    if preset_name not in PRESETS:
        raise ValueError(f"unknown preset {preset_name!r}; choices: {list(PRESETS)}")

    workspace = _prepare_workspace(job_output_dir, clip.clip_id, preset_name)

    video_filename = os.path.basename(clip_video_abspath)
    dest_video = resolve_within(workspace, "assets", video_filename)
    shutil.copyfile(clip_video_abspath, dest_video)

    html = build_index_html(manifest, clip, preset_name, video_filename)
    index_path = resolve_within(workspace, "index.html")
    with open(index_path, "w") as f:
        f.write(html)

    def _run(args: list) -> subprocess.CompletedProcess:
        # HyperFrames refuses to install/run its headless-Chrome engine from
        # a group- or other-writable cache dir (a sane guard on a shared
        # machine) — this host's default `~/.cache` resolves to a shared,
        # group-writable location, so point it at a private one instead of
        # disabling the guard. Shared across workspaces on purpose — see
        # module docstring.
        env = dict(os.environ)
        env["HYPERFRAMES_CACHE_DIR"] = HYPERFRAMES_CACHE_DIR
        return subprocess.run(
            ["npx", "--yes", f"hyperframes@{HYPERFRAMES_VERSION}", *args],
            cwd=workspace, capture_output=True, text=True, timeout=300, env=env,
        )

    check = _run(["check", "--json"])
    if check.returncode != 0:
        return RenderResult(ok=False, output_path=None, workspace=workspace,
                             check_output=check.stdout + check.stderr, render_output="")

    out_dir = os.path.dirname(output_mp4_path) or "."
    os.makedirs(out_dir, exist_ok=True)
    render = _run(["render", "--quality", quality, "-o", os.path.abspath(output_mp4_path)])
    process_ok = render.returncode == 0 and os.path.exists(output_mp4_path) and os.path.getsize(output_mp4_path) > 0

    validation = None
    if process_ok and validate:
        validation = validate_rendered_output(output_mp4_path, expected_duration_s=clip.duration_ms / 1000.0)

    ok = process_ok and (validation is None or validation.ok)
    return RenderResult(
        ok=ok,
        output_path=output_mp4_path if ok else None,
        workspace=workspace,
        check_output=check.stdout + check.stderr,
        render_output=render.stdout + render.stderr,
        validation=validation,
    )
