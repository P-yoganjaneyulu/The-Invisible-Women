"""PMMVY 2.0 eligibility. Deterministic, no LLM.

Every rule below is traceable to a published scheme condition. If a rule is not
in here, the agent must not claim it.

Source conditions (PMMVY 2.0, WCD):
  - Beneficiary must be pregnant or lactating.
  - Age >= 19.
  - LMP must be within 150 days of registration (registration deadline).
  - Aadhaar is mandatory (Aadhaar Act 2016 s.7, notified).
  - DBT only to an Aadhaar-seeded bank/post office account.
  - First living child: Rs 5000 in two instalments.
  - Second child: Rs 6000, one instalment, only if the child is a girl.
  - Excluded: central/state govt employees, and those already holding a similar
    maternity benefit from another scheme.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime

MAX_LMP_AGE_DAYS = 150
MIN_AGE = 19


@dataclass
class Applicant:
    name: str = ""
    husband: str = ""
    aadhaar_last4: str = ""
    age: int | None = None
    mobile: str = ""
    district: str = ""
    lmp: date | None = None
    bank_ifsc: str = ""
    children: int = 0
    girl_child: bool = False
    is_govt_employee: bool = False
    has_other_maternity_benefit: bool = False

    @property
    def benefit(self) -> int:
        if self.children == 0:
            return 5000
        if self.children == 1 and self.girl_child:
            return 6000
        return 0


@dataclass
class Verdict:
    eligible: bool
    reason: str
    benefit: int = 0

    def voice(self) -> str:
        if self.eligible:
            return f"{self.reason} Aapko {self.benefit} rupaye milenge."
        return self.reason


def _missing(a: Applicant) -> list[str]:
    out = []
    if not a.name.strip():
        out.append("name")
    if a.age is None:
        out.append("age")
    if a.lmp is None:
        out.append("lmp")
    if not a.mobile.strip():
        out.append("mobile")
    if not a.bank_ifsc.strip():
        out.append("bank_ifsc")
    return out


def evaluate(a: Applicant, today: date | None = None) -> Verdict:
    today = today or date.today()

    gaps = _missing(a)
    if gaps:
        return Verdict(False, f"Kuch jaankari abhi baaki hai: {', '.join(gaps)}.")

    if a.is_govt_employee:
        return Verdict(False, "Sarkari karmchariyon ke liye yeh yojana nahi hai.")

    if a.has_other_maternity_benefit:
        return Verdict(False, "Agar doosri yojana se bhi matritva labh mil raha hai, toh yeh nahi milega.")

    if a.age < MIN_AGE:
        return Verdict(False, f"Yeh yojana 19 saal ya usse zyada umar ke liye hai.")

    days = (today - a.lmp).days
    if days < 0:
        return Verdict(False, "LMP ki date aage ki hai, date check karke batayein.")
    if days > MAX_LMP_AGE_DAYS:
        return Verdict(
            False,
            f"Registration ka last din {MAX_LMP_AGE_DAYS} din tha, wo {days} din pehle nikal gaya.",
        )

    if not a.aadhaar_last4.isdigit() or len(a.aadhaar_last4) != 4:
        return Verdict(False, "Aadhaar ke aakhri chaar aankh nahi mile.")

    benefit = a.benefit
    if benefit == 0:
        if a.children == 1:
            return Verdict(False, "Doosre bachche ke liye sirf ladki ho toh hi labh milega.")
        return Verdict(False, "Is yojana mein sirf pehle do bachchon ka labh hai.")

    return Verdict(True, "Aap yojana ke liye yogya hain.", benefit)


def parse_date(s: str) -> date | None:
    """Accepts the shapes a voice transcript produces."""
    s = s.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fourty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}


def parse_int(s: str) -> int | None:
    """Hindi and Devanagari numerals both show up in transcripts, and because the
    agent is told to say numbers as words ("unbees", "twenty four"), so do words.
    """
    if not s:
        return None
    # Devanagari digits -> ASCII, before anything else looks at the string.
    s = str(s).translate(str.maketrans("०१२३४५६७८९", "0123456789"))
    digits = ""
    for ch in s:
        if ch.isdigit():
            digits += ch
        elif digits:
            break
    if digits:
        return int(digits)
    # ponytail: word-sum handles "twenty four" but not "one hundred and twenty".
    # Add a multiplier when a caller actually passes those.
    total, seen = 0, False
    for word in re.split(r"[^a-z]+", s.lower()):
        if word in _WORDS:
            total += _WORDS[word]
            seen = True
    return total if seen else None
