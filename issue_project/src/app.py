"""
Flask Image Compression API
A simple API for compressing uploaded images.

⚠️ KNOWN ISSUE: No memory protection - large images cause MemoryError crashes
"""

from flask import Flask, request, jsonify, send_file
from PIL import Image
import io
import os

app = Flask(__name__)

# ISSUE: No file size limit configured!
# This allows users to upload extremely large files that will crash the server
app.config['MAX_CONTENT_LENGTH'] = None  # Deliberately set to None (no limit)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "image-compression-api"})


@app.route('/compress', methods=['POST'])
def compress_image():
    """
    Compress an uploaded image and return the compressed version.
    
    ⚠️ ISSUE: This function has NO error handling for MemoryError!
    When a very large image is uploaded, PIL.Image.open() will try to load
    the entire image into memory, potentially causing MemoryError.
    
    Expected behavior: Should validate file size and handle errors gracefully
    Actual behavior: Crashes with 500 error when processing large images
    """
    
    # Check if file is present in request
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400
    
    # ISSUE #1: No file size validation before processing!
    # We should check file size here before attempting to load it
    
    try:
        # ISSUE #2: No exception handling for MemoryError!
        # Image.open() loads the entire image into memory
        # For very large images (100MB+), this will raise MemoryError
        img = Image.open(file.stream)
        
        # Get compression quality from request (default 85)
        quality = int(request.form.get('quality', 85))
        
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
    
    except Exception as e:
        # ISSUE #3: Generic exception handling doesn't distinguish MemoryError
        # This will catch MemoryError but doesn't handle it appropriately
        # The error message is not user-friendly and returns 500
        raise  # Re-raises the exception, causing 500 error


@app.route('/compress-safe', methods=['POST'])
def compress_image_safe():
    """
    A safer version that includes basic file size checking.
    This is NOT implemented in the main endpoint (intentional bug).
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
    return jsonify({"message": "This endpoint is safe but not used"}), 501


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
