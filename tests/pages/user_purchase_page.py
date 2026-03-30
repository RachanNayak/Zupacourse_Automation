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

    def _click_all_courses_nav(self) -> None:
        """After login: click 'All Courses' so the learner course listing is active."""
        all_courses = self.page.get_by_text(re.compile(r"^All\s+Courses$", re.I)).first
        if all_courses.count() == 0:
            all_courses = self.page.get_by_role("link", name=re.compile(r"All\s+Courses", re.I)).first
        if all_courses.count() > 0 and all_courses.is_visible():
            all_courses.click()
            try:
                self.page.wait_for_load_state("networkidle")
            except Exception:
                pass

    def _open_course_type_filter_and_select_short(self) -> None:
        """
        Top filter dropdown: All | Short Courses | Long Courses (mat-select).
        Open it and choose Short Courses.
        """
        # Click the closed control showing "All" (mat-select trigger or combobox).
        opened = False
        mat_trigger = self.page.locator("[id^='mat-select-value-']").first
        if mat_trigger.count() > 0 and mat_trigger.is_visible():
            mat_trigger.click()
            opened = True
        if not opened:
            combo = self.page.get_by_role("combobox", name=re.compile(r"^All$", re.I)).first
            if combo.count() > 0 and combo.is_visible():
                try:
                    combo.locator("svg").first.click()
                except Exception:
                    combo.click()
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
            pytest.fail("Could not open course-type filter (All / Short / Long).")

        short_label = re.compile(r"^\s*Short\s*Courses?\s*$", re.I)
        # Panel options are often mat-option with label in span.mdc-list-item__primary-text.
        short_option = (
            self.page.locator("mat-option").filter(has_text=short_label).first
        )
        if short_option.count() == 0:
            short_option = (
                self.page.locator("span.mdc-list-item__primary-text").filter(has_text=short_label).first
            )
        if short_option.count() == 0:
            short_option = self.page.get_by_role("option", name=re.compile(r"Short\s*Courses?", re.I)).first
        if short_option.count() == 0:
            short_option = self.page.get_by_text(short_label).first
        expect(short_option).to_be_visible(timeout=10000)
        short_option.click()
        self.page.wait_for_load_state("networkidle")
        time.sleep(2)

    def _apply_short_course_dropdown_filter(self) -> None:
        """
        User flow: (1) click All Courses, (2) open top filter, (3) select Short Courses.
        Then iterate cards and skip any with Enrolled tag (handled in select_nth_*).
        """
        self._click_all_courses_nav()
        self._open_course_type_filter_and_select_short()

    def select_nth_published_short_course(self, *, nth_index: int, exclude_title: str | None = None) -> str:
        """
        Select the Nth purchasable short course (0-based).

        Flow: All Courses -> filter Short Courses -> scan cards; skip unpublished and
        any card showing an Enrolled tag (already purchased). Optionally skip
        `exclude_title` for a second purchase.
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
            # Skip cards that are already purchased.
            # Match your DOM variants: class="enrolled ..." and older enrolled-badge styles.
            enrolled_badge = card.locator(
                ".enrolled, [class~='enrolled'], [class*='enrolled-badge'], [class*='enrolled']"
            ).first
            if enrolled_badge.count() > 0 and enrolled_badge.is_visible():
                continue
            # Text fallback in case class names change.
            enrolled_text = card.get_by_text(re.compile(r"\bEnrolled\b", re.I)).first
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
                        self.page.get_by_role("button", name=re.compile(r"Apply\s*Now", re.I)).first,
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
                enroll_btn = self.page.get_by_role("button", name=re.compile(r"(Apply|Enroll)\s*Now", re.I)).first
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
        self.page.wait_for_selector("iframe", timeout=45000)
        deadline = time.time() + 45
        while time.time() < deadline:
            iframes = self.page.locator("iframe")
            max_iframes = min(iframes.count(), 10)
            for i in range(max_iframes):
                frame_loc = iframes.nth(i).content_frame
                try:
                    # Primary locator from codegen.
                    field = frame_loc.get_by_test_id(test_id)
                    if field.count() > 0:
                        field.first.wait_for(state="visible", timeout=2000)
                        return frame_loc
                except Exception:
                    pass
                try:
                    # Fallbacks for Razorpay UI variants.
                    alt_contact = frame_loc.locator(
                        "[data-testid='contactNumber'], input[name='contact'], input[type='tel']"
                    ).first
                    if alt_contact.count() > 0 and alt_contact.is_visible():
                        return frame_loc
                except Exception:
                    continue
            time.sleep(1)
        return None

    def enroll_inr_one_time_and_proceed(self) -> None:
        """Enroll user in a short course and proceed to payment (codegen style)."""
        apply_now_btn = self.page.get_by_role("button", name=re.compile(r"Apply\s*Now", re.I)).first
        enroll_now_btn = self.page.get_by_role("button", name=re.compile(r"Enroll\s*Now", re.I)).first
        if apply_now_btn.count() > 0 and apply_now_btn.is_visible():
            apply_now_btn.click()
        else:
            expect(enroll_now_btn).to_be_visible(timeout=30000)
            enroll_now_btn.click()

        inr_radio = self.page.get_by_role("radio", name=re.compile(r"INR\s*\(\s*Indian Rupees\s*\)", re.I)).first
        if inr_radio.count() > 0 and inr_radio.is_visible():
            inr_radio.check()
        else:
            self.page.get_by_text("INR ( Indian Rupees )").first.click()
        self.page.get_by_role("button", name="Next").first.click()
        self.page.get_by_role("button", name=re.compile(r"Proceed to Payment", re.I)).first.click()

    def collect_selection_enroll_diagnostics(self) -> str:
        """Return compact diagnostics around selection->enroll boundary."""
        details_btn = self.page.get_by_role("button", name=re.compile(r"Course\s*Details", re.I)).first
        apply_now_btn = self.page.get_by_role("button", name=re.compile(r"Apply\s*Now", re.I)).first
        enroll_now_btn = self.page.get_by_role("button", name=re.compile(r"Enroll\s*Now", re.I)).first
        enroll_btn = self.page.get_by_role("button", name=re.compile(r"\bEnroll\b", re.I)).first
        join_btn = self.page.get_by_role("button", name=re.compile(r"\bJoin\b", re.I)).first
        return (
            f"url={self.page.url}\n"
            f"selected_course_title={self.selected_course_title}\n"
            f"course_details_visible={details_btn.count() > 0 and details_btn.is_visible()}\n"
            f"apply_now_visible={apply_now_btn.count() > 0 and apply_now_btn.is_visible()}\n"
            f"enroll_now_visible={enroll_now_btn.count() > 0 and enroll_now_btn.is_visible()}\n"
            f"enroll_visible={enroll_btn.count() > 0 and enroll_btn.is_visible()}\n"
            f"join_visible={join_btn.count() > 0 and join_btn.is_visible()}\n"
        )

    def complete_razorpay_upi_success(self, *, contact_number: str, vpa_success: str) -> None:
        """Complete Razorpay UPI payment using codegen-like UPI path."""
        razor_frame = self._select_razorpay_iframe_with_field("contactNumber")
        if razor_frame is None:
            pytest.fail(f"Could not find Razorpay iframe containing contact field. url={self.page.url}")

        expect(razor_frame.get_by_test_id("contactNumber")).to_be_visible(timeout=30000)
        razor_frame.get_by_test_id("contactNumber").click()
        razor_frame.get_by_test_id("contactNumber").fill(contact_number)
        expect(razor_frame.get_by_test_id("upi")).to_be_visible(timeout=15000)
        razor_frame.get_by_test_id("upi").click()

        vpa_input = razor_frame.get_by_placeholder("example@okhdfcbank")
        expect(vpa_input).to_be_visible(timeout=15000)
        vpa_input.click()
        vpa_input.fill(vpa_success)
        # Codegen flow may show '@razorpay' suggestion; click it if present.
        try:
            vpa_input.press("ArrowDown")
            suggestion = razor_frame.get_by_role("button", name="@razorpay").first
            if suggestion.count() > 0:
                suggestion.wait_for(state="visible", timeout=3000)
                suggestion.click()
            else:
                vpa_input.press("Enter")
        except Exception:
            # In some runs suggestion list never appears; continue with entered VPA.
            vpa_input.press("Enter")
        submit_btn = razor_frame.get_by_test_id("vpa-submit")
        expect(submit_btn).to_be_visible(timeout=15000)
        try:
            submit_btn.click(timeout=5000)
        except Exception:
            # Razorpay may transition to success overlay very quickly, making
            # submit temporarily covered/detached. If success is already visible,
            # continue flow instead of failing here.
            success_in_frame = False
            try:
                success_heading = razor_frame.get_by_text(re.compile(r"Payment Successful", re.I)).first
                success_in_frame = success_heading.count() > 0 and success_heading.is_visible()
            except Exception:
                success_in_frame = False
            if not success_in_frame and "payment-success" not in self.page.url:
                try:
                    submit_btn.click(timeout=3000, force=True)
                except Exception:
                    pass

        # Wait for success page controls to show up.
        success_deadline = time.time() + 120
        while time.time() < success_deadline:
            if "payment-success" in self.page.url:
                break
            if self.page.get_by_role("button", name="Course Details").count() > 0:
                break
            try:
                if razor_frame.get_by_text(re.compile(r"Payment Successful", re.I)).count() > 0:
                    break
            except Exception:
                pass
            time.sleep(1)

    def verify_post_payment_course_access(self, user_title: str) -> None:
        """Verify post-payment course access via Course Details + My Courses."""
        course_details_btn = self.page.get_by_role("button", name=re.compile(r"Course\s*Details", re.I)).first
        view_course_btn = self.page.get_by_role("button", name=re.compile(r"View\s*Course", re.I)).first

        # Post-payment UI can take time; wait until details or view action appears.
        deadline = time.time() + 60
        while time.time() < deadline:
            if course_details_btn.count() > 0 and course_details_btn.is_visible():
                course_details_btn.click()
                # After opening details, give UI a short moment to render CTA buttons.
                try:
                    self.page.wait_for_load_state("networkidle")
                except Exception:
                    pass
            if view_course_btn.count() > 0 and view_course_btn.is_visible():
                break
            time.sleep(1)

        expect(view_course_btn).to_be_visible(timeout=30000)
        view_course_btn.click()

        enrolled_visible = self.is_enrolled_tag_visible()

        # Best-effort: open a video entry if present
        try:
            self.page.locator("app-video-title").get_by_role("img").first.click()
        except Exception:
            pass

        my_courses = self.page.get_by_text("My Courses").first
        expect(my_courses).to_be_visible(timeout=30000)
        my_courses.click()
        expected_title = self._normalize_title_for_assertion(user_title)
        my_course_card = self.page.locator("mat-card, [class*='course-card'], [class*='course_card'], app-course-card").filter(
            has=self.page.get_by_text(expected_title, exact=False)
        ).first
        expect(my_course_card).to_be_visible(timeout=30000)
        my_course_card.click()

        my_view_course_btn = self.page.get_by_role("button", name="View Course").first
        expect(my_view_course_btn).to_be_visible(timeout=30000)
        my_view_course_btn.click()

        try:
            self.page.locator("app-video-title").get_by_role("img").first.click()
        except Exception:
            pass

        return enrolled_visible

    def is_enrolled_tag_visible(self) -> bool:
        """
        Check if the course page shows an "Enrolled" tag/pill (like the provided screenshot).
        """
        enrolled = self.page.get_by_text(re.compile(r"Enrolled", re.I)).first
        return enrolled.count() > 0 and enrolled.is_visible()

