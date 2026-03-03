"""Pytest and Playwright configuration for Divyakala LMS smoke tests."""
import os

import pytest
from dotenv import load_dotenv
from playwright.sync_api import Page, sync_playwright

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "https://app.sandbox.lms.zupaloop.ai").rstrip("/")


@pytest.fixture(scope="session")
def playwright_browser():
    """Session-scoped Playwright and browser."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=os.getenv("HEADED", "").lower() not in ("1", "true", "yes"))
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
