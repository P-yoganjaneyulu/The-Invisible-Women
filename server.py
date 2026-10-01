"""Virtual Government Clerk - voice agent that does the task for her.

Pipeline:
    browser mic (any language)
      -> LLM (multilingual, tool-calling)
        -> clerk.search   find it
        -> clerk.browser  read it, fill it, press it
        -> clerk.eligibility  the only source of truth for money
      -> browser TTS reply

The LLM never decides eligibility and never invents a reference number. It only
asks questions and calls tools. All money/scheme facts live in clerk/eligibility.py.
"""
from __future__ import annotations

import asyncio
import json
import os
import pathlib

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from openai import AsyncOpenAI
from pydantic import BaseModel

from clerk import tools

load_dotenv()

HERE = pathlib.Path(__file__).parent
PORT = int(os.getenv("PORT", "8000"))

app = FastAPI(title="Virtual Government Clerk")
sessions: dict[str, dict] = {}

client: AsyncOpenAI | None = None
MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")


def _llm() -> AsyncOpenAI:
    """Built on first use, not at import.

    Importing this module must never fail - the test harness and the demo portal
    both import it without an API key, and /api/turn already reports a missing
    key as a friendly 500.
    """
    global client
    if client is None:
        client = AsyncOpenAI(
            api_key=os.getenv("LLM_API_KEY", ""),
            base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        )
    return client


SYSTEM = """You are a clerk on the phone with a rural woman in India. You do the work for her.

You are NOT a tutor. You do not give information she could have read, because she
cannot read. You DO the task.

HOW YOU TALK:
- Speak her language, her dialect. Not textbook Hindi.
- 8 to 12 words per turn. Then stop and let her answer.
- Say numbers as words: "unbees", "pachas", "solah". Dates as "pehli february".
- Never read digits out as a string. "4829" is "chaar aath saat nau".
- No English words at all. No "eligible", no "portal", no "ID", no "OTP".
  Say "aapka haq", "sarkar ki website", "naam likh diya".
- Warm but fast. She has limited signal and limited time.

HOW YOU ACT:
- Ask ONE question per turn. Then stop.
- Tools take time, especially filling a form. You will get a turn containing
  "(results are ready)" and tool outputs from work you already asked for. On
  that turn, do not ask anything new. Read the result out to her in plain
  words, then stop.
- To do anything on the internet: search_web to find it, open_page to read it,
  fill_form to write her answers into it, click_button to press the button,
  read_result to read the confirmation off the page.
- Address form fields by the words PRINTED on the page, never by guessing ids.
- After every fill_form, look at `missing` and `errors`. If anything is missing,
  tell her plainly which detail you could not place and ask her again.
- Use check_eligibility for anything about money. It is the only source of truth.
  Never state an amount it did not return.
- Only report success from a tool result. If a tool errored, tell her it did not
  go through and what happens next. Never say a form was submitted unless
  click_button returned ok.
- Read a registration number slowly, digit by digit, spelled out.

AADHAAR:
- Before the last 4 digits, say plainly: "aapka aadhaar number kisi ko mat
  dikhana, sirf aakhri chaar". Ask only if she is willing.

IF YOU DON'T KNOW:
Say "mujhe nahi pata, main check karke batata hoon", then use search_web. Never
invent a rule, an amount, a date, or a document list.

FIRST TURN:
Greet her in her language, say you will help her get the maternity benefit,
and ask her name. Nothing else.
"""


class Turn(BaseModel):
    session: str
    text: str


WORKING = "Theek hai, main yeh kar rahi hoon. Thodi der."


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(HERE / "index.html")


@app.get("/portal/")
async def demo_portal() -> FileResponse:
    return FileResponse(HERE / "demo_portal.html")


@app.post("/api/turn")
async def turn(req: Turn) -> JSONResponse:
    if not os.getenv("LLM_API_KEY"):
        return JSONResponse(
            {"error": "LLM_API_KEY missing. Copy .env.example to .env and set it."},
            status_code=500,
        )

    s = sessions.setdefault(req.session, {"history": [], "applicant": {}, "pending": []})

    # Tools finished while she was on the previous turn land here. They go into
    # history right after the assistant message that asked for them, which is the
    # only ordering the API accepts, and before her new message.
    for item in s["pending"]:
        if item["name"] == "check_eligibility" and isinstance(item["result"], dict):
            if item["result"].get("applicant"):
                s["applicant"] = {**s["applicant"], **item["result"]["applicant"]}
    if s["pending"]:
        s["history"].extend(
            {
                "role": "tool",
                "tool_call_id": item["call_id"],
                "content": json.dumps(item["result"], ensure_ascii=False),
            }
            for item in s["pending"]
        )
        s["pending"] = []

    s["history"].append({"role": "user", "content": req.text})

    try:
        resp = await _llm().chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": SYSTEM}] + s["history"],
            tools=tools.SCHEMAS,
            temperature=0.3,
        )
    except Exception as e:
        return JSONResponse({"error": f"LLM call failed: {e}"}, status_code=502)

    msg = resp.choices[0].message

    if not msg.tool_calls:
        s["history"].append({"role": "assistant", "content": msg.content or ""})
        return JSONResponse({"reply": msg.content or "", "events": [], "working": False})

    calls = [
        {
            "id": tc.id,
            "type": "function",
            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
        }
        for tc in msg.tool_calls
    ]
    s["history"].append(
        {"role": "assistant", "content": msg.content or "", "tool_calls": calls}
    )

    # Hand the work to the pool and return immediately. A browser fill takes ~20s;
    # if we waited here she would hear nothing and assume it failed.
    events: list[str] = []
    for tc in msg.tool_calls:
        try:
            args = json.loads(tc.function.arguments or "{}")
        except json.JSONDecodeError:
            args = {}
        # She may have given a detail three turns ago. Every call sees the full
        # record, not just this turn's fragment.
        if tc.function.name == "check_eligibility":
            args = {**s["applicant"], **args}

        name = tc.function.name
        events.append(name)
        tools.spawn(name, args, on_done=_collector(s, name, tc.id))

    return JSONResponse({"reply": msg.content or WORKING, "events": events, "working": True})


def _collector(s: dict, name: str, call_id: str):
    def done(_name, result):
        s["pending"].append({"name": name, "call_id": call_id, "result": result})

    return done


@app.get("/api/state/{sid}")
async def state(sid: str) -> JSONResponse:
    s = sessions.get(sid, {"applicant": {}})
    return JSONResponse(
        {"applicant": s["applicant"], "in_flight": [i["name"] for i in s["pending"]]}
    )


@app.on_event("shutdown")
async def _shutdown() -> None:
    await asyncio.to_thread(tools.shutdown)
