"""Playwright acceptance tests for the static US-022 frontend."""

from __future__ import annotations

from dataclasses import dataclass, field
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from socket import socket
import threading
from socketserver import BaseServer
from typing import Iterator

import cv2
import numpy as np
import pytest
from playwright.sync_api import (
    Browser,
    BrowserContext,
    BrowserType,
    Page,
    sync_playwright,
)

from src.vsl.labels import VIETNAMESE_ALPHABET

ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web"

SUCCESS_RESPONSE = {
    "status": "ok",
    "detected": True,
    "letter": "đ",
    "confidence": 0.95,
    "top_k": [{"letter": "đ", "confidence": 0.95}],
    "has_hand": True,
    "has_face": True,
    "model_version": "v1.0",
}


@dataclass
class ApiStub:
    received: threading.Event = field(default_factory=threading.Event)
    release: threading.Event = field(default_factory=threading.Event)
    hold_response: bool = False
    response: dict[str, object] = field(default_factory=lambda: SUCCESS_RESPONSE.copy())
    request_method: str = ""
    request_content_type: str = ""
    request_body: bytes = b""


@dataclass
class LocalSite:
    url: str
    api: ApiStub


def _jpeg_bytes() -> bytes:
    encoded, buffer = cv2.imencode(
        ".jpg", np.zeros((16, 16, 3), dtype=np.uint8)
    )
    assert encoded, "Could not create a JPEG test image"
    return buffer.tobytes()


