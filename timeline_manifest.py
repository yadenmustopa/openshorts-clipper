"""The versioned contract between OpenShorts and the HyperFrames worker.

Per ``docs/ARCHITECTURE.md`` §4.1: word timestamps are **source-relative**
in the manifest (the same frame of reference OpenShorts' own
``*_metadata.json`` already uses); the HyperFrames adapter
(``hyperframes_adapter.py``) does the explicit transform to clip-relative
time when it builds the render project — never done here, so the manifest
itself stays an honest, unambiguous record of "what OpenShorts decided."

No absolute filesystem paths belong in a manifest that might move between
machines — ``source.path`` and ``clips[].video_path`` are relative to the
job's own output directory, not absolute. This module validates the
*shape* of a path (no traversal, no absolute path, no control characters);
it cannot validate symlink escape, which needs an actual filesystem to
resolve against — that check is ``hyperframes_adapter.resolve_within``'s
job, applied at the point a manifest path is actually opened.

Identifiers (``job_id``, ``clip_id``) are restricted to a safe charset
because the adapter uses them as path *components* when it builds a
per-job, per-clip render workspace (Phase 2 hardening, Step A.1/A.2) — an
identifier that could contain ``/`` or ``..`` would otherwise let a
crafted manifest escape the workspace it's supposed to be confined to.
"""
from __future__ import annotations

import re
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

SCHEMA_VERSION = "1.0.0"

# Conservative on purpose: letters, digits, dash, underscore, dot (for
# extensions in file-ish ids) — never a path separator, never "..".
_SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_.-]{1,200}$")
_SAFE_RELPATH_RE = re.compile(r"^[A-Za-z0-9_.\-/]{1,500}$")
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")


def _check_safe_identifier(v: str, field_name: str) -> str:
    if not _SAFE_IDENTIFIER_RE.match(v):
        raise ValueError(
            f"{field_name} must match {_SAFE_IDENTIFIER_RE.pattern} (got {v!r}) — "
            "it is used as a filesystem path component for this clip/job's "
            "isolated render workspace, so path separators and '..' are rejected"
        )
    return v


def _check_safe_relpath(v: str, field_name: str) -> str:
    if _CONTROL_CHARS_RE.search(v):
        raise ValueError(f"{field_name} contains a control character: {v!r}")
    if v.startswith("/") or v.startswith("\\") or (len(v) > 1 and v[1] == ":"):
        raise ValueError(f"{field_name} must be relative to the job dir, got {v!r}")
    # Reject '..' as a path *segment* (not merely the substring — a
    # filename genuinely called "a..b.mp4" is unusual but not a traversal).
    segments = re.split(r"[/\\]", v)
    if ".." in segments or "" in segments[1:-1]:
        raise ValueError(f"{field_name} must not contain a '..' segment or an empty segment: {v!r}")
    if not _SAFE_RELPATH_RE.match(v):
        raise ValueError(f"{field_name} contains characters outside {_SAFE_RELPATH_RE.pattern}: {v!r}")
    return v


class SourceInfo(BaseModel):
    path: str
    sha256: Optional[str] = None
    duration_ms: int = Field(ge=0)

    @field_validator("path")
    @classmethod
    def _path_is_safe(cls, v: str) -> str:
        return _check_safe_relpath(v, "source.path")


class Word(BaseModel):
    """One transcript word. ``start_ms``/``end_ms`` are source-relative —
    the same clock as ``SourceInfo.duration_ms``, not the clip's own."""
    text: str
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)

    @field_validator("end_ms")
    @classmethod
    def _end_after_start(cls, end_ms: int, info) -> int:
        start_ms = info.data.get("start_ms")
        if start_ms is not None and end_ms < start_ms:
            raise ValueError(f"word end_ms ({end_ms}) before start_ms ({start_ms})")
        return end_ms


class Layout(BaseModel):
    mode: Literal["track", "general", "split", "screencast"]
    aspect_ratio: str = "9:16"


class Overlay(BaseModel):
    type: Literal["hook"]
    text: str
    at_ms: int = Field(ge=0, default=0)


