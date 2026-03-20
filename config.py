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

# Manual OTP: test fills email and clicks Continue; you enter OTP in browser.
MANUAL_OTP = _env("MANUAL_OTP", "false").lower() in ("1", "true", "yes")
MANUAL_OTP_WAIT_SECONDS = int(_env("MANUAL_OTP_WAIT_SECONDS", "90") or "90")

# Sign out before login (e.g. when switching accounts)
SIGN_OUT_FIRST = _env("SIGN_OUT_FIRST", "").lower() in ("1", "true", "yes")

# -----------------------------------------------------------------------------
# Browser
# -----------------------------------------------------------------------------
# Run browser in headed mode (visible window)
HEADED = _env("HEADED", "").lower() in ("1", "true", "yes")
