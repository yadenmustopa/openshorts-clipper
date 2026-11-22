"""Unit tests for the OpenShorts -> HyperFrames adapter (Phase 2).

No test here invokes the actual `npx hyperframes` CLI (no browser/Node
subprocess) — these test the pure-Python manifest/HTML-generation logic.
The real render is exercised manually and recorded in
docs/ACCEPTANCE_TESTS.md, consistent with this fork's rule that a test
suite run must never claim a render passed without one actually having
happened.
"""
import json
import os

import pytest

from hyperframes_adapter import (
    PRESETS,
    ProbeResult,
    WorkspaceEscapeError,
    _prepare_workspace,
    build_index_html,
    group_words,
    load_manifest_from_job,
    resolve_within,
    validate_rendered_output,
    words_for_clip,
)
from timeline_manifest import Clip, Overlay, SourceInfo, TimelineManifest, Word


def _clip(source_in_ms=10_000, source_out_ms=20_000, words=None, overlays=None):
    return Clip(
        clip_id="job_clip_1", video_path="job_clip_1.mp4",
        source_in_ms=source_in_ms, source_out_ms=source_out_ms, score=70,
        layout={"mode": "track"},
        words=words or [], overlays=overlays or [],
    )


class TestWordsForClip:
    def test_converts_source_relative_to_clip_relative(self):
        clip = _clip(source_in_ms=10_000, source_out_ms=20_000, words=[
            Word(text="hi", start_ms=10_500, end_ms=10_800),
        ])
        out = words_for_clip(clip)
        assert out == [{"text": "hi", "start": 0.5, "end": 0.8}]

    def test_drops_a_word_that_ends_before_the_clip_starts(self):
        clip = _clip(source_in_ms=10_000, source_out_ms=20_000, words=[
            Word(text="before", start_ms=9_000, end_ms=9_900),
        ])
        assert words_for_clip(clip) == []

    def test_clamps_a_word_that_starts_before_the_clip(self):
        clip = _clip(source_in_ms=10_000, source_out_ms=20_000, words=[
            Word(text="straddle", start_ms=9_800, end_ms=10_200),
        ])
        out = words_for_clip(clip)
        assert out[0]["start"] == 0.0

    def test_clamps_a_word_that_ends_after_the_clip(self):
        clip = _clip(source_in_ms=10_000, source_out_ms=20_000, words=[
            Word(text="over", start_ms=19_900, end_ms=20_500),
        ])
        out = words_for_clip(clip)
        assert out[0]["end"] == 10.0  # clip.duration_ms / 1000


class TestGroupWords:
    def test_breaks_on_word_count_ceiling(self):
        words = [{"text": f"w{i}", "start": i * 0.3, "end": i * 0.3 + 0.2} for i in range(9)]
        groups = group_words(words, min_words=2, max_words=3)
        assert [len(g) for g in groups] == [3, 3, 3]

    def test_breaks_early_on_a_long_pause(self):
        words = [
            {"text": "hello", "start": 0.0, "end": 0.3},
            {"text": "world", "start": 0.35, "end": 0.6},
            {"text": "next", "start": 2.0, "end": 2.3},  # 1.4s pause
            {"text": "sentence", "start": 2.35, "end": 2.6},
        ]
        groups = group_words(words, min_words=2, max_words=6)
        assert [[w["text"] for w in g] for g in groups] == [["hello", "world"], ["next", "sentence"]]

    def test_empty_input_gives_no_groups(self):
        assert group_words([], min_words=2, max_words=5) == []

    def test_non_word_tokens_are_dropped(self):
        words = [
            {"text": "hello", "start": 0.0, "end": 0.3},
            {"text": "♪", "start": 0.3, "end": 0.35},
            {"text": "world", "start": 0.35, "end": 0.6},
        ]
        groups = group_words(words, min_words=1, max_words=5)
        assert groups == [[words[0], words[2]]]


