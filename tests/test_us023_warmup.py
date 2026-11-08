"""Browser acceptance tests for the US-023 page-load health warm-up."""

import threading
from dataclasses import dataclass, field
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterator

import pytest
from playwright.sync_api import Browser, Page, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web"


@dataclass
class WarmupSite:
    url: str
    health_requested: threading.Event = field(default_factory=threading.Event)
    release_health: threading.Event = field(default_factory=threading.Event)
    hold_health: bool = False
    health_methods: list[str] = field(default_factory=list)


@pytest.fixture
def test_site() -> Iterator[WarmupSite]:
    site = WarmupSite(url="")

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, request, client_address, server) -> None:
            super().__init__(request, client_address, server, directory=str(WEB_ROOT))

        def do_GET(self) -> None:
            if self.path.split("?", maxsplit=1)[0] == "/health":
                site.health_methods.append(self.command)
                site.health_requested.set()
                if site.hold_health:
                    site.release_health.wait(timeout=10)
                self.send_response(503)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return

            super().do_GET()

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    site.url = f"http://{host}:{port}"

    try:
        yield site
    finally:
        site.release_health.set()
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


@pytest.fixture
def page(test_site: WarmupSite) -> Iterator[Page]:
    with sync_playwright() as playwright:
        browser: Browser = playwright.chromium.launch()
        context = browser.new_context()
        page = context.new_page()
        page.add_init_script(f"window.VSL_CONFIG = {{ apiBaseUrl: {test_site.url!r} }};")
        try:
            yield page
        finally:
            context.close()
            browser.close()


def test_page_sends_health_get_without_waiting_or_user_interaction(
    page: Page, test_site: WarmupSite
) -> None:
    test_site.hold_health = True

    response = page.goto(test_site.url, wait_until="load", timeout=5000)

    assert response is not None and response.status == 200
    assert page.get_by_role("heading", name="Nhận diện ký hiệu bàn tay").is_visible()
    assert test_site.health_requested.wait(timeout=5), "Page load did not request /health"
    assert test_site.health_methods == ["GET"]
    assert not test_site.release_health.is_set(), "Page waited for the health response"


def test_failed_health_warmup_does_not_block_page_or_show_an_error(
    page: Page, test_site: WarmupSite
) -> None:
    health_requests: list[str] = []
    page.route("**/health", lambda route: route.abort())
    page.on(
        "request",
        lambda request: (
            health_requests.append(request.method) if request.url.endswith("/health") else None
        ),
    )

    response = page.goto(test_site.url, wait_until="load", timeout=5000)

    assert response is not None and response.status == 200
    assert page.get_by_role("heading", name="Nhận diện ký hiệu bàn tay").is_visible()
    assert health_requests == ["GET"]
    assert not page.locator("#error-message").is_visible()
    assert not page.locator("#loading-status").is_visible()
