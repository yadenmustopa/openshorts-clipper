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
    build_index_html,
    group_words,
    load_manifest_from_job,
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
