"""General browser control: drive a page nobody told us about.

The hard requirement from the problem statement is that the agent must be able
to work a site we have never seen. A table of hardcoded CSS selectors fails the
moment it meets a real portal, so we never hardcode selectors.

Instead we locate fields the way a human does: by the words printed next to
them. `get_by_label` handles the accessible cases; for the rest we score every
field on the page by how many of the label's words appear in its identifying
attributes (id, name, placeholder, aria-label, its <label>). That is what makes
this general rather than a demo.

Singular browser, reused across calls, window left open so a human can watch the
agent work. Slower, but it is the only honest way to show browser control.
"""

from __future__ import annotations

import re
import threading
from typing import Any

from playwright.sync_api import sync_playwright

_lock = threading.Lock()
_state: dict[str, Any] = {}

READ_CHARS = 4000
DEFAULT_HEADED = True
DEFAULT_SLOW_MO = 120

# Words that appear in almost every form and would match anything.
_STOP = {"the", "and", "for", "your", "you", "are", "please", "enter", "give", "with", "this"}


def _tokens(s: str) -> set[str]:
    return {w for w in re.split(r"[^a-z0-9]+", (s or "").lower()) if len(w) > 2 and w not in _STOP}


def _label_for(page, el) -> str:
    """Text of the <label> bound to an element, by for= or by nesting."""
    try:
        eid = el.get_attribute("id")
        if eid:
            loc = page.locator(f'label[for="{eid}"]')
            if loc.count():
                return loc.first.inner_text().strip()
        # Nested label, or an unlabelled field with text sitting right above it.
        wrapper = el.evaluate(
            "e => { const l = e.closest('label'); return l ? l.innerText : ''; }"
        )
        if wrapper.strip():
            return wrapper.strip()
        prev = el.evaluate("e => e.previousElementSibling ? e.previousElementSibling.innerText : ''")
        return (prev or "").strip()
    except Exception:  # noqa: BLE001 - a missing label is normal, not an error
        return ""


def _identity(page, el) -> str:
    """Every word that identifies this field, as one lowercase blob."""
    parts = []
    for attr in ("id", "name", "placeholder", "aria-label", "title", "autocomplete"):
        try:
            parts.append(el.get_attribute(attr) or "")
        except Exception:  # noqa: BLE001
            pass
    parts.append(_label_for(page, el))
    return " ".join(p for p in parts if p)


def _score(want: str, blob: str) -> float:
    """0..1 - how confidently `want` names the field described by `blob`."""
    want_t, blob_t, blob_l = _tokens(want), _tokens(blob), blob.lower()
    if not want_t or not blob_t:
        return 0.0
    want_l = want.lower().strip()
    if want_l and want_l in blob_l:
        return 1.0
    hits = want_t & blob_t
    return len(hits) / len(want_t)


def _kind(el) -> str:
    try:
        return (el.evaluate("e => e.tagName") or "").lower()
    except Exception:  # noqa: BLE001
        return ""


def locate(page, label: str, threshold: float = 0.6):
    """Find the field `label` refers to. Returns (locator, kind, score) or (None,'',0)."""
    want = (label or "").strip()
    if not want:
        return None, "", 0.0

    # 1. Playwright's own accessible locators get the easy cases right.
    for make in (
        lambda: page.get_by_label(want, exact=False),
        lambda: page.get_by_placeholder(want, exact=False),
    ):
        try:
            loc = make()
            if loc.count() == 1:
                return loc.first, _kind(loc.first), 1.0
        except Exception:  # noqa: BLE001
            continue

    # 2. Otherwise score every field on the page by word overlap.
    fields = page.locator(
        "input:not([type=hidden]):not([type=radio]):not([type=checkbox]), textarea, select"
    )
    best, best_score = None, 0.0
    for i in range(fields.count()):
        el = fields.nth(i)
        try:
            s = _score(want, _identity(page, el))
        except Exception:  # noqa: BLE001
            continue
        if s > best_score:
            best, best_score = el, s

    if best is not None and best_score >= threshold:
        return best, _kind(best), best_score
    return None, "", best_score


def _set(el, kind: str, value: str) -> str:
    """Write one value. Returns '' on success or a human-readable reason."""
    v = str(value)
    if kind == "select":
        try:
            el.select_option(label=v)
        except Exception:  # noqa: BLE001 - option label may differ from visible text
            try:
                el.select_option(value=v)
            except Exception as e:  # noqa: BLE001
                return f"select has no option matching {v!r} ({e})"
        return ""
    if kind == "textarea":
        el.fill(v)
        return ""
    # Checkbox / radio: value means "on".
    try:
        typ = (el.get_attribute("type") or "").lower()
    except Exception:  # noqa: BLE001
        typ = ""
    if typ == "checkbox":
        if v.lower() in ("true", "yes", "1", "haan", "on"):
            el.check()
        elif v.lower() in ("false", "no", "0", "nahi", "off"):
            el.uncheck()
        return ""
    el.fill(v)
    return ""


def _launch(pw, headed: bool, slow_mo: int):
    """Prefer the Chrome already installed on the machine.

    Playwright's bundled Chromium is a 195 MB download that stalls on half the
    networks this will run on. Chrome is already here, and it is a real browser
    with real bot-detection behaviour, which is what we want to be tested
    against. Fall back to the bundled build only if Chrome is absent.
    """
    opts = {"headless": not headed, "slow_mo": slow_mo}
    try:
        return pw.chromium.launch(channel="chrome", **opts)
    except Exception:  # noqa: BLE001 - no Chrome on this machine
        return pw.chromium.launch(**opts)


