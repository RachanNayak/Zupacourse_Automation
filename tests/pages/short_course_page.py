import os
import random
import re
import time

import pytest
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, expect


class ShortCoursePage:
    def __init__(self, page: Page) -> None:
        self.page = page

    def _select_type_of_course_for_current_org(self) -> None:
        """Handle org-specific differences for the Type of Course dropdown."""
        page = self.page
        page.get_by_role("combobox", name="Type of Course").locator("span").click()
        time.sleep(0.3)
        short_opt = page.get_by_role("option", name="Short Courses")
        courses_opt = page.get_by_role("option", name="Courses")
        if short_opt.count() > 0 and short_opt.first.is_visible():
            short_opt.first.click()
        elif courses_opt.count() > 0 and courses_opt.first.is_visible():
            courses_opt.first.click()
        else:
            # Fallback: try by text in case options use different roles
            if page.get_by_text("Short Courses", exact=True).count() > 0:
                page.get_by_text("Short Courses", exact=True).first.click()
            else:
                page.get_by_text("Courses", exact=True).first.click()
        time.sleep(0.2)

    # --- Create Course & basic info ---
    def fill_course_details(self, title: str, course_image_path: str, dummy_file_path: str) -> dict:
        """Fill course details form and return {"author": str, "image_filename": str}."""
        page = self.page
        selected_author: str = ""

        page.get_by_role("button", name="Create Course").wait_for(state="visible", timeout=10000)
        page.get_by_role("button", name="Create Course").click()
        page.wait_for_load_state("networkidle")

        # White-labelled: Divyakala has "Short Courses", Tapovana has "Courses"
        self._select_type_of_course_for_current_org()

        # Random Course Category
        page.get_by_role("combobox", name="Course Category").locator("span").click()
        time.sleep(0.2)
        category_options = page.get_by_role("option")
        category_count = category_options.count()
        visible_category_indices = [
            i
            for i in range(category_count)
            if category_options.nth(i).is_visible()
        ]
        if visible_category_indices:
            idx = random.choice(visible_category_indices)
            category_options.nth(idx).click()
        time.sleep(0.2)

        # Random Author — capture the selected name for later validation
        page.get_by_role("combobox", name="Author").locator("span").click()
        time.sleep(0.2)
        author_options = page.get_by_role("option")
        author_count = author_options.count()
        visible_author_indices = [
            i
            for i in range(author_count)
            if author_options.nth(i).is_visible()
        ]
        if visible_author_indices:
            idx = random.choice(visible_author_indices)
            author_options.nth(idx).scroll_into_view_if_needed()
            selected_author = author_options.nth(idx).inner_text().strip()
            author_options.nth(idx).click()
        time.sleep(0.2)

        page.get_by_role("textbox", name="Course Name").fill(title)

        # Start date: pick a date in the next month
        page.locator("mat-form-field").filter(has_text="Start Date").get_by_label("Open calendar").click()
        time.sleep(0.3)
        page.get_by_role("button", name="Next month").click()
        page.get_by_role("button", name=re.compile(r"April 1,")).first.click()
        time.sleep(0.2)

        # End date: a year later (similar pattern to long course)
        page.locator("mat-form-field").filter(has_text="End Date").get_by_label("Open calendar").click()
        time.sleep(0.3)
        for _ in range(12):
            page.get_by_role("button", name="Next month").click()
            time.sleep(0.05)
        page.get_by_role("button", name=re.compile(r"April 1,")).first.click()
        time.sleep(0.2)

        # Description – pick the main rich text editor generically
        description_editor = page.locator("form").locator("div.ql-editor[contenteditable='true']").first
        description_editor.click()
        description_editor.fill("Desc here")
        time.sleep(0.2)

        # Course image
        if os.path.isfile(course_image_path):
            file_inputs = page.locator('input[type="file"]')
            if file_inputs.count() > 0:
                file_inputs.first.set_input_files(course_image_path)
        else:
            pytest.skip(f"Course image not found: {course_image_path}")
        time.sleep(0.3)

        page.get_by_role("button", name="Add course info").click()
        time.sleep(0.4)

        # Additional course info
        page.get_by_role("textbox", name="Title").fill("title")
        extra_info_editor = page.locator("app-add-course-info div.ql-editor[contenteditable='true']").first
        extra_info_editor.click()
        extra_info_editor.fill("desc")
        page.locator("app-add-course-info").get_by_role("button", name="Add course info").click()
        time.sleep(0.3)

        # Attach an extra file if available
        if os.path.isfile(dummy_file_path):
            all_file_inputs = page.locator('input[type="file"]')
            if all_file_inputs.count() >= 2:
                all_file_inputs.nth(1).set_input_files(dummy_file_path)
            else:
                all_file_inputs.first.set_input_files(dummy_file_path)
        time.sleep(0.2)

        page.get_by_role("button", name="Save and Continue").click()
        page.wait_for_load_state("networkidle")

        return {"author": selected_author, "image_filename": os.path.basename(course_image_path)}

    # --- Create Modules ---
    def create_module(self, module_file_path: str) -> None:
        page = self.page

        page.get_by_role("textbox", name="Module Name").fill("module 1")
        module_desc_editor = page.get_by_role("tabpanel", name="Create Modules").locator(
            "div.ql-editor[contenteditable='true'][data-placeholder='Module Description']"
        ).first
        module_desc_editor.click()
        module_desc_editor.fill("desc")

        if os.path.isfile(module_file_path):
            file_inputs = page.get_by_role("tabpanel", name="Create Modules").locator('input[type="file"]')
            if file_inputs.count() > 0:
                file_inputs.first.set_input_files(module_file_path)
        time.sleep(0.2)

        page.get_by_role("button", name="Add Module").click()
        page.wait_for_load_state("networkidle")
        time.sleep(0.3)
        page.get_by_role("button", name="Save and Continue").click()
        page.wait_for_load_state("networkidle")

    # --- Add Videos ---
    def add_video(self, video_file_path: str) -> None:
        page = self.page

        page.get_by_role("combobox", name="Select Module").locator("span").click()
        # Module name appears as "module 1" in UI; adjust if needed
        page.get_by_role("option", name=re.compile(r"module", re.I)).first.click()
        time.sleep(0.2)

        page.get_by_role("textbox", name="Session Name").fill("session 1")

        if os.path.isfile(video_file_path):
            file_inputs = page.locator('input[type="file"]')
            if file_inputs.count() > 0:
                file_inputs.last.set_input_files(video_file_path)
            page.get_by_role("button", name="Add Video").click()
        else:
            page.get_by_role("button", name="Skip").click()

        page.wait_for_load_state("networkidle")
        time.sleep(0.3)
        page.get_by_role("button", name="Save and Continue").click()
        page.wait_for_load_state("networkidle")

    # --- Enrollment & Price ---
    def set_enrollment_and_publish(self) -> None:
        page = self.page
        loader = page.locator("div.page-loader")

        def _wait_loader_hidden(timeout_s: float = 15.0) -> None:
            """Best-effort wait for transient full-page loader to clear."""
            end_time = time.time() + timeout_s
            while time.time() < end_time:
                if loader.count() == 0:
                    return
                try:
                    if not loader.first.is_visible():
                        return
                except Exception:
                    # Detached loader means overlay is gone.
                    return
                time.sleep(0.2)

        # Ensure enrollment type is selected. Use check() to avoid accidental toggle behavior.
        subscription_opt = page.get_by_role("radio", name=re.compile(r"Subscription", re.I))
        if subscription_opt.count() > 0:
            try:
                if not subscription_opt.first.is_checked():
                    subscription_opt.first.check()
            except Exception:
                # Fallback for custom radio implementations
                subscription_opt.first.click()

        page.get_by_role("combobox", name="Currency").locator("span").click()
        page.get_by_role("option", name="INR").click()
        page.get_by_role("textbox", name="Amount").fill("100")
        add_btn = page.get_by_role("button", name="Add", exact=True)
        expect(add_btn).to_be_enabled(timeout=5000)
        add_btn.click()
        time.sleep(0.2)

        page.get_by_role("combobox", name="Currency").locator("span").click()
        page.get_by_role("option", name="USD").click()
        page.get_by_role("textbox", name="Amount").fill("20")
        add_btn = page.get_by_role("button", name="Add", exact=True)
        expect(add_btn).to_be_enabled(timeout=5000)
        add_btn.click()
        time.sleep(0.2)

        # Loader can briefly overlay the form after pricing updates; wait it out
        # before attempting to click Publish.
        _wait_loader_hidden(timeout_s=15.0)

        publish_btn = page.get_by_role("button", name="Publish Course").first
        publish_btn.wait_for(state="visible", timeout=10000)
        publish_btn.scroll_into_view_if_needed()
        expect(publish_btn).to_be_enabled(timeout=10000)
        try:
            publish_btn.click(timeout=5000)
        except PlaywrightTimeoutError:
            # Fallback for cases where a transient overlay still intercepts pointer events.
            handle = publish_btn.element_handle()
            if handle:
                page.evaluate("(el) => el.click()", handle)

        # Some org themes show a dialog-level Publish confirmation.
        # Scope to dialog so we never re-match the page-level Publish button.
        confirm_publish = page.get_by_role("dialog").get_by_role("button", name=re.compile(r"^Publish$", re.I))
        for _ in range(10):
            if confirm_publish.count() > 0 and confirm_publish.first.is_visible():
                confirm_publish.first.click()
                break
            time.sleep(0.2)

        # If publish did not trigger on first click due to transient overlays, retry once.
        if "/create-course" in page.url and publish_btn.is_visible():
            _wait_loader_hidden(timeout_s=10.0)
            try:
                publish_btn.click(timeout=4000)
            except PlaywrightTimeoutError:
                handle = publish_btn.element_handle()
                if handle:
                    page.evaluate("(el) => el.click()", handle)

        # Wait for the page-loader overlay to disappear, then networkidle.
        # Ignore if loader is not present in some org themes.
        _wait_loader_hidden(timeout_s=30.0)
        page.wait_for_load_state("networkidle")

