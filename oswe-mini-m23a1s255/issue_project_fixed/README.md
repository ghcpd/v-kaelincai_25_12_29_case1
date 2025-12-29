# issue_project_fixed — Image Compression API (fixed)

This repository contains a fixed version of the Flask Image Compression API that previously had memory-overflow vulnerabilities.

Key fixes
- Enforced upload size limit (10 MB) via Flask `MAX_CONTENT_LENGTH`
- Pre-validation of file size before passing data to Pillow
- Specific handling for `MemoryError` and `RequestEntityTooLarge` (returns 413)
- Clear JSON error responses for clients
- Sanitised `quality` parameter and protected image conversions

How to run

1. Create a virtualenv and install deps:

   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -r requirements.txt

2. Run tests:

   pytest -q

3. Run the app:

   python -m src.app

Behavioral guarantees
- Oversized uploads are rejected with HTTP 413 and a JSON body explaining the limit
- Valid images are compressed and returned as `image/jpeg`
- The server will not crash with MemoryError on oversized uploads

For full change log and rationale see `FIXES_APPLIED.md`.