@pytest.fixture
def test_site() -> Iterator[TestSite]:
    api = ApiStub()
    api.release.set()

    class Handler(SimpleHTTPRequestHandler):
        def __init__(
            self,
            request: socket,
            client_address: tuple[str, int],
            server: BaseServer,
        ) -> None:
            super().__init__(request, client_address, server, directory=str(WEB_ROOT))

        def do_POST(self) -> None:
            content_length = int(self.headers.get("Content-Length", "0"))
            api.request_method = self.command
            api.request_content_type = self.headers.get("Content-Type", "")
            api.request_body = self.rfile.read(content_length)
            api.received.set()

            if api.hold_response and not api.release.wait(timeout=10):
                self.send_error(504, "Test API response was not released")
                return

            body = json.dumps(api.response, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        Handler,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        yield LocalSite(url=f"http://{host}:{port}", api=api)
    finally:
        api.release.set()
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


@pytest.fixture
def page(test_site: LocalSite) -> Iterator[Page]:
    with sync_playwright() as playwright:
        browser: Browser = playwright.chromium.launch(
            args=[
                "--use-fake-device-for-media-stream",
                "--use-fake-ui-for-media-stream",
            ]
        )
        context: BrowserContext = browser.new_context(
            permissions=["camera"],
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()
        config = json.dumps({"apiBaseUrl": test_site.url})
        page.add_init_script(f"window.VSL_CONFIG = {config};")
        try:
            yield page
        finally:
            context.close()
            browser.close()


def _open_site(page: Page, test_site: LocalSite) -> None:
    response = page.goto(test_site.url, wait_until="domcontentloaded")
    assert response is not None and response.status == 200


def test_ac_022_01_upload_sends_file_and_displays_prediction(
    page: Page, test_site: LocalSite
) -> None:
    _open_site(page, test_site)

    page.get_by_label("Chọn ảnh").set_input_files(
        {
            "name": "ban-tay.jpg",
            "mimeType": "image/jpeg",
            "buffer": _jpeg_bytes(),
        }
    )
    assert page.get_by_role("img", name="Ảnh xem trước").is_visible()

    page.get_by_role("button", name="Dự đoán").click()
    result = page.get_by_role("region", name="Kết quả dự đoán")
    result.get_by_text("đ", exact=True).wait_for()

    assert test_site.api.request_method == "POST"
    assert test_site.api.request_content_type.startswith("multipart/form-data;")
    assert b'name="file"' in test_site.api.request_body
    assert b'filename="ban-tay.jpg"' in test_site.api.request_body
    assert "95%" in result.inner_text()


def test_ac_022_02_keeps_loading_and_page_visible_until_cold_start_finishes(
    page: Page, test_site: LocalSite
) -> None:
    _open_site(page, test_site)
    test_site.api.hold_response = True
    test_site.api.release.clear()

    page.get_by_label("Chọn ảnh").set_input_files(
        {
            "name": "ban-tay.jpg",
            "mimeType": "image/jpeg",
            "buffer": _jpeg_bytes(),
        }
    )
    page.get_by_role("button", name="Dự đoán").click()

    assert test_site.api.received.wait(timeout=5), "Frontend did not call /predict"
    loading = page.get_by_role("status")
    assert loading.is_visible()
    assert "Đang xử lý" in loading.inner_text()
    assert page.get_by_role("button", name="Dự đoán").is_visible()
    assert page.get_by_role("alert").count() == 0

    test_site.api.release.set()
    result = page.get_by_role("region", name="Kết quả dự đoán")
    result.get_by_text("đ", exact=True).wait_for()
    assert "95%" in result.inner_text()


def test_tsk_039_camera_capture_creates_preview(
    page: Page, test_site: LocalSite
) -> None:
    _open_site(page, test_site)

    page.get_by_role("button", name="Mở camera").click()
    page.locator("video").wait_for(state="visible")
    page.get_by_role("button", name="Chụp ảnh").click()

    assert page.get_by_role("img", name="Ảnh xem trước").is_visible()


def test_tsk_042_renders_supported_letters_and_fits_small_viewport(
    page: Page, test_site: LocalSite
) -> None:
    _open_site(page, test_site)
    page.set_viewport_size({"width": 375, "height": 812})

    letters = page.get_by_role(
        "list", name="23 ký tự được hỗ trợ"
    ).get_by_role("listitem").all_text_contents()

    assert letters == list(VIETNAMESE_ALPHABET)
    assert page.evaluate(
        "() => document.documentElement.scrollWidth <= window.innerWidth"
    )
    assert page.get_by_text("đ", exact=True).is_visible()


def test_tsk_042_generated_label_asset_matches_python_source() -> None:
    labels_path = WEB_ROOT / "labels.json"

    assert labels_path.is_file(), "Generated web/labels.json is missing"
    assert json.loads(labels_path.read_text(encoding="utf-8")) == list(
        VIETNAMESE_ALPHABET
    )


@pytest.mark.parametrize("browser_name", ["chromium", "edge", "firefox"])
def test_tsk_041_browser_matrix_and_mobile_layout(
    browser_name: str, test_site: LocalSite
) -> None:
    with sync_playwright() as playwright:
        browser_type: BrowserType
        channel = None
        if browser_name == "edge":
            browser_type = playwright.chromium
            channel = "msedge"
        elif browser_name == "firefox":
            browser_type = playwright.firefox
        else:
            browser_type = playwright.chromium

        browser: Browser = browser_type.launch(channel=channel)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()
        config = json.dumps({"apiBaseUrl": test_site.url})
        page.add_init_script(f"window.VSL_CONFIG = {config};")

        try:
            _open_site(page, test_site)
            assert page.get_by_role(
                "heading", name="Nhận diện ký hiệu bàn tay"
            ).is_visible()
            page.get_by_label("Chọn ảnh").set_input_files(
                {
                    "name": "ban-tay.jpg",
                    "mimeType": "image/jpeg",
                    "buffer": _jpeg_bytes(),
                }
            )
            assert page.get_by_role("img", name="Ảnh xem trước").is_visible()

            page.set_viewport_size({"width": 375, "height": 812})
            assert page.get_by_role("button", name="Dự đoán").is_visible()
            assert page.evaluate(
                "() => document.documentElement.scrollWidth <= window.innerWidth"
            )
        finally:
            context.close()
            browser.close()
