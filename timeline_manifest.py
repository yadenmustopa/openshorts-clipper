"""The versioned contract between OpenShorts and the HyperFrames worker.

Per ``docs/ARCHITECTURE.md`` §4.1: word timestamps are **source-relative**
in the manifest (the same frame of reference OpenShorts' own
``*_metadata.json`` already uses); the HyperFrames adapter
(``hyperframes_adapter.py``) does the explicit transform to clip-relative
time when it builds the render project — never done here, so the manifest
itself stays an honest, unambiguous record of "what OpenShorts decided."

No absolute filesystem paths belong in a manifest that might move between
machines — ``source.path`` and ``clips[].video_path`` are relative to the
job's own output directory, not absolute.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

SCHEMA_VERSION = "1.0.0"


class SourceInfo(BaseModel):
    path: str
    sha256: Optional[str] = None
    duration_ms: int

    @field_validator("path")
    @classmethod
    def _no_absolute_path(cls, v: str) -> str:
        if v.startswith("/") or v.startswith("\\") or (len(v) > 1 and v[1] == ":"):
            raise ValueError(f"source.path must be relative to the job dir, got {v!r}")
        return v


class Word(BaseModel):
    """One transcript word. ``start_ms``/``end_ms`` are source-relative —
    the same clock as ``SourceInfo.duration_ms``, not the clip's own."""
    text: str
    start_ms: int
    end_ms: int

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
    at_ms: int = 0


class Clip(BaseModel):
    clip_id: str
    video_path: str
    """Path to this clip's own rendered MP4, relative to the job dir —
    not the source video (that's ``SourceInfo.path``)."""
    source_in_ms: int
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

    @field_validator("video_path")
    @classmethod
    def _no_absolute_path(cls, v: str) -> str:
        if v.startswith("/") or v.startswith("\\") or (len(v) > 1 and v[1] == ":"):
            raise ValueError(f"clip.video_path must be relative to the job dir, got {v!r}")
        return v

    @field_validator("source_out_ms")
    @classmethod
    def _out_after_in(cls, out_ms: int, info) -> int:
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


def validate_manifest(data: dict) -> TimelineManifest:
    """Parse and validate ``data`` as a TimelineManifest, raising
    ``pydantic.ValidationError`` with a precise field path on any
    violation — negative/reversed timestamps, an absolute path, an
    out-of-range score, an unknown schema version, a clip's words
    stretching past the clip's own bounds (checked in
    ``hyperframes_adapter.words_for_clip``, not here, since that check
    needs the clip's own ``source_in_ms``/``source_out_ms`` already
    validated first)."""
    return TimelineManifest.model_validate(data)
