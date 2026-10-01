# The Invisible Woman — Problem Research & First-Principles Approach

**Hackathon:** The Invisible Woman
**Status:** pre-build, approach locked
**Date:** 2026-10-01
**Revision:** 2 — scope corrected. The product is a **general capability**, not a government form-filler.

---

## 1. The Problem, read carefully

> In India, 48% of girls in rural areas have never used the internet. Of those who have, most were guided by a male family member. Millions of women are locked out of digital systems not by capability — but by design.

> Build an AI tool that helps a first-time woman user — with no English, no tech background, and no one to ask — independently access **one essential government service, scheme, or skill resource** through voice or simple text in her own language. The tool must require **zero prior digital knowledge** to use.

Three phrases in that brief carry the entire design, and they are easy to under-read:

| Phrase | What it actually constrains |
|---|---|
| **"one essential … service, scheme, or skill resource"** | The **unit of work is one thing, done completely.** Not a portal, not a category. Not "government forms" specifically — the brief deliberately includes *skill resources*. |
| **"independently access"** | **Access**, not "be told about," and not necessarily "submit." Reading her benefit amount, finding a scheme she qualifies for, and completing a form are all in scope. |
| **"no one to ask"** | The human intermediary is **unavailable**, not merely inconvenient. |

### 1.1 The mistake we initially made, and why it matters

Our first pass scoped the product as "an agent that fills the government portal form on her behalf."

That is **one implementation of the general problem**, mistaken for the general problem. It is the failure mode of demo-driven design: pick one concrete target, then let the target redefine the product.

The consequence would have been a tool that fills PMMVY forms. That helps with one scheme on one portal — and leaves the other 99% of the internet exactly as locked as it was this morning.

**What we actually need to build is the capability, and prove it end-to-end on one thing.**

---

## 2. First-Principles Breakdown: this is an interface failure, not a capability failure

Every modern digital system silently assumes five conditions are true:

| # | Silent assumption | Reality for the target user |
|---|---|---|
| 1 | **Text literacy** — can read prompts, menus, labels | Cannot read forms or labels in any script |
| 2 | **Visual UI comprehension** — understands icons, hamburger menus, form structure | Has never encountered a nested menu or a dropdown |
| 3 | **Formal language standard** — speaks the textbook version of a state language | Speaks a hyper-local dialect with heavy code-mixing |
| 4 | **Device ownership & privacy** — has a personal smartphone, unobserved | The phone belongs to a male family member and is monitored |
| 5 | **Digital identity infrastructure** — has an email, password, and can complete an OTP flow | Has no credentials, no registered number, cannot receive an OTP |

**All five are violated simultaneously.** This is the central observation of the project.

Note what these five have in common. They are **not** five separate problems to solve. They are five faces of a single underlying assumption:

> **The internet assumes you can read.**

Every one of them is a special case of "this system was built for someone who can read text and operate a screen." Aadhaar, UPI, IRCTC, bank passbooks, MGNREGA job cards, hospital appointment portals, school admissions, crop prices on commodity boards, WhatsApp — **all of it inherits the same assumption.** A woman who cannot read is not excluded from one bad service. She is excluded from the internet.

Which yields the actual insight:

> **Remove the literacy assumption from the internet and you have a general capability, not a special-purpose tool.**

That is why this is a platform problem and not a government-schemes problem.

### 2.1 The irreducible primitives

Strip away text, screens, and apps and the problem collapses to what is physically available to her:

> **Hearing. Speaking. Telephony.**

Those three are the only interface primitives she has. **But they are enough — if something else does the seeing, reading, and clicking on her behalf.**

This is the precise boundary of the work:

| She provides | The agent provides |
|---|---|
| Hearing, speech, a phone | Reading, navigating, deciding, clicking, typing, submitting |

A text interface fails her because she lacks reading. An agent interface succeeds her because she supplies only the three things she actually has.

---

## 3. Field Research: the four constraints that break naive designs

Identified before any code, and each one has killed a plausible approach.

### 3.1 The Shared Phone Bottleneck

The phone is not hers. It belongs to her husband, father, or brother.

- Installing a new app creates suspicion, friction, or outright confiscation.
- Anything she does on the device is **visible and auditable** to the household.
- If she types an Aadhaar number into a form, someone is watching.

**Design rule:** **zero installs**, and never put sensitive data on a screen she does not privately own.

> Also a legal requirement. Aadhaar information is confidential under the Aadhaar (Targeted Delivery of Financial and Other Subsidies, Benefits and Services) Act, 2016, and its penal provisions cover leaking Aadhaar information. A design that has a woman read a 12-digit number aloud on a shared handset is a legal exposure *and* a violation of the privacy premise the product depends on.

