import os
import shutil
from pathlib import Path

import pytest

from app.agents.animation_skill_generator import _build_fallback_html

pytestmark = pytest.mark.browser

CHROMIUM_COMMANDS = (
    "msedge",
    "microsoft-edge",
    "chrome",
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
)
LOCAL_CHROMIUM_EXECUTABLES = (
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
)


def _is_truthy_env(name):
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _require_browser_tests():
    return _is_truthy_env("CI") or _is_truthy_env("AURA_REQUIRE_BROWSER_TESTS")


def _is_missing_managed_chromium_error(error):
    message = str(error)
    return "Executable doesn't exist" in message and "playwright install" in message


def _candidate_chromium_executables():
    candidates = []
    configured_path = os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH")
    if configured_path:
        candidates.append(configured_path)

    for command in CHROMIUM_COMMANDS:
        executable = shutil.which(command)
        if executable:
            candidates.append(executable)

    candidates.extend(str(path) for path in LOCAL_CHROMIUM_EXECUTABLES)

    seen = set()
    for candidate in candidates:
        path = Path(candidate)
        key = str(path).casefold()
        if key in seen:
            continue
        seen.add(key)
        yield path


def _browser_unavailable(message):
    if _require_browser_tests():
        pytest.fail(message)
    pytest.skip(message)


def _import_playwright():
    try:
        from playwright import sync_api as playwright
    except ImportError as error:
        _browser_unavailable(f"Playwright is unavailable for browser contract test: {error}")
    return playwright


def _launch_chromium(p, playwright):
    try:
        return p.chromium.launch(headless=True)
    except playwright.Error as error:
        if not _is_missing_managed_chromium_error(error):
            raise
        managed_error = error

    local_errors = []
    for executable in _candidate_chromium_executables():
        if not executable.exists():
            local_errors.append(f"{executable}: not found")
            continue
        try:
            return p.chromium.launch(headless=True, executable_path=str(executable))
        except playwright.Error as error:
            local_errors.append(f"{executable}: {error}")

    details = "; ".join(local_errors) if local_errors else str(managed_error)
    _browser_unavailable(f"Chromium is unavailable for browser contract test: {details}")


def test_fallback_animation_renders_visible_active_beat(tmp_path):
    playwright = _import_playwright()
    html = _build_fallback_html(
        title="排序算法",
        description="理解比较与交换",
        source_content="第一段说明。\n\n第二段说明。\n\n第三段说明。",
    )
    page_path = tmp_path / "animation.html"
    page_path.write_text(html, encoding="utf-8")

    errors = []
    page_errors = []
    with playwright.sync_playwright() as p:
        browser = _launch_chromium(p, playwright)
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 720})
            page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.goto(page_path.as_uri())
            active = page.locator(".beat.active")
            playwright.expect(active).to_have_count(1)
            playwright.expect(active.first).to_be_visible()
            assert "排序算法" in page.content()
            assert errors == []
            assert page_errors == []
        finally:
            browser.close()
