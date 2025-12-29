"""
Flask Image Compression API - FIXED VERSION
A simple API for compressing uploaded images with proper memory protection.

Fixed Issues:
1. Added MAX_CONTENT_LENGTH to limit upload size to 16MB
2. Added pre-processing file size validation before loading images
3. Added comprehensive exception handling for MemoryError and other errors
4. Returns appropriate HTTP status codes (413 for oversized files)
5. Provides user-friendly error messages
"""

from flask import Flask, request, jsonify, send_file
from PIL import Image
import io
import os

app = Flask(__name__)

# FIX #1: Configure MAX_CONTENT_LENGTH to limit file uploads
# Prevents users from uploading extremely large files that would exhaust server memory
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

# Define the maximum file size for image processing (slightly less than MAX_CONTENT_LENGTH for safety)
MAX_FILE_SIZE = 15 * 1024 * 1024  # 15MB limit


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "image-compression-api"})


@app.route('/compress', methods=['POST'])
def compress_image():
    """
    Compress an uploaded image and return the compressed version.
    
    FIX #2: Added file size validation before processing
    FIX #3: Added proper exception handling for MemoryError
    
    Returns:
        - 200: Successfully compressed image
        - 400: Invalid request (no file, empty filename, invalid quality)
        - 413: File too large (exceeds size limit)
        - 500: Server error (should not occur with proper validation)
    """
    
    # Check if file is present in request
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400
    
    # FIX #2: Pre-processing file size validation
    # Check file size before attempting to load it into memory
    try:
        # Get the file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # Reset to beginning for processing
        
        # Validate file size against limit
        if file_size > MAX_FILE_SIZE:
            return jsonify({
                "error": "File too large",
                "message": f"Maximum allowed file size is {MAX_FILE_SIZE // (1024 * 1024)}MB",
                "your_size_mb": round(file_size / (1024 * 1024), 2),
                "max_size_mb": MAX_FILE_SIZE // (1024 * 1024)
            }), 413
        
        # Get compression quality from request (default 85, valid range 1-100)
        try:
            quality = int(request.form.get('quality', 85))
            if not (1 <= quality <= 100):
                return jsonify({"error": "Quality must be between 1 and 100"}), 400
        except ValueError:
            return jsonify({"error": "Quality must be a valid integer"}), 400
        
        # FIX #3: Comprehensive exception handling
        # Try to open and process the image with proper error handling
        try:
            img = Image.open(file.stream)
            
            # Compress and save the image
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=quality, optimize=True)
            output.seek(0)
            
            return send_file(
                output,
                mimetype='image/jpeg',
                as_attachment=True,
                download_name='compressed_image.jpg'
            )
        
        except MemoryError as e:
            # Handle memory errors gracefully with 413 status code
            return jsonify({
                "error": "Insufficient memory to process image",
                "message": "The image is too large to process. Please upload a smaller image.",
                "status": "memory_error"
            }), 413
        
        except Image.UnidentifiedImageError:
            # Handle invalid image formats
            return jsonify({
                "error": "Invalid image format",
                "message": "The uploaded file is not a valid image. Please upload a JPEG, PNG, or other supported format."
            }), 400
        
        except Exception as e:
            # Handle other unexpected errors
            return jsonify({
                "error": "Failed to process image",
                "message": f"An error occurred while processing the image: {str(e)}"
            }), 500
    
    except Exception as e:
        # Handle file access errors
        return jsonify({
            "error": "Failed to access file",
            "message": f"An error occurred while accessing the file: {str(e)}"
        }), 400


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