### 3.2 App & Storage Fatigue

Target devices cost roughly $50–$80. Typical configuration is 1–2 GB RAM and a full storage partition.

- Any additional app competes for space she does not have.
- Realistic adoption pattern is *install → storage pressure → uninstall within days*.
- The most-installed app is usually WhatsApp, which is itself a shared app on a shared device.

**Design rule:** the entry point must already exist on every phone. **A phone call.**

### 3.3 Dialect vs. Official Language

Scheme and site language is a different system from rural spoken language.

| System | Example |
|---|---|
| Official register | *beneficiary*, *instalment*, *Aadhaar-seeded*, *documents required* |
| Rural speech | Bhojpuri, Mewati, Bundeli, Rayalaseema Telugu, Magahi |

Two compounding failures:

1. **Vocabulary.** She cannot translate her own situation into a site's vocabulary, because she has never been asked to think in those terms.
2. **Acoustic domain mismatch.** General-purpose voice models train predominantly on news broadcast and studio speech. Real rural audio is recorded on a ₹1,500 phone, at arm's length, outdoors, over background noise — livestock, rain, engines, other household members, a stone room with hard reverberation. Word-error-rate degrades sharply on this domain.

**Design rule:** speech recognition must be **fine-tuned on rural speech**. Non-negotiable, and the project's clearest technical moat.

### 3.4 The Action Gap

The failure most voice bots ship:

> Giving a rural woman a 500-word summary is useless.

She does not want **information**. She wants **a thing done**: am I eligible, which option is mine, how much, what do I bring, who do I talk to, can you just do it.

Information is the *output of a process she cannot run*. Handing her the output while leaving the process to her has not solved anything — it has relocated the burden and given it a voice.

This holds across domains, not just government:

| Domain | What "information" looks like | What she actually needs |
|---|---|---|
| Government scheme | A 400-word eligibility page | "Am I eligible? How much? Register me." |
| Bank / UPI | A list of transaction types | "Send ₹500 to my mother. Done." |
| Hospital | Department names and OPD timings | "Book me for tomorrow morning." |
| Agriculture | A commodity price table | "What is the rate today? Where do I sell?" |
| Skills | A course catalogue | "Teach me this." |
| Any site | Navigation | "Find the one button and press it." |

Same shape every time. **The general capability is: navigate to a goal, execute it, report the result.**

**Design rule:** the agent executes. It does not narrate.

---

## 4. First-Principles Conclusion: the UPI argument

UPI did not succeed because Indians love apps. It succeeded because it was designed around the constraints that actually exist:

| Constraint | UPI's answer | Our answer |
|---|---|---|
| No English needed | UPI 12303 from any bank app | Dial a number, speak |
| No new app | Lives inside an existing app | Missed call → we call back |
| No data plan | USSD fallback | Audio is the cheapest possible payload |
| No documentation | No signup form | No signup at all |
| No trust network | Bank-grade, government-backed | Same: we act on official sites, we never invent policy |

**"UPI for Voice."** A protocol that requires nothing of the user except the ability to speak and to hear.

---

## 5. The research finding that reshaped the idea

Before designing, we checked what already exists **for this exact user**.

From official PMMVY guidance, Ministry of Women & Child Development:

> "The nearest Anganwadi worker/ASHA worker can fill the form online for an eligible woman."
>
> "Field functionaries like Anganwadi Workers / ASHA workers can fill the application online for the beneficiary in their jurisdiction."

**A human clerk already exists.** Free, legal, authorised, trusted, physically present.

### 5.1 This is not specific to government — it is a pattern

Which is the actual finding. Across every domain, the universal fallback for a non-literate user is the same: **a person who reads and clicks on their behalf.**

| Domain | The existing fallback | What it costs the user |
|---|---|---|
| Government schemes | ASHA / Anganwadi / CSC operator | A 20-minute visit in working hours, during which she explains her situation in dialect and the worker translates it into official vocabulary |
| Banking | Branch staff, or a family member with a phone | Standing in line, or owing a favour |
| Hospitals | Front-desk staff | A queue, during illness |
| Education | Teacher, older sibling | Depends on their goodwill |
| Agriculture | Trader, middleman | **A cut of her income** — the middleman is the business model |

There is a **toll on every mediated interaction**, paid in time, dignity, or money — and in agriculture, paid directly out of her income.

That toll is the market. It is paid constantly, by millions, and it is almost entirely invisible because nobody prices it.

### 5.2 The strategic consequence

> **Do not replace the human clerk. Remove the toll.**

The agent absorbs the entire class of routine mediated tasks — the ones with knowable answers — and escalates only genuinely exceptional cases, handing that human a **completed record** instead of a blank form.

