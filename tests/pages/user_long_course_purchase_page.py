import re
import time

import pytest
from playwright.sync_api import Page, expect

from config import BASE_URL
from helpers.auth import login_as_admin, login_as_user, sign_out


class UserLongCoursePurchasePage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.selected_course_title: str = ""

    def go_to_courses_landing(self) -> None:
        candidate_paths = ["/", "/landing/lms/user/courses", "/landing/lms/courses"]
        cards = "mat-card, [class*='course-card'], [class*='course_card'], app-course-card"
        for path in candidate_paths:
            self.page.goto(f"{BASE_URL}{path}")
            self.page.wait_for_load_state("networkidle")
            if self.page.locator(cards).count() > 0:
                return
        pytest.fail(f"Courses landing not found. Last url: {self.page.url}")

    def _click_all_courses_nav(self) -> None:
        all_courses = self.page.get_by_text(re.compile(r"^All\s+Courses$", re.I)).first
        if all_courses.count() == 0:
            all_courses = self.page.get_by_role("link", name=re.compile(r"All\s+Courses", re.I)).first
        if all_courses.count() > 0 and all_courses.is_visible():
            all_courses.click()
            try:
                self.page.wait_for_load_state("networkidle")
            except Exception:
                pass

    def filter_long_courses(self) -> None:
        self._click_all_courses_nav()
        opened = False
        mat_trigger = self.page.locator("[id^='mat-select-value-']").first
        if mat_trigger.count() > 0 and mat_trigger.is_visible():
            mat_trigger.click()
            opened = True
        if not opened:
            combo = self.page.get_by_role("combobox", name=re.compile(r"All", re.I)).first
            if combo.count() > 0 and combo.is_visible():
                try:
                    combo.locator("svg").first.click()
                except Exception:
                    combo.click()
                opened = True
        if not opened:
            pytest.fail("Could not open course-type filter.")

        long_label = re.compile(r"^\s*Long\s*Courses?\s*$", re.I)
        long_opt = self.page.locator("mat-option").filter(has_text=long_label).first
        if long_opt.count() == 0:
            long_opt = self.page.locator("span.mdc-list-item__primary-text").filter(has_text=long_label).first
        if long_opt.count() == 0:
            long_opt = self.page.get_by_role("option", name=re.compile(r"Long\s*Courses?", re.I)).first
        if long_opt.count() == 0:
            long_opt = self.page.get_by_text(long_label).first
        expect(long_opt).to_be_visible(timeout=10000)
        long_opt.click()
        self.page.wait_for_load_state("networkidle")
        time.sleep(2)

    def _extract_title(self, card) -> str:
        title_loc = card.locator("mat-card-title, h1, h2, h3, [class*='course-title'], [class*='title'], [class*='heading']").first
        try:
            if title_loc.count() > 0:
                raw = title_loc.inner_text().strip()
            else:
                raw = card.inner_text().strip()
        except Exception:
            return ""
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        return lines[0] if lines else raw

    @staticmethod
    def _is_effectively_disabled(button) -> bool:
        """Handle disabled detection across native/material button variants."""
        try:
            if button.is_disabled():
                return True
        except Exception:
            pass
        try:
            if not button.is_enabled():
                return True
        except Exception:
            pass
        try:
            aria_disabled = (button.get_attribute("aria-disabled") or "").strip().lower()
            if aria_disabled in ("true", "1"):
                return True
        except Exception:
            pass
        try:
            classes = (button.get_attribute("class") or "").lower()
            if "disabled" in classes:
                return True
        except Exception:
            pass
        return False

    def select_first_non_enrolled_long_course(self, name_hint: str = "") -> str:
        self.filter_long_courses()
        cards_locator = "mat-card, [class*='course-card'], [class*='course_card'], app-course-card"
        cards = self.page.locator(cards_locator)
        cards.first.wait_for(state="visible", timeout=20000)

        max_cards = min(cards.count(), 30)
        preferred_indices = []
        other_indices = []

        for i in range(max_cards):
            card = cards.nth(i)
            unpublished = card.locator("[class*='unpublished-badge']").first
            if unpublished.count() > 0 and unpublished.is_visible():
                continue
            enrolled = card.locator(".enrolled, [class~='enrolled'], [class*='enrolled-badge'], [class*='enrolled']").first
            if enrolled.count() > 0 and enrolled.is_visible():
                continue
            enrolled_text = card.get_by_text(re.compile(r"\bEnrolled\b", re.I)).first
            if enrolled_text.count() > 0 and enrolled_text.is_visible():
                continue

            title = self._extract_title(card)
            if not title:
                continue
            if name_hint and name_hint.lower() in title.lower():
                preferred_indices.append(i)
            else:
                other_indices.append(i)

        candidate_indices = preferred_indices + other_indices
        if not candidate_indices:
            pytest.fail("No non-enrolled published long course found.")

        for idx in candidate_indices:
            # Re-query cards each loop in case listing re-rendered.
            cards = self.page.locator(cards_locator)
            current_count = cards.count()
            if idx >= current_count:
                continue
            card = cards.nth(idx)
            title = self._extract_title(card)
            if not title:
                continue
            thumb = card.locator(".thumb, [class*='thumb'], img, [class*='image']").first
            try:
                if thumb.count() > 0 and thumb.is_visible():
                    thumb.scroll_into_view_if_needed()
                    thumb.click()
                else:
                    card.scroll_into_view_if_needed()
                    card.click()
            except Exception:
                try:
                    card.click()
                except Exception:
                    continue

            apply_now = self.page.get_by_role("button", name=re.compile(r"Apply\s*Now", re.I)).first
            pay_now = self.page.get_by_role("button", name=re.compile(r"Pay\s*Now", re.I)).first
            details = self.page.get_by_role("button", name=re.compile(r"Course\s*Details", re.I)).first

            opened = False
            deadline = time.time() + 20
            while time.time() < deadline:
                try:
                    if (apply_now.count() > 0 and apply_now.is_visible()) or (pay_now.count() > 0 and pay_now.is_visible()) or (
                        details.count() > 0 and details.is_visible()
                    ):
                        opened = True
                        break
                except Exception:
                    pass
                time.sleep(0.5)

            if not opened:
                continue

            # If Apply Now exists but is disabled, course is already applied.
            # Go back to list and try the next non-enrolled course.
            if apply_now.count() > 0 and apply_now.is_visible():
                try:
                    if self._is_effectively_disabled(apply_now):
                        self.go_to_courses_landing()
                        self.filter_long_courses()
                        continue
                except Exception:
                    pass

            self.selected_course_title = title
            return title

        pytest.fail("Found long-course cards, but none had an enabled Apply Now / eligible state.")

    def apply_now_for_selected_course(self, *, reason: str, artistic_background: str, portfolio_link: str) -> None:
        apply_now = self.page.get_by_role("button", name=re.compile(r"Apply\s*Now", re.I)).first
        expect(apply_now).to_be_visible(timeout=30000)
        apply_now.click()

        modal = self.page.locator("app-apply-now")
        expect(modal).to_be_visible(timeout=15000)

        # Select first available batch card/chip if shown
        batch_choice = modal.locator("mat-card, [class*='batch'], .batch-card, .batch-item").first
        try:
            if batch_choice.count() > 0 and batch_choice.is_visible():
                batch_choice.click()
        except Exception:
            pass

        reason_box = self.page.get_by_role("textbox", name=re.compile(r"Reason for Apply", re.I)).first
        expect(reason_box).to_be_visible(timeout=10000)
        reason_box.fill(reason)

        bg_box = self.page.get_by_role("textbox", name=re.compile(r"Artistic Background", re.I)).first
        if bg_box.count() > 0 and bg_box.is_visible():
            bg_box.fill(artistic_background)

        portfolio_box = self.page.get_by_role("textbox", name=re.compile(r"Portfolio Link", re.I)).first
        if portfolio_box.count() > 0 and portfolio_box.is_visible():
            portfolio_box.fill(portfolio_link)

        apply_modal_btn = modal.get_by_role("button", name=re.compile(r"Apply\s*Now", re.I)).first
        expect(apply_modal_btn).to_be_visible(timeout=10000)
        apply_modal_btn.click()

        expect(self.page.get_by_text(re.compile(r"Course applied successfully", re.I))).to_be_visible(timeout=15000)

    def admin_accept_application(self, *, admin_email: str, learner_email: str, selected_course_title: str, manual_otp: bool = True) -> None:
        sign_out(self.page)
        self.page.goto(f"{BASE_URL}/auth/sign-in")
        self.page.wait_for_load_state("networkidle")
        login_as_admin(self.page, email=admin_email, manual_otp=manual_otp, wait_for_navigation=True)

        crm_entry = self.page.get_by_text(re.compile(r"CRM", re.I)).first
        expect(crm_entry).to_be_visible(timeout=20000)
        crm_entry.click()
        self.page.wait_for_load_state("networkidle")

        row = self.page.get_by_role("row").filter(has_text=learner_email).filter(has_text=re.compile(re.escape(selected_course_title), re.I)).first
        expect(row).to_be_visible(timeout=30000)
        expect(row.get_by_text(re.compile(r"unpaid", re.I)).first).to_be_visible(timeout=10000)
        expect(row.get_by_text(re.compile(r"applied", re.I)).first).to_be_visible(timeout=10000)

        action_btn = row.get_by_role("button").first
        action_btn.click()
        accept_item = self.page.get_by_role("menuitem", name=re.compile(r"Accept", re.I)).first
        expect(accept_item).to_be_visible(timeout=10000)
        accept_item.click()

    def relogin_as_learner(self, *, learner_email: str, manual_otp: bool = True) -> None:
        sign_out(self.page)
        self.page.goto(f"{BASE_URL}/auth/sign-in")
        self.page.wait_for_load_state("networkidle")
        login_as_user(self.page, email=learner_email, manual_otp=manual_otp, wait_for_navigation=True)

    def open_selected_long_course_from_listing(self, selected_course_title: str) -> None:
        self.go_to_courses_landing()
        self.filter_long_courses()

        card = self.page.locator("mat-card").filter(has_text=selected_course_title).first
        expect(card).to_be_visible(timeout=30000)
        card.click()

    @staticmethod
    def _money_to_float(raw: str) -> float:
        cleaned = re.sub(r"[^0-9.]", "", raw or "")
        return float(cleaned) if cleaned else 0.0

    def learner_pay_now_and_verify(self, *, contact_number: str, vpa_success: str, registration_fee_inr: int) -> None:
        pay_now = self.page.get_by_role("button", name=re.compile(r"Pay\s*Now", re.I)).first
        expect(pay_now).to_be_visible(timeout=30000)
        pay_now.click()

        inr_radio = self.page.get_by_role("radio", name=re.compile(r"INR", re.I)).first
        if inr_radio.count() > 0 and inr_radio.is_visible():
            inr_radio.check()
        else:
            self.page.get_by_text(re.compile(r"INR\s*\(", re.I)).first.click()

        self.page.get_by_role("button", name="Next").first.click()

        # Quarterly consistency: total should equal quarterly + fixed registration fee.
        summary_text = self.page.locator("body").inner_text()
        quarter_match = re.search(r"₹\s*([0-9,]+(?:\.\d{2})?)\s*per\s*quarter", summary_text, re.I)
        total_match = re.search(r"₹\s*([0-9,]+(?:\.\d{2})?)\s*₹\s*([0-9,]+(?:\.\d{2})?)\s*per\s*quarter", summary_text, re.I)

        quarter_amt = self._money_to_float(quarter_match.group(1) if quarter_match else "0")
        total_amt = self._money_to_float(total_match.group(1) if total_match else "0")

        if quarter_amt > 0 and total_amt > 0:
            expected_total = round(quarter_amt + float(registration_fee_inr), 2)
            assert abs(total_amt - expected_total) < 0.01, (
                f"Quarterly + registration mismatch: total={total_amt}, quarter={quarter_amt}, "
                f"registration={registration_fee_inr}, expected={expected_total}"
            )

        self.page.get_by_role("button", name=re.compile(r"Proceed to Payment", re.I)).first.click()

        # Razorpay flow (adapted from short-course resilience).
        self.page.wait_for_selector("iframe", timeout=45000)
        frame = self.page.locator("iframe").first.content_frame

        contact = frame.locator("#contact, [data-testid='contactNumber'], input[name='contact'], input[type='tel']").first
        expect(contact).to_be_visible(timeout=30000)
        contact.fill(contact_number)

        try:
            frame.get_by_role("button", name=re.compile(r"Proceed", re.I)).first.click(timeout=3000)
        except Exception:
            pass

        try:
            frame.get_by_role("listitem").filter(has_text=re.compile(r"UPI", re.I)).first.click(timeout=5000)
        except Exception:
            upi_tab = frame.get_by_test_id("upi").first
            if upi_tab.count() > 0:
                upi_tab.click()

        vpa = frame.locator("#vpa-upi, [placeholder='example@okhdfcbank']").first
        expect(vpa).to_be_visible(timeout=15000)
        vpa.fill(vpa_success)

        pay_btn = frame.get_by_role("button", name=re.compile(r"Pay Now|vpa-submit", re.I)).first
        if pay_btn.count() > 0:
            pay_btn.click()

        # Wait for successful transition indicators.
        deadline = time.time() + 120
        while time.time() < deadline:
            if "payment-success" in self.page.url:
                break
            if self.page.get_by_role("button", name=re.compile(r"Course\s*Details", re.I)).count() > 0:
                break
            time.sleep(1)

    def verify_post_payment_access(self, selected_course_title: str) -> None:
        details_btn = self.page.get_by_role("button", name=re.compile(r"Course\s*Details", re.I)).first
        if details_btn.count() > 0 and details_btn.is_visible():
            details_btn.click()

        my_courses = self.page.get_by_text("My Courses").first
        expect(my_courses).to_be_visible(timeout=30000)
        my_courses.click()

        card = self.page.locator("mat-card").filter(has_text=selected_course_title).first
        expect(card).to_be_visible(timeout=30000)
        card.click()

        view_course = self.page.get_by_role("button", name=re.compile(r"View\s*Course", re.I)).first
        expect(view_course).to_be_visible(timeout=30000)
        view_course.click()
        try:
            self.page.locator("app-video-title").get_by_role("img").first.click()
        except Exception:
            pass
