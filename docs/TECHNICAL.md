# Technical documentation

Everything an engineer needs to run, evaluate or extend this. For the argument
behind the design, read [`problem-and-approach.md`](problem-and-approach.md).
For the one-minute version, read the [root README](../README.md).

---

## 1. The shape of the system

```
she speaks
   |
   v
[1] TRANSPORT          browser Web Speech API  (today)
                        telephony / SIP         (next)
   |
   v
[2] CONVERSATION       server.py  -  LLM turn loop + behaviour prompt
   |                   decides which tool, in what order, and what to say
   v
[3] EXECUTOR           clerk/tools.py  -  6 tools, run OFF the audio path
   |
   +-- search.py       live web search (Tavily or DuckDuckGo)
   +-- browser.py      Playwright. finds fields by printed words
   +-- eligibility.py  scheme rules as plain Python
   |
   v
[4] HUMAN              identity confirmation. never automated.
```

Two properties hold at every layer and are enforced in code, not convention:

**Nothing auditable comes from the model.** Amounts, eligibility and dates
live in `clerk/eligibility.py`. If the model is asked for a rupee figure and
`check_eligibility` has not returned one, there is nothing to say.

**No tool blocks the audio path.** A browser fill takes ~20 s. If the voice
loop awaited it, the caller hears dead air, assumes it failed, and hangs up.
`tools.spawn()` runs tools on a separate thread and the turn returns
immediately. This is the single most important latency constraint in the
system and it has a test guarding it.

---

## 2. Running it

### Dependencies

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

`fastapi`, `uvicorn[standard]`, `openai`, `python-dotenv`, `playwright`.

**No browser download.** `clerk/browser.py:_launch()` requests
`channel="chrome"` and falls back to bundled Chromium only if Chrome is
absent. The bundled download is 195 MB and frequently stalls; there is no
reason to pay it when Chrome is already installed.

### Environment

```bash
copy .env.example .env
```

| Variable | Default | Read by |
|---|---|---|
| `LLM_API_KEY` | — | `server.py`. **Required.** `/api/turn` returns a friendly 500 without it |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | `server.py`. Any OpenAI-compatible endpoint |
| `LLM_MODEL` | `gpt-4o-mini` | `server.py` |
| `TAVILY_API_KEY` | — | `search.py`. Optional; DuckDuckGo is the fallback |
| `PORT` | `8000` | `server.py` |

`HEADED` appears in `.env.example` but **is not read by any current code** — it
is a leftover from the deleted `mock_portal/portal.py`. Remove it or wire it;
right now `browser.DEFAULT_HEADED = True` and headed mode is always on.

```bash
uvicorn server:app --port 8000
```

| Route | What |
|---|---|
| `GET /` | the voice UI |
| `GET /portal/` | the demo portal |
| `POST /api/turn` | one conversation turn |
| `GET /api/state/{sid}` | applicant record + tools in flight |

### Tests

```bash
python test_eligibility.py   # 9 checks — the rules
python test_clerk.py         # 9 checks — the executor
```

Plain `assert` functions, no framework, no fixtures. Both run under
`python <file>.py` and exit non-zero on failure.

`test_eligibility.py` is the faster and more important of the two. If it fails,
the agent is lying to women about money.

`test_clerk.py` includes a real end-to-end: it boots the server in a thread,
opens the demo portal, fills all nine fields **by printed label rather than id**,
clicks Submit through the generic clicker, and reads the reference back.

---

## 3. The six tools

`clerk/tools.py` holds `SCHEMAS` (what the model sees), `REGISTRY` (name →
function), and two dispatch paths. There is **no `submit_application` tool** —
`fill_form` + `click_button` + `read_result` *is* submitting, and it works the
same on a portal nobody configured.

| Tool | Signature | Notes |
|---|---|---|
| `search_web` | `(query, gov_only=False)` | Real network call |
| `open_page` | `(url)` | Returns up to 4000 chars of visible text |
| `fill_form` | `(fields, url=None)` | `fields: dict[printed_label, value]`. Returns `filled`, `missing`, `errors` — **always** |
| `click_button` | `(text, url=None)` | Matches visible button text |
| `read_result` | `(patterns, url=None)` | Regex over page text, then an ID-shaped heuristic sweep |
| `check_eligibility` | `(...)` | The only source of money. Returns a spoken `voice` string |

