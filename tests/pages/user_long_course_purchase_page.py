import json
import os
import re
import time

import pytest
from playwright.sync_api import Page, expect

from config import BASE_URL
from helpers.auth import login_as_admin, login_as_user, sign_out
from helpers import razorpay_checkout

try:
    import allure  # type: ignore
except ImportError:  # pragma: no cover
    allure = None


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

    def _debug_log(self, run_id: str, hypothesis_id: str, location: str, message: str, data: dict) -> None:
        """Append JSON lines only when DEBUG_LMS_LOG_PATH is set; never affects pass/fail."""
        path = (os.getenv("DEBUG_LMS_LOG_PATH") or "").strip()
        if not path:
            return
        payload = {
            "sessionId": "3049bc",
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=True) + "\n")
        except OSError:
            pass

    def _ensure_sign_in_form_visible(self) -> None:
        self.page.goto(f"{BASE_URL}/auth/sign-in")
        self.page.wait_for_load_state("networkidle")
        email_locator = self.page.get_by_label("Email ID", exact=False).or_(self.page.get_by_placeholder("Email ID"))
        if email_locator.count() == 0 or not email_locator.first.is_visible():
            # Fallback for sticky authenticated state: clear storage/cookies, then force sign-in.
            self.page.context.clear_cookies()
            self.page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
            self.page.goto(f"{BASE_URL}/auth/sign-in")
            self.page.wait_for_load_state("networkidle")

    def _open_module_or_batch_if_needed(self) -> None:
        """
        Some long-course UIs require opening an inner module/batch card
        before Apply/Pay actions become visible.
        """
        apply_now = self.page.get_by_role("button", name=re.compile(r"Apply\s*Now", re.I)).first
        pay_now = self.page.get_by_role("button", name=re.compile(r"Pay\s*Now", re.I)).first
        if (apply_now.count() > 0 and apply_now.is_visible()) or (pay_now.count() > 0 and pay_now.is_visible()):
            return

        # Codegen-like nudge: click an inner thumbnail/image first, then module card.
        img_candidates = self.page.get_by_role("img")
        img_count = min(img_candidates.count(), 6)
        for j in range(img_count):
            img = img_candidates.nth(j)
            try:
                if img.is_visible():
                    img.click(timeout=2000)
                    break
            except Exception:
                continue

        module_card = self.page.locator("mat-card").filter(
            has_text=re.compile(r"Module|Batch|Session|\|\s*\d+", re.I)
        ).first
        try:
            if module_card.count() > 0 and module_card.is_visible():
                module_card.click(timeout=3000)
                return
        except Exception:
            pass

        # Fallback: click first visible inner card.
        generic_card = self.page.locator("mat-card").first
        try:
            if generic_card.count() > 0 and generic_card.is_visible():
                generic_card.click(timeout=3000)
        except Exception:
            pass

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

            # In long-course flow, action buttons may appear only after opening
            # a module/batch card inside the selected course.
            self._open_module_or_batch_if_needed()
            time.sleep(1.5)
            apply_now = self.page.get_by_role("button", name=re.compile(r"Apply\s*Now", re.I)).first
            pay_now = self.page.get_by_role("button", name=re.compile(r"Pay\s*Now", re.I)).first
            details = self.page.get_by_role("button", name=re.compile(r"Course\s*Details", re.I)).first

            ready = False
            deadline = time.time() + 12
            while time.time() < deadline:
                try:
                    if (apply_now.count() > 0 and apply_now.is_visible()) or (pay_now.count() > 0 and pay_now.is_visible()) or (
                        details.count() > 0 and details.is_visible()
                    ):
                        ready = True
                        break
                except Exception:
                    pass
                time.sleep(0.5)
            if not ready:
                # Could not reach actionable state for this course; try next.
                self.go_to_courses_landing()
                self.filter_long_courses()
                continue

            # If Pay Now is already visible at first open, this course is already
            # in payment stage for this learner. Skip and try the next course.
            if pay_now.count() > 0 and pay_now.is_visible():
                self.go_to_courses_landing()
                self.filter_long_courses()
                continue

            # If Apply Now exists but is disabled, course is already applied.
            # Go back to list and try the next non-enrolled course.
            if apply_now.count() > 0 and apply_now.is_visible():
                try:
                    if self._is_effectively_disabled(apply_now):
                        # #region agent log
                        self._debug_log(
                            "pre-fix",
                            "H2",
                            "user_long_course_purchase_page.py:apply_disabled",
                            "Apply Now disabled; skip course and continue",
                            {"courseTitle": title, "idx": idx},
                        )
                        # #endregion
                        self.go_to_courses_landing()
                        self.filter_long_courses()
                        continue
                except Exception:
                    pass

            # #region agent log
            self._debug_log(
                "pre-fix",
                "H1",
                "user_long_course_purchase_page.py:selected_course",
                "Selected course deemed eligible for apply/pay flow",
                {
                    "courseTitle": title,
                    "idx": idx,
                    "applyVisible": apply_now.count() > 0 and apply_now.is_visible(),
                    "payVisible": pay_now.count() > 0 and pay_now.is_visible(),
                },
            )
            # #endregion
            self.selected_course_title = title
            return title

        # #region agent log
        self._debug_log(
            "pre-fix",
            "H1",
            "user_long_course_purchase_page.py:no_eligible_course",
            "No eligible course reached apply/pay actionable state",
            {"candidateCount": len(candidate_indices)},
        )
        # #endregion
        pytest.fail("Found long-course cards, but none had an enabled Apply Now / eligible state.")

    def apply_now_for_selected_course(self, *, reason: str, artistic_background: str, portfolio_link: str) -> None:
        apply_now = self.page.get_by_role("button", name=re.compile(r"Apply\s*Now", re.I)).first
        # #region agent log
        self._debug_log(
            "pre-fix",
            "H3",
            "user_long_course_purchase_page.py:apply_entry",
            "Entered apply_now_for_selected_course",
            {"selectedTitle": self.selected_course_title},
        )
        # #endregion
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
        # #region agent log
        self._debug_log(
            "pre-fix",
            "H3",
            "user_long_course_purchase_page.py:apply_success",
            "Course apply success toast visible",
            {"selectedTitle": self.selected_course_title},
        )
        # #endregion

    def admin_accept_application(self, *, admin_email: str, learner_email: str, selected_course_title: str, manual_otp: bool = True) -> None:
        # #region agent log
        self._debug_log(
            "pre-fix",
            "H4",
            "user_long_course_purchase_page.py:admin_accept_entry",
            "Entering admin acceptance flow",
            {"selectedTitle": selected_course_title, "manualOtp": manual_otp},
        )
        # #endregion
        sign_out(self.page)
        # #region agent log
        self._debug_log(
            "pre-fix",
            "H5",
            "user_long_course_purchase_page.py:after_sign_out",
            "After sign_out helper in admin handoff",
            {"url": self.page.url},
        )
        # #endregion
        self._ensure_sign_in_form_visible()
        email_locator = self.page.get_by_label("Email ID", exact=False).or_(self.page.get_by_placeholder("Email ID"))
        # #region agent log
        self._debug_log(
            "pre-fix",
            "H5",
            "user_long_course_purchase_page.py:before_admin_login",
            "Before login_as_admin call",
            {
                "url": self.page.url,
                "emailFieldCount": email_locator.count(),
                "crmVisible": self.page.get_by_text(re.compile(r"CRM", re.I)).first.count() > 0,
            },
        )
        # #endregion
        login_as_admin(self.page, email=admin_email, manual_otp=manual_otp, wait_for_navigation=False)

        crm_entry = self.page.get_by_text(re.compile(r"CRM", re.I)).first
        expect(crm_entry).to_be_visible(timeout=30000)
        crm_entry.click()
        self.page.wait_for_load_state("networkidle")

        row = self.page.get_by_role("row").filter(has_text=learner_email).filter(
            has_text=re.compile(re.escape(selected_course_title), re.I)
        ).first
        try:
            expect(row).to_be_visible(timeout=45000)
        except Exception:
            if allure is not None:
                try:
                    allure.attach(
                        self.page.locator("body").inner_text()[:50000],
                        name="crm_page_body_row_not_found",
                        attachment_type=allure.attachment_type.TEXT,
                    )
                except Exception:
                    pass
            raise
        expect(row.get_by_text(re.compile(r"unpaid", re.I)).first).to_be_visible(timeout=20000)
        expect(row.get_by_text(re.compile(r"applied", re.I)).first).to_be_visible(timeout=20000)

        action_btn = row.get_by_role("button").first
        action_btn.click()
        accept_item = self.page.get_by_role("menuitem", name=re.compile(r"Accept", re.I)).first
        expect(accept_item).to_be_visible(timeout=10000)
        accept_item.click()

    def relogin_as_learner(self, *, learner_email: str, manual_otp: bool = True) -> None:
        sign_out(self.page)
        self._ensure_sign_in_form_visible()
        login_as_user(self.page, email=learner_email, manual_otp=manual_otp, wait_for_navigation=True)

    def open_selected_long_course_from_listing(self, selected_course_title: str) -> None:
        self.go_to_courses_landing()
        self.filter_long_courses()

        card = self.page.locator("mat-card").filter(has_text=selected_course_title).first
        expect(card).to_be_visible(timeout=30000)
        card.click()
        # Long-course UI may require opening inner module/batch before Pay Now appears.
        self._open_module_or_batch_if_needed()

    @staticmethod
    def _money_to_float(raw: str) -> float:
        cleaned = re.sub(r"[^0-9.]", "", raw or "")
        return float(cleaned) if cleaned else 0.0

    @staticmethod
    def _normalize_title_for_assertion(title: str) -> str:
        t = title.replace("Unpublished", "").strip()
        t = re.sub(r"\s+\d{6,}$", "", t).strip()
        return t or title.strip()

    @staticmethod
    def _parse_quarterly_total_for_assertion(summary_text: str) -> tuple[float, float]:
        """Best-effort (quarterly, total) INR amounts from the payment summary body."""
        qm = re.search(r"(?:₹|Rs\.?)\s*([0-9,]+(?:\.\d{2})?)\s*per\s*quarter", summary_text, re.I)
        quarter = UserLongCoursePurchasePage._money_to_float(qm.group(1) if qm else "")

        dual = re.search(
            r"(?:₹|Rs\.?)\s*([0-9,]+(?:\.\d{2})?)\s*(?:₹|Rs\.?)\s*([0-9,]+(?:\.\d{2})?)\s*per\s*quarter",
            summary_text,
            re.I,
        )
        total = 0.0
        if dual:
            total = UserLongCoursePurchasePage._money_to_float(dual.group(1))
            if quarter <= 0:
                quarter = UserLongCoursePurchasePage._money_to_float(dual.group(2))

        if total <= 0:
            for pat in (
                r"(?:Grand\s+Total|Total\s+Amount|Amount\s+Payable|Total\s+payable)[^\n₹]*₹\s*([0-9,]+(?:\.\d{2})?)",
                r"(?:Grand\s+Total|Total\s+Amount)\s*[:\s]*₹\s*([0-9,]+(?:\.\d{2})?)",
            ):
                m = re.search(pat, summary_text, re.I)
                if m:
                    total = UserLongCoursePurchasePage._money_to_float(m.group(1))
                    break

        return quarter, total

    def learner_pay_now_and_verify(self, *, contact_number: str, vpa_success: str, registration_fee_inr: int) -> None:
        self._open_module_or_batch_if_needed()
        deadline = time.time() + 12
        pay_now = self.page.get_by_role("button", name=re.compile(r"Pay\s*Now", re.I)).first
        while time.time() < deadline:
            if pay_now.count() > 0 and pay_now.is_visible():
                break
            self._open_module_or_batch_if_needed()
            self.page.wait_for_timeout(800)
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
        quarter_amt, total_amt = self._parse_quarterly_total_for_assertion(summary_text)
        if quarter_amt > 0 and total_amt > 0:
            expected_total = round(quarter_amt + float(registration_fee_inr), 2)
            if abs(total_amt - expected_total) >= 0.01:
                if allure is not None:
                    allure.attach(
                        summary_text[:50000],
                        name="long_course_pricing_summary_mismatch",
                        attachment_type=allure.attachment_type.TEXT,
                    )
                pytest.fail(
                    f"Quarterly + registration mismatch: total={total_amt}, quarter={quarter_amt}, "
                    f"registration={registration_fee_inr}, expected={expected_total}"
                )

        self.page.get_by_role("button", name=re.compile(r"Proceed to Payment", re.I)).first.click()

        razorpay_checkout.complete_razorpay_upi_success(
            self.page, contact_number=contact_number, vpa_success=vpa_success
        )

    def is_enrolled_tag_visible(self) -> bool:
        enrolled = self.page.get_by_text(re.compile(r"Enrolled", re.I)).first
        return enrolled.count() > 0 and enrolled.is_visible()

    def verify_post_payment_access(self, selected_course_title: str) -> None:
        """Match short-course post-payment checks: details/view wait, My Courses, normalized title."""
        course_details_btn = self.page.get_by_role("button", name=re.compile(r"Course\s*Details", re.I)).first
        view_course_btn = self.page.get_by_role("button", name=re.compile(r"View\s*Course", re.I)).first

        deadline = time.time() + 60
        while time.time() < deadline:
            if course_details_btn.count() > 0 and course_details_btn.is_visible():
                course_details_btn.click()
                try:
                    self.page.wait_for_load_state("networkidle")
                except Exception:
                    pass
            if view_course_btn.count() > 0 and view_course_btn.is_visible():
                break
            time.sleep(1)

        expect(view_course_btn).to_be_visible(timeout=30000)
        view_course_btn.click()

        self.is_enrolled_tag_visible()

        try:
            self.page.locator("app-video-title").get_by_role("img").first.click()
        except Exception:
            pass

        my_courses = self.page.get_by_text("My Courses").first
        expect(my_courses).to_be_visible(timeout=30000)
        my_courses.click()
        expected_title = self._normalize_title_for_assertion(selected_course_title)
        my_course_card = self.page.locator(
            "mat-card, [class*='course-card'], [class*='course_card'], app-course-card"
        ).filter(has=self.page.get_by_text(expected_title, exact=False)).first
        expect(my_course_card).to_be_visible(timeout=30000)
        my_course_card.click()

        my_view_course_btn = self.page.get_by_role("button", name="View Course").first
        expect(my_view_course_btn).to_be_visible(timeout=30000)
        my_view_course_btn.click()

        try:
            self.page.locator("app-video-title").get_by_role("img").first.click()
        except Exception:
            pass
