# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Static HTML/CSS/JS in a single self-contained `.html` file (user-confirmed). No npm, no build step, no framework, no server. Chosen so a hackathon judge can open it offline or deploy it to GitHub Pages unchanged. The surrounding repo is Python: a Flask mock PMMVY portal under `mock_portal/` and a vendored Twilio + OpenAI realtime voice app under `vendor/`.

## Users

**Primary:** a rural Indian woman, often a first-generation phone user, with little or no text literacy and little or no prior internet use. Many still hold a feature/button phone (Nokia-style); those who own smartphones typically cannot operate one without being shown how by someone else — often a male family member. She may be dialling from a shared or borrowed handset, in noise, outdoors, in her own dialect.

She is not trying to learn the internet. She is trying to get one thing done: register for a pension scheme, check a crop price, find a hospital, send money, find a skills course.

**Secondary audiences:** hackathon judges and evaluators, who assess whether the mechanism is real and whether the team knows its own limits.

## Product Purpose

A voice agent reachable by dialling a short, government-style number (the 112/100/108 emergency-number muscle memory). She says what she wants in her own words; the agent works out what to do, does it on the internet, and tells her the outcome out loud. Success is a completed task on a phone she can already operate — not an explanation of how she might have completed it herself.

The product exists because **every existing digital service assumes the user can read**, and that assumption fails in five ways at once for this user.

## Positioning

**The agent executes; it does not narrate.** Not a summary, not a link, not a chatbot that describes where to click — it actually finds the form, fills it, and hands her a completed record.

Two claims a neighbouring product could not truthfully copy:

1. **Zero-install by construction.** There is no app and no login, not as a positioning choice but because a browser must be opened and an account must be created otherwise — and that is exactly the barrier she cannot cross. The agent drives **private browser instances server-side which are destroyed when the call hangs up**, so nothing sensitive ever lands on a shared screen and no session data persists anywhere.
2. **Not hardcoded to one task.** It reaches the live web through tool calls and interacts with real sites through those private browser instances, so it can handle a form nobody pre-taught it. Hardcoded selectors would make it a form-filler; the differentiator is general task execution.

## Operating Context

- **Entry ritual:** dial a short number. Green handset = answer, red = hang up. This is the entire interface the user already trusts.
- **Call flow:** she speaks in a rural dialect, outdoors, with background noise.
- **Server side:** real web search for discovery; deterministic browser control with vision as fallback; money and eligibility logic implemented as tested deterministic code, never delegated to the language model.
- **Privacy model:** ephemeral private browser instances, destroyed on hangup. No vector database. No data at rest.
- **The wall:** live `.gov.in` portals end in an identity check — FRS face scan, OTP to an Aadhaar-linked phone, or bot protection. The agent goes as far as the wall and hands a human clerk a **completed record**, converting the toll from explanation-time into confirmation-time. It does not defeat the wall, and never auto-solves CAPTCHAs or OTP.
- **Deployment reality:** not deployable against live `.gov.in` past the identity wall today. The path is a government or agency partnership.

## Capabilities and Constraints

- Voice in, voice out. The screen is optional and never required.
- **Sarvam.ai** models: multilingual across **22+ Indian languages**, with all inference hosted **in Indian servers** — data sovereignty is a product capability, not a compliance footnote.
- Works on feature/button phones and low-end smartphones, not only modern handsets.
- Speech recognition tuned for rural speech and dialect is the technical moat.
- Zero installs, zero logins, nothing stored on the device.
- Undecided by the user: the exact demonstration task(s) and which languages are shown on the landing page. Treat both as open; the page must not assert a single narrow task or a single language.

## Brand Commitments

Name: **The Invisible Woman**. Positioning line: **UPI for Voice.** The idea is that she already knows how to use a phone; she simply cannot read.

The user made these binding: the target user has the *least* digital knowledge in the room; any minimal UI still requires opening Chrome or installing and logging into an app, which is the same barrier in disguise; the button-phone user is the real target, so "no app, no login, no data" is a strength rather than a limitation. The identity wall is framed as a strength and a reason to remove the toll, never as a failure or an excuse.

Honesty is a brand commitment: no invented testimonials, customers, benchmarks, or deployment claims. Simulated components must be labelled as simulated. Overclaiming past the identity wall is a defect, not a sales tactic.

## Evidence on Hand

- `mock_portal/` — a working Python mock of the PMMVY portal (`static/index.html` voice-clerk UI, `static/portal.html` fake government portal).
- `vendor/` — vendored Twilio + OpenAI realtime voice application.
- `docs/problem-and-approach.md` — the source-of-truth brief, including a real-vs-simulated component table and a rejected-alternatives table.
- Anchor statistic from the brief: **48% of rural girls have never used the internet**, most of those who have were guided by a male family member.

**Absent and must not be fabricated:** real user testimonials, pilot deployments, live `.gov.in` integrations, uptime or accuracy benchmarks, named government partners, pricing.

## Product Principles

1. **One button, not one screen.** The interface is a handset. If a task needs a screen to complete, it has not been solved.
2. **Do the work, not the explaining.** The agent executes. A 500-word summary of how to register is a failure; a completed registration is success.
3. **Assume nothing about the reader.** No text literacy, no visual UI comprehension, no formal-language register, no device ownership, no digital identity.
4. **Remove the toll, not the clerk.** Never replace or bypass a human. Hand them a completed record.
5. **Be honest about the wall.** Stating the identity limit plainly buys more credibility than hiding it.

## Accessibility & Inclusion

The product itself is the primary accessibility mechanism: it removes reading, navigation, and typing from the task entirely. For the landing page, high legibility and generous type are therefore thematically honest rather than merely compliant — the page should be readable by the same people the product serves. Minimum 4.5:1 body contrast, visible focus states, full keyboard operation, `prefers-reduced-motion` respected, 44px minimum targets.
