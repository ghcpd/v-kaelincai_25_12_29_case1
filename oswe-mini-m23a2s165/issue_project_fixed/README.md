# issue_project_fixed — Image Compression API (fixed)

This repository contains a fixed version of the Flask image-compression API that previously crashed with MemoryError on large uploads.

What was fixed
- Enforced `MAX_CONTENT_LENGTH` (16 MB)
- Added pre-processing per-file size validation (10 MB)
- Checked image dimensions (max 25 megapixels)
- Caught `MemoryError` and returned HTTP 413 with friendly JSON
- Improved error handling and logging

How to run

1. Create and activate a virtual environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Run tests

```powershell
pytest -v
```

3. Run the server (development)

```powershell
python src/app.py
```

API behavior
- POST /compress: compresses uploaded image (returns image/jpeg) or returns 413/400 on errors
- GET /health: returns service health

Design notes
- Pre-checks prevent loading large files into memory
- Pillow's Image.open is used to inspect image headers (cheap) before compression
- MemoryError is handled gracefully and mapped to 413
