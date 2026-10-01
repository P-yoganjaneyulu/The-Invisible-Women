from datetime import date

from clerk.eligibility import Applicant, evaluate, parse_date, parse_int


def ok(**kw) -> Applicant:
    base = dict(
        name="Sunita",
        age=24,
        mobile="9876543210",
        lmp=date.today() - __import__("datetime").timedelta(days=40),
        bank_ifsc="SBIN0001234",
        aadhaar_last4="4829",
        children=0,
        district="Karnool",
    )
    base.update(kw)
    return Applicant(**base)


def test_first_child_is_eligible_for_5000():
    v = evaluate(ok())
    assert v.eligible and v.benefit == 5000, v


def test_girl_second_child_gets_6000():
    v = evaluate(ok(children=1, girl_child=True))
    assert v.eligible and v.benefit == 6000, v


def test_boy_second_child_is_not_eligible():
    v = evaluate(ok(children=1, girl_child=False))
    assert not v.eligible and v.benefit == 0, v


def test_under_19_rejected():
    v = evaluate(ok(age=17))
    assert not v.eligible and "19" in v.reason, v


def test_past_150_day_window_rejected():
    v = evaluate(ok(lmp=date.today() - __import__("datetime").timedelta(days=200)))
    assert not v.eligible and "150" in v.reason, v


def test_govt_employee_rejected():
    assert not evaluate(ok(is_govt_employee=True)).eligible


def test_missing_fields_block_rather_than_guess():
    v = evaluate(ok(lmp=None, bank_ifsc=""))
    assert not v.eligible
    assert "lmp" in v.reason and "bank_ifsc" in v.reason, v


def test_bad_aadhaar_rejected():
    assert not evaluate(ok(aadhaar_last4="48")).eligible


def test_parse_handles_devanagari_and_spoken_dates():
    assert parse_int("३२ साल") == 32
    assert parse_int("twenty four") == 24
    assert parse_date("05/03/2026") == date(2026, 3, 5)


if __name__ == "__main__":
    for fn in [v for k, v in sorted(globals().items()) if k.startswith("test_")]:
        fn()
        print("ok", fn.__name__)
    print("all rules checks passed")
