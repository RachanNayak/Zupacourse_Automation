import os
import re
import time
from pathlib import Path

import pytest
from playwright.sync_api import Page


# region agent debug log
_DEBUG_LOG_PATH = "/Users/rachan/Divyakala smoke testAutomation/.cursor/debug-67ea1f.log"
_DEBUG_SESSION_ID = "67ea1f"


def _debug_log(*, run_id: str, hypothesis_id: str, location: str, message: str, data: dict) -> None:
    try:
        payload = {
            "sessionId": _DEBUG_SESSION_ID,
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{payload}\n".replace("'", '"'))
    except Exception:
        # Never let debug logging break the test run.
        pass


# endregion agent debug log


class LongCoursePage:
    def __init__(self, page: Page) -> None:
        self.page = page

    # --- Create Course & basic info ---
    def fill_course_details(self, title: str, course_image_path: str, dummy_file_path: str) -> None:
        page = self.page

        page.get_by_role("button", name="Create Course").wait_for(state="visible", timeout=10000)
        page.get_by_role("button", name="Create Course").click()
        page.wait_for_load_state("networkidle")

        page.get_by_role("combobox", name="Type of Course").locator("span").click()
        page.get_by_text("Long Courses").click()
        time.sleep(0.2)

        page.get_by_role("combobox", name="Course Category").locator("span").click()
        page.get_by_role("option", name="Art").click()
        time.sleep(0.2)

        page.get_by_role("combobox", name="Author").locator("span").click()
        author_option = page.get_by_role("option", name="RACHAN NAYAK").first
        author_option.scroll_into_view_if_needed()
        author_option.click()
        time.sleep(0.2)

        page.get_by_role("textbox", name="Course Name").fill(title)

        page.locator("mat-form-field").filter(has_text="Start Date").get_by_label("Open calendar").click()
        time.sleep(0.3)
        start_btn = page.get_by_role("button", name=re.compile(r"March \d+,\s*\d{4}"))
        start_label = start_btn.first.get_attribute("aria-label") or start_btn.first.inner_text()
        m = re.search(r"^(?P<month>[A-Za-z]+)\s+(?P<day>\d+),\s*(?P<year>\d{4})", (start_label or "").strip())
        assert m, f"Could not parse start date label: {start_label!r}"
        start_btn.first.click()
        time.sleep(0.2)

        page.locator("mat-form-field").filter(has_text="End Date").get_by_label("Open calendar").click()
        time.sleep(0.3)
        for _ in range(12):
            page.get_by_role("button", name="Next month").click()
            time.sleep(0.05)
        end_label = f"{m.group('month')} {m.group('day')}, {int(m.group('year')) + 1}"
        page.get_by_role("button", name=end_label).click()
        time.sleep(0.2)

        page.locator("form").filter(has_text="Type of CourseLong").locator("quill-editor div").nth(2).click()
        page.locator("form").filter(has_text="Type of CourseLong").locator("quill-editor div").nth(2).fill("DESC here")
        time.sleep(0.2)

        if os.path.isfile(course_image_path):
            page.locator('input[type="file"]').first.set_input_files(course_image_path)
        else:
            pytest.skip(f"Course image not found: {course_image_path}")
        time.sleep(0.3)

        page.get_by_role("button", name="Add course info").click()
        time.sleep(0.4)
        page.get_by_role("textbox", name="Title").fill("Title Here")
        page.locator("app-add-course-info quill-editor div").nth(2).click()
        page.locator("app-add-course-info quill-editor div").nth(2).fill("Desc here.")
        page.locator("app-add-course-info").get_by_role("button", name="Add course info").click()
        time.sleep(0.3)

        if os.path.isfile(dummy_file_path):
            all_file_inputs = page.locator('input[type="file"]')
            if all_file_inputs.count() >= 2:
                all_file_inputs.nth(1).set_input_files(dummy_file_path)
            else:
                all_file_inputs.first.set_input_files(dummy_file_path)
        time.sleep(0.2)

        page.get_by_role("button", name="Save and Continue").click()
        page.wait_for_load_state("networkidle")

    # --- Create Batches ---
    def create_batches(self) -> None:
        page = self.page

        page.get_by_role("textbox", name="Batch Name").fill("Batch 1")
        start_date_cal = page.locator("div").filter(has_text=re.compile(r"^Start DateStart Time$")).get_by_label(
            "Open calendar"
        )
        start_date_cal.first.scroll_into_view_if_needed()
        time.sleep(0.3)
        start_date_cal.first.click()
        time.sleep(0.3)
        page.get_by_role("button", name=re.compile(r"March \d+,")).first.click()
        time.sleep(0.2)
        end_date_cal = page.locator("div").filter(has_text=re.compile(r"^End DateEnd Time$")).get_by_label(
            "Open calendar"
        )
        end_date_cal.first.scroll_into_view_if_needed()
        time.sleep(0.2)
        end_date_cal.first.click()
        time.sleep(0.3)
        page.get_by_role("button", name="Next month").click()
        time.sleep(0.2)
        page.get_by_role("button", name=re.compile(r"April \d+,")).first.click()
        time.sleep(0.2)
        page.locator("div").filter(has_text=re.compile(r"^Start Time$")).nth(3).click()
        page.get_by_text("5:00 AM").click()
        page.get_by_role("combobox", name="End Time").locator("span").click()
        page.get_by_text("6:00 AM").click()
        page.get_by_text("T", exact=True).first.click()
        page.get_by_text("T", exact=True).nth(1).click()
        page.get_by_role("textbox", name="Live Session Link").fill("https://live.example.com")
        page.get_by_role("button", name="Create Batch").click()
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)

        page.get_by_role("textbox", name="Batch Name").fill("Batch 2")
        page.get_by_role("radio", name="Schedule Non-Recurring Batch").check()
        time.sleep(0.2)
        page.get_by_role("button", name="Open calendar").first.click()
        time.sleep(0.3)
        page.get_by_role("button", name=re.compile(r"March \d+,")).first.click()
        page.get_by_role("combobox", name=re.compile(r"Start Time")).locator("svg").click()
        page.get_by_text("6:00 AM", exact=True).click()
        page.get_by_role("combobox", name=re.compile(r"End Time")).locator("svg").click()
        page.get_by_text("7:00 AM").click()
        page.get_by_role("textbox", name="Live Session Link").fill("https://live.example.com")
        page.get_by_role("button", name="Create Batch").click()
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)

        page.get_by_role("button", name="Continue").click()
        page.wait_for_load_state("networkidle")

    # --- Create Modules ---
    def create_module(self, module_file_path: str) -> None:
        page = self.page

        page.get_by_role("textbox", name="Module Name").fill("Module 1")
        page.get_by_role("tabpanel", name="Create Modules").locator("quill-editor div").nth(2).click()
        page.get_by_role("tabpanel", name="Create Modules").locator("quill-editor div").nth(2).fill(
            "Module desc here"
        )
        if os.path.isfile(module_file_path):
            page.get_by_role("tabpanel", name="Create Modules").locator('input[type="file"]').first.set_input_files(
                module_file_path
            )
        time.sleep(0.2)
        page.get_by_role("button", name="Add Module").click()
        page.wait_for_load_state("networkidle")
        time.sleep(0.3)
        page.get_by_role("button", name="Save and Continue").click()
        page.wait_for_load_state("networkidle")

    # --- Add Videos ---
    def add_video(self, video_file_path: str) -> None:
        page = self.page

        page.get_by_role("combobox", name="Select Module").locator("svg").click()
        page.get_by_role("option", name="Module 1").click()
        time.sleep(0.2)
        page.get_by_role("combobox", name="Select Batch").locator("svg").click()
        page.get_by_role("option", name="Batch 1").click()
        time.sleep(0.2)

        # Select session date first, then fill session name.
        run_id = os.getenv("DEBUG_RUN_ID", "session-date-pre")
        try:
            session_date_combo = page.get_by_role("combobox", name="Select Session Date")
            _debug_log(
                run_id=run_id,
                hypothesis_id="SD1",
                location="tests/smoke/test_admin_create_long_course.py:SelectSessionDate",
                message="About to open session date dropdown",
                data={
                    "combo_visible": session_date_combo.is_visible(),
                    "combo_enabled": session_date_combo.is_enabled(),
                },
            )
            session_date_combo.locator("span").click()

            # If it's an Angular Material select, options live in the overlay/panel.
            mat_options = page.locator("mat-option")
            try:
                oc = mat_options.count()
            except Exception as e:
                oc = None
                _debug_log(
                    run_id=run_id,
                    hypothesis_id="SD2",
                    location="tests/smoke/test_admin_create_long_course.py:SelectSessionDate",
                    message="Failed counting mat-option",
                    data={"error": repr(e)},
                )

            option_samples: list[str] = []
            if oc:
                for i in range(min(int(oc), 5)):
                    try:
                        t = (mat_options.nth(i).inner_text() or "").strip()
                        option_samples.append(t[:200])
                    except Exception as e:
                        option_samples.append(f"<err {i}: {repr(e)}>")

            _debug_log(
                run_id=run_id,
                hypothesis_id="SD2",
                location="tests/smoke/test_admin_create_long_course.py:SelectSessionDate",
                message="Session date options observed",
                data={"mat_option_count": oc, "samples": option_samples},
            )

            pattern = re.compile(r"Batch 1.*Session.*\d{4}-\d{2}-\d{2}")
            matches = page.get_by_text(pattern)
            try:
                mc = matches.count()
            except Exception as e:
                mc = None
                _debug_log(
                    run_id=run_id,
                    hypothesis_id="SD3",
                    location="tests/smoke/test_admin_create_long_course.py:SelectSessionDate",
                    message="Failed counting regex matches",
                    data={"error": repr(e)},
                )

            _debug_log(
                run_id=run_id,
                hypothesis_id="SD3",
                location="tests/smoke/test_admin_create_long_course.py:SelectSessionDate",
                message="Regex match count for session date",
                data={"match_count": mc, "pattern": pattern.pattern},
            )

            matches.first.click()
            time.sleep(0.2)
        except Exception as e:
            _debug_log(
                run_id=run_id,
                hypothesis_id="SD4",
                location="tests/smoke/test_admin_create_long_course.py:SelectSessionDate",
                message="Selecting session date failed",
                data={"error": repr(e), "url": page.url},
            )
            raise

        page.get_by_role("textbox", name="Session Name").fill("Session 1")

        run_id = os.getenv("DEBUG_RUN_ID", "video-upload-pre")
        _debug_log(
            run_id=run_id,
            hypothesis_id="H1",
            location="tests/smoke/test_admin_create_long_course.py:AddVideos",
            message="Video path check",
            data={
                "video_file_path": video_file_path,
                "is_file": os.path.isfile(video_file_path),
                "size_bytes": os.path.getsize(video_file_path) if os.path.isfile(video_file_path) else None,
            },
        )

        file_inputs = page.locator('input[type="file"]')
        try:
            input_count = file_inputs.count()
        except Exception as e:
            input_count = None
            _debug_log(
                run_id=run_id,
                hypothesis_id="H2",
                location="tests/smoke/test_admin_create_long_course.py:AddVideos",
                message="Failed counting file inputs",
                data={"error": repr(e)},
            )

        _debug_log(
            run_id=run_id,
            hypothesis_id="H2",
            location="tests/smoke/test_admin_create_long_course.py:AddVideos",
            message="File input locator count",
            data={"count": input_count},
        )

        if os.path.isfile(video_file_path):
            # Log basic metadata for each file input so we can identify the correct uploader.
            if input_count:
                inputs_meta: list[dict] = []
                for i in range(min(int(input_count), 6)):
                    li = file_inputs.nth(i)
                    try:
                        meta = {
                            "i": i,
                            "visible": li.is_visible(),
                            "enabled": li.is_enabled(),
                            "accept": li.get_attribute("accept"),
                            "multiple": li.get_attribute("multiple"),
                            "name": li.get_attribute("name"),
                            "id": li.get_attribute("id"),
                        }
                    except Exception as e:
                        meta = {"i": i, "error": repr(e)}
                    inputs_meta.append(meta)
                _debug_log(
                    run_id=run_id,
                    hypothesis_id="H2",
                    location="tests/smoke/test_admin_create_long_course.py:AddVideos",
                    message="File input metadata",
                    data={"inputs": inputs_meta},
                )

            target_input = file_inputs.last
            try:
                _debug_log(
                    run_id=run_id,
                    hypothesis_id="H3",
                    location="tests/smoke/test_admin_create_long_course.py:AddVideos",
                    message="About to set_input_files",
                    data={
                        "target_is_visible": target_input.is_visible(),
                        "target_is_enabled": target_input.is_enabled(),
                    },
                )
                target_input.set_input_files(video_file_path)
                _debug_log(
                    run_id=run_id,
                    hypothesis_id="H3",
                    location="tests/smoke/test_admin_create_long_course.py:AddVideos",
                    message="set_input_files succeeded",
                    data={},
                )
                add_video_btn = page.get_by_role("button", name="Add Video")
                try:
                    _debug_log(
                        run_id=run_id,
                        hypothesis_id="H4",
                        location="tests/smoke/test_admin_create_long_course.py:AddVideos",
                        message="About to click Add Video",
                        data={
                            "btn_enabled": add_video_btn.is_enabled(),
                            "btn_visible": add_video_btn.is_visible(),
                        },
                    )
                except Exception as e:
                    _debug_log(
                        run_id=run_id,
                        hypothesis_id="H4",
                        location="tests/smoke/test_admin_create_long_course.py:AddVideos",
                        message="Failed reading Add Video button state",
                        data={"error": repr(e)},
                    )
                add_video_btn.click()
                # After click, capture any alert text (common for validation errors).
                try:
                    alerts = page.get_by_role("alert")
                    ac = alerts.count()
                    texts = []
                    for j in range(min(ac, 2)):
                        t = (alerts.nth(j).inner_text() or "").strip()
                        texts.append(t[:200])
                    _debug_log(
                        run_id=run_id,
                        hypothesis_id="H4",
                        location="tests/smoke/test_admin_create_long_course.py:AddVideos",
                        message="Post-click alerts",
                        data={"alert_count": ac, "alert_texts": texts},
                    )
                except Exception as e:
                    _debug_log(
                        run_id=run_id,
                        hypothesis_id="H4",
                        location="tests/smoke/test_admin_create_long_course.py:AddVideos",
                        message="Failed reading post-click alerts",
                        data={"error": repr(e)},
                    )
                # Look for any toast/snackbar messages (often used instead of alerts).
                try:
                    snack = page.locator(".mat-mdc-snack-bar-container, .mat-snack-bar-container").first
                    if snack.count() > 0:
                        st = (snack.inner_text() or "").strip()
                    else:
                        st = ""
                    _debug_log(
                        run_id=run_id,
                        hypothesisId="H5",
                        location="tests/smoke/test_admin_create_long_course.py:AddVideos",
                        message="Snackbar text",
                        data={"text": st[:300]},
                    )
                except Exception as e:
                    _debug_log(
                        run_id=run_id,
                        hypothesis_id="H5",
                        location="tests/smoke/test_admin_create_long_course.py:AddVideos",
                        message="Failed reading snackbar",
                        data={"error": repr(e)},
                    )

                # Confirm the UI registered the upload (filename appears somewhere).
                try:
                    basename = Path(video_file_path).name
                    page.get_by_text(basename).first.wait_for(timeout=15000)
                    _debug_log(
                        run_id=run_id,
                        hypothesis_id="H6",
                        location="tests/smoke/test_admin_create_long_course.py:AddVideos",
                        message="Uploaded filename became visible",
                        data={"basename": basename},
                    )
                except Exception as e:
                    _debug_log(
                        run_id=run_id,
                        hypothesis_id="H6",
                        location="tests/smoke/test_admin_create_long_course.py:AddVideos",
                        message="Uploaded filename NOT visible after Add Video",
                        data={"error": repr(e), "basename": Path(video_file_path).name},
                    )
                    raise
            except Exception as e:
                _debug_log(
                    run_id=run_id,
                    hypothesis_id="H4",
                    location="tests/smoke/test_admin_create_long_course.py:AddVideos",
                    message="set_input_files failed",
                    data={"error": repr(e)},
                )
                raise
        else:
            page.get_by_role("button", name="Skip").click()
        try:
            page.wait_for_load_state("networkidle")
        except Exception as e:
            _debug_log(
                run_id=run_id,
                hypothesis_id="H7",
                location="tests/smoke/test_admin_create_long_course.py:AddVideos",
                message='wait_for_load_state("networkidle") failed',
                data={"error": repr(e), "url": page.url},
            )
            raise
        time.sleep(0.3)

    # --- Enrollment & Price ---
    def set_enrollment_and_publish(self, created_title: str) -> None:
        page = self.page

        page.get_by_role("combobox", name="Currency").locator("span").click()
        page.get_by_role("option", name="INR").click()
        page.get_by_role("textbox", name="Amount").fill("200")
        page.get_by_role("button", name="Add").click()
        time.sleep(0.2)
        page.get_by_role("combobox", name="Currency").locator("span").click()
        page.get_by_role("option", name="USD").click()
        page.get_by_role("textbox", name="Amount").fill("200")
        page.get_by_role("button", name="Add").click()
        time.sleep(0.2)
        page.get_by_role("button", name="Publish Course").click()
        page.wait_for_load_state("networkidle")

        # region agent log: after publish, capture first few course cards and their titles
        run_id = os.getenv("DEBUG_RUN_ID", "post-publish-cards")
        try:
            cards = page.locator(".course-card")
            try:
                count = cards.count()
            except Exception as e:
                count = None
                _debug_log(
                    run_id=run_id,
                    hypothesis_id="CARD1",
                    location="tests/pages/long_course_page.py:set_enrollment_and_publish",
                    message="Failed counting .course-card elements",
                    data={"error": repr(e)},
                )
            samples: list[dict] = []
            if count:
                for i in range(min(int(count), 5)):
                    card = cards.nth(i)
                    try:
                        text = (card.inner_text() or "").strip()
                    except Exception as e:
                        text = f"<err {repr(e)}>"
                    samples.append({"index": i, "text": text[:200]})
            _debug_log(
                run_id=run_id,
                hypothesis_id="CARD1",
                location="tests/pages/long_course_page.py:set_enrollment_and_publish",
                message="Course card texts after publish",
                data={"count": count, "samples": samples, "expected_title": created_title},
            )
        except Exception as e:
            _debug_log(
                run_id=run_id,
                hypothesis_id="CARD2",
                location="tests/pages/long_course_page.py:set_enrollment_and_publish",
                message="Error while logging course cards",
                data={"error": repr(e)},
            )
        # endregion agent log

