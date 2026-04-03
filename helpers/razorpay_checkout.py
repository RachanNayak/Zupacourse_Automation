"""Shared Razorpay embedded-checkout UPI success path for Playwright tests."""
from __future__ import annotations

import re
import time

import pytest
from playwright.sync_api import Page, expect


def select_razorpay_iframe_with_field(page: Page, test_id: str, timeout_sec: float = 45):
    """Return the iframe content frame that contains the given test id (e.g. contactNumber)."""
    page.wait_for_selector("iframe", timeout=45000)
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        iframes = page.locator("iframe")
        max_iframes = min(iframes.count(), 10)
        for i in range(max_iframes):
            frame_loc = iframes.nth(i).content_frame
            try:
                field = frame_loc.get_by_test_id(test_id)
                if field.count() > 0:
                    field.first.wait_for(state="visible", timeout=2000)
                    return frame_loc
            except Exception:
                pass
            try:
                alt_contact = frame_loc.locator(
                    "[data-testid='contactNumber'], input[name='contact'], input[type='tel']"
                ).first
                if alt_contact.count() > 0 and alt_contact.is_visible():
                    return frame_loc
            except Exception:
                continue
        time.sleep(1)
    return None


def complete_razorpay_upi_success(page: Page, *, contact_number: str, vpa_success: str) -> None:
    """Complete Razorpay UPI payment using the same sequence as short-course smoke tests."""
    razor_frame = select_razorpay_iframe_with_field(page, "contactNumber")
    if razor_frame is None:
        pytest.fail(f"Could not find Razorpay iframe containing contact field. url={page.url}")

    expect(razor_frame.get_by_test_id("contactNumber")).to_be_visible(timeout=30000)
    razor_frame.get_by_test_id("contactNumber").click()
    razor_frame.get_by_test_id("contactNumber").fill(contact_number)
    expect(razor_frame.get_by_test_id("upi")).to_be_visible(timeout=15000)
    razor_frame.get_by_test_id("upi").click()

    vpa_input = razor_frame.get_by_placeholder("example@okhdfcbank")
    expect(vpa_input).to_be_visible(timeout=15000)
    vpa_input.click()
    vpa_input.fill(vpa_success)
    try:
        vpa_input.press("ArrowDown")
        suggestion = razor_frame.get_by_role("button", name="@razorpay").first
        if suggestion.count() > 0:
            suggestion.wait_for(state="visible", timeout=3000)
            suggestion.click()
        else:
            vpa_input.press("Enter")
    except Exception:
        vpa_input.press("Enter")
    submit_btn = razor_frame.get_by_test_id("vpa-submit")
    expect(submit_btn).to_be_visible(timeout=15000)
    try:
        submit_btn.click(timeout=5000)
    except Exception:
        success_in_frame = False
        try:
            success_heading = razor_frame.get_by_text(re.compile(r"Payment Successful", re.I)).first
            success_in_frame = success_heading.count() > 0 and success_heading.is_visible()
        except Exception:
            success_in_frame = False
        if not success_in_frame and "payment-success" not in page.url:
            try:
                submit_btn.click(timeout=3000, force=True)
            except Exception:
                pass

    success_deadline = time.time() + 120
    while time.time() < success_deadline:
        if "payment-success" in page.url:
            break
        if page.get_by_role("button", name=re.compile(r"Course\s*Details", re.I)).count() > 0:
            break
        try:
            if razor_frame.get_by_text(re.compile(r"Payment Successful", re.I)).count() > 0:
                break
        except Exception:
            pass
        time.sleep(1)
