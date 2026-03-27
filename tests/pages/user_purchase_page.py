import re
import time

import pytest
from playwright.sync_api import Page, expect

from config import BASE_URL


class UserPurchasePage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.selected_course_title: str = ""

    def go_to_courses_landing(self) -> None:
        # Learner landing can vary by org/theme. Try the user-facing entry first,
        # then fall back to other known routes.
        candidate_paths = [
            "/",  # matches your manual flow (click course from home)
            "/landing/lms/user/courses",
            "/landing/lms/courses",
        ]

        cards = "mat-card, [class*='course-card'], [class*='course_card'], app-course-card"
        for path in candidate_paths:
            self.page.goto(f"{BASE_URL}{path}")
            self.page.wait_for_load_state("networkidle")
            if self.page.locator(cards).count() > 0:
                return

        pytest.fail(f"Courses landing not found. Last url: {self.page.url}")

    def _extract_course_title_from_card(self, card) -> str:
        """Best-effort extraction of course title text from a course card."""
        title_loc = card.locator(
            "mat-card-title, h1, h2, h3, [class*='course-title'], [class*='title'], [class*='heading']"
        ).first
        if title_loc.count() > 0:
            raw = title_loc.inner_text().strip()
        else:
            raw = card.inner_text().strip()

        raw = raw.replace("Unpublished", "").strip()
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        return lines[0] if lines else raw

    def _normalize_title_for_assertion(self, title: str) -> str:
        t = title.replace("Unpublished", "").strip()
        # Remove trailing numeric tokens that look like dates/ids.
        t = re.sub(r"\s+\d{6,}$", "", t).strip()
        return t or title.strip()

    def select_latest_published_short_course(self) -> str:
        """Select the latest published short course card from UI."""
        return self.select_nth_published_short_course(nth_index=0)

    def _apply_short_course_dropdown_filter(self) -> None:
        """Apply filter strictly as: All -> Short Courses."""
        self.page.locator("body").click()
        all_filter = self.page.get_by_role("combobox", name="All").first
        expect(all_filter).to_be_visible(timeout=10000)
        try:
            all_filter.locator("svg").first.click()
        except Exception:
            all_filter.click()

        short_option = self.page.get_by_text("Short Courses").first
        expect(short_option).to_be_visible(timeout=10000)
        short_option.click()
        self.page.wait_for_load_state("networkidle")

    def select_nth_published_short_course(self, *, nth_index: int, exclude_title: str | None = None) -> str:
        """
        Select the Nth published short course card from UI (0-based).

        Excludes any card with a visible unpublished badge, and optionally excludes `exclude_title`.
        """
        # Strict order requested: never click any course before this filter is applied.
        self._apply_short_course_dropdown_filter()

        cards = self.page.locator("mat-card, [class*='course-card'], [class*='course_card'], app-course-card")
        cards.first.wait_for(state="visible", timeout=20000)

        normalized_exclude = self._normalize_title_for_assertion(exclude_title) if exclude_title else None
        max_cards = min(cards.count(), 24)
        published_seen = 0

        for i in range(max_cards):
            card = cards.nth(i)
            badge = card.locator("[class*='unpublished-badge']").first
            if badge.count() > 0 and badge.is_visible():
                continue
            # Skip cards that are already enrolled (green "Enrolled" tag on top-right).
            # Use class-based locator from DOM: .enrolled-badge
            enrolled_badge = card.locator("[class*='enrolled-badge']").first
            if enrolled_badge.count() > 0 and enrolled_badge.is_visible():
                continue
            # Fallback for themes that render tag text without the class.
            # Use strict text so we do NOT match strings like "Not Enrolled".
            enrolled_text = card.get_by_text(re.compile(r"^\s*Enrolled\s*$", re.I)).first
            if enrolled_text.count() > 0 and enrolled_text.is_visible():
                continue

            title = self._extract_course_title_from_card(card)
            if not title:
                continue

            if normalized_exclude and self._normalize_title_for_assertion(title) == normalized_exclude:
                continue

            if published_seen == nth_index:
                # Click the course card with the requested codegen sequence:
                # `.thumb` first -> title -> card container.
                title_el = card.locator(
                    "mat-card-title, h1, h2, h3, [class*='course-title'], [class*='title'], [class*='heading']"
                ).first
                thumb_el = card.locator(".thumb, [class*='thumb'], img, [class*='image']").first

                def _click_card_to_open_details() -> None:
                    try:
                        if thumb_el.count() > 0:
                            thumb_el.wait_for(state="visible", timeout=5000)
                            thumb_el.scroll_into_view_if_needed()
                            thumb_el.click()
                            return
                    except Exception:
                        pass
                    try:
                        if title_el.count() > 0:
                            title_el.wait_for(state="visible", timeout=5000)
                            title_el.scroll_into_view_if_needed()
                            title_el.click()
                            return
                    except Exception:
                        pass
                    card.scroll_into_view_if_needed()
                    card.click()

                def _wait_for_course_details_ui(timeout_s: float = 20.0) -> bool:
                    # After opening details, we usually see one of these.
                    candidates = [
                        self.page.get_by_role("button", name=re.compile(r"Course\s*Details", re.I)).first,
                        self.page.get_by_role("button", name=re.compile(r"Enroll\s*Now", re.I)).first,
                        self.page.get_by_role("button", name=re.compile(r"View\s*Course", re.I)).first,
                        self.page.get_by_text(re.compile(r"Enrolled", re.I)).first,
                    ]
                    deadline = time.time() + timeout_s
                    while time.time() < deadline:
                        for loc in candidates:
                            try:
                                if loc.count() > 0 and loc.is_visible():
                                    return True
                            except Exception:
                                continue
                        time.sleep(0.5)
                    return False

                # Try click + wait; retry once if details UI doesn't show up.
                opened = False
                for _ in range(2):
                    _click_card_to_open_details()
                    if _wait_for_course_details_ui(timeout_s=20.0):
                        opened = True
                        break

                if not opened:
                    pytest.fail(f"Selected course card but course details UI didn't open. title={title!r} url={self.page.url}")

                # If this opened an already-enrolled course details page (no Enroll Now),
                # continue scanning for the next non-enrolled/purchasable card.
                enroll_btn = self.page.get_by_role("button", name=re.compile(r"Enroll\\s*Now", re.I)).first
                enrolled_tag = self.page.get_by_text(re.compile(r"Enrolled", re.I)).first
                enroll_visible = enroll_btn.count() > 0 and enroll_btn.is_visible()
                enrolled_visible = enrolled_tag.count() > 0 and enrolled_tag.is_visible()
                if (not enroll_visible) and enrolled_visible:
                    # Return to listing and keep scanning for a purchasable course.
                    self.go_to_courses_landing()
                    # Re-apply the same required filter sequence.
                    self._apply_short_course_dropdown_filter()
                    cards = self.page.locator("mat-card, [class*='course-card'], [class*='course_card'], app-course-card")
                    cards.first.wait_for(state="visible", timeout=20000)
                    published_seen += 1
                    continue

                self.selected_course_title = title
                try:
                    self.page.wait_for_load_state("networkidle")
                except Exception:
                    pass
                return title

            published_seen += 1

        pytest.fail(f"No published short course card found for nth_index={nth_index} (exclude_title={exclude_title!r}).")

    def _select_razorpay_iframe_with_field(self, test_id: str):
        """Find the iframe that contains a given test id field (e.g., contactNumber)."""
        iframes = self.page.locator("iframe")
        self.page.wait_for_selector("iframe", timeout=30000)
        max_iframes = min(iframes.count(), 6)
        for i in range(max_iframes):
            frame = iframes.nth(i).content_frame()
            if not frame:
                continue
            try:
                if frame.get_by_test_id(test_id).count() > 0:
                    return frame
            except Exception:
                continue
        return None

    def enroll_inr_one_time_and_proceed(self) -> None:
        """Enroll user in a short course and proceed to payment (codegen style)."""
        enroll_btn = self.page.get_by_role("button", name="Enroll Now").first
        expect(enroll_btn).to_be_visible(timeout=30000)
        enroll_btn.click()

        # Codegen sequence uses full label text.  
        self.page.get_by_text("INR ( Indian Rupees )").first.click()
        self.page.get_by_role("button", name="Next").first.click()
        self.page.get_by_role("button", name=re.compile(r"Proceed to Payment", re.I)).first.click()

    def collect_selection_enroll_diagnostics(self) -> str:
        """Return compact diagnostics around selection->enroll boundary."""
        details_btn = self.page.get_by_role("button", name=re.compile(r"Course\s*Details", re.I)).first
        enroll_now_btn = self.page.get_by_role("button", name=re.compile(r"Enroll\s*Now", re.I)).first
        enroll_btn = self.page.get_by_role("button", name=re.compile(r"\bEnroll\b", re.I)).first
        join_btn = self.page.get_by_role("button", name=re.compile(r"\bJoin\b", re.I)).first
        return (
            f"url={self.page.url}\n"
            f"selected_course_title={self.selected_course_title}\n"
            f"course_details_visible={details_btn.count() > 0 and details_btn.is_visible()}\n"
            f"enroll_now_visible={enroll_now_btn.count() > 0 and enroll_now_btn.is_visible()}\n"
            f"enroll_visible={enroll_btn.count() > 0 and enroll_btn.is_visible()}\n"
            f"join_visible={join_btn.count() > 0 and join_btn.is_visible()}\n"
        )

    def complete_razorpay_upi_success(self, *, contact_number: str, vpa_success: str) -> None:
        """Complete Razorpay UPI payment using codegen-like UPI path."""
        razor_frame = self._select_razorpay_iframe_with_field("contactNumber")
        if razor_frame is None:
            pytest.fail("Could not find Razorpay iframe containing contactNumber field.")

        razor_frame.get_by_test_id("contactNumber").click()
        razor_frame.get_by_test_id("contactNumber").fill(contact_number)
        razor_frame.get_by_test_id("upi").click()

        vpa_input = razor_frame.get_by_placeholder("example@okhdfcbank")
        vpa_input.click()
        vpa_input.fill(vpa_success)
        # Codegen flow: choose the '@razorpay' suggestion option.
        vpa_input.press("ArrowDown")
        razor_frame.get_by_role("button", name="@razorpay").click()
        razor_frame.get_by_test_id("vpa-submit").click()

        # Wait for success page controls to show up.
        success_deadline = time.time() + 120
        while time.time() < success_deadline:
            if "payment-success" in self.page.url:
                break
            if self.page.get_by_role("button", name="Course Details").count() > 0:
                break
            time.sleep(1)

    def verify_post_payment_course_access(self, user_title: str) -> None:
        """Verify post-payment course access via Course Details + My Courses."""
        course_details_btn = self.page.get_by_role("button", name="Course Details").first
        if course_details_btn.count() > 0 and course_details_btn.is_visible():
            course_details_btn.click()

        view_course_btn = self.page.get_by_role("button", name="View Course").first
        expect(view_course_btn).to_be_visible(timeout=30000)
        view_course_btn.click()

        enrolled_visible = self.is_enrolled_tag_visible()

        # Best-effort: open a video entry if present
        try:
            self.page.locator("app-video-title").get_by_role("img").first.click()
        except Exception:
            pass

        self.page.get_by_text("My Courses").first.click()
        expected_title = self._normalize_title_for_assertion(user_title)
        expect(self.page.get_by_text(expected_title, exact=False)).to_be_visible(timeout=30000)

        return enrolled_visible

    def is_enrolled_tag_visible(self) -> bool:
        """
        Check if the course page shows an "Enrolled" tag/pill (like the provided screenshot).
        """
        enrolled = self.page.get_by_text(re.compile(r"Enrolled", re.I)).first
        return enrolled.count() > 0 and enrolled.is_visible()

