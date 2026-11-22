"""Unit tests for the TimelineManifest schema/validator (Phase 2)."""
import pytest
from pydantic import ValidationError

from timeline_manifest import Clip, Layout, SourceInfo, TimelineManifest, Word, validate_manifest


def _clip(**overrides):
    base = dict(
        clip_id="c1", video_path="job_clip_1.mp4",
        source_in_ms=1000, source_out_ms=5000, score=80,
        layout={"mode": "track"},
    )
    base.update(overrides)
    return base


def _manifest(**clip_overrides):
    return {
        "job_id": "job-1",
        "source": {"path": "source.mp4", "duration_ms": 10000},
        "clips": [_clip(**clip_overrides)],
    }


class TestValidManifest:
    def test_minimal_manifest_validates(self):
        m = validate_manifest(_manifest())
        assert m.schema_version == "1.0.0"
        assert m.clips[0].duration_ms == 4000

    def test_words_and_overlays_round_trip(self):
        m = validate_manifest(_manifest(
            words=[{"text": "hi", "start_ms": 1000, "end_ms": 1200}],
            overlays=[{"type": "hook", "text": "Watch this", "at_ms": 0}],
        ))
        assert m.clips[0].words[0].text == "hi"
        assert m.clips[0].overlays[0].text == "Watch this"


class TestRejectsBadData:
    def test_absolute_source_path_rejected(self):
        data = _manifest()
        data["source"]["path"] = "/etc/passwd"
        with pytest.raises(ValidationError):
            validate_manifest(data)

    def test_absolute_clip_video_path_rejected(self):
        with pytest.raises(ValidationError):
            validate_manifest(_manifest(video_path="/tmp/evil.mp4"))

    def test_windows_absolute_path_rejected(self):
        with pytest.raises(ValidationError):
            validate_manifest(_manifest(video_path="C:\\evil.mp4"))

    def test_clip_end_before_start_rejected(self):
        with pytest.raises(ValidationError):
            validate_manifest(_manifest(source_in_ms=5000, source_out_ms=1000))

    def test_clip_end_equal_start_rejected(self):
        with pytest.raises(ValidationError):
            validate_manifest(_manifest(source_in_ms=1000, source_out_ms=1000))

    def test_word_end_before_start_rejected(self):
        with pytest.raises(ValidationError):
            validate_manifest(_manifest(words=[{"text": "x", "start_ms": 100, "end_ms": 50}]))

    def test_score_out_of_range_rejected(self):
        with pytest.raises(ValidationError):
            validate_manifest(_manifest(score=150))

    def test_unknown_schema_version_rejected(self):
        data = _manifest()
        data["schema_version"] = "99.0.0"
        with pytest.raises(ValidationError):
            validate_manifest(data)

    def test_unknown_layout_mode_rejected(self):
        with pytest.raises(ValidationError):
            validate_manifest(_manifest(layout={"mode": "not-a-real-mode"}))

    def test_negative_source_in_ms_rejected(self):
        with pytest.raises(ValidationError):
            validate_manifest(_manifest(source_in_ms=-1, source_out_ms=5000))

    def test_negative_duration_ms_rejected(self):
        data = _manifest()
        data["source"]["duration_ms"] = -1
        with pytest.raises(ValidationError):
            validate_manifest(data)

    def test_negative_word_timestamp_rejected(self):
        with pytest.raises(ValidationError):
            validate_manifest(_manifest(words=[{"text": "x", "start_ms": -5, "end_ms": 100}]))

    def test_negative_overlay_at_ms_rejected(self):
        with pytest.raises(ValidationError):
            validate_manifest(_manifest(overlays=[{"type": "hook", "text": "h", "at_ms": -1}]))


class TestPathTraversalAndIdentifierHardening:
    @pytest.mark.parametrize("bad_path", [
        "../escape.mp4",
        "a/../../escape.mp4",
        "a/..",
        "a//b.mp4",  # empty internal segment
        "job\x00hidden.mp4",
        "job\nhidden.mp4",
    ])
    def test_traversal_or_control_chars_in_video_path_rejected(self, bad_path):
        with pytest.raises(ValidationError):
            validate_manifest(_manifest(video_path=bad_path))

    @pytest.mark.parametrize("bad_path", [
        "../escape.mp4", "..", "a/../b.mp4", "x\x00y.mp4",
    ])
    def test_traversal_in_source_path_rejected(self, bad_path):
        data = _manifest()
        data["source"]["path"] = bad_path
        with pytest.raises(ValidationError):
            validate_manifest(data)

    @pytest.mark.parametrize("bad_id", [
        "../escape", "a/b", "a\\b", "", "a" * 201, "a b", "a;rm -rf",
    ])
    def test_unsafe_clip_id_rejected(self, bad_id):
        with pytest.raises(ValidationError):
            validate_manifest(_manifest(clip_id=bad_id))

    @pytest.mark.parametrize("bad_id", ["../escape", "a/b", "", "a;b"])
    def test_unsafe_job_id_rejected(self, bad_id):
        data = _manifest()
        data["job_id"] = bad_id
        with pytest.raises(ValidationError):
            validate_manifest(data)

    def test_safe_relpath_with_subdirectory_is_allowed(self):
        m = validate_manifest(_manifest(video_path="sub/clip_1.mp4"))
        assert m.clips[0].video_path == "sub/clip_1.mp4"

    def test_duplicate_clip_id_rejected(self):
        data = _manifest()
        data["clips"].append(_clip())  # same clip_id "c1" as the first
        with pytest.raises(ValidationError):
            validate_manifest(data)


class TestClipWordsOutOfBounds:
    def test_flags_a_clip_whose_words_stray_far_outside_its_window(self):
        m = validate_manifest(_manifest(
            source_in_ms=10_000, source_out_ms=15_000,
            words=[{"text": "far", "start_ms": 0, "end_ms": 200}],
        ))
        assert m.clip_words_out_of_bounds() == ["c1"]

    def test_a_word_straddling_the_edge_by_a_little_is_not_flagged(self):
        m = validate_manifest(_manifest(
            source_in_ms=10_000, source_out_ms=15_000,
            words=[{"text": "straddle", "start_ms": 9_800, "end_ms": 10_200}],
        ))
        assert m.clip_words_out_of_bounds() == []
