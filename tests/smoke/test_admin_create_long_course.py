"""Smoke test: Can an admin create a Long Course? (Full flow from codegen.)"""
import os
import re
import time

import pytest
from playwright.sync_api import Page, expect

from helpers.auth import login_as_admin, sign_out

# Fixtures
TESTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES_DIR = os.path.join(TESTS_DIR, "fixtures")
COURSE_IMAGE_PATH = os.path.join(FIXTURES_DIR, "course-image.png")
DUMMY_FILE_PATH = os.path.join(FIXTURES_DIR, "dummy-attachment.txt")
# Optional: set MODULE_FILE_PATH / VIDEO_FILE_PATH in env for Add Module / Add Video (e.g. a PDF and an MP4)
MODULE_FILE_PATH = os.getenv("MODULE_FILE_PATH", DUMMY_FILE_PATH)
VIDEO_FILE_PATH = os.getenv("VIDEO_FILE_PATH", "")


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
    use_manual_otp = os.getenv("MANUAL_OTP", "").lower() in ("1", "true", "yes")
    login_as_admin(page, email=admin_email, manual_otp=use_manual_otp, wait_for_navigation=True)
    page.wait_for_load_state("networkidle")
    assert "/auth/sign-in" not in page.url
    # After login we're on /landing/lms/courses; click Create Course to open the form
    page.get_by_role("button", name="Create Course").wait_for(state="visible", timeout=10000)
    page.get_by_role("button", name="Create Course").click()
    page.wait_for_load_state("networkidle")

    page.get_by_role("combobox", name="Type of Course").locator("span").click()
    page.get_by_text("Long Courses").click()
    time.sleep(0.2)

    page.get_by_role("combobox", name="Course Category").locator("span").click()
    page.get_by_role("option", name="Art").click()
    time.sleep(0.2)

    page.get_by_role("combobox", name="Author").locator("span").click()
    page.get_by_text("Abhinava Krishna K S").click()
    time.sleep(0.2)

    title = "Divyakala art"
    page.get_by_role("textbox", name="Course Name").fill(title)

    page.locator("mat-form-field").filter(has_text="Start Date").get_by_label("Open calendar").click()
    time.sleep(0.3)
    page.get_by_role("button", name=re.compile(r"March \d+,")).first.click()
    time.sleep(0.2)

    page.locator("mat-form-field").filter(has_text="End Date").get_by_label("Open calendar").click()
    time.sleep(0.3)
    page.get_by_role("button", name=re.compile(r"March \d+,")).last.click()
    time.sleep(0.2)

    page.locator("form").filter(has_text="Type of CourseLong").locator("quill-editor div").nth(2).click()
    page.locator("form").filter(has_text="Type of CourseLong").locator("quill-editor div").nth(2).fill("DESC here")
    time.sleep(0.2)

    if os.path.isfile(COURSE_IMAGE_PATH):
        page.locator('input[type="file"]').first.set_input_files(COURSE_IMAGE_PATH)
    else:
        pytest.skip(f"Course image not found: {COURSE_IMAGE_PATH}")
    time.sleep(0.3)

    page.get_by_role("button", name="Add course info").click()
    time.sleep(0.4)
    page.get_by_role("textbox", name="Title").fill("Title Here")
    page.locator("app-add-course-info quill-editor div").nth(2).click()
    page.locator("app-add-course-info quill-editor div").nth(2).fill("Desc here.")
    page.locator("app-add-course-info").get_by_role("button", name="Add course info").click()
    time.sleep(0.3)

    if os.path.isfile(DUMMY_FILE_PATH):
        all_file_inputs = page.locator('input[type="file"]')
        if all_file_inputs.count() >= 2:
            all_file_inputs.nth(1).set_input_files(DUMMY_FILE_PATH)
        else:
            all_file_inputs.first.set_input_files(DUMMY_FILE_PATH)
    time.sleep(0.2)

    page.get_by_role("button", name="Save and Continue").click()
    page.wait_for_load_state("networkidle")

    # --- Create Batches ---
    page.get_by_role("textbox", name="Batch Name").fill("Batch 1")
    start_date_cal = page.locator("div").filter(has_text=re.compile(r"^Start DateStart Time$")).get_by_label("Open calendar")
    start_date_cal.first.scroll_into_view_if_needed()
    time.sleep(0.3)
    start_date_cal.first.click()
    time.sleep(0.3)
    page.get_by_role("button", name=re.compile(r"March \d+,")).first.click()
    time.sleep(0.2)
    end_date_cal = page.locator("div").filter(has_text=re.compile(r"^End DateEnd Time$")).get_by_label("Open calendar")
    end_date_cal.first.scroll_into_view_if_needed()
    time.sleep(0.2)
    end_date_cal.first.click()
    time.sleep(0.3)
    page.get_by_role("button", name="Next month").click()
    time.sleep(0.2)
    page.get_by_role("button", name=re.compile(r"April \d+,")).first.click()
    time.sleep(0.2)
    page.locator("div").filter(has_text=re.compile(r"^Start Time$")).nth(3).click()
    page.get_by_text("5:00 AM").click()
    page.get_by_role("combobox", name="End Time").locator("span").click()
    page.get_by_text("6:00 AM").click()
    page.get_by_text("T", exact=True).first.click()
    page.get_by_text("T", exact=True).nth(1).click()
    page.get_by_role("textbox", name="Live Session Link").fill("https://live.example.com")
    page.get_by_role("button", name="Create Batch").click()
    page.wait_for_load_state("networkidle")
    time.sleep(0.5)

    page.get_by_role("textbox", name="Batch Name").fill("Batch 2")
    page.get_by_role("radio", name="Schedule Non-Recurring Batch").check()
    time.sleep(0.2)
    page.get_by_role("button", name="Open calendar").first.click()
    time.sleep(0.3)
    page.get_by_role("button", name=re.compile(r"March \d+,")).first.click()
    page.get_by_role("combobox", name=re.compile(r"Start Time")).locator("svg").click()
    page.get_by_text("6:00 AM", exact=True).click()
    page.get_by_role("combobox", name=re.compile(r"End Time")).locator("svg").click()
    page.get_by_text("7:00 AM").click()
    page.get_by_role("textbox", name="Live Session Link").fill("https://live.example.com")
    page.get_by_role("button", name="Create Batch").click()
    page.wait_for_load_state("networkidle")
    time.sleep(0.5)

    page.get_by_role("button", name="Continue").click()
    page.wait_for_load_state("networkidle")

    # --- Create Modules ---
    page.get_by_role("textbox", name="Module Name").fill("Module 1")
    page.get_by_role("tabpanel", name="Create Modules").locator("quill-editor div").nth(2).click()
    page.get_by_role("tabpanel", name="Create Modules").locator("quill-editor div").nth(2).fill("Module desc here")
    if os.path.isfile(MODULE_FILE_PATH):
        page.get_by_role("tabpanel", name="Create Modules").locator('input[type="file"]').first.set_input_files(MODULE_FILE_PATH)
    time.sleep(0.2)
    page.get_by_role("button", name="Add Module").click()
    page.wait_for_load_state("networkidle")
    time.sleep(0.3)
    page.get_by_role("button", name="Save and Continue").click()
    page.wait_for_load_state("networkidle")

    # --- Add Videos ---
    page.get_by_role("combobox", name="Select Module").locator("svg").click()
    page.get_by_role("option", name="Module 1").click()
    time.sleep(0.2)
    page.get_by_role("combobox", name="Select Batch").locator("svg").click()
    page.get_by_role("option", name="Batch 1").click()
    time.sleep(0.2)
    page.get_by_role("textbox", name="Session Name").fill("Session 1")
    page.get_by_role("combobox", name="Select Session Date").locator("span").click()
    page.get_by_text(re.compile(r"Batch 1.*Session.*\d{4}-\d{2}-\d{2}")).first.click()
    time.sleep(0.2)
    if os.path.isfile(VIDEO_FILE_PATH):
        page.locator('input[type="file"]').last.set_input_files(VIDEO_FILE_PATH)
        page.get_by_role("button", name="Add Video").click()
    else:
        page.get_by_role("button", name="Skip").click()
    page.wait_for_load_state("networkidle")
    time.sleep(0.3)

    # --- Enrollment & Price ---
    page.get_by_role("combobox", name="Currency").locator("span").click()
    page.get_by_role("option", name="INR").click()
    page.get_by_role("textbox", name="Amount").fill("200")
    page.get_by_role("button", name="Add").click()
    time.sleep(0.2)
    page.get_by_role("combobox", name="Currency").locator("span").click()
    page.get_by_role("option", name="USD").click()
    page.get_by_role("textbox", name="Amount").fill("200")
    page.get_by_role("button", name="Add").click()
    time.sleep(0.2)
    page.get_by_role("button", name="Publish Course").click()
    page.wait_for_load_state("networkidle")

    expect(page.get_by_text(re.compile(rf"{re.escape(title)}.*Abhinava", re.I))).to_be_visible(timeout=15000)
