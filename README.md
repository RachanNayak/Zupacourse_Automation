# LMS – Smoke test automation

Playwright + Python smoke tests for the LMS (white-labelled orgs like Divyakala / Tapovana).

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

Copy `.env.example` to `.env` and set values for your org:

- `BASE_URL` – e.g. `https://app.tapovanalife.com` or `https://app.sandbox.lms.zupaloop.ai`
- `ADMIN_EMAIL`
- **Manual OTP:** set `MANUAL_OTP=1` so the test fills email, clicks Continue, waits for you to enter the OTP in the browser, then clicks Verify (wait time: `MANUAL_OTP_WAIT_SECONDS`, default 90).
- Or set `ADMIN_PASSWORD` for password login; or `TEST_OTP` to fill OTP automatically.

Config is **hybrid**:
- `config.py` contains safe defaults and parses env vars.
- `.env` overrides `config.py` (and is not committed).

## Run tests

```bash
# Smoke test: browser visible (headed)
HEADED=1 pytest tests/smoke -m smoke -v
```

When `MANUAL_OTP=1`, the test will open the login page, fill your email, and click Continue. **Enter the OTP in the browser** when you receive it; the test will wait up to 90 seconds (or `MANUAL_OTP_WAIT_SECONDS`) then click Verify/Continue.

## Allure dashboard (local)

This project can produce an **Allure** dashboard (interactive HTML report) for managers and stakeholders.

### Install Allure CLI

You already installed the Python packages via `requirements.txt` (which includes `allure-pytest`). To generate and view reports you also need the Allure CLI:

- macOS (Homebrew):

```bash
brew install allure
```

- Or download from the Allure docs and add it to your `PATH`.

### Generate Allure results

Run your tests with the Allure plugin enabled:

```bash
HEADED=1 pytest tests/smoke -m smoke --alluredir=allure-results
```

This creates an `allure-results/` folder with raw data for the report.

### View the Allure dashboard locally

For ad‑hoc viewing (temporary server):

```bash
allure serve allure-results
```

This opens the Allure dashboard in your browser.

Or generate a static HTML report folder:

```bash
allure generate allure-results -o allure-report --clean
```

You can then open `allure-report/index.html` in a browser or archive `allure-report/` and share it.

## Project layout

- `conftest.py` – Pytest and Playwright fixtures, base URL from env.
- `helpers/auth.py` – `login_as_admin(page, email=..., password=...)` for admin login.
- `tests/smoke/test_admin_create_long_course.py` – Admin login and Long Course creation.
