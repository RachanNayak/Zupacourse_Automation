"""
Single place for site URL and login credentials.
Change this file when switching between Divyakala, Tapovana, or another org.

Hybrid approach (recommended):
- `config.py` holds safe defaults + parsing.
- `.env` (ignored by git) holds secrets/overrides (passwords, OTPs, per-machine URLs).

Precedence:
- Environment variables (including from `.env`) override the defaults in this file.
"""
import os

from dotenv import load_dotenv

load_dotenv()


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key) or default).strip()


def _env_int(key: str, default: int) -> int:
    raw = _env(key, str(default))
    try:
        return int(raw)
    except ValueError:
        return default


# -----------------------------------------------------------------------------
# Site / base URL — change when switching org
# -----------------------------------------------------------------------------
# Divyakala (sandbox): https://app.sandbox.lms.zupaloop.ai
# Tapovana:           https://app.tapovanalife.com
BASE_URL = _env("BASE_URL", "https://app.tapovanalife.com").rstrip("/")

# -----------------------------------------------------------------------------
# Login credentials
# -----------------------------------------------------------------------------
ADMIN_EMAIL = _env("ADMIN_EMAIL", "rachan@zupaloop.com")
# Keep secrets in `.env` (or your shell env), not in git.
ADMIN_PASSWORD = _env("ADMIN_PASSWORD", "password")  # optional; use for password login
TEST_OTP = _env("TEST_OTP", "")  # optional; use for automatic OTP

# -----------------------------------------------------------------------------
# Learner (user) credentials
# -----------------------------------------------------------------------------
# Used for "user purchase" smoke tests.
# Provide these in `.env` (ignored by git) or environment variables.
USER_EMAIL = _env("USER_EMAIL", "")
USER_PASSWORD = _env("USER_PASSWORD", "")  # optional; use for password login
USER_TEST_OTP = _env("USER_TEST_OTP", "")  # optional; use for automatic OTP

# Manual OTP: test fills email and clicks Continue; you enter OTP in browser.
USER_MANUAL_OTP = _env("USER_MANUAL_OTP", "false").lower() in ("1", "true", "yes")
USER_MANUAL_OTP_WAIT_SECONDS = int(_env("USER_MANUAL_OTP_WAIT_SECONDS", "90") or "90")

# Manual OTP: test fills email and clicks Continue; you enter OTP in browser.
MANUAL_OTP = _env("MANUAL_OTP", "false").lower() in ("1", "true", "yes")
MANUAL_OTP_WAIT_SECONDS = int(_env("MANUAL_OTP_WAIT_SECONDS", "90") or "90")

# Sign out before login (e.g. when switching accounts)
SIGN_OUT_FIRST = _env("SIGN_OUT_FIRST", "").lower() in ("1", "true", "yes")

# -----------------------------------------------------------------------------
# Long course — subscription enrollment pricing (admin create flow)
# -----------------------------------------------------------------------------
# Override via `.env` without editing page objects. Breakup assertions derive from these.
LONG_COURSE_SUBSCRIPTION_TERMS = _env_int("LONG_COURSE_SUBSCRIPTION_TERMS", 8)
LONG_COURSE_FULL_AMOUNT_INR = _env("LONG_COURSE_FULL_AMOUNT_INR", "10000")
LONG_COURSE_FULL_AMOUNT_USD = _env("LONG_COURSE_FULL_AMOUNT_USD", "1000")
LONG_COURSE_REGISTRATION_FEE_INR = _env_int("LONG_COURSE_REGISTRATION_FEE_INR", 1840)
LONG_COURSE_REGISTRATION_FEE_USD = _env_int("LONG_COURSE_REGISTRATION_FEE_USD", 20)

# -----------------------------------------------------------------------------
# Learner long-course apply/pay flow configuration
# -----------------------------------------------------------------------------
USER_LONG_COURSE_NAME_HINT = _env("USER_LONG_COURSE_NAME_HINT", "")
USER_APPLY_REASON = _env("USER_APPLY_REASON", "To learn")
USER_ARTISTIC_BACKGROUND = _env("USER_ARTISTIC_BACKGROUND", "no experience")
USER_PORTFOLIO_LINK = _env("USER_PORTFOLIO_LINK", "link.com")
USER_LONG_PAYMENT_CONTACT_NUMBER = _env("USER_LONG_PAYMENT_CONTACT_NUMBER", "6360295267")
USER_LONG_PAYMENT_VPA = _env("USER_LONG_PAYMENT_VPA", "success@razorpay")

# -----------------------------------------------------------------------------
# Browser
# -----------------------------------------------------------------------------
# Run browser in headed mode (visible window)
HEADED = _env("HEADED", "").lower() in ("1", "true", "yes")
