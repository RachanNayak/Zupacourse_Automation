"""Login helper for LMS (email + password or OTP)."""
from typing import Optional

from playwright.sync_api import Page, expect

from config import ADMIN_EMAIL as _DEFAULT_EMAIL, ADMIN_PASSWORD, BASE_URL, MANUAL_OTP_WAIT_SECONDS, TEST_OTP


def sign_out(page: Page, base_url: Optional[str] = None) -> None:
    """Sign out from the current session. Navigates to /auth/sign-out then to sign-in."""
    url = (base_url or "").rstrip("/") or BASE_URL
    page.goto(f"{url}/auth/sign-out")
    page.wait_for_load_state("networkidle")
    page.goto(f"{url}/auth/sign-in")
    page.wait_for_load_state("networkidle")


def login_as_admin(
    page: Page,
    email: Optional[str] = None,
    password: Optional[str] = None,
    *,
    manual_otp: bool = False,
    base_path: str = "/auth/sign-in",
    wait_for_navigation: bool = True,
) -> None:
    """
    Log in as admin with email and password, OTP from env, or manual OTP.

    - Set ADMIN_PASSWORD in .env for password login.
    - Set TEST_OTP in .env to fill OTP automatically.
    - Set manual_otp=True: fill email, click Continue, then wait for you to type OTP
      in the browser; after MANUAL_OTP_WAIT_SECONDS (default 90), click Verify/Continue.
    """
    from config import BASE_URL as _base

    # Use full URL so we always hit the org set in config (not a cached context base_url)
    path = base_path if base_path.startswith("http") else f"{_base.rstrip('/')}{base_path if base_path.startswith('/') else '/' + base_path}"
    page.goto(path)
    page.wait_for_load_state("networkidle")

    login_email = (email or _DEFAULT_EMAIL).strip()
    # Email step: fill Email ID
    email_input = (
        page.get_by_label("Email ID", exact=False).or_(page.get_by_placeholder("Email ID"))
    )
    email_input.wait_for(state="visible", timeout=10000)
    email_input.fill(login_email)

    # Decide flow BEFORE clicking anything else:
    # - manual_otp / OTP flows: email -> Continue -> OTP screen
    # - password flow: email + password on same screen, no intermediate Continue
    password_val = password or ADMIN_PASSWORD
    otp_val = TEST_OTP

    if manual_otp or (not password_val and otp_val):
        # OTP-based flows: wait for Continue to be enabled (form may validate email first), then click
        continue_btn = (
            page.get_by_role("button", name="Continue")
            .or_(page.get_by_role("button", name="Next"))
            .first
        )
        continue_btn.wait_for(state="visible", timeout=10000)
        expect(continue_btn).to_be_enabled(timeout=10000)
        continue_btn.click()

    if manual_otp:
        _login_manual_otp(page, wait_for_navigation)
        return

    # Wait for next step: either Password or OTP

    # Prefer password if available
    if password_val:
        pwd_input = (
            page.get_by_label("Password", exact=False)
            .or_(page.get_by_placeholder("Password"))
            .or_(page.get_by_role("textbox", name="Password"))
        )
        pwd_input.first.wait_for(state="visible", timeout=15000)
        pwd_input.first.fill(password_val)
        submit = (
            page.get_by_role("button", name="Sign in")
            .or_(page.get_by_role("button", name="Login"))
            .or_(page.get_by_role("button", name="Continue"))
            .or_(page.get_by_role("button", name="Submit"))
        )
        submit.first.click()
    elif otp_val:
        otp_input = (
            page.get_by_label("OTP", exact=False)
            .or_(page.get_by_placeholder("OTP"))
            .or_(page.get_by_placeholder("Enter OTP"))
        )
        otp_input.first.wait_for(state="visible", timeout=15000)
        otp_input.first.fill(otp_val)
        submit = (
            page.get_by_role("button", name="Verify")
            .or_(page.get_by_role("button", name="Submit"))
            .or_(page.get_by_role("button", name="Continue"))
        )
        submit.first.click()
    else:
        raise ValueError(
            f"Login requires ADMIN_PASSWORD or TEST_OTP. Set them in config.py or .env for {login_email}."
        )

    if wait_for_navigation:
        page.wait_for_url(lambda url: "dashboard" in url or "landing" in url, timeout=20000)


def _login_manual_otp(page: Page, wait_for_navigation: bool) -> None:
    """Wait for OTP step, then wait for Continue/Verify to become enabled (after you enter OTP), then click."""
    otp_input = (
        page.get_by_label("OTP", exact=False)
        .or_(page.get_by_placeholder("OTP"))
        .or_(page.get_by_placeholder("Enter OTP"))
    )
    try:
        otp_input.first.wait_for(state="visible", timeout=10000)
    except Exception:
        page.get_by_role("button", name="Continue").wait_for(state="visible", timeout=10000)
    submit = (
        page.get_by_role("button", name="Verify")
        .or_(page.get_by_role("button", name="Submit"))
        .or_(page.get_by_role("button", name="Continue"))
    )
    timeout_ms = MANUAL_OTP_WAIT_SECONDS * 1000
    expect(submit.first).to_be_enabled(timeout=timeout_ms)
    submit.first.click()
    if wait_for_navigation:
        # App redirects to /landing/lms/courses or **/dashboard**
        page.wait_for_url("**/landing/**", timeout=20000)
