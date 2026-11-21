"""Unit + integration tests for feature_flags.py and its wiring into app.py.

Covers the Phase 1 requirement that every out-of-scope feature (AI UGC
generation, TTS, dubbing, social publishing, Gemini vision) is off by
default and refused *at the backend* — not just omitted from the UI — with
a structured ``FEATURE_DISABLED`` response, while the core clipping path
(``CLIPPER_ENABLED``, ``LOCAL_LLM_ENABLED``) stays on.
"""
import asyncio

import httpx
import pytest

import feature_flags

# Self-host mode is guaranteed by tests/conftest.py (BILLING_ENABLED=0),
# which runs before any test module can import app — same precondition
# test_mcp_endpoint.py relies on.
import app as app_module
from app import app


ALL_FLAG_NAMES = (
    "CLIPPER_ENABLED", "LOCAL_LLM_ENABLED", "UGC_ENABLED", "TTS_ENABLED",
    "DUBBING_ENABLED", "SOCIAL_PUBLISHING_ENABLED", "GEMINI_VISION_ENABLED",
)


@pytest.fixture(autouse=True)
def _clean_flag_env(monkeypatch):
    """Every test starts from nobody having set any of these — defaults
    only — so one test's monkeypatch can never leak into the next."""
    for name in ALL_FLAG_NAMES:
        monkeypatch.delenv(name, raising=False)
    yield


# --- feature_flags.py itself ------------------------------------------------

class TestDefaults:
    def test_core_pipeline_flags_default_on(self):
        assert feature_flags.enabled("CLIPPER_ENABLED") is True
        assert feature_flags.enabled("LOCAL_LLM_ENABLED") is True

    @pytest.mark.parametrize("name", [
        "UGC_ENABLED", "TTS_ENABLED", "DUBBING_ENABLED",
        "SOCIAL_PUBLISHING_ENABLED", "GEMINI_VISION_ENABLED",
    ])
    def test_out_of_scope_flags_default_off(self, name):
        assert feature_flags.enabled(name) is False

    def test_cloud_billing_mirrors_billing_enabled_not_a_second_switch(self, monkeypatch):
        monkeypatch.setenv("BILLING_ENABLED", "0")
        assert feature_flags.enabled("CLOUD_BILLING_ENABLED") is False
        monkeypatch.setenv("BILLING_ENABLED", "1")
        assert feature_flags.enabled("CLOUD_BILLING_ENABLED") is True
        # Setting a same-named CLOUD_BILLING_ENABLED env var must do nothing —
        # there is deliberately no such env var, only the BILLING_ENABLED alias.
        monkeypatch.setenv("CLOUD_BILLING_ENABLED", "0")
        assert feature_flags.enabled("CLOUD_BILLING_ENABLED") is True


class TestParsing:
    @pytest.mark.parametrize("raw", ["1", "true", "True", "TRUE", "yes", "on"])
    def test_truthy_strings_turn_an_off_by_default_flag_on(self, monkeypatch, raw):
        monkeypatch.setenv("UGC_ENABLED", raw)
        assert feature_flags.enabled("UGC_ENABLED") is True

    @pytest.mark.parametrize("raw", ["0", "false", "False", "no", "off"])
    def test_falsy_strings_turn_an_on_by_default_flag_off(self, monkeypatch, raw):
        monkeypatch.setenv("CLIPPER_ENABLED", raw)
        assert feature_flags.enabled("CLIPPER_ENABLED") is False

    def test_unrecognised_value_falls_back_to_the_default_rather_than_guessing(self, monkeypatch):
        monkeypatch.setenv("UGC_ENABLED", "maybe")
        assert feature_flags.enabled("UGC_ENABLED") is False  # default for this flag
        monkeypatch.setenv("CLIPPER_ENABLED", "maybe")
        assert feature_flags.enabled("CLIPPER_ENABLED") is True  # default for this flag

    def test_empty_string_is_treated_as_unset(self, monkeypatch):
        monkeypatch.setenv("UGC_ENABLED", "")
        assert feature_flags.enabled("UGC_ENABLED") is False

    def test_unknown_flag_name_is_a_programming_error_not_a_silent_default(self):
        with pytest.raises(ValueError):
            feature_flags.enabled("NOT_A_REAL_FLAG")


