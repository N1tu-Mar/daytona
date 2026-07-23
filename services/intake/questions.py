"""Fixed-order red-flag question script for the voice intake line.

CLAUDE.md: "Structured question flow, not open-ended chat... Asks the
red-flag questions in a fixed order, with follow-ups for duration." This is
the script. It's deliberately a plain data structure, not a prompt, so the
call flow is auditable the same way the rule engine is.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Question:
    field: str
    prompt: str
    kind: str  # "yes_no" | "number" | "choice"
    choices: tuple[str, ...] = ()
    # if this yes/no question is True, ask this follow-up field next
    duration_follow_up: str | None = None


QUESTION_SCRIPT: list[Question] = [
    Question(field="age", prompt="Can you tell me your age?", kind="number"),
    Question(
        field="rectal_bleeding",
        prompt="Have you noticed any rectal bleeding?",
        kind="yes_no",
        duration_follow_up="bleeding_duration_weeks",
    ),
    Question(
        field="bleeding_duration_weeks",
        prompt="About how many weeks has that been going on?",
        kind="number",
    ),
    Question(
        field="change_in_bowel_habit",
        prompt="Have you had any change in your bowel habits, like new diarrhea or constipation?",
        kind="yes_no",
        duration_follow_up="bowel_habit_duration_weeks",
    ),
    Question(
        field="bowel_habit_duration_weeks",
        prompt="About how many weeks has that been going on?",
        kind="number",
    ),
    Question(
        field="unintentional_weight_loss",
        prompt="Have you lost weight recently without trying to?",
        kind="yes_no",
    ),
    Question(
        field="abdominal_pain",
        prompt="Have you had any abdominal pain?",
        kind="yes_no",
    ),
    Question(
        field="iron_deficiency_anemia",
        prompt="Has a doctor told you that you have iron deficiency anemia, or low iron?",
        kind="yes_no",
    ),
    Question(
        field="fit_result",
        prompt="Have you had a FIT or fecal occult blood test, and if so was it positive or negative?",
        kind="choice",
        choices=("positive", "negative", "not_done"),
    ),
    Question(
        field="family_history_crc",
        prompt="Does anyone in your immediate family have a history of colorectal cancer?",
        kind="choice",
        choices=("none", "first_degree", "multiple"),
    ),
    Question(
        field="abdominal_or_rectal_mass",
        prompt="Has a doctor ever felt a lump or mass in your abdomen or during a rectal exam?",
        kind="yes_no",
    ),
]

# Fields that only get asked as a follow-up, never as a top-level script step.
FOLLOW_UP_FIELDS = {q.duration_follow_up for q in QUESTION_SCRIPT if q.duration_follow_up}


def ordered_top_level_questions() -> list[Question]:
    return [q for q in QUESTION_SCRIPT if q.field not in FOLLOW_UP_FIELDS]
