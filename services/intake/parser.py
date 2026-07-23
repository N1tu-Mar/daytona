"""Deterministic answer parsing for the fixed-order intake script.

Because every question is closed-form (yes/no, a number, or one of a few
named choices — never open-ended), parsing the ASR transcript of an answer
doesn't need an LLM at all. That keeps the whole call path auditable and
fast, and it means "low confidence" has a precise meaning: the parser
couldn't map the words to one of the expected answers, full stop.
"""

from __future__ import annotations

import re

YES_WORDS = {"yes", "yeah", "yep", "yup", "correct", "affirmative", "definitely"}
NO_WORDS = {"no", "nope", "nah", "negative", "not really", "never", "haven't", "hasn't", "don't"}
NOT_DONE_PHRASES = {"haven't had", "never had", "not done", "no test", "don't know", "haven't done"}
# Genuinely ambiguous — must not be forced into either bucket.
AMBIGUOUS_PHRASES = {"not sure", "maybe", "i don't know", "unsure", "not certain"}

_NUMBER_RE = re.compile(r"-?\d+")


def _contains_word(text: str, word: str) -> bool:
    if " " in word or "'" in word:
        return word in text
    return re.search(rf"\b{re.escape(word)}\b", text) is not None

_WORD_NUMBERS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90,
}


def parse_yes_no(text: str) -> bool | None:
    t = text.strip().lower()
    if any(phrase in t for phrase in AMBIGUOUS_PHRASES):
        return None
    if any(_contains_word(t, w) for w in NO_WORDS):
        return False
    if any(_contains_word(t, w) for w in YES_WORDS):
        return True
    return None


def parse_number(text: str) -> int | None:
    t = text.strip().lower()
    m = _NUMBER_RE.search(t)
    if m:
        return int(m.group())
    for word, value in _WORD_NUMBERS.items():
        if word in t:
            return value
    return None


def parse_choice(text: str, choices: tuple[str, ...]) -> str | None:
    t = text.strip().lower()
    for choice in choices:
        if choice == "not_done":
            continue  # matched below via NOT_DONE_PHRASES/NO_WORDS, not literal text
        if choice.replace("_", " ") in t or _contains_word(t, choice):
            return choice
    if "not_done" in choices and (
        any(phrase in t for phrase in NOT_DONE_PHRASES) or any(_contains_word(t, w) for w in NO_WORDS)
    ):
        return "not_done"
    return None
