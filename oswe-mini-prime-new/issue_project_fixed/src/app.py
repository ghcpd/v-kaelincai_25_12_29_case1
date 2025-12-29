"""
Fixed Flask Image Compression API
- Configured upload size limits
- Pre-processing file size validation
- Proper MemoryError and general exception handling
- Dimension checks to avoid loading extremely large images
"""

from flask import Flask, request, jsonify, send_file
from werkzeug.exceptions import RequestEntityTooLarge
from PIL import Image
import io
import os
import logging

app = Flask(__name__)

# Configure a reasonable maximum request size to protect memory (16MB)
# Flask/Werkzeug will automatically respond with 413 if request body exceeds this.
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

# Application-level limits
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB - enforce before processing
MAX_PIXELS = 25_000_000  # 25 megapixels - protect against huge dimensions

# Configure logging
logging.basicConfig(level=logging.INFO)


@app.errorhandler(RequestEntityTooLarge)
def handle_request_entity_too_large(e):
    """Return JSON 413 when Flask/Werkzeug rejects oversized requests."""
    return jsonify({
        "error": "Payload too large",
        "message": "The uploaded file is too large. Maximum total request size is 16MB."
    }), 413


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "service": "image-compression-api"})


@app.route('/compress', methods=['POST'])
def compress_image():
    """Compress an uploaded image with safety checks to prevent MemoryError.

    Steps:
    - Validate presence of file
    - Check filename
    - Check raw file size before attempting any PIL operations
    - Open image and check dimensions before heavy processing
    - Catch MemoryError and return 413
    - Return helpful error messages and appropriate HTTP codes
    """

    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400

    # Pre-check raw file size without loading image into memory
    try:
        file.stream.seek(0, os.SEEK_END)
        file_size = file.stream.tell()
        file.stream.seek(0)
    except Exception:
        # If stream doesn't support seek/tell, proceed carefully
        file_size = None

    if file_size is not None and file_size > MAX_FILE_SIZE:
        return jsonify({
            "error": "File too large",
            "max_size_mb": MAX_FILE_SIZE // (1024 * 1024),
            "your_size_mb": round(file_size / (1024 * 1024), 2)
        }), 413

    # Attempt to open the image and validate dimensions without forcing full decode
    try:
        with Image.open(file.stream) as img:
            width, height = img.size

            # Check pixel count to avoid excessive memory use on decompression
            if width * height > MAX_PIXELS:
                return jsonify({
                    "error": "Image resolution too high",
                    "max_pixels": MAX_PIXELS,
                    "your_pixels": width * height
                }), 413

            # Get compression quality (clamped to reasonable range)
            try:
                quality = int(request.form.get('quality', 85))
            except Exception:
                quality = 85

            quality = max(10, min(95, quality))

            # Convert and save compressed image to BytesIO
            output = io.BytesIO()

            # Use convert('RGB') to ensure compatibility when saving as JPEG
            img_converted = img.convert('RGB')
            img_converted.save(output, format='JPEG', quality=quality, optimize=True)
            output.seek(0)

            return send_file(
                output,
                mimetype='image/jpeg',
                as_attachment=True,
                download_name='compressed_image.jpg'
            )

    except MemoryError:
        app.logger.error("MemoryError while processing image", exc_info=True)
        return jsonify({
            "error": "Image too large to process",
            "message": "The uploaded image requires more memory than is available. Please upload a smaller file."
        }), 413
    except Exception as e:
        # Log and return a user-friendly error
        app.logger.exception("Error processing image: %s", e)
        return jsonify({"error": "Failed to process image", "message": str(e)}), 400


@app.route('/compress-safe', methods=['POST'])
def compress_image_safe():
    """A convenience endpoint that uses the same safe logic as /compress.

    Kept for compatibility/testing; delegates to the same logic.
    """
    return compress_image()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
