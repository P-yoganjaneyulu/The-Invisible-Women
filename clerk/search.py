"""Real web search. No embeddings, no vector DB, no index.

Discovery genuinely is a search problem: the answer lives on a page we have
never seen and cannot have pre-chunked. So we search, read the top snippets,
and let the agent decide whether to keep looking.

Backends, in order of preference:
  Tavily   - if TAVILY_API_KEY is set. Agent-friendly, returns clean snippets.
  DuckDuckGo - no key, no signup, HTML endpoint. Fine for a demo, rate-limited.

Both return the same shape: a list of {title, url, snippet}.
"""

from __future__ import annotations

import html
import os
import re
from urllib.parse import unquote

import httpx

# Ponytail: gov.in trust filter is the whole point of the gov_only flag. One
# list, kept deliberately small. Extend when a real deployment needs more.
GOV_SUFFIXES = (".gov.in", ".nic.in", ".gov", ".ac.in")

MAX_RESULTS = 6
SNIPPET_CHARS = 400
TIMEOUT = 20.0


def _clean(text: str) -> str:
    """Strip tags/entities and collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _is_gov(url: str) -> bool:
    return url.endswith(GOV_SUFFIXES) or any(s in url for s in GOV_SUFFIXES)


def _search_tavily(query: str, gov_only: bool) -> list[dict]:
    key = os.environ["TAVILY_API_KEY"]
    include = "gov.in" if gov_only else None
    with httpx.Client(timeout=TIMEOUT) as c:
        r = c.post(
            "https://api.tavily.com/search",
            json={
                "api_key": key,
                "query": query,
                "max_results": MAX_RESULTS * 2 if gov_only else MAX_RESULTS,
                "search_depth": "basic",
                # Ask for official sources up front rather than filtering after.
                "include_domains": ["gov.in", "nic.in"] if gov_only else None,
                "include_answer": False,
            },
        )
        r.raise_for_status()
        hits = r.json().get("results", [])
    out = [
        {"title": h.get("title", ""), "url": h.get("url", ""), "snippet": h.get("content", "")}
        for h in hits
    ]
    # Drop Tavily's own include-domain expansion artefacts.
    return [h for h in out if h["url"].startswith("http") and (not include or _is_gov(h["url"]))]


def _search_duckduckgo(query: str, gov_only: bool) -> list[dict]:
    with httpx.Client(
        timeout=TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (compatible; hackathon-demo/1.0)"},
    ) as c:
        r = c.post("https://html.duckduckgo.com/html/", data={"q": query, "kl": "in-en"})
        r.raise_for_status()
        page = r.text

    # DDG wraps every result link in a redirect; unwrap it or the agent gets a
    # useless duckduckgo.com/l/?uddg=... URL it cannot open.
    out: list[dict] = []
    for m in re.finditer(
        r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', page, re.S
    ):
        href, title = m.group(1), _clean(m.group(2))
        u = re.search(r"[?&]uddg=([^&]+)", href)
        if u:
            href = unquote(u.group(1))
        elif href.startswith("//"):
            href = "https:" + href

        # Snippet lives in the block after the title link.
        tail = page[m.end() : m.end() + 1200]
        sn = re.search(r'class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>', tail, re.S)
        snippet = _clean(sn.group(1)) if sn else ""

        if href.startswith("http"):
            out.append({"title": title, "url": href, "snippet": snippet[:SNIPPET_CHARS]})

    # Fallback: some responses drop the class attr onto an <a> without it.
    if not out:
        for m in re.finditer(r'<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>', page, re.S):
            href, title = m.group(1), _clean(m.group(2))
            if len(title) > 12 and "duckduckgo.com" not in href:
                out.append({"title": title, "url": href, "snippet": ""})

    if gov_only:
        out = [h for h in out if _is_gov(h["url"])]
    return out[:MAX_RESULTS]


def search_web(query: str, gov_only: bool = False) -> dict:
    """Search the live web. Returns snippets only - never whole pages."""
    query = (query or "").strip()
    if not query:
        return {"query": query, "results": [], "error": "empty query"}

    backend, errors = None, []
    if os.environ.get("TAVILY_API_KEY"):
        backend = "tavily"
        try:
            results = _search_tavily(query, gov_only)
        except Exception as e:  # noqa: BLE001 - fall through to the free backend
            errors.append(f"tavily: {e}")
            backend = None
    if backend is None:
        backend = "duckduckgo"
        try:
            results = _search_duckduckgo(query, gov_only)
        except Exception as e:  # noqa: BLE001
            return {
                "query": query,
                "results": [],
                "backend": "duckduckgo",
                "error": "; ".join(errors + [f"duckduckgo: {e}"]) or "search failed",
            }

    # An empty gov_only result is information: tell the agent to widen, don't hide it.
    note = "no matches" if not results else ""
    if gov_only and not results:
        note = "no official .gov.in sources matched; try a wider search without gov_only"

    return {"query": query, "backend": backend, "results": results, "note": note}


def format_results(res: dict) -> str:
    """Compact snippet block for the LLM. No URLs to fetch yet - decide first."""
    if res.get("error") and not res["results"]:
        return f"search failed ({res['error']})"
    if not res["results"]:
        return res.get("note") or "no results"
    lines = []
    for i, h in enumerate(res["results"], 1):
        lines.append(f"{i}. {h['title']}\n   {h['url']}\n   {h['snippet']}")
    out = "\n".join(lines)
    if res.get("note"):
        out += f"\n(note: {res['note']})"
    return out
