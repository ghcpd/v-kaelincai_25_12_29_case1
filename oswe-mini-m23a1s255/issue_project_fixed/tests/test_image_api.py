"""
Integration tests for the fixed Image Compression API
All tests must pass without xfail markers. Large uploads are simulated
with byte payloads to avoid consuming excessive test runner memory.
"""

import io
import pytest
from PIL import Image
from src.app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def create_test_image(width=100, height=100, format="JPEG"):
    img = Image.new("RGB", (width, height), color="red")
    img_io = io.BytesIO()
    img.save(img_io, format=format)
    img_io.seek(0)
    return img_io


def test_health_check(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "healthy"


def test_compress_small_image_success(client):
    img = create_test_image(100, 100)
    r = client.post(
        "/compress",
        data={"file": (img, "small.jpg")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 200
    assert r.mimetype == "image/jpeg"


def test_compress_medium_image_success(client):
    img = create_test_image(1000, 1000)
    r = client.post(
        "/compress",
        data={"file": (img, "medium.jpg")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 200
    assert r.mimetype == "image/jpeg"


def test_compress_large_image_rejected(client):
    """Simulate a large upload (just over the 10MB limit) and expect 413."""
    large_payload = io.BytesIO(b"0" * (11 * 1024 * 1024))
    r = client.post(
        "/compress",
        data={"file": (large_payload, "large.jpg")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 413
    data = r.get_json()
    assert data is not None and "error" in data
    # message may vary; ensure it communicates size limit
    msg = data.get("message", "").lower()
    assert ("mb" in msg) or ("too" in msg) or ("limit" in msg)


def test_compress_extremely_large_image_validation(client):
    """Another oversized payload test to ensure validation happens early."""
    huge = io.BytesIO(b"x" * (20 * 1024 * 1024))
    r = client.post(
        "/compress",
        data={"file": (huge, "huge.jpg")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 413
    data = r.get_json()
    assert data.get("error") in {"file_too_large", "payload_too_large"}


def test_compress_no_file_provided(client):
    r = client.post("/compress", data={})
    assert r.status_code == 400
    assert "no_file" in r.get_json().get("error", "")


def test_compress_empty_filename(client):
    img = create_test_image(50, 50)
    r = client.post(
        "/compress",
        data={"file": (img, "")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_compress_with_custom_quality(client):
    img = create_test_image(100, 100)
    r = client.post(
        "/compress",
        data={"file": (img, "q.jpg"), "quality": "50"},
        content_type="multipart/form-data",
    )
    assert r.status_code == 200
    assert r.mimetype == "image/jpeg"
