"""Iteration 10 — Gallery backend tests"""
import io
import os
import pytest
import requests
from PIL import Image

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback: read frontend/.env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "admin", "password": "admin"}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def _jpeg_bytes(w=32, h=32, color=(120, 180, 255)):
    im = Image.new("RGB", (w, h), color)
    b = io.BytesIO()
    im.save(b, format="JPEG")
    return b.getvalue()


def _png_bytes(w=24, h=24, color=(50, 200, 50)):
    im = Image.new("RGB", (w, h), color)
    b = io.BytesIO()
    im.save(b, format="PNG")
    return b.getvalue()


created_ids = []


class TestGalleryUpload:
    def test_upload_no_token(self):
        r = requests.post(f"{BASE_URL}/api/admin/gallery",
                          files={"file": ("t.jpg", _jpeg_bytes(), "image/jpeg")}, timeout=60)
        assert r.status_code in (401, 403)

    def test_upload_jpeg(self, auth_headers):
        data = _jpeg_bytes()
        r = requests.post(f"{BASE_URL}/api/admin/gallery",
                          headers=auth_headers,
                          files={"file": ("test.jpg", data, "image/jpeg")},
                          data={"caption": "TEST jpeg"}, timeout=90)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["kind"] == "image"
        assert j["content_type"] == "image/jpeg"
        assert j["caption"] == "TEST jpeg"
        assert j["size"] == len(data) or j["size"] > 0
        assert j["width"] == 32 and j["height"] == 32
        assert "id" in j and "order" in j and "created_at" in j
        created_ids.append(j["id"])

    def test_upload_png(self, auth_headers):
        data = _png_bytes()
        r = requests.post(f"{BASE_URL}/api/admin/gallery",
                          headers=auth_headers,
                          files={"file": ("test.png", data, "image/png")}, timeout=90)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["kind"] == "image"
        assert j["content_type"] == "image/png"
        created_ids.append(j["id"])

    def test_upload_text_rejected(self, auth_headers):
        r = requests.post(f"{BASE_URL}/api/admin/gallery",
                          headers=auth_headers,
                          files={"file": ("bad.txt", b"hello", "text/plain")}, timeout=30)
        assert r.status_code == 400


class TestGalleryPublic:
    def test_list_public(self):
        r = requests.get(f"{BASE_URL}/api/gallery", timeout=30)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        assert len(items) >= 2
        orders = [it["order"] for it in items]
        assert orders == sorted(orders), f"Not sorted asc: {orders}"

    def test_file_serve(self):
        r = requests.get(f"{BASE_URL}/api/gallery/{created_ids[0]}/file", timeout=30)
        assert r.status_code == 200
        assert r.headers.get("Content-Type", "").startswith("image/jpeg")
        assert "Cache-Control" in r.headers
        assert len(r.content) > 0

    def test_file_unknown(self):
        r = requests.get(f"{BASE_URL}/api/gallery/nonexistent-id/file", timeout=30)
        assert r.status_code == 404


class TestGalleryPatch:
    def test_patch_caption(self, auth_headers):
        r = requests.patch(f"{BASE_URL}/api/admin/gallery/{created_ids[0]}",
                           headers=auth_headers, json={"caption": "Sunset"}, timeout=30)
        assert r.status_code == 200
        assert r.json()["caption"] == "Sunset"

    def test_patch_empty(self, auth_headers):
        r = requests.patch(f"{BASE_URL}/api/admin/gallery/{created_ids[0]}",
                           headers=auth_headers, json={}, timeout=30)
        assert r.status_code == 400

    def test_patch_unknown(self, auth_headers):
        r = requests.patch(f"{BASE_URL}/api/admin/gallery/nonexistent-id",
                           headers=auth_headers, json={"caption": "x"}, timeout=30)
        assert r.status_code == 404


class TestGalleryReorder:
    def test_reorder(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/gallery", timeout=30)
        ids = [it["id"] for it in r.json()]
        reversed_ids = list(reversed(ids))
        r2 = requests.post(f"{BASE_URL}/api/admin/gallery/reorder",
                           headers=auth_headers, json={"ids": reversed_ids}, timeout=30)
        assert r2.status_code == 200
        r3 = requests.get(f"{BASE_URL}/api/gallery", timeout=30)
        new_items = r3.json()
        # only items in reversed_ids will have updated orders 0..n-1
        for i, it in enumerate(new_items):
            assert it["order"] == i


class TestGalleryDelete:
    def test_delete_and_verify(self, auth_headers):
        # delete the 2nd created item (keep the first for cleanup + existing 'Test vol du matin')
        target = created_ids[1]
        r = requests.delete(f"{BASE_URL}/api/admin/gallery/{target}", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        assert r.json().get("ok") is True

        r2 = requests.get(f"{BASE_URL}/api/gallery", timeout=30)
        assert target not in [it["id"] for it in r2.json()]

        r3 = requests.get(f"{BASE_URL}/api/gallery/{target}/file", timeout=30)
        assert r3.status_code == 404

        r4 = requests.delete(f"{BASE_URL}/api/admin/gallery/{target}", headers=auth_headers, timeout=30)
        assert r4.status_code == 404


@pytest.fixture(scope="module", autouse=True)
def cleanup(auth_headers):
    yield
    # Cleanup uploaded jpeg (test item); keep the existing 'Test vol du matin'
    for i in created_ids[:1]:
        try:
            requests.delete(f"{BASE_URL}/api/admin/gallery/{i}", headers=auth_headers, timeout=15)
        except Exception:
            pass
