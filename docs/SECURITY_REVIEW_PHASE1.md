# Security Review — Phase 1 changes

Scope: everything introduced on `feat/phase-1-local-first-pipeline` since
it branched from upstream (`946087d..326b031`) — `feature_flags.py`, the
26 `require_feature()` call sites in `app.py`, the 4
`feature_flags.enabled("GEMINI_VISION_ENABLED")` call sites in
`main.py`/`layout_picker.py`/`screencast_layout.py`/`hook_grounding.py`,
`tests/fixtures/fetch_fixtures.sh`, and the dashboard changes
(`App.jsx`, `ResultCard.jsx`, `AuthContext.jsx`). Pre-existing upstream
code is out of scope (per PRD §J: a full upstream security review is a
separate, not-yet-run item — see `docs/UPSTREAM_AUDIT.md` §4).

Methodology: a dedicated review pass checking for command injection, path
traversal, authZ/gate bypass, secret leakage, and injection/code-execution
risk, specifically targeting the categories named in the user's directive
(path traversal, command injection, API-key leakage, secret scanning,
file-input validation) plus standard OWASP categories.

## Result: no high-confidence findings (>80% exploitability)

Specifically verified:

1. **Gate coverage is complete, not partial.** Every route under
   `/api/saasshorts/*`, `/api/translate*`, `/api/social/*`,
   `/api/thumbnail/publish*`, `/api/edit`, `/api/effects/generate`,
   `/api/thumbnail/analyze`, `/api/thumbnail/generate`, and `/api/process`
   that reaches UGC/TTS/dubbing/social-publishing/Gemini-vision code has a
   `require_feature(...)` call. The few thumbnail routes left ungated
   (`/api/thumbnail/upload`, `/titles`, `/frames/{id}`, `/describe`) are
   local transcription / text-only refinement / local frame extraction —
   not vision analysis, UGC, dubbing, or publishing — a scoping choice,
   not a missed gate, and they still require a Gemini key via the
   pre-existing `resolve_gemini`.
2. **Gate placement is first, not racy.** In every modified handler,
   `require_feature(...)` is the first statement in the function body,
   before any file read, entitlement reservation, job lookup, or key
   resolution — no case where a side effect happens before the check.
3. **Fails closed on a typo.** `feature_flags.enabled()` raises
   `ValueError` on an unknown flag name rather than silently treating it
   as disabled or enabled; every call site passes a name that exists in
   `_FLAGS`.
4. **No bypass via MCP/CLI.** `mcp_server.py`'s `publish_clip` tool and
   `process_video` tool call the real HTTP endpoints (`/api/social/post`,
   `/api/process`), not internal Python functions directly — they inherit
   the gate, they can't route around it.
5. **No secret/path/stack-trace leakage in the new error path.**
   `feature_flags.disabled_detail()` returns only a static per-flag
   description string and the flag name in the 403 body — nothing from
   the request, environment, or filesystem.
6. **`fetch_fixtures.sh` has no injection surface.** Every `yt-dlp`/
   `ffmpeg`/`curl` invocation uses hardcoded, author-controlled URLs and
   fixed flags (`-t 90`, a fixed resolution filter) — no variable is
   interpolated into a shell command or command argument. It is also a
   `tests/` fixture-prep script that the user runs manually, not something
   reachable from a network request.
7. **Dashboard changes are render-only.** `features.*` gates only which
   buttons/tabs render; no `dangerouslySetInnerHTML` or equivalent sink
   was touched, and `features` comes from the trusted `/api/config`
   response, not from user input. The backend re-enforces independently
   regardless of what the UI shows (point 1-4 above), so even a
   compromised/bypassed frontend cannot reach a disabled feature.
8. **No change to `cloud/`.** Its own `BILLING_ENABLED` gate (the route
   doesn't exist at all without it) is untouched and is a stronger
   control than anything added here.

## What this review does not cover

- A full security pass over pre-existing upstream code (secret scanning
  beyond a manual check, dependency scanning beyond `npm audit`,
  path-traversal testing of routes this PR didn't touch) — tracked as a
  pre-existing open item in `docs/UPSTREAM_AUDIT.md` §4, not resolved by
  this review.
- Anything introduced in a later phase (Phase 2 HyperFrames render
  pipeline gets its own review once it exists).
