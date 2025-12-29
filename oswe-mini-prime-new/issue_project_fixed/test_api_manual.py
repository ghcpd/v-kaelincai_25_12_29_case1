#!/usr/bin/env python
"""Manual API test script to verify compress endpoint"""
from PIL import Image
import io
import requests

# Test 1: Small valid image
img = Image.new('RGB', (100, 100), color='red')
buf = io.BytesIO()
img.save(buf, format='JPEG')
buf.seek(0)

r = requests.post('http://127.0.0.1:5000/compress', files={'file': ('test.jpg', buf)})
print(f"Test 1 - Small image: Status={r.status_code}, Type={r.headers.get('Content-Type')}, Size={len(r.content)} bytes")

# Test 2: Large file (simulated by padding)
img2 = Image.new('RGB', (500, 500), color='blue')
buf2 = io.BytesIO()
img2.save(buf2, format='JPEG')
buf2.seek(0, io.SEEK_END)
size = buf2.tell()
buf2.write(b'\0' * (11 * 1024 * 1024 - size))  # Pad to 11MB
buf2.seek(0)

r2 = requests.post('http://127.0.0.1:5000/compress', files={'file': ('large.jpg', buf2)})
print(f"Test 2 - Large file: Status={r2.status_code}, Response={r2.json()}")