class Clip(BaseModel):
    clip_id: str
    video_path: str
    """Path to this clip's own rendered MP4, relative to the job dir —
    not the source video (that's ``SourceInfo.path``)."""
    source_in_ms: int = Field(ge=0)
    source_out_ms: int
    score: float = Field(ge=0, le=100)
    score_type: Literal["model_estimate"] = "model_estimate"
    reason: str = ""
    layout: Layout
    caption_style: str = "kinetic_clean"
    words: List[Word] = Field(default_factory=list)
    """Source-relative. The adapter subtracts ``source_in_ms`` to get
    clip-relative captions timing — see ``hyperframes_adapter.words_for_clip``."""
    overlays: List[Overlay] = Field(default_factory=list)

    @field_validator("clip_id")
    @classmethod
    def _clip_id_is_safe(cls, v: str) -> str:
        return _check_safe_identifier(v, "clip.clip_id")

    @field_validator("video_path")
    @classmethod
    def _path_is_safe(cls, v: str) -> str:
        return _check_safe_relpath(v, "clip.video_path")

    @field_validator("source_out_ms")
    @classmethod
    def _out_after_in_and_bounded(cls, out_ms: int, info) -> int:
        if out_ms < 0:
            raise ValueError(f"clip source_out_ms ({out_ms}) must not be negative")
        in_ms = info.data.get("source_in_ms")
        if in_ms is not None and out_ms <= in_ms:
            raise ValueError(f"clip source_out_ms ({out_ms}) <= source_in_ms ({in_ms})")
        return out_ms

    @property
    def duration_ms(self) -> int:
        return self.source_out_ms - self.source_in_ms


class TimelineManifest(BaseModel):
    schema_version: str = SCHEMA_VERSION
    job_id: str
    source: SourceInfo
    clips: List[Clip]

    @field_validator("schema_version")
    @classmethod
    def _known_version(cls, v: str) -> str:
        if v != SCHEMA_VERSION:
            raise ValueError(
                f"unsupported schema_version {v!r}; this adapter understands {SCHEMA_VERSION!r} only"
            )
        return v

    @field_validator("job_id")
    @classmethod
    def _job_id_is_safe(cls, v: str) -> str:
        return _check_safe_identifier(v, "job_id")

    @field_validator("clips")
    @classmethod
    def _clip_ids_unique(cls, clips: List[Clip]) -> List[Clip]:
        ids = [c.clip_id for c in clips]
        if len(ids) != len(set(ids)):
            dupes = {i for i in ids if ids.count(i) > 1}
            raise ValueError(f"duplicate clip_id(s) in one manifest: {sorted(dupes)}")
        return clips

    def clip_words_out_of_bounds(self) -> List[str]:
        """Clip ids whose words extend past the clip's own
        ``source_in_ms``/``source_out_ms`` window — not a hard validation
        error (upstream transcript boundaries can legitimately straddle a
        cut point by a word or two), but a caller should decide whether to
        clamp or reject. ``hyperframes_adapter.words_for_clip`` clamps."""
        out = []
        for clip in self.clips:
            for w in clip.words:
                if w.end_ms <= clip.source_in_ms or w.start_ms >= clip.source_out_ms:
                    continue  # entirely outside; words_for_clip drops these, not an error
            # A word stretching more than a few seconds past either edge is
            # suspicious enough to flag (likely wrong frame of reference).
            tolerance_ms = 5000
            for w in clip.words:
                if w.start_ms < clip.source_in_ms - tolerance_ms or w.end_ms > clip.source_out_ms + tolerance_ms:
                    out.append(clip.clip_id)
                    break
        return out


def validate_manifest(data: dict) -> TimelineManifest:
    """Parse and validate ``data`` as a TimelineManifest, raising
    ``pydantic.ValidationError`` with a precise field path on any
    violation — negative/reversed timestamps, an absolute or traversing
    path, an unsafe identifier, an out-of-range score, an unknown schema
    version, or a duplicate clip_id within one manifest."""
    return TimelineManifest.model_validate(data)
