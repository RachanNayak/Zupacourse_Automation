# Divyakala LMS – Smoke test automation

Playwright + Python smoke tests for [Divyakala LMS](https://app.sandbox.lms.zupaloop.ai/) (Zupaloop sandbox).

## Smoke scenario

**Can an admin create a Long Course?** – Admin (`rachan@zupaloop.com`) logs in and creates a Long Course.

## Setup

```bash
# Create virtualenv (recommended)
python3 -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt
playwright install chromium
```

Copy `.env.example` to `.env` and set:

- `BASE_URL` – default `https://app.sandbox.lms.zupaloop.ai`
- `ADMIN_EMAIL` – default `rachan@zupaloop.com`
- **Manual OTP:** set `MANUAL_OTP=1` so the test fills email, clicks Continue, waits for you to enter the OTP in the browser, then clicks Verify (wait time: `MANUAL_OTP_WAIT_SECONDS`, default 90).
- Or set `ADMIN_PASSWORD` for password login; or `TEST_OTP` to fill OTP automatically.

## Run tests

```bash
# Smoke test: admin creates a Long Course (with manual OTP, browser visible)
MANUAL_OTP=1 HEADED=1 pytest tests/smoke -m smoke -v
```

When `MANUAL_OTP=1`, the test will open the login page, fill your email, and click Continue. **Enter the OTP in the browser** when you receive it; the test will wait up to 90 seconds (or `MANUAL_OTP_WAIT_SECONDS`) then click Verify/Continue.

## Project layout

- `conftest.py` – Pytest and Playwright fixtures, base URL from env.
- `helpers/auth.py` – `login_as_admin(page, email=..., password=...)` for admin login.
- `tests/smoke/test_admin_create_long_course.py` – Admin login and Long Course creation.
