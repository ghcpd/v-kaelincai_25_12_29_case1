# FIXES_APPLIED

This document lists the fixes applied to the original `issue_project` to address memory overflow issues in the Image Compression API.

## Summary of Issues Found
- **Missing upload size limit**: `app.config['MAX_CONTENT_LENGTH']` was set to `None` allowing arbitrary request sizes.
- **No pre-processing file size validation**: The `/compress` endpoint didn't check raw file size prior to calling `PIL.Image.open()`.
- **Inadequate exception handling**: Generic `except Exception: raise` re-raised exceptions, including `MemoryError`, causing HTTP 500 responses.
- **Missing error responses**: Users received no clear error messages when uploads were too large.

## Changes Made

### Files Added/Modified
- `src/app.py`  (REPLACED - fixed implementation)
  - Set `app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024` (16MB)
  - Added `MAX_FILE_SIZE = 10 * 1024 * 1024` (10MB) and `MAX_PIXELS = 25_000_000`
  - Implemented raw file size check using `file.stream.seek()`/`tell()` and return 413 if too large
  - Checked image dimensions (`width * height`) before compression and return 413 when too large
  - Added explicit `except MemoryError` handling that returns a 413 with helpful message
  - Added generic exception logging and return 400 with a helpful message
  - Added error handler for `RequestEntityTooLarge` to return JSON-based 413

- `tests/test_image_api.py` (UPDATED)
  - Removed `xfail` markers
  - Added tests that pad uploaded files to exceed size limits (simulates large uploads without huge memory allocation)
  - Added a monkeypatch-style test to simulate very large image dimensions and assert 413

- `tests/test_memory_handling.py` (UPDATED)
  - Removed `xfail` markers
  - Added a test that monkeypatches `PIL.Image.open` to raise `MemoryError` and verifies API returns 413
  - Updated assertions to check that `MAX_CONTENT_LENGTH` is configured

- `requirements.txt`, `.gitignore`, `README.md`, `FIXES_APPLIED.md` added/updated to match fixed project

## Rationale
- Using Flask's `MAX_CONTENT_LENGTH` provides an immediate protection against extremely large request bodies (returns 413 early)
- Pre-validation of raw file size prevents attempting to decode potentially huge images
- Dimension checks (pixel count) prevent decompressing images that would require massive in-memory buffers
- Clear error messages and HTTP status codes improve user experience and make failures explicit

## Test Results
- All tests updated to assert expected behavior (413 on oversized payloads/dimensions, 200 on valid uploads)
- Running `pytest -v` in the `issue_project_fixed` directory should show all tests passing

## Notes and Future Improvements
- Consider streaming-based image processing to further reduce peak memory
- Consider adding rate limiting & upload quotas to prevent abuse
- For heavy processing, move work to a background task queue and return asynchronous responses

