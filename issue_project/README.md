# Image Compression API - Memory Overflow Issue Demo

## Overview

This is a minimal Flask web application that demonstrates a **memory overflow vulnerability** in an image processing API. The application provides an endpoint for compressing uploaded images, but it contains intentionally planted bugs that cause `MemoryError` crashes when users upload very large images.

## Project Structure

```
issue_project/
├── src/
│   ├── __init__.py
│   └── app.py                 # Flask API with memory issue
├── tests/
│   ├── __init__.py
│   ├── test_image_api.py      # Integration tests (2 failing)
│   └── test_memory_handling.py # Unit tests (4 failing)
├── data/
│   └── .gitkeep
├── requirements.txt
├── README.md
├── KNOWN_ISSUE.md
└── .gitignore
```

## Technology Stack

- **Language**: Python 3.8+
- **Framework**: Flask 3.0.0
- **Image Processing**: Pillow (PIL) 10.1.0
- **Testing**: pytest 7.4.3
- **Platform**: Windows 11 (cross-platform compatible)

## The Planted Issue

### Problem Type
**Python Runtime Error - Uncaught MemoryError Exception**

### Issue Summary
The `/compress` endpoint attempts to load entire uploaded images into memory without any size validation or proper error handling. When users upload extremely large images (e.g., 100MB+ high-resolution photos), PIL's `Image.open()` triggers a `MemoryError`, causing the API to crash and return HTTP 500 errors.

### Specific Problems

1. **No file size limit** (Line 14 in `src/app.py`)
   - `app.config['MAX_CONTENT_LENGTH'] = None`
   
2. **No pre-processing size validation** (Lines 38-44 in `src/app.py`)
   - File is opened directly without checking size
   
3. **Inadequate exception handling** (Lines 58-62 in `src/app.py`)
   - Generic `except Exception` re-raises `MemoryError` instead of handling it gracefully

### Trigger Conditions

- Upload image file > 50MB (size varies based on available system memory)
- High-resolution images (e.g., 10000x10000 pixels or larger)
- Multiple concurrent large uploads (exhausts memory faster)

### Expected vs Actual Behavior

**Expected:**
- API validates file size before processing
- Returns HTTP 413 (Payload Too Large) for oversized files
- Catches `MemoryError` and returns user-friendly error message
- Service remains stable for other users

**Actual:**
- No file size validation
- PIL attempts to load entire image into memory
- `MemoryError` is raised and re-thrown
- API returns HTTP 500 (Internal Server Error)
- Service may crash or hang

## Quick Start

### 1. Install Dependencies

```powershell
# Create virtual environment (recommended)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Tests to See the Issues

```powershell
# Run all tests (6 will fail, demonstrating the bugs)
pytest -v

# Run only integration tests
pytest tests/test_image_api.py -v

# Run only memory handling tests
pytest tests/test_memory_handling.py -v

# Run with detailed output
pytest -v -s
```

### 3. Run the API Server (Optional)

```powershell
# Start the Flask development server
python src/app.py
```

Then test manually:
```powershell
# Health check
curl http://localhost:5000/health

# Upload a small image (works fine)
curl -X POST -F "file=@small_image.jpg" http://localhost:5000/compress -o compressed.jpg

# Upload a large image (triggers MemoryError)
# Note: This will crash the endpoint
curl -X POST -F "file=@large_image.jpg" http://localhost:5000/compress
```

## Test Results

The project includes **6 automated tests**, with **6 expected to fail** (marked with `@pytest.mark.xfail`), demonstrating the planted bugs:

### Integration Tests (`test_image_api.py`)

1. ✅ `test_health_check` - Passes
2. ✅ `test_compress_small_image_success` - Passes  
3. ✅ `test_compress_medium_image_success` - Passes
4. ❌ `test_compress_large_image_causes_memory_error` - **Fails (demonstrates bug)**
5. ❌ `test_compress_extremely_large_image_validation` - **Fails (demonstrates bug)**
6. ✅ `test_compress_no_file_provided` - Passes
7. ✅ `test_compress_empty_filename` - Passes
8. ✅ `test_compress_with_custom_quality` - Passes

### Unit Tests (`test_memory_handling.py`)

1. ✅ `test_pil_memory_limit_detection` - Passes
2. ❌ `test_loading_extremely_large_image_without_validation` - **Fails (demonstrates bug)**
3. ❌ `test_file_size_should_be_checked_before_processing` - **Fails (demonstrates bug)**
4. ❌ `test_memory_error_should_be_caught` - **Fails (demonstrates bug)**
5. ❌ `test_max_content_length_is_not_configured` - **Fails (demonstrates bug)**

## Issue Details

See [KNOWN_ISSUE.md](KNOWN_ISSUE.md) for:
- Detailed problem analysis
- Root cause explanation
- Fix recommendations (implementation not included)
- References to specific code locations

## Key Files

- **[src/app.py](src/app.py)**: Main Flask application with planted memory bugs
  - Line 14: `MAX_CONTENT_LENGTH = None` (no upload limit)
  - Lines 38-44: No file size validation in `compress_image()`
  - Lines 58-62: Inadequate exception handling
  
- **[tests/test_image_api.py](tests/test_image_api.py)**: Integration tests showing API behavior with various file sizes

- **[tests/test_memory_handling.py](tests/test_memory_handling.py)**: Unit tests isolating the memory handling issues

## Development Notes

- This is a **demonstration project** with intentional bugs
- Do NOT use this code in production
- The bugs are simple and well-documented for educational purposes
- A safer (but incomplete) endpoint exists at `/compress-safe` (not implemented)

## License

MIT License - Educational/Demo Purpose Only

---

**⚠️ WARNING**: This application contains intentional security and stability issues. It is designed for testing, education, and bug demonstration purposes only.