class TestDisabledDetail:
    def test_shape_matches_the_codebase_structured_error_convention(self):
        detail = feature_flags.disabled_detail("UGC_ENABLED")
        assert detail == {
            "error": "FEATURE_DISABLED",
            "feature": "UGC_ENABLED",
            "message": detail["message"],  # just confirming the key exists
        }
        assert "UGC_ENABLED=true" in detail["message"]

    def test_custom_message_is_used_verbatim(self):
        detail = feature_flags.disabled_detail("TTS_ENABLED", "custom text")
        assert detail["message"] == "custom text"
        assert detail["feature"] == "TTS_ENABLED"


class TestAllFlags:
    def test_includes_every_flag_and_the_billing_alias(self):
        flags = feature_flags.all_flags()
        for name in ALL_FLAG_NAMES + ("CLOUD_BILLING_ENABLED",):
            assert name in flags
        # Matches enabled() exactly — no second source of truth drifting apart.
        for name, value in flags.items():
            assert value == feature_flags.enabled(name)


# --- wired into app.py: each route refuses at the backend, not just the UI -

def _request(method, path, **kwargs):
    async def _run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
            return await client.request(method, path, **kwargs)
    return asyncio.run(_run())


def _assert_feature_disabled(resp, flag):
    assert resp.status_code == 403, resp.text
    detail = resp.json()["detail"]
    assert detail["error"] == "FEATURE_DISABLED"
    assert detail["feature"] == flag


class TestBackendRefusesByDefault:
    """No env var is set for any of these (the autouse fixture guarantees
    it) — this is what a plain ``git clone`` + run looks like. Each route
    must refuse with FEATURE_DISABLED before doing any other work (job
    lookups, key checks), which is also what proves the gate runs first."""

    def test_ugc_gallery(self):
        _assert_feature_disabled(_request("GET", "/api/saasshorts/gallery"), "UGC_ENABLED")

    def test_ugc_status(self):
        _assert_feature_disabled(_request("GET", "/api/saasshorts/status/x"), "UGC_ENABLED")

    def test_tts_voices(self):
        _assert_feature_disabled(_request("GET", "/api/saasshorts/voices"), "TTS_ENABLED")

    def test_dubbing_languages(self):
        _assert_feature_disabled(_request("GET", "/api/translate/languages"), "DUBBING_ENABLED")

    def test_dubbing_translate(self):
        resp = _request("POST", "/api/translate", json={
            "job_id": "nonexistent", "clip_index": 0, "target_language": "es",
        })
        _assert_feature_disabled(resp, "DUBBING_ENABLED")

    def test_social_post(self):
        resp = _request("POST", "/api/social/post", json={
            "job_id": "nonexistent", "clip_index": 0, "platforms": ["tiktok"],
        })
        _assert_feature_disabled(resp, "SOCIAL_PUBLISHING_ENABLED")

    def test_social_user(self):
        _assert_feature_disabled(_request("GET", "/api/social/user"), "SOCIAL_PUBLISHING_ENABLED")

    def test_saasshorts_post_requires_both_ugc_and_social_flags(self):
        # UGC_ENABLED is checked first in saasshorts_post_to_socials, so with
        # neither flag set it is UGC_ENABLED that fires.
        resp = _request("POST", "/api/saasshorts/post", json={
            "job_id": "nonexistent", "platforms": ["tiktok"],
        })
        _assert_feature_disabled(resp, "UGC_ENABLED")

    def test_gemini_vision_edit(self):
        resp = _request("POST", "/api/edit", json={"job_id": "nonexistent", "clip_index": 0})
        _assert_feature_disabled(resp, "GEMINI_VISION_ENABLED")

    def test_gemini_vision_effects(self):
        resp = _request("POST", "/api/effects/generate", json={"job_id": "nonexistent", "clip_index": 0})
        _assert_feature_disabled(resp, "GEMINI_VISION_ENABLED")

    def test_process_stays_enabled_by_default(self):
        """CLIPPER_ENABLED defaults to True — the core pipeline must NOT be
        gated off out of the box. (A real call still needs a file/url and a
        key/local-LLM, so this isn't a 200, just not a feature-flag 403.)"""
        resp = _request("POST", "/api/process", data={})
        if resp.status_code == 403:
            assert resp.json()["detail"].get("feature") != "CLIPPER_ENABLED"

    def test_process_can_be_explicitly_turned_off(self, monkeypatch):
        monkeypatch.setenv("CLIPPER_ENABLED", "false")
        resp = _request("POST", "/api/process", data={})
        _assert_feature_disabled(resp, "CLIPPER_ENABLED")