This framing converts our biggest constraint into our strongest claim. The human-in-the-loop is not a fallback we tolerate. It is the **only legally valid design** for identity-bearing steps, and we say so on stage.

---

## 6. The idea

> She phones in. She says what she wants in her own words. The agent figures out what has to be done, does it on the internet, and tells her the result out loud.

### 6.1 What the agent actually is

**A voice layer that removes the literacy requirement from the internet.**

- Not a tutor, not an information source, not a form-filler for one portal.
- A general executor: **goal in, task done, result spoken back.**
- She never sees a screen, never reads, never chooses from a menu, never types.

### 6.2 What "general" has to mean in practice

General is not a slogan. It has a testable definition:

| Capability | Required? |
|---|---|
| Find anything on the open web from a dialect query | Yes — search |
| Read a page she would otherwise have to read herself | Yes — extract and summarise |
| Work a site never built by us, without hardcoded selectors | Yes — browser control |
| Find and fill a form nobody told us about | Yes — this is the crux |
| Complete a multi-step flow across several sites | Yes |
| Know when it is **not allowed** to finish, and hand off to a human with the work already done | Yes |

**The crux is the fourth row.** If the agent can only fill forms we pre-taught it, we have built a form-filler. It must be able to look at a page it has never seen and work out what to press.

### 6.3 Design rules that hold across every domain

| Rule | Reason |
|---|---|
| One task per interaction, completed fully | Matches the brief's "one essential … resource." Partial completion is failure. |
| Deterministic code for anything auditable — amounts, eligibility, money | A model hallucinating a rupee amount is catastrophic for a user who has no way to verify it. |
| **No vector database** | Scheme and product *rules* are structured, not semantic. Similarity search over policy text returns confidently wrong answers about money. Rules live in code and get tests. |
| Real web search, scoped and filtered, for *discovery* | Discovery genuinely is a search problem. Search → read top result → answer → re-search if thin. No embeddings, no index, no vector store. |
| Browser control with a deterministic path, not an LLM clicking blindly | A model in the click loop is nondeterministic and fails on stage with no recovery. |
| Ask for **last 4 digits**, never 12, and only as session recall | Confidentiality. See §3.1. |
| Never auto-solve CAPTCHAs or bypass OTP | Not ours to decide, and identity-bearing by design. |

---

## 7. Hard boundaries, stated in advance

We state these plainly. A demo that overclaims is worse than a smaller honest one.

### 7.1 Identity and consent cannot be automated away

Verified against the live PMMVY portal (`pmmvy.wcd.gov.in`), the citizen flow is:

1. Mobile number **seeded with Aadhaar** → OTP
2. Aadhaar verification
3. **Facial Recognition System (FRS)** — mandatory
4. Submit

Three walls, each independently fatal to end-to-end automation:

| Wall | Why |
|---|---|
| **FRS** | A face scan *is* the step. Automating it is biometric fraud, not an engineering problem. |
| **OTP to an Aadhaar-linked phone** | The target user by definition does not have that phone. This is the premise of the whole problem. |
| **UIDAI bot protection** | UIDAI deploys CAPTCHA and passive browser-environment bot detection. Automated submission is also a terms-of-service violation, not merely a technical risk. |

**This generalises, and that is the point.** *Verification of identity and consent is not a UI problem and cannot be one.* Every serious service has at least one such step — OTP, a signature, a biometric, a witness, a payment confirmation.

So the correct architecture is not "the agent does everything." It is:

> **The agent does everything up to the identity wall, then completes the human side with the work already done.**

The human spends 30 seconds confirming what the agent prepared, instead of 20 minutes explaining her situation from scratch. **That is the product**, and it is what makes the approach deployable rather than a demo.

### 7.2 What is real in our demo

| Real | Simulated |
|---|---|
| Voice loop, multilingual, full turn-taking | The target portal itself |
| Web search and result reading | The OTP / face-scan step |
| Browser control on an unseen page | — |
| Deterministic rules and eligibility | — |
| Job orchestration, handoff, state | — |

We say this out loud during the demo. Claiming otherwise is the fastest way to lose the room.

### 7.3 The compliance reality

| Question | Answer |
|---|---|
| Deployable against live `.gov.in` today? | **No**, not past the identity wall. |
| Deployable with government partnership? | **Yes** — that is the actual ask, and the honest one. |
| Are we asking to bypass any check? | **No.** We stop at the wall and hand over a completed record. |

---

## 8. Architecture

