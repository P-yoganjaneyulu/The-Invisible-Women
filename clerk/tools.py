"""Tool registry and dispatcher.

Two rules from the design doc live here:

1. Nothing auditable comes from the model. Amounts and eligibility go through
   code (`clerk.eligibility`) that has tests. The model decides *what* to
   do; it never decides *what a woman is owed*.

2. No tool blocks the audio path. `spawn()` runs a tool off-thread and returns a
   handle, so the caller's voice keeps flowing while a page loads. Only
   `call()` blocks, and only the demo/test path uses it.

Note there is no `submit_application` tool. Submitting a form is
fill_form + click_button + read_result, which works on any portal - which is
the entire point. The earlier portal-specific version was removed.
"""

from __future__ import annotations

import threading
import traceback
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable

from . import browser, search
from .eligibility import Applicant, evaluate, parse_date, parse_int

# One worker. Browsers are not thread-safe and a second concurrent fill would
# fight the first; ponytail: serialise it rather than build a scheduler.
_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="clerk")


# ---------------------------------------------------------------- tools


def tool_search_web(query: str, gov_only: bool = False) -> dict:
    """Search the live web. Use this to discover what exists before opening pages."""
    res = search.search_web(query, gov_only=gov_only)
    return {"query": res["query"], "results": res["results"], "note": res.get("note", ""),
            "format": search.format_results(res)}


def tool_open_page(url: str) -> dict:
    """Open a URL and read it. Returns the page text you would have had to read."""
    return browser.open_page(url)


def tool_fill_form(fields: dict[str, Any], url: str | None = None) -> dict:
    """Fill in a form on the page, addressed by the words printed next to each field.

    fields maps a printed label to a value, e.g. {"Full Name": "Sunita Devi",
    "Age": "27", "District": "Karnool"}. Works on sites we have never seen.

    ALWAYS check `missing` and `errors` in the result. If anything is missing,
    tell the woman which detail you could not place, and ask her again. Never
    claim a form was filled when it was not.
    """
    return browser.fill_form(fields, url=url)


def tool_click_button(text: str, url: str | None = None) -> dict:
    """Click a button or link by the words printed on it, e.g. "Submit"."""
    return browser.click_button(text, url=url)


def tool_read_result(patterns: list[str] | None = None, url: str | None = None) -> dict:
    """Read a confirmation off the page - registration number, amount, status.

    Pass regex patterns taken from what the page actually says, e.g.
    ["PMMVY\\\\s*\\\\d{8}", "Registration No[^0-9]*([0-9]+)"]. Only read a value
    that is really on the page. Never compose one yourself.
    """
    return browser.read_result(patterns, url=url)


def build_applicant(args: dict) -> Applicant:
    """Coerce LLM tool args into an Applicant. Every string goes through the
    shared parsers, because a voice transcript is full of spoken numbers
    ("solah", "२७") that a naive int() would either crash on or get wrong."""
    s = lambda k, d="": str(args.get(k, d) or "").strip()  # noqa: E731
    return Applicant(
        name=s("name"),
        husband=s("husband"),
        aadhaar_last4="".join(c for c in s("aadhaar_last4") if c.isdigit())[-4:],
        age=parse_int(s("age")),
        mobile="".join(c for c in s("mobile") if c.isdigit())[-10:],
        district=s("district"),
        lmp=parse_date(s("lmp")),
        bank_ifsc=s("bank_ifsc"),
        children=parse_int(s("children", "0")) or 0,
        girl_child=bool(args.get("girl_child")),
        is_govt_employee=bool(args.get("is_govt_employee")),
        has_other_maternity_benefit=bool(args.get("has_other_maternity_benefit")),
    )


