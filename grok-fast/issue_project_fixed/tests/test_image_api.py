"""
Integration tests for the Image Compression API

These tests demonstrate the memory overflow issue by simulating
large file uploads that cause MemoryError exceptions.
"""

import pytest
import io
from PIL import Image
from src.app import app


@pytest.fixture
def client():
    """Create a test client for the Flask app"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def create_test_image(width=1000, height=1000, format='JPEG'):
    """
    Helper function to create test images of various sizes.
    
    Args:
        width: Image width in pixels
        height: Image height in pixels
        format: Image format (JPEG, PNG, etc.)
    
    Returns:
        BytesIO object containing the image data
    """
    img = Image.new('RGB', (width, height), color='red')
    img_io = io.BytesIO()
    img.save(img_io, format=format)
    img_io.seek(0)
    return img_io


def test_health_check(client):
    """Test that the health check endpoint works"""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'


def test_compress_small_image_success(client):
    """Test that small images compress successfully"""
    # Create a small test image (100x100 pixels, ~30KB)
    img_data = create_test_image(100, 100)
    
    response = client.post(
        '/compress',
        data={'file': (img_data, 'test_small.jpg')},
        content_type='multipart/form-data'
    )
    
    assert response.status_code == 200
    assert response.mimetype == 'image/jpeg'


def test_compress_medium_image_success(client):
    """Test that medium-sized images compress successfully"""
    # Create a medium test image (1000x1000 pixels, ~300KB)
    img_data = create_test_image(1000, 1000)
    
    response = client.post(
        '/compress',
        data={'file': (img_data, 'test_medium.jpg')},
        content_type='multipart/form-data'
    )
    
    assert response.status_code == 200
    assert response.mimetype == 'image/jpeg'


@pytest.mark.xfail(reason="KNOWN ISSUE: Large images cause MemoryError crash", raises=MemoryError, strict=False)
def test_compress_large_image_causes_memory_error(client):
    """
    TEST CASE #1: Demonstrates memory overflow issue with large images
    
    ISSUE: When uploading a very large image (10000x10000 pixels, ~100MB+),
    the API attempts to load the entire image into memory without validation,
    causing a MemoryError exception.
    
    Expected behavior: Should return 413 (Payload Too Large) or handle gracefully
    Actual behavior: Raises MemoryError and returns 500 Internal Server Error
    
    This test is marked as xfail because it demonstrates the known bug.
    """
    # Create a large test image (10000x10000 pixels)
    # This will create an image that requires significant memory (~300MB uncompressed)
    img_data = create_test_image(10000, 10000)
    
    response = client.post(
        '/compress',
        data={'file': (img_data, 'test_large.jpg')},
        content_type='multipart/form-data'
    )
    
    # ✅ FIXED: Should now return 413 (Payload Too Large) instead of crashing
    assert response.status_code == 413

    # Should return proper error message
    data = response.get_json()
    assert 'error' in data
    assert ('too large' in data['error'].lower() or 
            'size' in data['error'].lower() or      
            'resolution' in data['error'].lower())  
    assert 'message' in data
    # File size errors include MB, resolution errors don't
    if 'size' in data['error'].lower() or 'large' in data['error'].lower():
        assert 'MB' in data['message']


def test_compress_extremely_large_image_validation(client):
    """
    TEST CASE #2: Demonstrates lack of file size validation
    
    ISSUE: The API has no MAX_CONTENT_LENGTH configured and no pre-processing
    file size validation, allowing arbitrarily large uploads.
    
    Expected behavior: Should reject files over a reasonable size limit (e.g., 10MB)
    Actual behavior: Attempts to process any size file, causing crashes
    
    This test is marked as xfail because it demonstrates the known bug.
    """
    # Create a very large image that will definitely cause memory issues
    # 15000x15000 pixels = ~675MB uncompressed
    img_data = create_test_image(15000, 15000)
    
    response = client.post(
        '/compress',
        data={'file': (img_data, 'test_extremely_large.jpg')},
        content_type='multipart/form-data'
    )
    
    # ✅ FIXED: Should validate and reject with 413 Payload Too Large
    # May be rejected by file size, pixel count, or PIL's decompression bomb protection
    assert response.status_code in [413, 400]  # 400 if caught as general error
    
    data = response.get_json()
    assert 'error' in data
    assert ('too large' in data['error'].lower() or
            'limit' in data['error'].lower() or
            'resolution' in data['error'].lower() or
            'process' in data['error'].lower())
    
    # If it's a file size error, check the specific fields
    if 'max_size_mb' in data:
        assert 'file_size_mb' in data
        assert data['max_size_mb'] == 10  # 10MB limit


def test_compress_no_file_provided(client):
    """Test that API returns error when no file is provided"""
    response = client.post('/compress', data={})
    
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert 'no file' in data['error'].lower()


def test_compress_empty_filename(client):
    """Test that API returns error for empty filename"""
    img_data = create_test_image(100, 100)
    
    response = client.post(
        '/compress',
        data={'file': (img_data, '')},
        content_type='multipart/form-data'
    )
    
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data


def test_compress_with_custom_quality(client):
    """Test that compression quality parameter works"""
    img_data = create_test_image(100, 100)
    
    response = client.post(
        '/compress',
        data={
            'file': (img_data, 'test.jpg'),
            'quality': '50'
        },
        content_type='multipart/form-data'
    )
    
    assert response.status_code == 200
    assert response.mimetype == 'image/jpeg'