class TestBuildIndexHtml:
    def test_duration_matches_clip_length(self):
        clip = _clip(source_in_ms=0, source_out_ms=12_500)
        manifest = TimelineManifest(job_id="j", source=SourceInfo(path="s.mp4", duration_ms=12_500), clips=[clip])
        html = build_index_html(manifest, clip, "clean_podcast", "job_clip_1.mp4")
        assert 'data-duration="12.500"' in html

    def test_video_asset_path_has_no_leading_slash(self):
        clip = _clip()
        manifest = TimelineManifest(job_id="j", source=SourceInfo(path="s.mp4", duration_ms=20_000), clips=[clip])
        html = build_index_html(manifest, clip, "clean_podcast", "job_clip_1.mp4")
        assert 'src="assets/job_clip_1.mp4"' in html
        assert 'src="/assets' not in html

    def test_gsap_is_vendored_locally_not_a_cdn(self):
        clip = _clip()
        manifest = TimelineManifest(job_id="j", source=SourceInfo(path="s.mp4", duration_ms=20_000), clips=[clip])
        html = build_index_html(manifest, clip, "clean_podcast", "job_clip_1.mp4")
        assert 'src="assets/vendor/gsap.min.js"' in html
        assert "cdn." not in html and "http://" not in html and "https://" not in html

    def test_video_is_a_timed_clip_with_audio_declared(self):
        clip = _clip()
        manifest = TimelineManifest(job_id="j", source=SourceInfo(path="s.mp4", duration_ms=20_000), clips=[clip])
        html = build_index_html(manifest, clip, "clean_podcast", "job_clip_1.mp4")
        assert 'class="clip"' in html
        assert 'data-has-audio="true"' in html

    def test_hook_overlay_renders_when_present(self):
        clip = _clip(overlays=[Overlay(type="hook", text="Wait for it", at_ms=0)])
        manifest = TimelineManifest(job_id="j", source=SourceInfo(path="s.mp4", duration_ms=20_000), clips=[clip])
        html = build_index_html(manifest, clip, "bold_kinetic", "job_clip_1.mp4")
        assert "Wait for it" in html

    def test_timeline_is_registered_under_the_composition_id(self):
        clip = _clip()
        manifest = TimelineManifest(job_id="j", source=SourceInfo(path="s.mp4", duration_ms=20_000), clips=[clip])
        html = build_index_html(manifest, clip, "educational_screen", "job_clip_1.mp4")
        assert 'window.__timelines["main"] = tl;' in html
        assert 'data-composition-id="main"' in html

    def test_every_preset_renders_without_raising(self):
        clip = _clip(words=[Word(text="hi", start_ms=10_100, end_ms=10_400)],
                      overlays=[Overlay(type="hook", text="Hook", at_ms=0)])
        manifest = TimelineManifest(job_id="j", source=SourceInfo(path="s.mp4", duration_ms=20_000), clips=[clip])
        for preset in PRESETS:
            html = build_index_html(manifest, clip, preset, "job_clip_1.mp4")
            assert "<html" in html

    def test_unknown_preset_raises_keyerror(self):
        clip = _clip()
        manifest = TimelineManifest(job_id="j", source=SourceInfo(path="s.mp4", duration_ms=20_000), clips=[clip])
        with pytest.raises(KeyError):
            build_index_html(manifest, clip, "not-a-real-preset", "job_clip_1.mp4")


class TestLoadManifestFromJob:
    def test_reads_a_real_shaped_metadata_json(self, tmp_path):
        meta = {
            "shorts": [{
                "start": 10.0, "end": 15.0, "predicted_score": 82,
                "video_title_for_youtube_short": "t", "why": "because",
                "viral_hook_text": "Look at this",
                "layout_ranges": [{"start": 0, "end": 5, "layout": "track"}],
            }],
            "transcript": {
                "language": "en",
                "segments": [{
                    "start": 10.0, "end": 12.0, "text": "hi there",
                    "words": [
                        {"word": "hi", "start": 10.0, "end": 10.3},
                        {"word": "there", "start": 10.3, "end": 10.6},
                    ],
                }],
            },
        }
        meta_path = tmp_path / "myjob_metadata.json"
        meta_path.write_text(json.dumps(meta))
        manifest = load_manifest_from_job(str(meta_path), "source.mp4", "myjob")
        assert len(manifest.clips) == 1
        c = manifest.clips[0]
        assert c.source_in_ms == 10_000 and c.source_out_ms == 15_000
        assert c.layout.mode == "track"
        assert c.overlays[0].text == "Look at this"
        assert [w.text for w in c.words] == ["hi", "there"]


