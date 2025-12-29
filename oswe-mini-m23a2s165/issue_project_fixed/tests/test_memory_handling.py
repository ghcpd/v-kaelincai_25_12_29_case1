"""
Unit tests focused on memory handling for the fixed API.
All tests should pass and validate the memory-protection behavior.
"""

import io
import pytest
from PIL import Image
from src import app as tested_app


def create_large_image_data(width, height):
    img = Image.new("RGB", (width, height), color="blue")
    img_io = io.BytesIO()
    img.save(img_io, format="JPEG", quality=95)
    img_io.seek(0)
    return img_io


def test_pil_memory_limit_detection():
    small_img_data = create_large_image_data(100, 100)
    img = Image.open(small_img_data)
    assert img.size == (100, 100)
    img.close()


def test_loading_extremely_large_image_without_validation_is_handled(monkeypatch, client=None):
    """Simulate Image.open raising MemoryError and verify API returns 413."""
    from src.app import app

    app.config["TESTING"] = True
    with app.test_client() as client:
        # Monkeypatch PIL.Image.open used by our app to raise MemoryError
        import PIL.Image as PilImage

        monkeypatch.setattr(PilImage, "open", lambda *a, **k: (_ for _ in ()).throw(MemoryError("simulated")))

        # Send a small valid image (the patched Image.open will raise MemoryError)
        small_img = create_large_image_data(100, 100)

        response = client.post(
            "/compress",
            data={"file": (small_img, "test.jpg")},
            content_type="multipart/form-data",
        )

        assert response.status_code == 413
        data = response.get_json()
        assert data is not None
        assert "image too large" in data["error"].lower() or "too large" in data["error"].lower()


def test_file_size_should_be_checked_before_processing():
    from src.app import app

    app.config["TESTING"] = True
    with app.test_client() as client:
        # Create a dummy file that exceeds the per-file MAX_FILE_SIZE (~10MB)
        big_bytes = io.BytesIO(b"0" * (12 * 1024 * 1024))
        response = client.post(
            "/compress",
            data={"file": (big_bytes, "large.jpg")},
            content_type="multipart/form-data",
        )

        assert response.status_code == 413
        data = response.get_json()
        assert "error" in data
        assert "too large" in data["error"].lower()


def test_memory_error_should_be_caught_by_endpoint(monkeypatch):
    # Ensure MemoryError during processing is caught and translated to 413
    from src.app import app

    app.config["TESTING"] = True
    with app.test_client() as client:
        # Patch PIL.Image.open to raise MemoryError
        import PIL.Image as PilImage

        monkeypatch.setattr(PilImage, "open", lambda *a, **k: (_ for _ in ()).throw(MemoryError("simulated")))

        small_img = create_large_image_data(50, 50)
        response = client.post(
            "/compress",
            data={"file": (small_img, "img.jpg")},
            content_type="multipart/form-data",
        )

        assert response.status_code == 413
        data = response.get_json()
        assert data is not None
        assert "image too large" in data["error"].lower() or "too large" in data["error"].lower()


def test_max_content_length_is_configured():
    from src.app import app

    max_length = app.config.get("MAX_CONTENT_LENGTH")
    expected_max_size = 16 * 1024 * 1024
    assert max_length == expected_max_size