### The dead-air mechanism

```python
tools.spawn(name, args, on_done=collector)   # returns immediately
# turn returns {"reply": "theek hai, ...", "working": true}

# next turn: pending results are merged into history as role:"tool"
# messages, positioned after the assistant tool_calls message
```

`spawn()` submits to a `ThreadPoolExecutor(max_workers=1)`. Single worker on
purpose: a Playwright browser is not thread-safe.

Results are collected by `on_done`, which fires whenever the thread finishes —
including after the call that started it has already returned. `_collector()`
appends to `sessions[sid]["pending"]`, and the **next** request drains it.

The old design ran tools synchronously, then made a second LLM call to phrase
the reply. That was removed: the next turn's LLM call does the phrasing
naturally, with the tool output already in context.

Message ordering matters and is easy to get wrong. OpenAI requires the `tool`
message to immediately follow the assistant message that made the calls, with
a matching `tool_call_id`. Pending results are therefore spliced in *before*
the new user message. `_collector` is what guarantees the id survives the
thread hop.

---

## 4. How field matching works

This is the load-bearing piece. It is what makes "works on a site we have never
seen" true instead of aspirational.

`browser.py` scores a candidate against what the model asked for:

1. `_tokens()` — split on non-alphanumerics, drop tokens ≤ 2 chars and
   stopwords (`the`, `and`, `for`, `your`, `please`, `enter`, …).
2. `_identity()` — join the element's `id`, `name`, `placeholder`, `aria-label`,
   `title`, `autocomplete` and resolved `<label>` text into one blob.
3. `_score(want, blob)` — **1.0 on exact substring match**, else the ratio of
   shared tokens to the smaller set.
4. `locate()` — `threshold = 0.6`. Tries `get_by_label`, then
   `get_by_placeholder`, then a fuzzy sweep over every
   `input`/`textarea`/`select`, skipping hidden, radio and checkbox types.

Exact-substring-first is why `pmpmvy_district` scores 1.0 against a request for
`district`. Real portals prefix their ids with the form name, and without that
rule the token ratio alone would not be sufficient.

### Failure modes

Being honest here, because a judge will find them:

- **Label in an image.** Several real `.gov.in` forms are image-based CAPTCHAs
  or canvas-rendered text. There is no label text to score. Not handled.
- **Frames and iframes.** `locate()` scans one document. Payment gateways and
  some Aadhaar widgets live in nested frames. Not handled.
- **Shadow DOM.** Custom dropdowns hide their real `<select>`. `_kind()` sees
  a div. `_set()` fails for that element type.
- **Colliding vocabulary.** Two fields whose labels share tokens — e.g. two
  fields both containing "address". `_score` cannot break the tie; `locate`
  returns the highest and the system reports the other as `missing` rather than
  guessing twice.
- **`missing` is a feature, not a bug.** `fill_form` never claims success it did
  not have. The agent is instructed to read `missing` back to the caller and
  ask again.

The escape hatch for all of these is vision: screenshot the element, ask a
multimodal model what it is. That is deliberately the second path, not the
first, because it is slow and non-deterministic on stage.

---

## 5. Search

`search.py` uses Tavily when `TAVILY_API_KEY` is set, otherwise the DuckDuckGo
HTML endpoint. No key is required for the default path, which matters for a
demo that must run on a stranger's laptop.

`gov_only` filters on `GOV_SUFFIXES = (".gov.in", ".nic.in", ".gov", ".ac.in")`.
DuckDuckGo wraps results in `duckduckgo.com/l/?uddg=…`; those are unwrapped
with a regex plus `urllib.parse.unquote`, otherwise every result URL handed to
the model is a redirect it cannot open.

`MAX_RESULTS = 6`, `SNIPPET_CHARS = 400`, `TIMEOUT = 20.0`. Results are
snippets only — this is an agent that goes and reads the page, so fetching full
documents here would be wasted tokens.