def get_page(url: str, headed: bool = DEFAULT_HEADED, slow_mo: int = DEFAULT_SLOW_MO):
    """Reuse one browser. Opens `url` in the shared page."""
    with _lock:
        if _state.get("page") is None or _state["page"].is_closed():
            pw = sync_playwright().start()
            browser = _launch(pw, headed, slow_mo)
            ctx = browser.new_context(viewport={"width": 1280, "height": 1000})
            page = ctx.new_page()
            _state.update(pw=pw, browser=browser, ctx=ctx, page=page)
        page = _state["page"]
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(500)
    return page


def open_page(url: str, headed: bool = DEFAULT_HEADED) -> dict:
    """Open a URL and return the text a human would have had to read."""
    page = get_page(url, headed=headed)
    text = page.inner_text("body")
    return {
        "url": page.url,
        "title": page.title(),
        "text": text[:READ_CHARS],
        "truncated": len(text) > READ_CHARS,
        "forms": page.locator("form").count(),
        "fields": page.locator("input, textarea, select").count(),
    }


def fill_form(fields: dict[str, Any], url: str | None = None, headed: bool = DEFAULT_HEADED) -> dict:
    """Fill a form we have never seen, addressed by the words printed on it.

    Always reports which fields it could NOT place. A silent partial fill is
    the worst outcome here, because the agent would then tell the user it
    succeeded.
    """
    if url:
        page = get_page(url, headed=headed)
    else:
        with _lock:
            page = _state.get("page")
        if page is None or page.is_closed():
            return {"filled": {}, "missing": list(fields), "errors": ["no page open; pass a url"]}

    filled, missing, errors = {}, [], []
    for label, value in fields.items():
        if value in (None, "", []):
            continue
        el, kind, score = locate(page, label)
        if el is None:
            missing.append(label)
            continue
        try:
            why = _set(el, kind, value)
        except Exception as e:  # noqa: BLE001
            why = f"{type(e).__name__}: {e}"
        if why:
            errors.append(f"{label}: {why}")
        else:
            filled[label] = {"value": str(value), "control": kind, "confidence": round(score, 2)}

    return {"filled": filled, "missing": missing, "errors": errors, "url": page.url}


def click_button(text: str, url: str | None = None, headed: bool = DEFAULT_HEADED) -> dict:
    """Click a button by its visible words."""
    if url:
        page = get_page(url, headed=headed)
    else:
        with _lock:
            page = _state.get("page")
        if page is None or page.is_closed():
            return {"ok": False, "error": "no page open; pass a url"}

    t = (text or "").strip()
    for loc in (page.get_by_role("button", name=t, exact=False),
                page.get_by_role("link", name=t, exact=False),
                page.locator(f'button:has-text("{t}")'),
                page.locator(f'[type="submit"]:has-text("{t}")')):
        try:
            if loc.count() == 1:
                loc.first.click()
                page.wait_for_timeout(1200)
                return {"ok": True, "clicked": t, "url": page.url, "title": page.title()}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    return {"ok": False, "error": f"no single button matching {t!r}"}


def read_result(patterns: list[str] | None = None, url: str | None = None) -> dict:
    """Pull a confirmation value (reference number, amount) off the page.

    Patterns are regexes the agent chose from the page it just saw, so this
    works on a portal we have never seen. Falls back to a heuristic sweep for
    anything that looks like an ID.
    """
    if url:
        page = get_page(url, headed=DEFAULT_HEADED)
    else:
        with _lock:
            page = _state.get("page")
        if page is None or page.is_closed():
            return {"ok": False, "error": "no page open"}

    text = page.inner_text("body")
    for p in patterns or []:
        try:
            m = re.search(p, text, re.I)
        except re.error:
            continue
        if m:
            return {"ok": True, "pattern": p, "value": m.group(0), "text": text[:READ_CHARS]}

    # Heuristic: a labelled element holding something ID-shaped.
    for node in page.locator("[id], [data-ref], strong, h2, h3").all()[:200]:
        try:
            label = (node.get_attribute("id") or "").lower()
            val = node.inner_text().strip()
        except Exception:  # noqa: BLE001
            continue
        if val and len(val) < 80 and re.search(r"[A-Z]{2,}\s?\d{5,}|\d{7,}", val) and re.search(
            r"ref|reg|id|no|number|status|amount|paid|success", label
        ):
            return {"ok": True, "matched_id": label, "value": val, "text": text[:READ_CHARS]}

    return {"ok": False, "error": "no confirmation value found", "text": text[:READ_CHARS]}


def screenshot(url: str | None = None) -> bytes:
    """PNG of the current page, for a vision-model fallback on unknown markup."""
    if url:
        page = get_page(url, headed=DEFAULT_HEADED)
    else:
        with _lock:
            page = _state.get("page")
        if page is None or page.is_closed():
            raise RuntimeError("no page open")
    return page.screenshot(full_page=True)


def shutdown() -> None:
    with _lock:
        for key in ("browser", "pw"):
            obj = _state.get(key)
            if obj:
                try:
                    obj.close() if key == "browser" else obj.stop()
                except Exception:  # noqa: BLE001
                    pass
        _state.clear()
