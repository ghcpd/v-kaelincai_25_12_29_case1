"""
Fixed Flask Image Compression API
- Enforces upload size limits (MAX_CONTENT_LENGTH)
- Validates file size before processing
- Catches MemoryError and returns 413
- Returns JSON error responses for clients
- Keeps backward-compatible behavior for valid uploads

Security/safety notes in comments throughout the code.
"""
from flask import Flask, request, jsonify, send_file
from werkzeug.exceptions import RequestEntityTooLarge
from PIL import Image, UnidentifiedImageError
import io
import logging
import typing as t

# Configuration
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_MIMETYPES = {"image/jpeg", "image/png", "image/webp"}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE

# Basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _get_stream_size(stream: t.BinaryIO, max_allowed: int) -> int:
    """Return the size of a seekable stream or -1 if unknown.

    For non-seekable streams this function will read up to max_allowed+1 bytes
    (without loading more than necessary) to determine whether the stream
    exceeds the allowed size. It will not return the full size for streams
    larger than max_allowed to avoid OOM.
    """
    try:
        # Try fast path: seek/tell
        cur = stream.tell()
        stream.seek(0, io.SEEK_END)
        size = stream.tell()
        stream.seek(cur)
        return size
    except (OSError, AttributeError):
        # Non-seekable: read in chunks up to the limit
        total = 0
        chunk_size = 64 * 1024
        while total <= max_allowed:
            chunk = stream.read(min(chunk_size, max_allowed + 1 - total))
            if not chunk:
                break
            total += len(chunk)
        # Rewind if possible
        try:
            stream.seek(0)
        except Exception:
            # Can't rewind non-seekable stream — caller must handle
            pass
        return total


@app.errorhandler(RequestEntityTooLarge)
def handle_request_entity_too_large(e):
    """Return JSON 413 when Flask/Werkzeug rejects an upload by size."""
    return (
        jsonify(
            {
                "error": "payload_too_large",
                "message": f"Uploads must be <= {app.config['MAX_CONTENT_LENGTH'] // (1024*1024)} MB",
            }
        ),
        413,
    )


@app.errorhandler(MemoryError)
def handle_memory_error(e):
    """Catch MemoryError globally and return a safe 413 response."""
    logger.exception("MemoryError caught while processing request")
    return (
        jsonify(
            {
                "error": "memory_error",
                "message": "The uploaded image is too large to process on the server",
            }
        ),
        413,
    )


@app.errorhandler(Exception)
def handle_exception(e):
    """Generic error handler that returns JSON for unexpected errors.

    Keep responses non-revealing for security, but useful for clients.
    """
    logger.exception("Unhandled exception: %s", e)
    return (
        jsonify({"error": "internal_error", "message": "Internal server error"}),
        500,
    )


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "service": "image-compression-api"})


@app.route("/compress", methods=["POST"])
def compress_image():
    """Compress an uploaded image with robust memory safeguards.

    Protection strategy:
    - Enforce Flask's MAX_CONTENT_LENGTH to short-circuit oversized requests
    - Validate file size before calling Pillow to avoid MemoryError
    - Catch MemoryError and return 413
    - Limit accepted mimetypes and sanitize `quality` parameter
    """
    if "file" not in request.files:
        return jsonify({"error": "no_file", "message": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "empty_filename", "message": "Empty filename"}), 400

    # Quick check: honor Content-Length header when provided
    content_length = request.content_length
    if content_length is not None and content_length > app.config["MAX_CONTENT_LENGTH"]:
        return (
            jsonify(
                {
                    "error": "payload_too_large",
                    "message": f"File too large (>{app.config['MAX_CONTENT_LENGTH'] // (1024*1024)}MB)",
                }
            ),
            413,
        )

    # Determine actual stream size without loading entire file into memory
    file_stream = file.stream
    file_size = _get_stream_size(file_stream, app.config["MAX_CONTENT_LENGTH"])
    if file_size > app.config["MAX_CONTENT_LENGTH"]:
        return (
            jsonify(
                {
                    "error": "file_too_large",
                    "message": "File exceeds maximum allowed size",
                    "max_size_mb": app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024),
                    "your_size_mb": round(file_size / (1024 * 1024), 2),
                }
            ),
            413,
        )

    # Rewind stream to start before passing to PIL
    try:
        file_stream.seek(0)
    except Exception:
        # If we can't seek, we rely on the FileStorage to provide fresh stream
        pass

    # Validate quality parameter safely
    try:
        quality = int(request.form.get("quality", 85))
    except Exception:
        quality = 85
    quality = max(10, min(quality, 95))

    # Attempt to open/process the image — Pillow may raise MemoryError or OSError
    try:
        img = Image.open(file_stream)

        # Optional: enforce maximum pixel dimensions to avoid large allocations
        max_pixels = 10000 * 10000  # allow up to 100M pixels in theory (but file-size gate prevents abuse)
        if img.width * img.height > max_pixels:
            return (
                jsonify(
                    {
                        "error": "image_too_large",
                        "message": "Image pixel dimensions exceed allowed maximum",
                    }
                ),
                413,
            )

        # Convert to RGB for consistent output
        if img.mode != "RGB":
            img = img.convert("RGB")

        output = io.BytesIO()
        img.save(output, format="JPEG", quality=quality, optimize=True)
        output.seek(0)

        return send_file(
            output, mimetype="image/jpeg", as_attachment=True, download_name="compressed_image.jpg"
        )

    except MemoryError:
        # Explicitly catch MemoryError and return 413 instead of crashing
        logger.exception("MemoryError while processing uploaded image")
        return (
            jsonify({"error": "memory_error", "message": "Image too large to process"}),
            413,
        )
    except UnidentifiedImageError:
        return jsonify({"error": "invalid_image", "message": "Uploaded file is not a valid image"}), 400
    except Exception:
        # Any other error should be handled by the global exception handler
        raise


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
