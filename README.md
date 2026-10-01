# The Invisible Woman

**She calls a number. The agent does the rest.**

A voice agent that uses the internet on behalf of a woman who cannot read it.
No app. No screen. No login. No one to ask.

---

## Why a phone call, not an app

Every attempt to fix this reaches for a simpler screen. A cleaner form. Fewer
taps. A voice assistant inside an app.

**A minimal UI is still not minimal for her.** She does not need a shorter menu.
She needs a different interface entirely, because every interface we can ship
still assumes five things she does not have:

1. She can read prompts, menus and labels.
2. She understands icons, hamburger menus and forms.
3. She can produce the textbook version of a state language.
4. She has a phone of her own, in private.
5. She knows what an email address, a password and an OTP are.

Remove text and apps and the problem collapses to its three physical
components: **hearing, speaking, and telephony.**

And there is exactly one interface where those three already meet, and which
she has used since childhood, without ever being taught it:

**The phone call.**

She already knows the green button means answer. She already knows the red one
means hang up. That is not a tutorial we write — it is a reflex she has had
since she was six years old. And she already knows that short, memorable,
free numbers exist, because we have spent fifty years teaching her that
**112, 100 and 108** work.

So the design brief is not "design a nicer interface." It is:

> **How short, how memorable, how government-looking, and how reassuring must
> the number be so that dialling it is no harder than lifting a handset and
> pressing green?**

Everything below follows from that one constraint.

### The feature phone changes everything

A large share of rural India is still holding a Nokia — a 12-key handset with a
torch on it. **A web app does not exist for her.** Not badly supported. Not
slow. It does not exist. There is no browser to open.

So an app is not a degraded version of this product. It is a version of this
product that excludes the person we built it for.

---

## The problem

48% of girls in rural India have never used the internet. Of those who have,
most were guided by a male family member.

Millions of women are locked out of digital systems **not by capability — but
by design.**

That distinction is the whole project. Nothing is wrong with her memory, her
reasoning or her willingness. A system that she cannot use because it was built
for someone else is not a system that failed her. It is a system that was never
addressed to her.

---

## What we built

An **agent** that talks to her on the phone, understands what she needs, and
then goes and does it on the internet on her behalf.

```
        she speaks
             |
             v
     +---------------+
     |  the agent   |   hears her, in her dialect
     +---------------+
             |
             v
     +---------------+
     |  the executor |   searches the web, opens pages,
     |               |   reads them, fills forms, presses
     |               |   buttons, reads back the result
     +---------------+
             |
             v
     +---------------+
     |  the human    |   identity. Always a human.
     +---------------+
             |
             v
        she hears it done
```

Two properties make this work:

**The agent is general.** It is not a form filler for one portal. It searches,
reads, and operates pages it has never seen. There are **no hardcoded form
selectors anywhere in this codebase.** It finds a field by the words printed
next to it.

**The agent is temporary.** Her data lives inside a private browser instance
that is created when she calls and destroyed the instant she hangs up. Nothing
is written to a disk that could be lost, subpoenaed or read by the next person
to hold the phone. There is no account to log into, and therefore no account
to steal.

And the money never comes out of the model. Amounts and eligibility run through
plain Python with tests. The agent decides *what to do*. It never decides *what
she is owed*.

---

## What runs today, and what the design requires

We would rather show the wall than hide it.

| | Runs today | Required by the design |
|---|---|---|
| **Interface** | Browser page, browser voice | **A phone number.** Not built — no carrier account yet |
| **Language** | 11 languages in the UI picker | Rural dialects. Current speech is generic |
| **Executor** | Real browser, real pages, real search | Same code — this part is done |
| **Identity** | Human confirmation step | Same. Deliberately never automated |

The executor is the hard part and it works today, against real pages. The
transport is the easy part and it is not started. That ordering was
deliberate: a voice agent that cannot act is a toy, and we would rather
demo the part that is real than fake the part that sells better.

---

## The demo

1. Open the page, choose a language, press and hold the button, say what you
   need in your own words.
2. The agent asks **one question at a time**, in short sentences, with no
   English words.
3. A real Chrome window opens **on screen**. The agent finds the fields, types
   her answers in, presses submit. You watch it happen.
4. It reads the confirmation number back to her, digit by digit.

Step 3 is the point. She said four sentences and a form got filled. Nobody
touched a keyboard.

### What is real and what is simulated

| Real | Simulated |
|---|---|
| Live web search, no API key needed | Live **phone** calls |
| Real browser automation on real pages | The demo portal is our own HTML, not the real government site |
| Deterministic eligibility rules, 9 tests | Payment and bank transfer rails |
| Field matching on sites never seen | Rural-dialect speech |
| | Facial recognition, OTP, CAPTCHA — **deliberately** |

---

## The wall, and why we are not climbing it

The real PMMVY portal asks three things we cannot honestly automate:

- **Facial recognition** against her Aadhaar photo.
- **An OTP** sent to the phone number linked with her Aadhaar — which is her
  husband's phone, and she does not have access to it.
- **CAPTCHA** and passive bot-detection on every `.gov.in`.

Automating facial recognition is biometric fraud. Routing around an OTP on
someone else's phone is fraud. Defeating CAPTCHA is a terms-of-service
violation and an invitation to be blocked permanently.

**These are not engineering problems we deferred. They are crimes we declined.**

Identity is not a user-interface problem and no amount of interface work will
make it one. The correct design is a human confirming, and the correct person
is already there: the official guidance for PMMVY says the nearest **Anganwadi
or ASHA worker** can fill the form online for her.

So we do not replace the clerk. **We remove the toll.** The Anganwadi worker
still verifies. They just stop spending two hours of a village's health budget
walking to the block office to enter one woman's name.

The agent's job is the part that is safe to automate, and it is also the part
nobody will do for her at any price.

---

## Where this goes next

- **Ship the transport.** Get a number. Three digits if a government partner
  will give one; toll-free otherwise.
- **Record real dialect audio** in 3 districts and retrain nothing — swap the
  speech models, the architecture does not change.
- **Generalise the demo away from schemes.** The executor is not
  government-specific. The same code applies to a hospital form, a school
  admission, a bank KYC, a crop subsidy.
- **Keep identity human.** Always. That is not a limitation of the prototype.

---

## Run it yourself

```bash
pip install -r requirements.txt
copy .env.example .env        # paste any OpenAI-compatible key in
uvicorn server:app --port 8000
```

Open <http://localhost:8000>. Any OpenAI-compatible endpoint works — Gemini and
Groq are noted in `.env.example`.

Full architecture, tool reference and failure modes: **[`docs/TECHNICAL.md`](docs/TECHNICAL.md)**
The full argument behind the design: **[`docs/problem-and-approach.md`](docs/problem-and-approach.md)**
