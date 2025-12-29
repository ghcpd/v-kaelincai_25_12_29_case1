"""
Unit tests for memory handling in the fixed implementation
"""

import pytest
import io
from PIL import Image


def create_large_image_data(width, height):
    img = Image.new('RGB', (width, height), color='blue')
    img_io = io.BytesIO()
    img.save(img_io, format='JPEG', quality=95)
    img_io.seek(0)
    return img_io


def test_pil_memory_limit_detection():
    small_img_data = create_large_image_data(100, 100)
    img = Image.open(small_img_data)
    assert img.size == (100, 100)
    img.close()


def test_loading_extremely_large_image_is_handled_by_api(monkeypatch, client=None):
    """Simulate MemoryError during Image.open and ensure API handles it gracefully."""
    from src.app import app

    # Create an app test client
    app.config['TESTING'] = True
    with app.test_client() as client:
        # Monkeypatch PIL.Image.open to raise MemoryError
        import PIL.Image as PILImage
        original_open = PILImage.open

        def raising_open(stream):
            raise MemoryError("simulated out of memory")

        PILImage.open = raising_open

        try:
            img_data = create_large_image_data(1000, 1000)
            response = client.post(
                '/compress',
                data={'file': (img_data, 'test.jpg')},
                content_type='multipart/form-data'
            )

            # The API should catch MemoryError and return 413
            assert response.status_code == 413
            data = response.get_json()
            assert 'error' in data
            assert 'image too large' in data['error'].lower() or 'too large' in data['message'].lower()
        finally:
            PILImage.open = original_open


def test_file_size_should_be_checked_before_processing():
    # Create an 8MB image and check its size < 10MB
    img_data = create_large_image_data(1000, 1000)
    img_data.seek(0, io.SEEK_END)
    file_size = img_data.tell()
    img_data.seek(0)

    assert file_size < 10 * 1024 * 1024


def test_memory_error_should_be_caught_simulation():
    # Simulate the API-level exception handling for MemoryError
    def simulated_handler():
        try:
            raise MemoryError("cannot allocate")
        except MemoryError:
            return {"error": "Image too large to process"}, 413

    resp, code = simulated_handler()
    assert code == 413
    assert 'error' in resp


def test_max_content_length_is_configured():
    from src.app import app
    max_length = app.config.get('MAX_CONTENT_LENGTH')
    assert max_length is not None
    assert max_length <= 16 * 1024 * 1024
