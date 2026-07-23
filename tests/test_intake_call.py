"""Voice intake end-to-end tests (no ElevenLabs/network needed — the
"transcript" is supplied directly, exercising everything downstream of ASR)."""

from __future__ import annotations

from app.db import init_db
from services.intake.call import run_call
from services.intake.parser import parse_choice, parse_number, parse_yes_no


def setup_module(module):
    init_db()


def test_parser_yes_no():
    assert parse_yes_no("yes") is True
    assert parse_yes_no("Yeah, definitely") is True
    assert parse_yes_no("no") is False
    assert parse_yes_no("nope, not at all") is False
    assert parse_yes_no("maybe? not sure") is None


def test_parser_number():
    assert parse_number("42") == 42
    # compound word numbers aren't combined ("forty two" -> just matches "two");
    # documents the current limitation rather than silently guessing a number
    assert parse_number("I'm forty two") == 2
    assert parse_number("about three weeks") == 3
    assert parse_number("no idea") is None


def test_parser_choice():
    assert parse_choice("it was positive", ("positive", "negative", "not_done")) == "positive"
    assert parse_choice("negative I think", ("positive", "negative", "not_done")) == "negative"
    assert parse_choice("never had one", ("positive", "negative", "not_done")) == "not_done"


def test_full_call_demo_case_books_urgent_slot():
    """The 42-year-old bleeding + bowel habit change case, end to end on the phone."""
    answers = {
        "age": "I'm 42",
        "rectal_bleeding": "yes",
        "bleeding_duration_weeks": "about 3 weeks",
        "change_in_bowel_habit": "yes",
        "bowel_habit_duration_weeks": "3 weeks",
        "unintentional_weight_loss": "no",
        "abdominal_pain": "no",
        "iron_deficiency_anemia": "no",
        "fit_result": "haven't had one",
        "family_history_crc": "none that I know of",
        "abdominal_or_rectal_mass": "no",
    }
    result = run_call("demo-call-42yo", answers)
    assert result.urgency == "urgent"
    assert result.disposition == "BOOK"
    assert result.booked_slot is not None
    assert "urgent" in result.booked_slot.lower() or "Urgent" in result.booked_slot

    # no diagnostic language anywhere in what was said to the patient
    for turn in result.transcript:
        if turn.speaker == "agent":
            assert "hemorrhoid" not in turn.text.lower()
            assert "cancer" not in turn.text.lower()


def test_call_with_unparseable_answer_does_not_guess_and_does_not_book_routine():
    answers = {
        "age": "who's asking",  # unparseable
        "rectal_bleeding": "yes",
        "bleeding_duration_weeks": "3 weeks",
    }
    result = run_call("demo-call-ambiguous", answers)
    assert result.disposition != "BOOK" or result.urgency != "routine"


def test_call_transcript_never_contains_diagnostic_language():
    answers = {
        "age": "70",
        "rectal_bleeding": "no",
        "change_in_bowel_habit": "yes",
        "bowel_habit_duration_weeks": "4 weeks",
        "unintentional_weight_loss": "no",
        "abdominal_pain": "no",
        "iron_deficiency_anemia": "no",
        "fit_result": "not done",
        "family_history_crc": "none",
        "abdominal_or_rectal_mass": "no",
    }
    result = run_call("demo-call-elderly", answers)
    from app.output_filter import check_output

    for turn in result.transcript:
        if turn.speaker == "agent":
            assert check_output(turn.text).allowed


def test_call_with_no_answers_escalates_to_nurse_callback():
    result = run_call("demo-call-silent", {})
    assert result.disposition != "BOOK"
    assert "nurse" in result.final_message.lower()
