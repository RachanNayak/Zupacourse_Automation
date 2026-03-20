"""Smoke test: Can an admin create a Short Course? (Full flow using POM.)"""
import os
import random
import time as _time
from typing import Iterable, Optional

import allure
import pytest
from playwright.sync_api import Page, expect

from config import ADMIN_EMAIL, BASE_URL, MANUAL_OTP, SIGN_OUT_FIRST
from helpers.auth import login_as_admin, sign_out
from tests.pages.short_course_page import ShortCoursePage

# Fixtures (reuse the same structure as the long-course test)
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


@allure.epic("LMS Admin")
@allure.feature("Course Management")
@allure.story("Create Short Course")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.smoke
def test_admin_create_short_course(page: Page) -> None:
    """
    Full Short Course flow: Login (manual OTP) → Create Course → Create Module →
    Add Video → Enrollment & Price → Publish Course.
    """
    with allure.step("Login as admin"):
        if SIGN_OUT_FIRST:
            sign_out(page)
        login_as_admin(page, email=ADMIN_EMAIL, manual_otp=MANUAL_OTP, wait_for_navigation=True)
        page.wait_for_load_state("networkidle")
        assert "/auth/sign-in" not in page.url

    titles = [
        "Test Draw",
        "Short Course Cricket",
        "Short Course Football",
        "Short Divine Art",
    ]
    suffix = _time.strftime("%m%d%H%M")
    title = random.choice(titles) + " " + suffix
    allure.dynamic.title(f"Admin creates Short Course: {title}")

    short_course = ShortCoursePage(page)

    with allure.step(f"Fill course details (title={title!r})"):
        course_info = short_course.fill_course_details(title=title, course_image_path=COURSE_IMAGE_PATH, dummy_file_path=DUMMY_FILE_PATH)

    allure.attach(
        f"Title: {title}\nAuthor: {course_info['author']}\nImage: {course_info['image_filename']}",
        name="Course details entered",
        attachment_type=allure.attachment_type.TEXT,
    )

    with allure.step("Create module"):
        short_course.create_module(module_file_path=MODULE_FILE_PATH)

    with allure.step("Add video"):
        short_course.add_video(video_file_path=VIDEO_FILE_PATH)

    with allure.step("Set enrollment and publish"):
        short_course.set_enrollment_and_publish()

    with allure.step("Navigate to courses list"):
        page.goto(f"{BASE_URL}/landing/lms/courses")
        page.wait_for_load_state("networkidle")

    with allure.step("Verify course card shows exact title, image and author"):
        # Click the Short Courses tab if it exists (scoped to tab roles to avoid matching combobox spans)
        short_tab = page.get_by_role("tab", name="Short Courses").or_(
            page.get_by_role("button", name="Short Courses")
        )
        if short_tab.count() > 0:
            short_tab.first.click()
            page.wait_for_load_state("networkidle")

        # Wait for any course card to appear
        card_locator = page.locator("mat-card, [class*='course-card'], [class*='course_card'], app-course-card").first
        card_locator.wait_for(state="visible", timeout=20000)
        # Search for the title we created
        title_on_page = page.get_by_text(title, exact=False).first
        expect(title_on_page).to_be_visible(timeout=10000)
        # Find the specific card containing that title
        course_card = page.locator("mat-card, [class*='course-card'], [class*='course_card'], app-course-card").filter(
            has=page.get_by_text(title, exact=False)
        ).first
        # Course image — check <img> tag first; fall back to CSS background-image or thumbnail divs
        img_tag = course_card.locator("img")
        bg_img = course_card.locator("[style*='background-image'], [class*='thumbnail'], [class*='banner'], [class*='cover'], [class*='image']")
        if img_tag.count() > 0:
            expect(img_tag.first).to_be_visible()
        elif bg_img.count() > 0:
            expect(bg_img.first).to_be_visible()
        # Author — must match the author selected during form fill
        if course_info["author"]:
            expect(course_card.get_by_text(course_info["author"], exact=False)).to_be_visible()

    with allure.step("Verify course is PUBLISHED (no unpublished badge on card)"):
        unpublished_badge = course_card.locator("[class*='unpublished-badge']")
        expect(unpublished_badge).to_be_hidden()
