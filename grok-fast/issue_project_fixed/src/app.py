"""
Flask Image Compression API - FIXED VERSION
A simple API for compressing uploaded images with proper memory protection.

✅ FIXED: Memory protection implemented - large images handled gracefully
"""

from flask import Flask, request, jsonify, send_file
from PIL import Image
import io
import os

app = Flask(__name__)

# ✅ FIX #1: Set reasonable upload size limit to prevent abuse
# Before: MAX_CONTENT_LENGTH = None (no limit)
# After: 16MB limit - Flask will automatically reject larger requests with 413
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "image-compression-api"})


@app.route('/compress', methods=['POST'])
def compress_image():
    """
    Compress an uploaded image and return the compressed version.

    ✅ FIXED: Now includes proper memory protection and error handling
    - File size validation before processing
    - MemoryError handling with user-friendly messages
    - Appropriate HTTP status codes (413 for too large, 400 for other errors)
    """

    # Check if file is present in request
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400

    # ✅ FIX #2: Add pre-processing file size validation
    # Check file size before attempting to load into memory
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit for processing

    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    if file_size > MAX_FILE_SIZE:
        return jsonify({
            "error": "File too large",
            "message": f"File size {round(file_size / (1024 * 1024), 2)}MB exceeds maximum allowed size of {MAX_FILE_SIZE // (1024 * 1024)}MB",
            "max_size_mb": MAX_FILE_SIZE // (1024 * 1024),
            "file_size_mb": round(file_size / (1024 * 1024), 2)
        }), 413

    try:
        # Load the image (now safe due to size validation above)
        img = Image.open(file.stream)

        # Optional: Check image dimensions as additional safety
        MAX_PIXELS = 25_000_000  # 25 megapixels
        if img.width * img.height > MAX_PIXELS:
            return jsonify({
                "error": "Image resolution too high",
                "message": f"Image dimensions {img.width}x{img.height} ({img.width * img.height} pixels) exceed maximum allowed resolution",
                "max_pixels": MAX_PIXELS,
                "your_pixels": img.width * img.height
            }), 413

        # Get compression quality from request (default 85)
        quality = int(request.form.get('quality', 85))
        if quality < 1 or quality > 100:
            quality = 85

        # Compress the image
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)

        return send_file(
            output,
            mimetype='image/jpeg',
            as_attachment=True,
            download_name='compressed_image.jpg'
        )

    # ✅ FIX #3: Proper exception handling for MemoryError and other errors
    except MemoryError:
        # Handle memory allocation failures gracefully
        return jsonify({
            "error": "Image too large to process",
            "message": "The uploaded image exceeds available memory. Please upload a smaller file or reduce the image resolution."
        }), 413

    except Exception as e:
        # Check if this is PIL's decompression bomb protection
        error_str = str(e).lower()
        if "decompression bomb" in error_str or "exceeds limit" in error_str:
            return jsonify({
                "error": "Image too large to process",
                "message": "The uploaded image is too large or complex to process safely. Please upload a smaller file."
            }), 413

        # Log the error for debugging
        app.logger.error(f"Error processing image: {str(e)}")
        # Return user-friendly error message
        return jsonify({
            "error": "Failed to process image",
            "message": f"Unable to process the uploaded image: {str(e)}"
        }), 400


@app.route('/compress-safe', methods=['POST'])
def compress_image_safe():
    """
    A safer version that includes basic file size checking.
    This endpoint demonstrates the proper implementation pattern.
    """
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit

    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']

    # Read file to check size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    if file_size > MAX_FILE_SIZE:
        return jsonify({
            "error": "File too large",
            "max_size_mb": MAX_FILE_SIZE // (1024 * 1024),
            "your_size_mb": round(file_size / (1024 * 1024), 2)
        }), 413

    # Process with size limit...
    return jsonify({"message": "This endpoint validates file size but delegates to main endpoint"}), 501


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)