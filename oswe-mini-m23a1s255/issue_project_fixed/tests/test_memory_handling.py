"""
Unit tests focused on memory handling for the fixed implementation.
These tests avoid allocating huge real images; oversized uploads are
simulated with large byte payloads and MemoryError is simulated via
monkeypatching where needed.
"""

import io
import pytest
from PIL import Image
from src import app as _app


def create_small_image_bytes(width=100, height=100):
    img = Image.new("RGB", (width, height), color="blue")
    b = io.BytesIO()
    img.save(b, format="JPEG")
    b.seek(0)
    return b


def test_pil_small_image_opens_locally():
    small = create_small_image_bytes(100, 100)
    img = Image.open(small)
    assert img.size == (100, 100)
    img.close()


def test_rejects_oversized_payload_before_pillow(client=None):
    """Ensure the app rejects > MAX_UPLOAD_SIZE without calling Pillow."""
    from src.app import app

    with app.test_client() as c:
        big = io.BytesIO(b"0" * (11 * 1024 * 1024))
        r = c.post(
            "/compress",
            data={"file": (big, "big.jpg")},
            content_type="multipart/form-data",
        )
        assert r.status_code == 413
        msg = r.get_json().get("message", "").lower()
        assert ("mb" in msg) or ("too" in msg) or ("limit" in msg)


def test_file_size_should_be_checked_before_processing():
    """Create a payload larger than the configured MAX and assert rejection."""
    from src.app import app

    large = io.BytesIO(b"z" * (12 * 1024 * 1024))
    large.seek(0, io.SEEK_END)
    size = large.tell()
    large.seek(0)

    assert size > 10 * 1024 * 1024

    with app.test_client() as c:
        r = c.post(
            "/compress",
            data={"file": (large, "big.jpg")},
            content_type="multipart/form-data",
        )
        assert r.status_code == 413


def test_memory_error_is_caught_and_translated(monkeypatch):
    """Simulate Pillow raising MemoryError and ensure API returns 413."""
    from src import app

    # Monkeypatch PIL.Image.open to raise MemoryError for this test
    import PIL.Image as _pil_image

    def _fake_open(stream):
        raise MemoryError("simulated out of memory")

    monkeypatch.setattr(_pil_image, "open", _fake_open)

    small = create_small_image_bytes(50, 50)
    with app.test_client() as c:
        r = c.post(
            "/compress",
            data={"file": (small, "img.jpg")},
            content_type="multipart/form-data",
        )
        assert r.status_code == 413
        data = r.get_json()
        assert data.get("error") == "memory_error"


def test_max_content_length_configured():
    from src.app import app
    max_length = app.config.get("MAX_CONTENT_LENGTH")
    assert max_length is not None
    assert max_length == 10 * 1024 * 1024
