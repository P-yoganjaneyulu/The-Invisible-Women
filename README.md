# The Invisible Woman

**A voice agent that uses the internet for a woman who can't read it.**

48% of girls in rural India have never used the internet. Of those who have, most
were guided by a male family member. The exclusion is not a capability gap — it
is an interface that assumes you can read.

So we removed the interface. She speaks. An agent works. She never sees a screen.

---

## What this is

The agent is a **general executor**. It is not tied to one government form.

It searches the live web, opens pages, reads them, finds form fields by the
words printed next to them, types her answers in, presses the button, and reads
the confirmation out loud.

Point it at a page it has never seen and it works out what to press. There are
**no hardcoded selectors anywhere in this repo.**

```
voice  ->  LLM (multilingual, tool-calling)
            -> search_web   find it
            -> open_page    read it
            -> fill_form    write her answers into it
            -> click_button press it
            -> read_result  read the confirmation back
            -> check_eligibility   the only source of truth for money
        ->  voice reply
```

Government schemes are the vertical we demo, not the boundary of the product.
`docs/problem-and-approach.md` has the full argument, including why a vector
database is the wrong tool here and why eligibility must never come out of a
language model.

---

## Two rules the code actually enforces

**1. Nothing auditable comes from the model.**
Amounts, eligibility, and dates go through `clerk/eligibility.py` — plain Python
with 9 tests. The model decides *what to do*. It never decides *what a woman is
owed*. Ask it for a rupee amount and it has nothing to say unless
`check_eligibility` returned one.

**2. No tool blocks the audio path.**
A browser fill takes ~20 seconds. If the voice loop waits for it, she hears dead
air and assumes it failed and hangs up. `clerk/tools.py:spawn()` runs tools off
the audio path so she can be spoken to while the page loads.

---

## Honesty: what is real and what is simulated

We would rather show the wall than hide it.

| Real in this repo | Simulated / not built yet |
|---|---|
| Live web search (no key required) | Live **phone** calls — see open decisions below |
| Real browser automation on real pages | The demo portal at `/portal/` is our own HTML, not `pmmvy.wcd.gov.in` |
| Deterministic eligibility rules | Payment / DBT rails |
| The general executor | Facial recognition, OTP, CAPTCHA — deliberately not automated |
| Voice in/out via the browser's Web Speech API | Rural-dialect speech (current TTS/ASR is generic) |

On the last row of the real column: automating Aadhaar facial recognition, or
routing around an OTP sent to a phone she doesn't have, is not a technical
problem to be solved later. It is biometric fraud and a terms-of-service
violation. Identity is not a UI problem and cannot be made into one. A human
confirmation step is the correct design, not a compromise — the official PMMVY
guidance already names the nearest Anganwadi/ASHA worker as the person who fills
this form. **We are not replacing the human clerk. We are removing the toll.**

---

## Run it

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

copy .env.example .env          # then paste a key in
uvicorn server:app --port 8000
```

Open <http://localhost:8000>. The demo portal is at
<http://localhost:8000/portal/>.

Any OpenAI-compatible endpoint works — see the comments in `.env.example` for
Gemini and Groq.

Playwright uses your **installed Chrome** (`channel="chrome"`), so there is no
195 MB browser download. It falls back to bundled Chromium only if Chrome is
absent.

### Tests

```bash
python test_cligibility.py   # 9 checks, the rules
python test_clerk.py         # 8 checks, the executor
```

`test_clerk.py` is the one that matters. Its final test boots the server, opens
the demo portal, addresses every field **by its printed label rather than its
id**, clicks Submit through the generic clicker, and reads back the reference
number. The four field-matcher tests are what make that claim defensible: they
assert the matcher finds the right field, rejects the wrong one, and handles the
`pmpmvy_district` style of prefixed ids that real portals use.

---

## Layout

```
server.py             FastAPI app, LLM turn loop, the agent's behaviour prompt
index.html            the voice UI (browser Web Speech API)
demo_portal.html      simulated government portal, for the demo
landing.html          project landing page
clerk/
  browser.py          general browser control. locates fields by printed words
  search.py           live web search. Tavily if you have a key, else DuckDuckGo
  tools.py            tool schemas + dispatch. spawn() keeps the voice alive
  eligibility.py      scheme rules as code. never ask the model for money
docs/
  problem-and-approach.md   the full argument
test_clerk.py
test_eligibility.py
```

---

## Open decisions

**Speech stack.** Either keep OpenAI Realtime — zero lines of speech code, free
barge-in, but no credible Hindi or rural-dialect voice — or keep the Twilio
transport and swap the model peer for our own ASR → LLM → Indic TTS chain
(~250 lines, ~1.5s latency). We lean toward the second: language *is* the
problem statement, and the latency is affordable because this is a task
executor, not a conversation.

**Telephony.** No Twilio account wired up yet. The browser path proves the same
code path; a phone number only decides who can try it.
