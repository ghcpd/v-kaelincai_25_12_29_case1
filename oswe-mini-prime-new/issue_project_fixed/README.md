# issue_project_fixed

This is a fixed version of the Flask Image Compression API that addresses memory overflow issues when processing large image uploads.

Highlights:
- Enforces `MAX_CONTENT_LENGTH = 16MB` at Flask config level (returns HTTP 413 for large requests)
- Validates file size before image processing (`MAX_FILE_SIZE = 10MB`)
- Checks image dimensions (`MAX_PIXELS = 25_000_000`) before heavy processing
- Catches `MemoryError` and returns a helpful 413 response
- Returns clear JSON error messages with proper HTTP status codes

How to run tests:

```powershell
cd issue_project_fixed
pip install -r requirements.txt
pytest -v
```