class TestResolveWithin:
    def test_a_plain_subpath_resolves(self, tmp_path):
        result = resolve_within(str(tmp_path), "a", "b.mp4")
        assert result == os.path.realpath(os.path.join(str(tmp_path), "a", "b.mp4"))

    def test_the_base_dir_itself_resolves(self, tmp_path):
        assert resolve_within(str(tmp_path)) == os.path.realpath(str(tmp_path))

    def test_dotdot_escape_is_rejected(self, tmp_path):
        with pytest.raises(WorkspaceEscapeError):
            resolve_within(str(tmp_path), "..", "..", "etc", "passwd")

    def test_a_symlink_pointing_outside_the_base_is_rejected(self, tmp_path):
        outside = tmp_path.parent / "outside_target"
        outside.mkdir(exist_ok=True)
        base = tmp_path / "base"
        base.mkdir()
        link = base / "escape"
        os.symlink(str(outside), str(link))
        with pytest.raises(WorkspaceEscapeError):
            resolve_within(str(base), "escape", "file.txt")

    def test_a_symlink_pointing_inside_the_base_is_allowed(self, tmp_path):
        base = tmp_path / "base"
        base.mkdir()
        real_sub = base / "real"
        real_sub.mkdir()
        link = base / "alias"
        os.symlink(str(real_sub), str(link))
        result = resolve_within(str(base), "alias", "file.txt")
        assert result == os.path.realpath(str(real_sub / "file.txt"))


class TestPrepareWorkspace:
    def test_two_clips_of_the_same_job_get_separate_workspaces(self, tmp_path):
        job_dir = str(tmp_path / "job1")
        ws1 = _prepare_workspace(job_dir, "clipA", "clean_podcast")
        ws2 = _prepare_workspace(job_dir, "clipB", "clean_podcast")
        assert ws1 != ws2
        assert os.path.isdir(ws1) and os.path.isdir(ws2)

    def test_same_clip_different_preset_gets_separate_workspace(self, tmp_path):
        job_dir = str(tmp_path / "job1")
        ws1 = _prepare_workspace(job_dir, "clipA", "clean_podcast")
        ws2 = _prepare_workspace(job_dir, "clipA", "bold_kinetic")
        assert ws1 != ws2

    def test_two_different_jobs_get_separate_workspaces_even_with_the_same_clip_id(self, tmp_path):
        ws1 = _prepare_workspace(str(tmp_path / "jobA"), "clip_1", "clean_podcast")
        ws2 = _prepare_workspace(str(tmp_path / "jobB"), "clip_1", "clean_podcast")
        assert ws1 != ws2
        assert ws1.startswith(os.path.realpath(str(tmp_path / "jobA")))
        assert ws2.startswith(os.path.realpath(str(tmp_path / "jobB")))

    def test_a_stale_workspace_from_a_previous_run_is_reset_not_merged(self, tmp_path):
        job_dir = str(tmp_path / "job1")
        ws = _prepare_workspace(job_dir, "clipA", "clean_podcast")
        stale_file = os.path.join(ws, "index.html")
        with open(stale_file, "w") as f:
            f.write("stale content from a previous render")
        ws2 = _prepare_workspace(job_dir, "clipA", "clean_podcast")
        assert ws2 == ws
        assert not os.path.exists(stale_file)  # wiped, not left behind

    def test_vendor_assets_are_copied_into_the_workspace(self, tmp_path):
        ws = _prepare_workspace(str(tmp_path / "job1"), "clipA", "clean_podcast")
        assert os.path.exists(os.path.join(ws, "assets", "vendor", "gsap.min.js"))


class TestValidateRenderedOutput:
    def test_missing_file_is_not_ok(self, tmp_path):
        report = validate_rendered_output(str(tmp_path / "missing.mp4"), expected_duration_s=10.0)
        assert report.ok is False
        assert "missing" in report.problems[0] or "empty" in report.problems[0]

    def test_empty_file_is_not_ok(self, tmp_path):
        path = tmp_path / "empty.mp4"
        path.write_bytes(b"")
        report = validate_rendered_output(str(path), expected_duration_s=10.0)
        assert report.ok is False

    def test_a_non_video_file_fails_ffprobe_cleanly(self, tmp_path):
        path = tmp_path / "not_a_video.mp4"
        path.write_bytes(b"this is not an mp4 file, just text pretending to be one" * 10)
        report = validate_rendered_output(str(path), expected_duration_s=10.0)
        assert report.ok is False
        assert report.problems  # some reason is recorded, not a silent False

    def test_probe_result_dataclass_defaults_are_safe(self):
        r = ProbeResult()
        assert r.exists is False and r.has_video_stream is False and r.has_audio_stream is False