```
[Inbound: phone call / missed call → callback / WhatsApp voice note]
                              │
                              ▼
        LAYER 1 ── Telephony, zero-install
        Twilio Media Streams · G.711 µ-law 8 kHz · raw byte relay, no transcoding
                              │
                              ▼
        LAYER 2 ── Speech, multilingual
        Rural-dialect ASR → LLM with tools → Indic TTS
                              │
                              ▼
        LAYER 3 ── The general executor  ← this is the product
        ├─ search_web(query)      real web search, snippet-level, no embeddings
        ├─ open_page(url)         read and distil a page she would have to read
        ├─ control_browser(goal)  drive an unseen page: find, fill, click, submit
        └─ check_rule(...)        deterministic code for anything auditable
                              │
                              ▼
        LAYER 4 ── Off-platform completion
        Identity wall → ASHA / Anganwadi / CSC / family → confirmation
```

**Layers 1 and 2 are plumbing. Layer 3 is the entire product.** Everything hard about this project lives in Layer 3, and none of it is government-specific.

### 8.1 The engineering constraint nobody expects: dead air

Our reference implementation handles tool calls synchronously inside the single loop that reads the model socket. The moment a tool takes longer than a fraction of a second, that loop stops reading — and **the caller hears silence.**

Harmless for a stock lookup. Fatal for opening a page, or a twenty-second form fill.

**Our rule: no tool call ever blocks the audio path.** Tools run as detached tasks; the agent speaks a filler immediately; results arrive when they land, and long work reaches her by a channel other than the live call.

---

## 9. Why each choice, and what we rejected

### 9.1 General executor, not one-portal form-filler

Rejected in §1.1 and §6.1. A narrow tool helps with one thing; the problem statement asks for a capability. **General is also the honest bet** — we cannot enumerate what she'll need.

### 9.2 Voice-only, not text

Text was rejected in §2 and §3.1. No version of this product has a screen as its primary interface.

### 9.3 Missed-call / phone-call entry, not app install

Rejected in §3.2. The phone call is the only interface guaranteed to exist.

### 9.4 Multilingual STT/LLM/TTS, not a general-purpose realtime voice model

General realtime voice models are English-first with no credible Hindi or rural-dialect voice. Since language is the core of the problem (§3.3), this is the moat and the one place we refuse to compromise.

Trade-off: ~1.5 s added latency versus native realtime speech. **Acceptable specifically because the agent is not having a conversation** — it is executing a task. A pause between questions is invisible; an unintelligible voice is fatal.

### 9.5 Real search, not RAG

Rejected in §6.3. Money and eligibility must be auditable and testable — so those are code with tests. Discovery genuinely needs search, so it gets search. An embedding pipeline would add cost, latency, and a large surface for confidently wrong answers about money.

### 9.6 Deterministic browser control first, vision fallback second

General "AI browser agents" put a model in the click loop and fail unrecoverably. We do the reliable thing first — locate fields by label text and placeholder, which is how real sites are actually built, not by hardcoded CSS selectors — and use screenshot-driven control only as fallback for pages with no usable markup. The demo depends only on the deterministic path.

### 9.7 Transcription logging

Our reference implementation logs nothing. A voice product with no transcript cannot be debugged, evaluated, or shown to a judge. Non-optional.

### 9.8 One task, one language, one district — for the demo

Depth that demonstrably works for one real person beats thinness everywhere. The architecture is language- and site-parameterised; the demo is narrow on purpose.

---

## 10. What would make us lose

| Risk | Mitigation |
|---|---|
| Agent's voice slips into English or textbook Hindi | System prompt forbids English vocabulary. Any slip is a demo failure; rehearse it. |
| Agent hallucinates an amount or a condition | Nothing auditable may come from the model. Code or nothing. |
| Agent claims a task succeeded when it failed | Only report success from a real tool return value. Failure is spoken as failure. |
| ASR collapses on real rural audio | Build the demo on **real recorded rural audio**, not studio TTS. This is the claim; it must be evidenced. |
| Human handoff reads as failure | Reframe on stage: the worker is the legally authorised actor, and we turn a 20-minute session into a 30-second confirmation. |
| Judges hear "chatbot for rural women" | The differentiator is not the form fill. It is that a woman with no literacy and no English can complete a task on the internet **alone**. |

---

## 11. Open questions

1. **Which single task for the demo?** A government scheme registration is a strong default — high stakes, clear rules, well documented, and a visible before/after. Other candidates: sending money to family, booking a hospital appointment, checking a crop price.
2. **Do we have real recorded rural-audio samples?** Without them the §3.3 claim is unevidenced.
3. **Which language?** The single biggest architectural fork.
4. **Telephony cost** — toll-free is a real per-minute expense, not free.
5. **Is there an identity path with no Aadhaar?** (e-Shram card is a zero-KYC digital identity worth evaluating.)
