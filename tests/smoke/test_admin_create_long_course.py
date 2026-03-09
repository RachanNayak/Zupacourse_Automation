"""Smoke test: Can an admin create a Long Course? (Full flow using POM.)"""
import os
import random
from typing import Iterable, Optional

import pytest
from playwright.sync_api import Page, expect

from helpers.auth import login_as_admin, sign_out
from tests.pages.long_course_page import LongCoursePage

# Fixtures (paths and env wiring are unchanged; now passed into page objects)
TESTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES_DIR = os.path.join(TESTS_DIR, "fixtures")
IMAGES_DIR = os.path.join(FIXTURES_DIR, "images")
VIDEOS_DIR = os.path.join(FIXTURES_DIR, "videos")
DEFAULT_COURSE_IMAGE_PATH = os.path.join(FIXTURES_DIR, "download.jpeg")
FALLBACK_COURSE_IMAGE_PATH = os.path.join(FIXTURES_DIR, "course-image.png")
DUMMY_FILE_PATH = os.path.join(FIXTURES_DIR, "dummy-attachment.txt")
# Default video fixture path (can be overridden via VIDEO_FILE_PATH env var)
DEFAULT_VIDEO_FIXTURE_PATH = os.path.join(FIXTURES_DIR, "Playwright_Cursor_AI_in_QA_How_to_Save_Hours_240P.mp4")


def _pick_random_file(
    directory: str, *, exts: Optional[Iterable[str]] = None, fallback: Optional[str] = None
) -> Optional[str]:
    """Pick a random file from directory (filtered by extensions), or return fallback."""
    if not os.path.isdir(directory):
        return fallback
    files: list[str] = []
    for name in os.listdir(directory):
        full = os.path.join(directory, name)
        if not os.path.isfile(full):
            continue
        if exts:
            _, ext = os.path.splitext(name)
            if ext.lower() not in {e.lower() for e in exts}:
                continue
        files.append(full)
    if not files:
        return fallback
    return random.choice(files)


# Optional: set MODULE_FILE_PATH / COURSE_IMAGE_PATH / VIDEO_FILE_PATH via env to override random choice
MODULE_FILE_PATH = os.getenv("MODULE_FILE_PATH", DUMMY_FILE_PATH)
COURSE_IMAGE_PATH = os.getenv(
    "COURSE_IMAGE_PATH",
    _pick_random_file(
        IMAGES_DIR,
        exts={".png", ".jpg", ".jpeg", ".webp"},
        fallback=DEFAULT_COURSE_IMAGE_PATH if os.path.isfile(DEFAULT_COURSE_IMAGE_PATH) else FALLBACK_COURSE_IMAGE_PATH,
    ),
)
VIDEO_FILE_PATH = os.getenv(
    "VIDEO_FILE_PATH",
    _pick_random_file(
        VIDEOS_DIR,
        exts={".mp4", ".mov", ".m4v"},
        fallback=DEFAULT_VIDEO_FIXTURE_PATH,
    ),
)


@pytest.mark.smoke
def test_admin_create_long_course(page: Page) -> None:
    """
    Full Long Course flow: Login (manual OTP) → Create Course → Create Batches →
    Create Modules → Add Videos → Enrollment & Price → Publish Course.
    Uses codegen locators.
    """
    if os.getenv("SIGN_OUT_FIRST", "").lower() in ("1", "true", "yes"):
        sign_out(page)
    admin_email = os.getenv("ADMIN_EMAIL", "rachan@zupaloop.com")
    # Use manual OTP flow so you can type the OTP yourself, then the test continues automatically.
    login_as_admin(page, email=admin_email, manual_otp=True, wait_for_navigation=True)
    page.wait_for_load_state("networkidle")
    assert "/auth/sign-in" not in page.url

    titles = [
        "Divyakala art",
        "Testing course",
        "Cricket",
        "Football",
        "Looong cousre",
        "Drawing",
        "Divine Art",
    ]
    title = random.choice(titles)

    long_course = LongCoursePage(page)
    long_course.fill_course_details(title=title, course_image_path=COURSE_IMAGE_PATH, dummy_file_path=DUMMY_FILE_PATH)
    long_course.create_batches()
    long_course.create_module(module_file_path=MODULE_FILE_PATH)
    long_course.add_video(video_file_path=VIDEO_FILE_PATH)
    long_course.set_enrollment_and_publish(created_title=title)

    first_card = page.locator(".course-card").first
    expect(first_card.get_by_text(title, exact=False)).to_be_visible(timeout=15000)