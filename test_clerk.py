"""One runnable check for the general executor.

  python test_clerk.py

Covers the three things that can silently break: the fuzzy field matcher (the
whole reason we can work a site we have never seen), the search backend, and a
real end-to-end form fill against the demo portal.
"""

from __future__ import annotations

import socket
import sys
import threading
import time
from datetime import date, timedelta

from clerk.browser import _score, _tokens
from clerk import browser, search, tools
from clerk.eligibility import Applicant, evaluate

FIELDS = {
    "full name": "full name",
    "husband": "husband",
    "aadhaar": "aadhaar",
    "age": "age",
    "mobile": "mobile",
    "district": "select_district",
    "lmp": "lmp",
    "ifsc": "bank ifsc",
    "children": "children",
}


def test_tokens():
    assert _tokens("Aadhaar - Last 4 digits") == {"aadhaar", "last", "digits"}
    assert _tokens("Enter your name") == {"name"}, "stop words must drop"
    assert _tokens("") == set()


def test_field_matcher_picks_the_right_field():
    """The crux of 'works on a portal we never saw'."""
    for label, identity in FIELDS.items():
        s = _score(label, identity)
        assert s >= 0.6, f"{label!r} vs {identity!r} scored only {s}"


def test_field_matcher_rejects_the_wrong_field():
    # Labels must not collide across fields.
    for a, b in [("aadhaar", "bank ifsc"), ("district", "children"),
                 ("husband", "mobile"), ("age", "ifsc")]:
        assert _score(a, b) < 0.6, f"{a!r} wrongly matched {b!r}"

    # And a field with nothing in common must not match at all.
    assert _score("full name", "captcha token") == 0.0


def test_field_matcher_ignores_id_prefixes():
    """Real portals prefix ids with the form name: 'pmpmvy_district'."""
    assert _score("district", "pmpmvy_district") == 1.0
    assert _score("bank ifsc", "applicant_bank_ifsc_code") == 1.0


def test_eligibility_still_runs_as_code():
    # An amount must come from these rules, never from the model.
    a = Applicant(
        name="Sunita Devi",
        age=27,
        mobile="9876543210",
        bank_ifsc="SBIN0001234",
        aadhaar_last4="1234",
        district="Karnool",
        lmp=date.today() - timedelta(days=30),
        children=1,
        girl_child=True,
    )
    v = evaluate(a)
    assert v.eligible, v.reason
    assert v.benefit == 6000, v.benefit
    assert "6000" in v.voice(), "amount must reach the spoken line"

    # Second child who is a boy: no benefit.
    assert Applicant(**{**a.__dict__, "children": 2, "girl_child": False}).benefit == 0
    # Under 19: rejected.
    assert not evaluate(Applicant(**{**a.__dict__, "age": 17})).eligible


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_search_reaches_the_live_web():
    res = search.search_web("Pradhan Mantri Matru Vandana Yojana")
    if res.get("error"):
        print(f"  search SKIP ({res['error']})")
        return
    assert res["results"], "live search returned nothing"
    assert all(r["url"].startswith("http") for r in res["results"])
    assert "duckduckgo.com/l/?uddg=" not in search.format_results(res), "redirects not unwrapped"


def test_search_gov_filter_keeps_only_official_sources():
    res = search.search_web("Matru Vandana Yojana", gov_only=True)
    if res.get("error"):
        print(f"  gov search SKIP ({res['error']})")
        return
    for r in res["results"]:
        assert ".gov.in" in r["url"] or ".nic.in" in r["url"], f"leaked non-gov: {r['url']}"


def test_end_to_end_fill_on_a_portal_we_did_not_configure():
    """The money shot: open a page, address its fields by printed label, submit."""
    import uvicorn

    from server import app

    port = _free_port()
    cfg = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(cfg)
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    assert server.started, "demo portal did not start"

    url = f"http://127.0.0.1:{port}/portal/"
    try:
        # Deliberately the printed labels, not the #ids.
        res = tools.call("fill_form", {
            "url": url,
            "fields": {
                "Name": "Sunita Devi",
                "Husband's Name": "Ramesh",
                "Aadhaar": "1234",
                "Age": "27",
                "Mobile": "9876543210",
                "District": "Karnool",
                "LMP": "01/02/2026",
                "Bank IFSC": "SBIN0001234",
                "Children": "1",
            },
        })
        assert not res["missing"], f"could not place: {res['missing']}"
        assert not res["errors"], f"errors: {res['errors']}"
        assert len(res["filled"]) == 9, f"only filled {len(res['filled'])}/9"

        # Now the same via the generic click tool - no portal-specific submitter.
        assert tools.call("click_button", {"text": "Submit"})["ok"]
        out = tools.call("read_result", {"patterns": [r"PMMVY\d{8}"]})
        assert out["ok"], f"no reference read back: {out}"
        assert out["value"].startswith("PMMVY")
        print(f"  submitted and read back {out['value']}")
    finally:
        browser.shutdown()


def test_a_slow_tool_does_not_make_the_caller_wait():
    """The dead-air constraint. A real fill takes ~20s. The caller must get an
    answer immediately, and the result must arrive on a later turn."""
    import asyncio
    import json
    import os
    from types import SimpleNamespace

    import server
    from server import Turn

    llm_calls: list[list[dict]] = []

    async def fake_create(*, model, messages, tools=None, temperature=None):
        llm_calls.append(messages)
        if len(llm_calls) == 1:
            msg = SimpleNamespace(
                content=None,
                tool_calls=[
                    SimpleNamespace(
                        id="call_1",
                        function=SimpleNamespace(
                            name="search_web",
                            arguments='{"query": "matru vandana yojana"}',
                        ),
                    )
                ],
            )
        else:
            msg = SimpleNamespace(content="Ho gaya.", tool_calls=[])
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])

    os.environ["LLM_API_KEY"] = "sk-test"
    server.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
    )
    server.sessions.clear()

    try:
        r1 = asyncio.run(server.turn(Turn(session="t1", text="khojo")))
        d1 = json.loads(r1.body)
        assert d1["working"] is True, d1
        assert d1["events"] == ["search_web"], d1
        assert d1["reply"], "she must hear something immediately, not silence"

        # The result lands in the session, off the request path.
        for _ in range(60):
            if server.sessions["t1"]["pending"]:
                break
            time.sleep(0.25)
        assert server.sessions["t1"]["pending"], "tool never reported back"

        r2 = asyncio.run(server.turn(Turn(session="t1", text="aur batao")))
        d2 = json.loads(r2.body)
        assert d2["working"] is False, d2
        # The tool output must reach the model as a tool message matching its call.
        tool_msgs = [m for m in llm_calls[-1] if m.get("role") == "tool"]
        assert tool_msgs and tool_msgs[0]["tool_call_id"] == "call_1", tool_msgs
        print(f"  replied immediately, delivered result on turn 2")
    finally:
        server.client = None
        server.sessions.clear()


if __name__ == "__main__":
    fns = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    failed = 0
    for name, fn in fns:
        try:
            fn()
            print(f"PASS {name}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"FAIL {name}: {type(e).__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
