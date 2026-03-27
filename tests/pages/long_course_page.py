import os
import random
import re
import time
from datetime import datetime
from pathlib import Path

import pytest
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, expect


class LongCoursePage:
    def __init__(self, page: Page) -> None:
        self.page = page

    def _capture_timeout_screenshot(self, step_name: str) -> None:
        """Capture a screenshot for timeout/debug and continue the flow."""
        screenshots_dir = Path("artifacts") / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = screenshots_dir / f"long_course_{step_name}_{ts}.png"
        self.page.screenshot(path=str(path), full_page=True)

    # --- Create Course & basic info ---
    def fill_course_details(self, title: str, course_image_path: str, dummy_file_path: str) -> dict:
        """Fill course details form and return {"author": str, "image_filename": str}."""
        page = self.page
        selected_author: str = ""

        page.get_by_role("button", name="Create Course").wait_for(state="visible", timeout=10000)
        page.get_by_role("button", name="Create Course").click()
        page.wait_for_load_state("networkidle")

        page.get_by_role("combobox", name="Type of Course").locator("span").click()
        page.get_by_text("Long Courses").click()
        time.sleep(0.2)

        page.get_by_role("combobox", name="Course Category").locator("span").click()
        page.get_by_role("option", name="Art").click()
        time.sleep(0.2)

        try:
            page.get_by_role("combobox", name="Author").locator("span").click()
            time.sleep(0.2)
            author_options = page.get_by_role("option")
            author_count = author_options.count()
            visible_author_indices = [
                i for i in range(author_count) if author_options.nth(i).is_visible()
            ]
            if visible_author_indices:
                idx = random.choice(visible_author_indices)
                author_options.nth(idx).scroll_into_view_if_needed()
                selected_author = author_options.nth(idx).inner_text().strip()
                author_options.nth(idx).click()
            time.sleep(0.2)
        except PlaywrightTimeoutError:
            self._capture_timeout_screenshot("author_selection_timeout")
            try:
                fallback_options = page.get_by_role("option")
                fallback_count = fallback_options.count()
                for i in range(fallback_count):
                    if fallback_options.nth(i).is_visible():
                        selected_author = fallback_options.nth(i).inner_text().strip()
                        fallback_options.nth(i).click()
                        break
            except Exception:
                pass
        except Exception:
            self._capture_timeout_screenshot("author_selection_error")

        page.get_by_role("textbox", name="Course Name").fill(title)

        page.locator("mat-form-field").filter(has_text="Start Date").get_by_label("Open calendar").click()
        time.sleep(0.3)
        start_btn = page.get_by_role("button", name=re.compile(r"March \d+,\s*\d{4}"))
        start_label = start_btn.first.get_attribute("aria-label") or start_btn.first.inner_text()
        m = re.search(r"^(?P<month>[A-Za-z]+)\s+(?P<day>\d+),\s*(?P<year>\d{4})", (start_label or "").strip())
        assert m, f"Could not parse start date label: {start_label!r}"
        start_btn.first.click()
        time.sleep(0.2)

        page.locator("mat-form-field").filter(has_text="End Date").get_by_label("Open calendar").click()
        time.sleep(0.3)
        for _ in range(12):
            page.get_by_role("button", name="Next month").click()
            time.sleep(0.05)
        end_label = f"{m.group('month')} {m.group('day')}, {int(m.group('year')) + 1}"
        page.get_by_role("button", name=end_label).click()
        time.sleep(0.2)

        description_editor = page.locator("form").filter(has_text="Type of CourseLong").locator(
            "div.ql-editor[contenteditable='true']"
        ).first
        description_editor.click()
        description_editor.fill("DESC here")
        time.sleep(0.2)

        if os.path.isfile(course_image_path):
            page.locator('input[type="file"]').first.set_input_files(course_image_path)
        else:
            pytest.skip(f"Course image not found: {course_image_path}")
        time.sleep(0.3)

        page.get_by_role("button", name="Add course info").click()
        time.sleep(0.4)
        page.get_by_role("textbox", name="Title").fill("Title Here")
        extra_info_editor = page.locator("app-add-course-info div.ql-editor[contenteditable='true']").first
        extra_info_editor.click()
        extra_info_editor.fill("Desc here.")
        page.locator("app-add-course-info").get_by_role("button", name="Add course info").click()
        time.sleep(0.3)

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

    # --- Create Batches ---
    def create_batches(self) -> None:
        page = self.page

        page.get_by_role("textbox", name="Batch Name").fill("Batch 1")
        start_date_cal = page.locator("div").filter(has_text=re.compile(r"^Start DateStart Time$")).get_by_label(
            "Open calendar"
        )
        start_date_cal.first.scroll_into_view_if_needed()
        time.sleep(0.3)
        start_date_cal.first.click()
        time.sleep(0.3)
        page.get_by_role("button", name=re.compile(r"March \d+,")).first.click()
        time.sleep(0.2)
        end_date_cal = page.locator("div").filter(has_text=re.compile(r"^End DateEnd Time$")).get_by_label(
            "Open calendar"
        )
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
    def create_module(self, module_file_path: str) -> None:
        page = self.page

        page.get_by_role("textbox", name="Module Name").fill("Module 1")
        module_desc_editor = page.get_by_role("tabpanel", name="Create Modules").locator(
            "div.ql-editor[contenteditable='true'][data-placeholder='Module Description']"
        ).first
        module_desc_editor.click()
        module_desc_editor.fill("Module desc here")
        if os.path.isfile(module_file_path):
            page.get_by_role("tabpanel", name="Create Modules").locator('input[type="file"]').first.set_input_files(
                module_file_path
            )
        time.sleep(0.2)
        page.get_by_role("button", name="Add Module").click()
        page.wait_for_load_state("networkidle")
        time.sleep(0.3)
        page.get_by_role("button", name="Save and Continue").click()
        page.wait_for_load_state("networkidle")

    # --- Add Videos ---
    def add_video(self, video_file_path: str) -> None:
        page = self.page

        page.get_by_role("combobox", name="Select Module").locator("svg").click()
        page.get_by_role("option", name="Module 1").click()
        time.sleep(0.2)
        page.get_by_role("combobox", name="Select Batch").locator("svg").click()
        page.get_by_role("option", name="Batch 1").click()
        time.sleep(0.2)

        # Select session date first, then fill session name.
        session_date_combo = page.get_by_role("combobox", name="Select Session Date")
        session_date_combo.scroll_into_view_if_needed()
        # Prefer clicking the combobox directly; fallback to inner span for variant UIs.
        try:
            session_date_combo.click()
        except Exception:
            session_date_combo.locator("span").click()

        # Prefer the expected Batch/Session pattern, then fallback to first visible option.
        expected_session_opt = page.get_by_role(
            "option",
            name=re.compile(r"Batch\s*1.*Session.*\d{4}-\d{2}-\d{2}", re.I),
        )
        if expected_session_opt.count() > 0:
            expected_session_opt.first.click()
        else:
            all_options = page.get_by_role("option")
            option_count = all_options.count()
            clicked = False
            for i in range(option_count):
                opt = all_options.nth(i)
                if opt.is_visible():
                    opt.click()
                    clicked = True
                    break
            if not clicked:
                page.locator("mat-option").first.click()
        time.sleep(0.2)

        page.get_by_role("textbox", name="Session Name").fill("Session 1")

        if os.path.isfile(video_file_path):
            file_inputs = page.locator('input[type="file"]')
            if file_inputs.count() > 0:
                file_inputs.last.set_input_files(video_file_path)
            page.get_by_role("button", name="Add Video").click()
        else:
            page.get_by_role("button", name="Skip").click()

        page.get_by_role("button", name = "Save and Continue").click()

        page.wait_for_load_state("networkidle")
        time.sleep(0.3)

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
                    return
                time.sleep(0.2)

        # Ensure Subscription Enrollment checkbox is checked.
        subscription_checkbox = page.get_by_role("checkbox", name=re.compile(r"Subscription Enrollment", re.I)).first
        expect(subscription_checkbox).to_be_visible(timeout=10000)
        try:
            if not subscription_checkbox.is_checked():
                subscription_checkbox.check()
        except Exception:
            subscription_checkbox.click()

        # Select # Terms = 8
        terms_combo = page.get_by_role("combobox", name=re.compile(r"#\s*Terms", re.I)).first
        expect(terms_combo).to_be_visible(timeout=10000)
        try:
            terms_combo.locator("svg").first.click()
        except Exception:
            terms_combo.click()
        page.get_by_role("option", name="8").first.click()

        def _add_price(currency: str, amount: str) -> None:
            currency_combo = page.get_by_role("combobox", name=re.compile(r"Currency", re.I)).first
            try:
                currency_combo.locator("svg, path, span").first.click()
            except Exception:
                currency_combo.click()
            page.get_by_role("option", name=currency).first.click()
            amount_box = page.get_by_role("textbox", name=re.compile(r"Full Course Amount|Amount", re.I)).first
            try:
                amount_box.fill(amount)
            except Exception:
                # Some Material labels intercept pointer events during click/focus transitions.
                # Force value through JS fallback and trigger input/change events.
                handle = amount_box.element_handle()
                if handle:
                    page.evaluate(
                        """(el, val) => {
                            el.value = val;
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                            el.dispatchEvent(new Event('change', { bubbles: true }));
                        }""",
                        handle,
                        amount,
                    )
            add_btn = page.get_by_role("button", name="Add", exact=True).first
            expect(add_btn).to_be_enabled(timeout=5000)
            add_btn.click()
            time.sleep(0.2)

        # Add pricing rows.
        _add_price("INR", "10000")
        _add_price("USD", "1000")

        # Validate price breakup values in the right panel.
        expect(page.get_by_text(re.compile(r"Term Fee \+ GST\s*₹1,250\.00", re.I))).to_be_visible(timeout=10000)
        expect(page.get_by_text(re.compile(r"Sub Total \+ GST\s*₹10,000\.00", re.I))).to_be_visible(timeout=10000)
        expect(page.get_by_text(re.compile(r"One-time registration fee\s*₹1,840\.00", re.I))).to_be_visible(timeout=10000)
        expect(page.get_by_text(re.compile(r"Total fee\s*₹11,840\.00", re.I))).to_be_visible(timeout=10000)

        expect(page.get_by_text(re.compile(r"Term Fee \+ GST\s*\$125\.00", re.I))).to_be_visible(timeout=10000)
        expect(page.get_by_text(re.compile(r"Sub Total \+ GST\s*\$1,000\.00", re.I))).to_be_visible(timeout=10000)
        expect(page.get_by_text(re.compile(r"One-time registration fee\s*\$20\.00", re.I))).to_be_visible(timeout=10000)
        expect(page.get_by_text(re.compile(r"Total fee\s*\$1,020\.00", re.I))).to_be_visible(timeout=10000)

        # Wait out transient overlays before publishing.
        _wait_loader_hidden(timeout_s=15.0)

        publish_btn = page.get_by_role("button", name="Publish Course").first
        publish_btn.wait_for(state="visible", timeout=10000)
        publish_btn.scroll_into_view_if_needed()
        expect(publish_btn).to_be_enabled(timeout=10000)
        try:
            publish_btn.click(timeout=5000)
        except PlaywrightTimeoutError:
            handle = publish_btn.element_handle()
            if handle:
                page.evaluate("(el) => el.click()", handle)

        # Some org themes show a dialog-level publish confirmation.
        confirm_publish = page.get_by_role("dialog").get_by_role("button", name=re.compile(r"^Publish$", re.I))
        for _ in range(10):
            if confirm_publish.count() > 0 and confirm_publish.first.is_visible():
                confirm_publish.first.click()
                break
            time.sleep(0.2)

        # Retry once if still on create page.
        if "/create-course" in page.url and publish_btn.is_visible():
            _wait_loader_hidden(timeout_s=10.0)
            try:
                publish_btn.click(timeout=4000)
            except PlaywrightTimeoutError:
                handle = publish_btn.element_handle()
                if handle:
                    page.evaluate("(el) => el.click()", handle)

        _wait_loader_hidden(timeout_s=30.0)
        page.wait_for_load_state("networkidle")

