"""
Integration tests for the fixed Image Compression API
"""

import io
import pytest
from PIL import Image
from src.app import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def create_test_image(width=1000, height=1000, format='JPEG'):
    img = Image.new('RGB', (width, height), color='red')
    img_io = io.BytesIO()
    img.save(img_io, format=format)
    img_io.seek(0)
    return img_io


def pad_file_to_size(fobj, target_size_bytes):
    """Pad an existing file-like object with zeros to reach target size."""
    fobj.seek(0, io.SEEK_END)
    current = fobj.tell()
    if current < target_size_bytes:
        fobj.write(b"\0" * (target_size_bytes - current))
    fobj.seek(0)
    return fobj


def test_health_check(client):
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'


def test_compress_small_image_success(client):
    img_data = create_test_image(100, 100)
    response = client.post(
        '/compress',
        data={'file': (img_data, 'test_small.jpg')},
        content_type='multipart/form-data'
    )
    assert response.status_code == 200
    assert response.mimetype == 'image/jpeg'


def test_compress_medium_image_success(client):
    img_data = create_test_image(1000, 1000)
    response = client.post(
        '/compress',
        data={'file': (img_data, 'test_medium.jpg')},
        content_type='multipart/form-data'
    )
    assert response.status_code == 200
    assert response.mimetype == 'image/jpeg'


def test_compress_large_file_rejected_by_size(client):
    # Create a valid small image and pad it to exceed the MAX_FILE_SIZE (10MB)
    img_data = create_test_image(1000, 1000)
    padded = pad_file_to_size(img_data, 11 * 1024 * 1024)

    response = client.post(
        '/compress',
        data={'file': (padded, 'test_large.jpg')},
        content_type='multipart/form-data'
    )

    assert response.status_code == 413
    data = response.get_json()
    assert 'error' in data
    assert 'too large' in data['error'].lower()


def test_compress_extremely_large_image_validation(client):
    # Ensure very large images by dimensions are rejected (simulate by monkeypatching Image.open)
    # We'll create a small image but monkeypatch Image.open to report a huge size
    from PIL import Image as PILImage

    original_open = PILImage.open

    def fake_open(stream):
        class FakeImage:
            size = (20000, 20000)
            def convert(self, *args, **kwargs):
                return self
            def save(self, *args, **kwargs):
                pass
            def close(self):
                pass
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc, tb):
                return False
        return FakeImage()

    try:
        PILImage.open = fake_open
        img_data = create_test_image(100, 100)
        response = client.post(
            '/compress',
            data={'file': (img_data, 'test_extremely_large.jpg')},
            content_type='multipart/form-data'
        )
        assert response.status_code == 413
        data = response.get_json()
        assert 'error' in data
        assert 'resolution' in data['error'].lower() or 'too high' in data['error'].lower()
    finally:
        PILImage.open = original_open


def test_compress_no_file_provided(client):
    response = client.post('/compress', data={})
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert 'no file' in data['error'].lower()


def test_compress_empty_filename(client):
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
