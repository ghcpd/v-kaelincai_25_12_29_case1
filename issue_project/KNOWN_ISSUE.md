# Known Issue: Memory Overflow in Image Compression API

## Issue Summary

**Type**: Python Runtime Error - Uncaught `MemoryError` Exception  
**Severity**: High (Service Availability Impact)  
**Status**: Unfixed (Intentionally Planted for Demonstration)

## Problem Description

The Flask image compression API crashes with `MemoryError` when users upload very large images (e.g., 100MB+ high-resolution files). This causes HTTP 500 errors and can affect service availability for all users, especially in single-process deployments.

## Root Causes

### 1. Missing Upload Size Limit

**Location**: `src/app.py`, line 14

```python
app.config['MAX_CONTENT_LENGTH'] = None  # Deliberately set to None (no limit)
```

**Problem**: Flask's built-in upload size limiting is disabled, allowing arbitrarily large file uploads that can exhaust server memory.

**Impact**: Users can upload multi-gigabyte files that the server will attempt to process.

---

### 2. No Pre-Processing File Size Validation

**Location**: `src/app.py`, lines 38-46 in `compress_image()`

```python
try:
    # ISSUE: No file size check here!
    img = Image.open(file.stream)  # Loads entire image into memory
```

**Problem**: The function directly calls `PIL.Image.open()` without first checking the file size. PIL loads the entire decompressed image into memory, which for a 100MB JPEG could require 500MB+ of RAM.

**Impact**: Large images cause immediate memory allocation failures.

---

### 3. Inadequate Exception Handling

**Location**: `src/app.py`, lines 58-62 in `compress_image()`

```python
except Exception as e:
    # Generic exception handling doesn't distinguish MemoryError
    raise  # Re-raises the exception, causing 500 error
```

**Problem**: 
- Generic `except Exception` catches `MemoryError` but doesn't handle it appropriately
- The exception is re-raised, causing Flask to return HTTP 500
- No user-friendly error message
- No logging or recovery mechanism

**Impact**: Poor user experience and difficult debugging.

---

## Trigger Conditions

The issue can be reproduced when:

1. User uploads an image file larger than available server memory
2. Typical trigger sizes:
   - JPEG/PNG > 50-100MB (varies by available RAM)
   - Uncompressed images > 20MB
   - Dimensions > 10000x10000 pixels
3. Multiple concurrent large uploads exhaust memory faster
4. Server has limited memory (e.g., 512MB container)

## Observed Behavior

### User Experience
- Upload request hangs or times out
- Receives HTTP 500 Internal Server Error
- No meaningful error message
- Subsequent requests may also fail if service crashed

### Server Side
- Python process attempts to allocate large memory block
- `MemoryError: cannot allocate memory for image` raised
- Exception propagates uncaught to Flask error handler
- Process may crash or become unstable
- Other concurrent requests may be affected

### Logs
```
MemoryError: cannot allocate memory for image
[2025-12-29 10:15:32] ERROR in app: Exception on /compress [POST]
Traceback (most recent call last):
  File "src/app.py", line 44, in compress_image
    img = Image.open(file.stream)
  ...
MemoryError: cannot allocate memory for image
```

## Test Evidence

The following tests demonstrate the issue:

1. **`test_compress_large_image_causes_memory_error`** (test_image_api.py)
   - Creates 10000x10000 pixel image (~300MB uncompressed)
   - Expected: HTTP 413 or graceful error
   - Actual: MemoryError raised

2. **`test_compress_extremely_large_image_validation`** (test_image_api.py)
   - Creates 15000x15000 pixel image (~675MB uncompressed)
   - Expected: HTTP 413 with validation error
   - Actual: No size validation, crashes

3. **`test_loading_extremely_large_image_without_validation`** (test_memory_handling.py)
   - Directly tests PIL behavior with 20000x20000 image
   - Demonstrates MemoryError at Image.open() call
   - Shows missing pre-validation

