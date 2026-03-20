"""Pytest and Playwright configuration for LMS smoke tests."""
from datetime import datetime
from pathlib import Path

import pytest
from playwright.sync_api import Page, sync_playwright

from config import BASE_URL, HEADED

try:
    import allure  # type: ignore
except ImportError:  # pragma: no cover - optional at runtime
    allure = None


@pytest.fixture(scope="session")
def playwright_browser():
    """Session-scoped Playwright and browser."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not HEADED)
        yield browser
        browser.close()


@pytest.fixture
def context(playwright_browser):
    """New browser context per test (fresh state)."""
    context = playwright_browser.new_context(base_url=BASE_URL)
    yield context
    context.close()


@pytest.fixture
def page(context) -> Page:
    """New page per test."""
    return context.new_page()


@pytest.fixture(scope="session")
def base_url():
    """Base URL for the app under test."""
    return BASE_URL


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    """Hook to attach the test report to the item for later inspection."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)


@pytest.fixture(autouse=True)
def capture_screenshot_on_failure(request, page: Page):
    """On test failure, capture a screenshot and attach it to Allure (if available)."""
    yield
    rep = getattr(request.node, "rep_call", None)
    if rep is not None and rep.failed:
        try:
            png = page.screenshot(full_page=True)

            # Always persist failure screenshots to disk for easy review.
            screenshots_dir = Path("artifacts") / "screenshots"
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            safe_test_name = request.node.nodeid.replace("/", "_").replace("::", "__").replace(" ", "_")
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = screenshots_dir / f"{safe_test_name}_{ts}.png"
            screenshot_path.write_bytes(png)

            # Also attach to Allure when plugin is available.
            if allure is not None:
                allure.attach(
                    png,
                    name=f"failure-screenshot:{safe_test_name}",
                    attachment_type=allure.attachment_type.PNG,
                )
        except Exception:
            # Best-effort only; never break the test teardown because of reporting.
            pass
