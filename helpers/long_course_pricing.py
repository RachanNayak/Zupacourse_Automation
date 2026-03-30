"""
Derived long-course subscription pricing for UI assertions and fills.

Reads amounts/terms from `config` so enrollment fill, price-breakup panel, and
course-card term amounts stay aligned.
"""
from __future__ import annotations

import re

from config import (
    LONG_COURSE_FULL_AMOUNT_INR,
    LONG_COURSE_FULL_AMOUNT_USD,
    LONG_COURSE_REGISTRATION_FEE_INR,
    LONG_COURSE_REGISTRATION_FEE_USD,
    LONG_COURSE_SUBSCRIPTION_TERMS,
)


def _terms() -> int:
    return max(LONG_COURSE_SUBSCRIPTION_TERMS, 1)


def _full_inr() -> int:
    return int(LONG_COURSE_FULL_AMOUNT_INR or "0")


def _full_usd() -> int:
    return int(LONG_COURSE_FULL_AMOUNT_USD or "0")


def term_fee_inr() -> float:
    return _full_inr() / _terms()


def term_fee_usd() -> float:
    return _full_usd() / _terms()


def _fmt_money_2(amount: float) -> str:
    return f"{amount:,.2f}"


def subscription_terms_option_label() -> str:
    return str(_terms())


def full_amount_inr_fill() -> str:
    return LONG_COURSE_FULL_AMOUNT_INR


def full_amount_usd_fill() -> str:
    return LONG_COURSE_FULL_AMOUNT_USD


def breakup_regex_term_fee_inr() -> re.Pattern[str]:
    s = _fmt_money_2(term_fee_inr())
    return re.compile(rf"Term Fee \+ GST\s*₹{re.escape(s)}", re.I)


def breakup_regex_subtotal_inr() -> re.Pattern[str]:
    s = _fmt_money_2(float(_full_inr()))
    return re.compile(rf"Sub Total \+ GST\s*₹{re.escape(s)}", re.I)


def breakup_regex_registration_inr() -> re.Pattern[str]:
    s = _fmt_money_2(float(LONG_COURSE_REGISTRATION_FEE_INR))
    return re.compile(rf"One-time registration fee\s*₹{re.escape(s)}", re.I)


def breakup_regex_total_inr() -> re.Pattern[str]:
    total = float(_full_inr() + LONG_COURSE_REGISTRATION_FEE_INR)
    s = _fmt_money_2(total)
    return re.compile(rf"Total fee\s*₹{re.escape(s)}", re.I)


def breakup_regex_term_fee_usd() -> re.Pattern[str]:
    s = _fmt_money_2(term_fee_usd())
    return re.compile(rf"Term Fee \+ GST\s*\${re.escape(s)}", re.I)


def breakup_regex_subtotal_usd() -> re.Pattern[str]:
    s = _fmt_money_2(float(_full_usd()))
    return re.compile(rf"Sub Total \+ GST\s*\${re.escape(s)}", re.I)


def breakup_regex_registration_usd() -> re.Pattern[str]:
    s = _fmt_money_2(float(LONG_COURSE_REGISTRATION_FEE_USD))
    return re.compile(rf"One-time registration fee\s*\${re.escape(s)}", re.I)


def breakup_regex_total_usd() -> re.Pattern[str]:
    total = float(_full_usd() + LONG_COURSE_REGISTRATION_FEE_USD)
    s = _fmt_money_2(total)
    return re.compile(rf"Total fee\s*\${re.escape(s)}", re.I)


def _card_term_amount_display(amount: float) -> str:
    if abs(amount - round(amount)) < 1e-9:
        return f"{int(round(amount)):,}"
    return _fmt_money_2(amount)


def course_card_term_inr_pattern() -> re.Pattern[str]:
    """Match per-term INR on list card (with optional .00 / 'term' suffix variants)."""
    num = _card_term_amount_display(term_fee_inr())
    esc = re.escape(num)
    return re.compile(rf"(₹\s*{esc}(?:\.00)?)|(\b{esc}(?:\.00)?\b.*term)", re.I)


def course_card_term_usd_pattern() -> re.Pattern[str]:
    num = _card_term_amount_display(term_fee_usd())
    esc = re.escape(num)
    return re.compile(rf"(\$\s*{esc}(?:\.00)?)|(\b{esc}(?:\.00)?\b.*term)", re.I)
