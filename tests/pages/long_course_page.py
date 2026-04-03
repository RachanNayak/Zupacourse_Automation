import calendar
import os
import random
import re
import time
from datetime import date, datetime
from pathlib import Path

import pytest
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, expect

from helpers.long_course_pricing import (
    breakup_regex_registration_inr,
    breakup_regex_registration_usd,
    breakup_regex_subtotal_inr,
    breakup_regex_subtotal_usd,
    breakup_regex_term_fee_inr,
    breakup_regex_term_fee_usd,
    breakup_regex_total_inr,
    breakup_regex_total_usd,
    full_amount_inr_fill,
    full_amount_usd_fill,
    subscription_terms_option_label,
)


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

    @staticmethod
    def _add_calendar_years(d: date, years: int) -> date:
        """Same month/day, N calendar years later (handles Feb 29 vs non-leap)."""
        y = d.year + years
        try:
            return date(y, d.month, d.day)
        except ValueError:
            last = calendar.monthrange(y, d.month)[1]
            return date(y, d.month, min(d.day, last))

    @staticmethod
    def _parse_mat_calendar_period(text: str) -> tuple[int, int] | None:
        text = (text or "").strip()
        for fmt in ("%b %Y", "%B %Y"):
            try:
                dt = datetime.strptime(text, fmt)
                return dt.year, dt.month
            except ValueError:
                continue
        return None

    def _mat_datepicker_go_to_month(self, page: Page, year: int, month: int) -> None:
        """Navigate Material calendar until the given year/month is shown."""
        for _ in range(120):
            period = page.locator(".mat-calendar-period-button").first
            if period.count() == 0:
                break
            parsed = self._parse_mat_calendar_period(period.inner_text())
            if not parsed:
                break
            cy, cm = parsed
            if cy == year and cm == month:
                return
            delta = (year - cy) * 12 + (month - cm)
            if delta > 0:
                page.get_by_role("button", name="Next month").click()
            elif delta < 0:
                page.get_by_role("button", name="Previous month").click()
            else:
                break
            time.sleep(0.08)

    def _select_day_in_open_mat_calendar(self, target: date) -> None:
        """With the Material datepicker overlay open, go to ``target`` and select that day."""
        page = self.page
        self._mat_datepicker_go_to_month(page, target.year, target.month)
        day_btn = page.get_by_role(
            "button",
            name=re.compile(
                rf"^{re.escape(target.strftime('%B'))}\s+0*{target.day},\s*{target.year}$",
                re.I,
            ),
        ).first
        expect(day_btn).to_be_visible(timeout=10000)
        day_btn.click()
        time.sleep(0.2)

    def _select_course_form_date(self, field_has_text: str, target: date) -> None:
        """Open Start/End Date on course form and pick ``target`` (locale: English month names)."""
        page = self.page
        page.locator("mat-form-field").filter(has_text=field_has_text).get_by_label("Open calendar").click()
        time.sleep(0.3)
        self._select_day_in_open_mat_calendar(target)

    def _open_batch_calendar_and_select(self, calendar_locator, target: date) -> None:
        """Scroll to batch datepicker trigger, open it, select ``target`` (same rules as course dates)."""
        calendar_locator.first.scroll_into_view_if_needed()
        time.sleep(0.3)
        calendar_locator.first.click()
        time.sleep(0.3)
        self._select_day_in_open_mat_calendar(target)

    def _click_long_course_session_date_option(self, page: Page, session_start: date) -> None:
        """
        Pick the session row that matches Batch 1 and the batch start date (today when creating the course).
        Option text varies (ISO, slashes, or verbose English); try several patterns then visible mat-options.
        """
        ymd = session_start.strftime("%Y-%m-%d")
        mdY = f"{session_start.month}/{session_start.day}/{session_start.year}"
        mdY_padded = session_start.strftime("%m/%d/%Y")
        dmy_padded = session_start.strftime("%d/%m/%Y")
        mon_full = session_start.strftime("%B")
        mon_abbr = session_start.strftime("%b")

        patterns: list[re.Pattern[str]] = [
            re.compile(rf"Batch\s*1.*{re.escape(ymd)}", re.I | re.DOTALL),
            re.compile(rf"Batch\s*1.*{re.escape(mdY_padded)}", re.I | re.DOTALL),
            re.compile(rf"Batch\s*1.*{re.escape(mdY)}", re.I | re.DOTALL),
            re.compile(rf"Batch\s*1.*{re.escape(dmy_padded)}", re.I | re.DOTALL),
            re.compile(
                rf"Batch\s*1.*{re.escape(mon_full)}\s+0*{session_start.day}\s*,?\s*{session_start.year}",
                re.I | re.DOTALL,
            ),
            re.compile(
                rf"Batch\s*1.*{re.escape(mon_abbr)}\s+0*{session_start.day}\s*,?\s*{session_start.year}",
                re.I | re.DOTALL,
            ),
            re.compile(rf".*{re.escape(ymd)}.*", re.I),
            re.compile(r"Batch\s*1", re.I),
        ]
        for pat in patterns:
            opt = page.get_by_role("option", name=pat)
            try:
                if opt.count() > 0:
                    el = opt.first
                    if el.is_visible():
                        el.click()
                        return
            except Exception:
                continue

        all_opt = page.locator("mat-option")
        n = min(all_opt.count(), 40)
        for i in range(n):
            o = all_opt.nth(i)
            try:
                if not o.is_visible():
                    continue
                txt = o.inner_text()
                low = txt.lower()
                if "batch" in low and re.search(r"\b1\b", txt):
                    if ymd in txt or mdY in txt or mdY_padded in txt or mon_full.lower() in low or mon_abbr.lower() in low:
                        o.click()
                        return
            except Exception:
                continue
        for i in range(n):
            o = all_opt.nth(i)
            try:
                if o.is_visible():
                    o.click()
                    return
            except Exception:
                continue
        pytest.fail("Could not select a session date option from the dropdown.")

    def _set_long_course_video_file(self, page: Page, abs_path: str) -> None:
        """Attach video to the correct file input (Angular often keeps multiple inputs in the DOM)."""
        last_err: Exception | None = None
        inputs = page.locator('input[type="file"]')
        try:
            expect(inputs.first).to_be_attached(timeout=15000)
        except Exception:
            pass
        n = inputs.count()
        if n == 0:
            pytest.fail(f"No file input found for video upload (path={abs_path!r}).")
        # Prefer inputs in the add-video / session area; try from last to first (video is usually the newest control).
        order = list(range(n - 1, -1, -1)) + list(range(n))
        seen: set[int] = set()
        for idx in order:
            if idx in seen:
                continue
            seen.add(idx)
            inp = inputs.nth(idx)
            try:
                inp.set_input_files(abs_path)
                return
            except Exception as e:
                last_err = e
                continue
        pytest.fail(f"Could not set video file {abs_path!r}: {last_err}")

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

        start_d = date.today()
        end_d = self._add_calendar_years(start_d, 2)
        self._select_course_form_date("Start Date", start_d)
        self._select_course_form_date("End Date", end_d)

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
        start_d = date.today()
        end_d = self._add_calendar_years(start_d, 2)

        page.get_by_role("textbox", name="Batch Name").fill("Batch 1")
        start_date_cal = page.locator("div").filter(has_text=re.compile(r"^Start DateStart Time$")).get_by_label(
            "Open calendar"
        )
        self._open_batch_calendar_and_select(start_date_cal, start_d)
        end_date_cal = page.locator("div").filter(has_text=re.compile(r"^End DateEnd Time$")).get_by_label(
            "Open calendar"
        )
        self._open_batch_calendar_and_select(end_date_cal, end_d)
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
        non_recurring_cal = page.get_by_role("button", name="Open calendar").first
        non_recurring_cal.scroll_into_view_if_needed()
        time.sleep(0.2)
        non_recurring_cal.click()
        time.sleep(0.3)
        self._select_day_in_open_mat_calendar(start_d)
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
        # Matches batch start in create_batches (today).
        session_start = date.today()
        abs_video = (
            os.path.abspath(os.path.normpath((video_file_path or "").strip())) if (video_file_path or "").strip() else ""
        )

        module_combo = page.get_by_role("combobox", name="Select Module")
        expect(module_combo).to_be_visible(timeout=15000)
        module_combo.locator("svg").click()
        time.sleep(0.2)
        page.get_by_role("option", name="Module 1").click()
        time.sleep(0.2)

        batch_combo = page.get_by_role("combobox", name="Select Batch")
        batch_combo.locator("svg").click()
        time.sleep(0.2)
        page.get_by_role("option", name="Batch 1").click()
        time.sleep(0.3)

        session_date_combo = page.get_by_role("combobox", name="Select Session Date")
        expect(session_date_combo).to_be_visible(timeout=15000)
        session_date_combo.scroll_into_view_if_needed()
        try:
            session_date_combo.click()
        except Exception:
            session_date_combo.locator("span").first.click()

        expect(page.locator("mat-option").first).to_be_visible(timeout=15000)
        self._click_long_course_session_date_option(page, session_start)
        time.sleep(0.3)

        session_name = page.get_by_role("textbox", name="Session Name")
        expect(session_name).to_be_visible(timeout=10000)
        session_name.fill("Session 1")
        time.sleep(0.2)

        if os.path.isfile(abs_video):
            self._set_long_course_video_file(page, abs_video)
            page.get_by_role("button", name="Add Video").click()
        else:
            page.get_by_role("button", name="Skip").click()

        page.wait_for_load_state("networkidle")
        time.sleep(0.2)
        page.get_by_role("button", name="Save and Continue").click()
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
        page.get_by_role("option", name=subscription_terms_option_label()).first.click()

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

        # Add pricing rows (amounts from config via helpers).
        _add_price("INR", full_amount_inr_fill())
        _add_price("USD", full_amount_usd_fill())

        # Validate price breakup values in the right panel (derived from config).
        expect(page.get_by_text(breakup_regex_term_fee_inr())).to_be_visible(timeout=10000)
        expect(page.get_by_text(breakup_regex_subtotal_inr())).to_be_visible(timeout=10000)
        expect(page.get_by_text(breakup_regex_registration_inr())).to_be_visible(timeout=10000)
        expect(page.get_by_text(breakup_regex_total_inr())).to_be_visible(timeout=10000)

        expect(page.get_by_text(breakup_regex_term_fee_usd())).to_be_visible(timeout=10000)
        expect(page.get_by_text(breakup_regex_subtotal_usd())).to_be_visible(timeout=10000)
        expect(page.get_by_text(breakup_regex_registration_usd())).to_be_visible(timeout=10000)
        expect(page.get_by_text(breakup_regex_total_usd())).to_be_visible(timeout=10000)

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

