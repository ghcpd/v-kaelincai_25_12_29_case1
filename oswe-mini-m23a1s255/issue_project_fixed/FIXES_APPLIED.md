# FIXES_APPLIED — issue_project_fixed

Summary
- Fixed memory-overflow vulnerabilities and added size validation and robust error handling.

What was wrong
1. `MAX_CONTENT_LENGTH` was set to `None` allowing arbitrary uploads.
2. `compress_image()` did not validate incoming file size before calling `PIL.Image.open()`.
3. `MemoryError` was not handled and bubbled up causing 500 crashes.
4. No JSON error responses for oversized payloads (client unfriendly).

What I changed (files & key changes)

- `src/app.py`
  - Set `app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024` (10MB).
  - Implemented `_get_stream_size()` to check stream size without OOM.
  - Validate `request.content_length` and stream size before calling Pillow.
  - Catch `MemoryError` and return HTTP 413 with a JSON error body.
  - Added `RequestEntityTooLarge` and generic error handlers returning JSON.
  - Sanitised `quality` parameter and limited pixel-dimension allocations.

- `tests/` (both files)
  - Removed `@pytest.mark.xfail` markers and updated tests to assert the
    corrected behavior.
  - Large uploads are simulated with byte streams slightly over the limit
    to avoid creating extremely large in-memory images during tests.
  - Added a test that monkeypatches `PIL.Image.open` to simulate `MemoryError`
    and assert the API returns HTTP 413 instead of crashing.

Why these fixes
- Pre-validating sizes prevents expensive allocations inside Pillow.
- Using Flask/Werkzeug's MAX_CONTENT_LENGTH provides a first-line defense.
- Explicitly handling MemoryError and RequestEntityTooLarge prevents 500
  responses and gives clients actionable error messages.

Testing
- All tests in `tests/` are passing locally in the development environment used
  to make these changes. They verify both happy-path compression and the
  failure modes (oversized upload, invalid images, MemoryError handling).

Further recommendations
- For production: move hard limits to configuration (env var), add
  virus/malware scanning for uploads, and consider server-side streaming
  processing or offloading to a worker for very large images.

Contact
- Fix implemented by: automated assistant
- Date: 2025-12-29