class TestBackendAllowsWhenEnabled:
    """Flipping the flag on must make the gate step aside — any failure
    after that point is a *different*, pre-existing check (missing job,
    missing key), proving the feature flag isn't masking those."""

    def test_dubbing_languages_now_succeeds(self, monkeypatch):
        monkeypatch.setenv("DUBBING_ENABLED", "true")
        resp = _request("GET", "/api/translate/languages")
        assert resp.status_code == 200
        assert "languages" in resp.json()

    def test_ugc_gallery_no_longer_feature_disabled(self, monkeypatch):
        monkeypatch.setenv("UGC_ENABLED", "true")
        resp = _request("GET", "/api/saasshorts/gallery")
        assert not (resp.status_code == 403 and resp.json().get("detail", {}).get("error") == "FEATURE_DISABLED")

    def test_social_post_now_fails_on_the_job_check_not_the_flag(self, monkeypatch):
        monkeypatch.setenv("SOCIAL_PUBLISHING_ENABLED", "true")
        resp = _request("POST", "/api/social/post", json={
            "job_id": "nonexistent-job", "clip_index": 0, "platforms": ["tiktok"],
        })
        assert resp.status_code != 403

    def test_gemini_vision_edit_now_fails_on_the_job_or_key_check(self, monkeypatch):
        monkeypatch.setenv("GEMINI_VISION_ENABLED", "true")
        resp = _request("POST", "/api/edit", json={"job_id": "nonexistent", "clip_index": 0})
        assert not (resp.status_code == 403 and resp.json().get("detail", {}).get("error") == "FEATURE_DISABLED")


# --- local-LLM master switch ------------------------------------------------

class TestLocalLlmEnabled:
    def test_disabling_forces_the_gemini_path_even_with_llm_base_url_set(self, monkeypatch):
        monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434/v1")
        monkeypatch.setenv("LOCAL_LLM_ENABLED", "false")
        import llm_backend
        assert llm_backend.active() is False

    def test_enabled_by_default_with_llm_base_url_set(self, monkeypatch):
        monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434/v1")
        import llm_backend
        assert llm_backend.active() is True

    def test_no_effect_without_llm_base_url(self, monkeypatch):
        monkeypatch.delenv("LLM_BASE_URL", raising=False)
        import llm_backend
        assert llm_backend.active() is False


# --- Gemini-vision pipeline call sites (main.py / layout_picker / screencast_layout / hook_grounding) --

class TestGeminiVisionPipelineCallSites:
    """These run inside the main.py subprocess, not through app.py's HTTP
    layer, so they're tested by calling the functions directly."""

    def test_layout_picker_pick_returns_none_without_vision_enabled(self, monkeypatch):
        monkeypatch.setenv("AUTO_LAYOUT", "1")  # ENABLED=True
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key-present")
        import importlib
        import layout_picker
        importlib.reload(layout_picker)
        assert layout_picker.ENABLED is True
        result = layout_picker.pick("does-not-matter.mp4", 30.0)
        assert result == "none"

    def test_screencast_detect_returns_empty_without_vision_enabled(self, monkeypatch):
        monkeypatch.setenv("SCREENCAST_LAYOUT", "1")  # ENABLED=True
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key-present")
        import importlib
        import screencast_layout
        importlib.reload(screencast_layout)
        assert screencast_layout.ENABLED is True
        result = screencast_layout.detect_content_ranges("does-not-matter.mp4", [(0, 1)], 30)
        assert result == []

    def test_hook_grounding_reground_skips_without_vision_enabled(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key-present")
        import hook_grounding
        result = hook_grounding.reground("does-not-matter.mp4", {}, {}, 0, 1)
        assert result is None

    def test_get_visual_clips_fails_clearly_without_vision_enabled(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key-present")
        import main
        result = main.get_visual_clips("does-not-matter.mp4", 30.0)
        assert result is None
