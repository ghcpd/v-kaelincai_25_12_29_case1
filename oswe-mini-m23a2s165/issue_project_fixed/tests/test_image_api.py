"""
Integration tests for the fixed Image Compression API
All tests should pass against the fixed implementation.
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


def create_test_image(width=1000, height=1000, format="JPEG"):
    img = Image.new("RGB", (width, height), color="red")
    img_io = io.BytesIO()
    img.save(img_io, format=format)
    img_io.seek(0)
    return img_io


def create_dummy_file_of_size(size_bytes):
    """Create a BytesIO that reports a given size (contains non-image bytes).
    This is used to exercise the file-size checks without allocating huge images.
    """
    b = io.BytesIO()
    b.write(b"0" * size_bytes)
    b.seek(0)
    return b


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"


def test_compress_small_image_success(client):
    img_data = create_test_image(100, 100)

    response = client.post(
        "/compress",
        data={"file": (img_data, "test_small.jpg")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.mimetype == "image/jpeg"


def test_compress_medium_image_success(client):
    img_data = create_test_image(1000, 1000)

    response = client.post(
        "/compress",
        data={"file": (img_data, "test_medium.jpg")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.mimetype == "image/jpeg"


def test_compress_large_image_returns_413(client):
    # Create a dummy file larger than the configured per-file limit (10MB)
    large_bytes = 12 * 1024 * 1024
    big_file = create_dummy_file_of_size(large_bytes)

    response = client.post(
        "/compress",
        data={"file": (big_file, "test_large.jpg")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 413
    data = response.get_json()
    assert data is not None
    assert "error" in data
    assert "too large" in data["error"].lower()


def test_compress_extremely_large_file_validation(client):
    # Simulate an even larger upload (just checking validation path)
    huge_bytes = 20 * 1024 * 1024
    huge_file = create_dummy_file_of_size(huge_bytes)

    response = client.post(
        "/compress",
        data={"file": (huge_file, "test_extremely_large.jpg")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 413
    data = response.get_json()
    assert "error" in data


def test_compress_no_file_provided(client):
    response = client.post("/compress", data={})

    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "no file" in data["error"].lower()


def test_compress_empty_filename(client):
    img_data = create_test_image(100, 100)

    response = client.post(
        "/compress",
        data={"file": (img_data, "")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


def test_compress_with_custom_quality(client):
    img_data = create_test_image(100, 100)

    response = client.post(
        "/compress",
        data={"file": (img_data, "test.jpg"), "quality": "50"},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.mimetype == "image/jpeg"
