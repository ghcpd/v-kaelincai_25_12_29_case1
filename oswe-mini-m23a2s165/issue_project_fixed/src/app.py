"""
Fixed Flask Image Compression API
- Adds MAX_CONTENT_LENGTH configuration
- Validates file size before processing
- Catches MemoryError and returns HTTP 413
- Provides clear, user-friendly error responses
- Maintains backward compatibility for valid requests
"""
from flask import Flask, request, jsonify, send_file
from PIL import Image, UnidentifiedImageError
import io
import os
import logging

app = Flask(__name__)

# Security / safety: enforce a reasonable maximum upload size for the whole request
# Flask will return a 413 if the Content-Length header exceeds this value.
# Keep this larger than our per-file pre-check to allow for multipart overhead.
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

# Per-file maximum accepted size (pre-processing check)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
# Maximum allowed pixel count to avoid huge decompressed images
MAX_PIXELS = 25_000_000  # 25 megapixels (e.g. ~5000x5000)

# Configure logging for easier debugging in production
logging.basicConfig(level=logging.INFO)


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "service": "image-compression-api"})


def _get_file_size(file_storage):
    """Return the size (in bytes) of the uploaded file stream without changing
    the stream position for the caller.
    Works with Werkzeug's FileStorage and io.BytesIO-like objects.
    """
    stream = file_storage.stream
    try:
        current = stream.tell()
        stream.seek(0, os.SEEK_END)
        size = stream.tell()
        stream.seek(current)
        return size
    except (AttributeError, OSError):
        # If the stream doesn't support seeking, fall back to reading into memory
        data = stream.read()
        size = len(data)
        stream.seek(0)
        return size


@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "Payload too large", "message": "Request payload exceeds limit."}), 413


@app.route("/compress", methods=["POST"])
def compress_image():
    # Basic request validations
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    # Pre-processing file size validation (protects against large uploads)
    file_size = _get_file_size(file)
    if file_size > MAX_FILE_SIZE:
        return (
            jsonify({
                "error": "File too large",
                "max_size_mb": MAX_FILE_SIZE // (1024 * 1024),
                "your_size_mb": round(file_size / (1024 * 1024), 2),
            }),
            413,
        )

    # Attempt to open image in a safe context and check dimensions before heavy processing
    try:
        # Pillow's Image.open reads headers first; it will not decompress the whole image
        # until operations that require pixel data are performed. This allows us to
        # validate image dimensions without allocating large image buffers.
        img = Image.open(file.stream)
        width, height = img.size

        if width * height > MAX_PIXELS:
            img.close()
            return (
                jsonify(
                    {
                        "error": "Image resolution too high",
                        "max_pixels": MAX_PIXELS,
                        "your_pixels": width * height,
                    }
                ),
                413,
            )

        # Compression — save into an in-memory BytesIO buffer
        quality = int(request.form.get("quality", 85))
        output = io.BytesIO()
        # Convert to RGB to ensure JPEG compatibility
        if img.mode in ("RGBA", "LA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])  # 3 is the alpha channel
            save_img = background
        else:
            save_img = img.convert("RGB")

        save_img.save(output, format="JPEG", quality=quality, optimize=True)
        output.seek(0)
        img.close()

        return send_file(
            output, mimetype="image/jpeg", as_attachment=True, download_name="compressed_image.jpg"
        )

    except MemoryError:
        # Out-of-memory during image processing — handle gracefully
        app.logger.error("MemoryError while processing image")
        return (
            jsonify(
                {
                    "error": "Image too large to process",
                    "message": "The uploaded image requires more memory than available; please upload a smaller file.",
                }
            ),
            413,
        )
    except UnidentifiedImageError:
        return jsonify({"error": "Invalid image file"}), 400
    except Exception as e:
        app.logger.exception("Unexpected error while processing image")
        return jsonify({"error": "Failed to process image", "message": str(e)}), 400


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