4. **`test_file_size_should_be_checked_before_processing`** (test_memory_handling.py)
   - Verifies absence of size checking code
   - Confirms no validation between file receipt and processing

5. **`test_memory_error_should_be_caught`** (test_memory_handling.py)
   - Tests exception handling logic
   - Confirms MemoryError is re-raised instead of handled

6. **`test_max_content_length_is_not_configured`** (test_memory_handling.py)
   - Verifies Flask config issue
   - Confirms MAX_CONTENT_LENGTH is None

## Recommended Fixes

### Fix #1: Set Upload Size Limit

**File**: `src/app.py`, line 14

```python
# Before (buggy):
app.config['MAX_CONTENT_LENGTH'] = None

# After (fixed):
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit
```

**Benefit**: Flask automatically rejects requests exceeding this size with HTTP 413.

---

### Fix #2: Add Pre-Processing File Size Validation

**File**: `src/app.py`, after line 37

```python
# Add after checking file.filename
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Check file size before processing
file.seek(0, os.SEEK_END)
file_size = file.tell()
file.seek(0)

if file_size > MAX_FILE_SIZE:
    return jsonify({
        "error": "File too large",
        "max_size_mb": MAX_FILE_SIZE // (1024 * 1024),
        "file_size_mb": round(file_size / (1024 * 1024), 2)
    }), 413
```

**Benefit**: Validates file size before attempting memory-intensive operations.

---

### Fix #3: Implement Proper Exception Handling

**File**: `src/app.py`, lines 58-62

```python
# Before (buggy):
except Exception as e:
    raise

# After (fixed):
except MemoryError:
    return jsonify({
        "error": "Image too large to process",
        "message": "The uploaded image exceeds available memory. Please upload a smaller file."
    }), 413
except Exception as e:
    # Log the error
    app.logger.error(f"Error processing image: {str(e)}")
    return jsonify({
        "error": "Failed to process image",
        "message": str(e)
    }), 400
```

**Benefit**: Graceful error handling with user-friendly messages.

---

### Fix #4: Optional - Use Image Size Check Without Loading

```python
from PIL import Image

# Check image dimensions without loading entire file
with Image.open(file.stream) as img:
    width, height = img.size
    
    MAX_PIXELS = 25_000_000  # 25 megapixels
    if width * height > MAX_PIXELS:
        return jsonify({
            "error": "Image resolution too high",
            "max_pixels": MAX_PIXELS,
            "your_pixels": width * height
        }), 413
```

**Benefit**: Detects oversized images by dimensions before full load.

---

## Implementation Priority

1. **High Priority**: Fix #1 (Set MAX_CONTENT_LENGTH) - Quick win, prevents worst cases
2. **High Priority**: Fix #3 (Exception handling) - Improves stability
3. **Medium Priority**: Fix #2 (Pre-processing validation) - Better user feedback
4. **Low Priority**: Fix #4 (Dimension check) - Nice to have, additional safety

## Testing Strategy

After implementing fixes:

1. Remove `@pytest.mark.xfail` from failing tests
2. Update assertions to match new behavior
3. All 6 previously failing tests should pass
4. Add new tests for:
   - Correct 413 responses
   - Error message format validation
   - Boundary testing (files just under/over limits)

## References

- PIL Memory Usage: https://pillow.readthedocs.io/en/stable/handbook/concepts.html
- Flask Upload Limits: https://flask.palletsprojects.com/en/latest/patterns/fileuploads/
- HTTP 413 Status Code: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/413

## Additional Notes

- Consider using streaming processing or chunked reading for very large images
- Implement rate limiting to prevent abuse
- Add monitoring/alerting for memory usage
- Consider using background task queue for large file processing
- Deploy with multiple workers to isolate failures

---

**Last Updated**: December 29, 2025  
**Maintainer**: Demo Project (Educational Purpose)
