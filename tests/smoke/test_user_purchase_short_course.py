"""Smoke test: Learner purchases a published short course (admin-created)."""

import os
import allure
import pytest
from playwright.sync_api import Page

from config import USER_EMAIL, USER_MANUAL_OTP
from helpers.auth import login_as_user
from tests.pages.user_purchase_page import UserPurchasePage


@allure.epic("LMS Learner")
@allure.feature("Course Purchase")
@allure.story("Purchase Published Short Course")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.smoke
def test_user_purchase_short_course(page: Page) -> None:
    """
    User-side flow:
    - login as learner
    - pick latest published short course from UI
    - enroll and complete Razorpay UPI success path
    - verify in "My Courses"
    """
    if not USER_EMAIL:
        pytest.skip("USER_EMAIL is not set. Add USER_EMAIL in .env/config for user purchase tests.")

    user_title: str = ""
    user_purchase = UserPurchasePage(page)

    with allure.step("Login as learner user"):
        login_as_user(page, email=USER_EMAIL, manual_otp=USER_MANUAL_OTP, wait_for_navigation=True)
        # Ensure user is on landing/courses
        user_purchase.go_to_courses_landing()

    with allure.step("Select latest published short course card"):
        user_title = user_purchase.select_latest_published_short_course()
        allure.dynamic.title(f"User purchases short course: {user_title}")
        allure.attach(user_title, name="Selected course title", attachment_type=allure.attachment_type.TEXT)

    with allure.step("Enroll and proceed to payment"):
        user_purchase.enroll_inr_one_time_and_proceed()

    with allure.step("Complete Razorpay UPI payment"):
        contact_number = os.getenv("USER_PAYMENT_CONTACT_NUMBER", "6360295267")
        vpa_success = os.getenv("USER_PAYMENT_VPA", "success@razorpay")
        user_purchase.complete_razorpay_upi_success(
            contact_number=contact_number, vpa_success=vpa_success
        )

    with allure.step("Verify post-payment course access"):
        enrolled_visible = user_purchase.verify_post_payment_course_access(user_title)

    # If we see the "Enrolled" tag, buy the next published short course as well.
    if enrolled_visible:
        with allure.step("Enrolled tag visible -> purchase second short course"):
            user_purchase.go_to_courses_landing()
            second_title = user_purchase.select_nth_published_short_course(
                nth_index=1, exclude_title=user_title
            )
            allure.dynamic.title(f"User purchases second short course: {second_title}")

            user_purchase.enroll_inr_one_time_and_proceed()

            contact_number = os.getenv("USER_PAYMENT_CONTACT_NUMBER", "6360295267")
            vpa_success = os.getenv("USER_PAYMENT_VPA", "success@razorpay")
            user_purchase.complete_razorpay_upi_success(
                contact_number=contact_number, vpa_success=vpa_success
            )
            user_purchase.verify_post_payment_course_access(second_title)

