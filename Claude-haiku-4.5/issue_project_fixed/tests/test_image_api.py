"""
Integration tests for the Image Compression API - FIXED VERSION

All tests should pass with the fixed implementation that includes:
1. Proper file size validation
2. Comprehensive exception handling
3. Appropriate HTTP status codes
4. User-friendly error messages
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


def test_compress_large_image_returns_413(client):
    """
    FIXED TEST #1: Large images are now rejected with HTTP 413
    
    FIX: File size validation is now performed before processing.
    The fixed API validates file size and returns 413 Payload Too Large
    instead of attempting to process and causing MemoryError.
    
    Expected behavior: Should return 413 (Payload Too Large) with error message
    """
    # Create a large test image that exceeds the 15MB limit
    # Note: The actual file size depends on compression, so we create a very large image
    # A 6000x6000 PNG typically creates a >15MB file
    img = Image.new('RGB', (6000, 6000), color='red')
    img_io = io.BytesIO()
    # Save as PNG with no compression to ensure file size exceeds limit
    img.save(img_io, format='PNG', compress_level=0)
    img_io.seek(0)
    
    # Check the actual file size
    img_io.seek(0, 2)  # Seek to end
    file_size = img_io.tell()
    img_io.seek(0)  # Reset to start
    
    # Only run test if we actually created a file larger than the limit
    if file_size > 15 * 1024 * 1024:
        response = client.post(
            '/compress',
            data={'file': (img_io, 'test_large.png')},
            content_type='multipart/form-data'
        )
        
        # Fixed: Should return 413 Payload Too Large
        assert response.status_code == 413
        
        # Fixed: Should include helpful error message (response may have content)
        if response.get_json() is not None:
            data = response.get_json()
            assert 'error' in data
            assert 'too large' in data['error'].lower() or 'size' in data['error'].lower()
    else:
        # Test environment doesn't have enough resources, skip
        pytest.skip(f"Could not create large enough file (got {file_size / (1024*1024):.2f}MB, need >15MB)")


def test_compress_extremely_large_image_validation(client):
    """
    FIXED TEST #2: Extremely large images are validated and rejected
    
    FIX: File size validation is performed before attempting to load the image.
    The fixed API returns 413 instead of attempting to process and causing crashes.
    
    Expected behavior: Should validate and reject with 413 Payload Too Large
    """
    # Create a very large image file that exceeds the 15MB limit
    # A 7000x7000 PNG with minimal compression should exceed 15MB
    img = Image.new('RGB', (7000, 7000), color='blue')
    img_io = io.BytesIO()
    img.save(img_io, format='PNG', compress_level=0)
    img_io.seek(0)
    
    # Check the actual file size
    img_io.seek(0, 2)  # Seek to end
    file_size = img_io.tell()
    img_io.seek(0)  # Reset to start
    
    # Only run test if we actually created a file larger than the limit
    if file_size > 15 * 1024 * 1024:
        response = client.post(
            '/compress',
            data={'file': (img_io, 'test_extremely_large.png')},
            content_type='multipart/form-data'
        )
        
        # Fixed: Should validate and reject with 413 Payload Too Large
        assert response.status_code == 413
        
        # Fixed: Should include helpful error message (response may have content)
        if response.get_json() is not None:
            data = response.get_json()
            assert 'error' in data
            assert 'too large' in data['error'].lower() or 'limit' in data['error'].lower()
    else:
        # Test environment doesn't have enough resources, skip
        pytest.skip(f"Could not create large enough file (got {file_size / (1024*1024):.2f}MB, need >15MB)")


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


def test_compress_with_invalid_quality(client):
    """Test that invalid quality parameter is rejected"""
    img_data = create_test_image(100, 100)
    
    # Test quality out of range (>100)
    response = client.post(
        '/compress',
        data={
            'file': (img_data, 'test.jpg'),
            'quality': '150'
        },
        content_type='multipart/form-data'
    )
    
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data


def test_compress_with_non_numeric_quality(client):
    """Test that non-numeric quality parameter is rejected"""
    img_data = create_test_image(100, 100)
    
    response = client.post(
        '/compress',
        data={
            'file': (img_data, 'test.jpg'),
            'quality': 'invalid'
        },
        content_type='multipart/form-data'
    )
    
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
