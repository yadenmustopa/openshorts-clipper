"""Centralized feature flags for the Clipper fork's out-of-scope surface.

The default pipeline (ingest, transcribe, scene-detect, local-LLM moment
scoring, cut, reframe, subtitle, hook overlay) stays on. Everything the
project's PRD marks as a non-goal for the MVP — AI UGC generation, TTS,
dubbing, social auto-publishing, Gemini vision calls, cloud billing — is
off by default and refused at the backend (not just hidden in the UI).

Flags are read from the environment so the same binary/image serves every
deployment; a flag is never hidden behind a config file this fork would
need to maintain in parallel. ``CLOUD_BILLING_ENABLED`` is deliberately an
alias for the existing upstream ``BILLING_ENABLED`` (see ``app.py``) rather
than a second, independent switch — the billing surface already has its
own authoritative gate (``cloud.setup_sync`` only mounts billing routes
when ``BILLING_ENABLED`` is set; see ``docs/LICENSE_AUDIT.md``), and two
flags controlling the same thing is how they drift out of sync.

Every stage that runs inside the ``main.py`` subprocess (layout picking,
screencast detection, silent-video analysis, hook grounding) reads these
same environment variables directly — ``app.py``'s ``child_env()`` already
copies the full environment (minus its secrets denylist) into that
subprocess, so a flag set for the API process reaches the pipeline process
for free, no extra plumbing needed.
"""
from __future__ import annotations

import os
from typing import Optional

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}

# name -> (env var, default). CLOUD_BILLING_ENABLED is handled separately
# below since it mirrors BILLING_ENABLED instead of owning its own env var.
_FLAGS: dict[str, tuple[str, bool]] = {
    "CLIPPER_ENABLED": ("CLIPPER_ENABLED", True),
    "LOCAL_LLM_ENABLED": ("LOCAL_LLM_ENABLED", True),
    "UGC_ENABLED": ("UGC_ENABLED", False),
    "TTS_ENABLED": ("TTS_ENABLED", False),
    "DUBBING_ENABLED": ("DUBBING_ENABLED", False),
    "SOCIAL_PUBLISHING_ENABLED": ("SOCIAL_PUBLISHING_ENABLED", False),
    "GEMINI_VISION_ENABLED": ("GEMINI_VISION_ENABLED", False),
}

# Human-readable blurb per flag, reused by both the HTTP error detail and
# the dashboard config payload so the two never say something different.
DESCRIPTIONS: dict[str, str] = {
    "CLIPPER_ENABLED": "the core clipping pipeline",
    "LOCAL_LLM_ENABLED": "the local-LLM moment picker",
    "UGC_ENABLED": "AI UGC video generation (AI actors, text/image-to-video)",
    "TTS_ENABLED": "text-to-speech voice synthesis",
    "DUBBING_ENABLED": "AI voice dubbing/translation",
    "SOCIAL_PUBLISHING_ENABLED": "social/YouTube auto-publishing",
    "GEMINI_VISION_ENABLED": "Gemini-powered visual analysis (layout picking, screencast detection, silent-video clipping, AI video effects, thumbnail analysis)",
    "CLOUD_BILLING_ENABLED": "cloud billing",
}


def _parse_bool(raw: Optional[str], default: bool) -> bool:
    if raw is None or raw.strip() == "":
        return default
    val = raw.strip().lower()
    if val in _TRUE:
        return True
    if val in _FALSE:
        return False
    return default


def enabled(flag: str) -> bool:
    """Whether ``flag`` is on. Unknown flag names are a programming error,
    not a silent False, so they raise rather than fail open or closed by
    accident."""
    if flag == "CLOUD_BILLING_ENABLED":
        return os.environ.get("BILLING_ENABLED", "").lower() in ("1", "true", "yes")
    try:
        env_var, default = _FLAGS[flag]
    except KeyError:
        raise ValueError(f"Unknown feature flag: {flag!r}")
    return _parse_bool(os.environ.get(env_var), default)


def all_flags() -> dict[str, bool]:
    """Every flag's current value, for the dashboard config endpoint and
    for tests. Keeps the UI and the backend reading the exact same source."""
    names = list(_FLAGS.keys()) + ["CLOUD_BILLING_ENABLED"]
    return {name: enabled(name) for name in names}


def disabled_detail(flag: str, message: Optional[str] = None) -> dict:
    """The structured error body every gated surface (HTTP, MCP via its
    pass-through of HTTPException.detail, CLI via the same JSON) returns
    when ``flag`` is off. Shape matches this codebase's existing
    ``payment_required``/``post_requires_plan`` convention: a dict with a
    stable ``error`` code plus a human message, not a bare string."""
    what = DESCRIPTIONS.get(flag, flag)
    return {
        "error": "FEATURE_DISABLED",
        "feature": flag,
        "message": message or (
            f"{what} is disabled in this deployment. "
            f"Set {flag}=true to turn it on."
        ),
    }
