import pytest
from pathlib import Path

from app.agents.animation_skill_generator import _build_fallback_html

pytestmark = pytest.mark.browser

LOCAL_CHROMIUM_EXECUTABLES = (
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
)


def _is_missing_managed_chromium_error(error):
    message = str(error)
    return "Executable doesn't exist" in message and "playwright install" in message


def _launch_chromium(p):
    playwright = pytest.importorskip("playwright.sync_api")
    try:
        return p.chromium.launch(headless=True)
    except playwright.Error as error:
        if not _is_missing_managed_chromium_error(error):
            raise
        managed_error = error

    local_errors = []
    for executable in LOCAL_CHROMIUM_EXECUTABLES:
        if not executable.exists():
            continue
        try:
            return p.chromium.launch(headless=True, executable_path=str(executable))
        except playwright.Error as error:
            local_errors.append(f"{executable}: {error}")

    details = "; ".join(local_errors) if local_errors else str(managed_error)
    pytest.skip(f"Chromium is unavailable for browser contract test: {details}")


def test_fallback_animation_renders_visible_active_beat(tmp_path):
    playwright = pytest.importorskip("playwright.sync_api")
    html = _build_fallback_html(
        title="排序算法",
        description="理解比较与交换",
        source_content="第一段说明。\n\n第二段说明。\n\n第三段说明。",
    )
    page_path = tmp_path / "animation.html"
    page_path.write_text(html, encoding="utf-8")

    errors = []
    with playwright.sync_playwright() as p:
        browser = _launch_chromium(p)
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.goto(page_path.as_uri())
        active = page.locator(".beat.active")
        assert active.count() == 1
        assert active.first.is_visible()
        assert "排序算法" in page.content()
        assert errors == []
        browser.close()
