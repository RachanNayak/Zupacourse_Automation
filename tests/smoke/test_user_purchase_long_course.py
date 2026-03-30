"""Smoke test: Learner applies and pays for a long course after admin acceptance."""

import os

import allure
import pytest
from playwright.sync_api import Page

from config import (
    ADMIN_EMAIL,
    LONG_COURSE_REGISTRATION_FEE_INR,
    MANUAL_OTP,
    USER_APPLY_REASON,
    USER_ARTISTIC_BACKGROUND,
    USER_EMAIL,
    USER_LONG_COURSE_NAME_HINT,
    USER_LONG_PAYMENT_CONTACT_NUMBER,
    USER_LONG_PAYMENT_VPA,
    USER_MANUAL_OTP,
    USER_PORTFOLIO_LINK,
)
from helpers.auth import login_as_user
from tests.pages.user_long_course_purchase_page import UserLongCoursePurchasePage


@allure.epic("LMS Learner")
@allure.feature("Long Course Purchase")
@allure.story("Apply, Admin Accept, Then Pay")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.smoke
def test_user_purchase_long_course(page: Page) -> None:
    if not USER_EMAIL:
        pytest.skip("USER_EMAIL is not set. Add USER_EMAIL in .env/config for long-course purchase tests.")

    long_purchase = UserLongCoursePurchasePage(page)

    with allure.step("Learner login and open long-courses listing"):
        login_as_user(page, email=USER_EMAIL, manual_otp=USER_MANUAL_OTP, wait_for_navigation=True)
        long_purchase.go_to_courses_landing()
        selected_title = long_purchase.select_first_non_enrolled_long_course(
            name_hint=USER_LONG_COURSE_NAME_HINT
        )
        allure.dynamic.title(f"User long-course apply/pay: {selected_title}")
        allure.attach(selected_title, "Selected long course", allure.attachment_type.TEXT)

    with allure.step("Learner applies to selected long course"):
        long_purchase.apply_now_for_selected_course(
            reason=USER_APPLY_REASON,
            artistic_background=USER_ARTISTIC_BACKGROUND,
            portfolio_link=USER_PORTFOLIO_LINK,
        )

    with allure.step("Admin validates CRM row and accepts application"):
        long_purchase.admin_accept_application(
            admin_email=ADMIN_EMAIL,
            learner_email=USER_EMAIL,
            selected_course_title=selected_title,
            manual_otp=MANUAL_OTP,
        )

    with allure.step("Learner relogs, sees Pay Now, and pays quarterly fee"):
        long_purchase.relogin_as_learner(learner_email=USER_EMAIL, manual_otp=USER_MANUAL_OTP)
        long_purchase.open_selected_long_course_from_listing(selected_title)
        long_purchase.learner_pay_now_and_verify(
            contact_number=USER_LONG_PAYMENT_CONTACT_NUMBER or os.getenv("USER_PAYMENT_CONTACT_NUMBER", "6360295267"),
            vpa_success=USER_LONG_PAYMENT_VPA or os.getenv("USER_PAYMENT_VPA", "success@razorpay"),
            registration_fee_inr=LONG_COURSE_REGISTRATION_FEE_INR,
        )

    with allure.step("Verify post-payment access"):
        long_purchase.verify_post_payment_access(selected_title)