---

## 6. The behaviour prompt

`server.py:SYSTEM` is not decoration; it is the part that makes a 27-year-old
with no English sound like a clerk rather than a chatbot.

- **One question per turn.** Then stop. Not "one question and three optional
  follow-ups".
- **Numbers as words.** "unbees", "pachas", "solah". Never read digits as a
  string.
- **No English loanwords at all.** Not "eligible", not "portal", not "OTP".
  "aapka haq", "sarkar ki website", "naam likh diya".
- **Address fields by printed words**, never by guessing ids.
- **Read `missing` and `errors` after every fill.** Tell her plainly which
  detail could not be placed.
- **When it does not know, say so, then search.** Never invent a rule, amount,
  date or document list.
- **Aadhaar: last 4 only**, with an explicit warning to the caller first. Ask
  only if she is willing.

`eligibility.py:parse_int()` accepts Devanagari digits and spoken number words
because of two of those lines. That was not hypothetical — it was a real bug:
the prompt said "say numbers as words", the parser only scanned for digits, so
an obedient model produced `None`.

---

## 7. Layout

```
server.py             FastAPI app, LLM turn loop, behaviour prompt, dead-air wiring
index.html            voice UI. browser Web Speech API, 11 languages
demo_portal.html      simulated government portal for the demo
landing.html          project landing page
requirements.txt
.env.example

clerk/
  __init__.py         empty; makes this a real package instead of PEP 420 luck
  tools.py            6 tool schemas + registry + call()/spawn() + shutdown()
  browser.py          Playwright control, field matching, single shared browser
  search.py           live web search
  eligibility.py      scheme rules as plain Python. 9 tests

docs/
  problem-and-approach.md    the full argument and rejected alternatives
  TECHNICAL.md               this file

test_clerk.py         9 checks on the executor
test_eligibility.py   9 checks on the rules
```

`clerk/browser.py` keeps a **module-level singleton** browser guarded by a
`threading.Lock`, exposed as `get_page()`. One browser, many tools. Launching
per call costs ~1.5 s and leaks processes.

`clerk/tools.py:shutdown()` closes the browser and drains the pool. Wired to
FastAPI's `shutdown` event.

---

## 8. Next steps, in dependency order

1. **Telephony transport.** The Twilio + `<Connect><Stream>` pattern from
   `vendor/` is the right shape — bidirectional media over a WebSocket, G.711
   µ-law in and out, no transcoding. Note that vendor's loop `await`s tool
   execution inline, which reintroduces dead air; it must be restructured the
   way `spawn()` is here.
2. **Rural-dialect speech.** Options: keep the transport and swap the model peer
   for own ASR → LLM → Indic TTS (~250 lines, ~1.5 s latency, `audioop` handles
   µ-law — verified available on Python 3.13.5 here). Or keep OpenAI Realtime
   and accept generic Hindi. The first is the honest answer to the problem
   statement; the second is cheaper.
3. **ID masking** for logs and call recordings. See below.
4. **The privacy claim, precisely.** Ephemeral browsers mean nothing persists
   on our side. Two things that does *not* cover: audio sent to an LLM provider
   is logged by them, and if she is dialling from her husband's phone, **the
   call is in his call log**. Ephemeral infrastructure does not hide a call
   record from the person who owns the handset.
5. **Zero-retention API terms** if the privacy claim is going to be made
   publicly.

---

## 9. Deliberately not built

| | Why |
|---|---|
| Facial recognition bypass | Biometric fraud. Aadhaar Act 2016 §7 |
| OTP interception | The OTP goes to a phone she does not own |
| CAPTCHA solving | ToS violation, and a permanent block |
| Vector DB / RAG for eligibility | Eligibility is rules, not semantics. A similarity search over scheme documents returns confidently wrong money advice |
| 22 languages | One language, one district. A voice agent that is mediocre in twelve languages is worse than one that is native in one |
| LangGraph / agent framework | Six tools and a two-pass loop. A framework here is more code to read than the thing it replaced |