def tool_check_eligibility(**kw: Any) -> dict:
    """The ONLY source of truth on scheme eligibility and benefit amounts.

    Compute it here. Never estimate, never guess an amount, never rely on what a
    web page says a scheme pays. Takes the applicant's details and returns the
    verdict plus the amount in words, ready to be spoken.
    """
    a = build_applicant(kw)
    v = evaluate(a)
    return {
        "eligible": v.eligible,
        "reason": v.reason,
        "benefit": v.benefit,
        "spoken": v.voice(),
        # Echoed back so the caller can persist the record it just validated.
        "applicant": {
            "name": a.name, "husband": a.husband, "aadhaar_last4": a.aadhaar_last4,
            "age": a.age, "mobile": a.mobile, "district": a.district,
            "lmp": a.lmp.isoformat() if a.lmp else "", "bank_ifsc": a.bank_ifsc,
            "children": a.children, "girl_child": a.girl_child,
        },
    }


# ---------------------------------------------------------------- registry

SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the live web. First step for anything you do not already know.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "gov_only": {
                        "type": "boolean",
                        "description": "Restrict to official .gov.in sources. Use for schemes, rules and entitlements.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_page",
            "description": "Open a URL and read its text.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fill_form",
            "description": (
                "Fill a form on the current page, keyed by the words printed beside each field. "
                "Check the returned 'missing' list and re-ask for anything you could not place."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "fields": {"type": "object", "additionalProperties": {"type": "string"}},
                    "url": {"type": "string", "description": "Optional: open this page first."},
                },
                "required": ["fields"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "click_button",
            "description": "Click a button or link by its printed text.",
            "parameters": {
                "type": "object",
                "properties": {"text": {"type": "string"}, "url": {"type": "string"}},
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_result",
            "description": "Read a confirmation value (registration number, amount) off the page.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patterns": {"type": "array", "items": {"type": "string"}},
                    "url": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_eligibility",
            "description": "Deterministic eligibility and benefit amount. Never estimate an amount.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "husband": {"type": "string"},
                    "aadhaar_last4": {"type": "string"},
                    "age": {"type": ["integer", "string"]},
                    "mobile": {"type": "string"},
                    "district": {"type": "string"},
                    "lmp": {"type": "string"},
                    "bank_ifsc": {"type": "string"},
                    "children": {"type": ["integer", "string"]},
                    "girl_child": {"type": "boolean"},
                    "is_govt_employee": {"type": "boolean"},
                    "has_other_maternity_benefit": {"type": "boolean"},
                },
                "required": ["age", "children"],
            },
        },
    },
]

REGISTRY: dict[str, Callable[..., Any]] = {
    "search_web": tool_search_web,
    "open_page": tool_open_page,
    "fill_form": tool_fill_form,
    "click_button": tool_click_button,
    "read_result": tool_read_result,
    "check_eligibility": tool_check_eligibility,
}


# ---------------------------------------------------------------- dispatch


def call(name: str, args: dict | None = None, timeout: float = 90.0) -> Any:
    """Run a tool and block. Demo and test path only."""
    fn = REGISTRY.get(name)
    if fn is None:
        return {"error": f"unknown tool {name!r}", "available": sorted(REGISTRY)}
    try:
        return fn(**(args or {}))
    except TypeError as e:
        return {"error": f"bad arguments for {name}: {e}"}
    except Exception as e:  # noqa: BLE001 - a failed tool must not kill the call
        return {"error": f"{name} failed: {type(e).__name__}: {e}",
                "trace": traceback.format_exc(limit=3)}


def spawn(name: str, args: dict | None = None, on_done: Callable[[str, Any], None] | None = None):
    """Run a tool off the audio path.

    This is the fix for dead air (design doc 8.1): the caller speaks a filler
    immediately, and `on_done` fires whenever the result lands - even after the
    call has ended, which is how long work still reaches her.

    Returns the Future so the caller can ignore it.
    """

    def run():
        result = call(name, args)
        if on_done:
            try:
                on_done(name, result)
            except Exception:  # noqa: BLE001 - never let a callback kill the worker
                pass
        return result

    return _pool.submit(run)


def shutdown() -> None:
    _pool.shutdown(wait=False, cancel_futures=True)
    browser.shutdown()
