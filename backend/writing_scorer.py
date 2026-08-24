"""
Rule-based writing assessment for NAPLAN-style open-response tasks.

There's no LLM API wired into this app (that would need an API key, network
calls, and per-submission cost), so this scores writing the way a rubric
checklist would: length against a year-level target, sentence/paragraph
structure, vocabulary variety, sentence mechanics, and spelling — each
worth a slice of 100 points. Deterministic, explainable, and free to run.
"""

import re

from spellchecker import SpellChecker

_spell = SpellChecker()

# (min_words, target_words) — full length marks at target_words, prorated below it.
LENGTH_TARGETS = {
    3: (40, 100),
    5: (80, 180),
    7: (120, 260),
    9: (150, 320),
}

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_WORD_RE = re.compile(r"[A-Za-z']+")


def _split_sentences(text):
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text.strip()) if s.strip()]


def _words(text):
    return _WORD_RE.findall(text)


def score_writing(text, year_level_id):
    text = (text or "").strip()
    if not text:
        return {
            "score_percent": 0,
            "criteria": [],
            "comments": ["No response was submitted for this writing task."],
        }

    words = _words(text)
    word_count = len(words)
    sentences = _split_sentences(text)
    sentence_count = len(sentences)
    min_words, target_words = LENGTH_TARGETS.get(year_level_id, (80, 180))

    criteria = []
    comments = []

    # --- Length (25 pts) ---------------------------------------------
    length_score = round(min(25, 25 * word_count / target_words), 1)
    criteria.append({"name": "Length", "score": length_score, "max": 25})
    if word_count < min_words:
        comments.append(f"This response is quite short ({word_count} words) — aim for at least {min_words} to develop your ideas fully.")
    elif word_count >= target_words:
        comments.append(f"Good length ({word_count} words) — enough room to develop your ideas.")

    # --- Structure: sentence count as a proxy (20 pts) ----------------
    structure_score = round(min(20, 20 * sentence_count / 5), 1)
    criteria.append({"name": "Structure", "score": structure_score, "max": 20})
    if sentence_count < 3:
        comments.append("Try breaking your writing into more sentences — this reads as one long block of text.")

    # --- Vocabulary variety: type-token ratio (20 pts) -----------------
    if word_count > 0:
        unique_ratio = len(set(w.lower() for w in words)) / word_count
    else:
        unique_ratio = 0
    vocab_score = round(min(20, unique_ratio * 40), 1)
    criteria.append({"name": "Vocabulary", "score": vocab_score, "max": 20})
    if unique_ratio < 0.5 and word_count > 15:
        comments.append("Try varying your word choice — several words are repeated often.")

    # --- Sentence mechanics: capital start + terminal punctuation (15 pts) ---
    well_formed = sum(
        1 for s in sentences
        if s and s[0].isupper() and s[-1] in ".!?"
    )
    mechanics_score = round(15 * (well_formed / sentence_count), 1) if sentence_count else 0
    criteria.append({"name": "Sentence mechanics", "score": mechanics_score, "max": 15})
    if sentence_count and well_formed / sentence_count < 0.7:
        comments.append("Check that every sentence starts with a capital letter and ends with a full stop, question mark or exclamation mark.")

    # --- Spelling (20 pts) ---------------------------------------------
    checkable = [w.lower() for w in words if not w[0].isupper()]  # skip likely proper nouns
    if checkable:
        misspelled = _spell.unknown(checkable)
        spelling_accuracy = 1 - (len(misspelled) / len(checkable))
    else:
        misspelled = set()
        spelling_accuracy = 1
    spelling_score = round(20 * spelling_accuracy, 1)
    criteria.append({"name": "Spelling", "score": spelling_score, "max": 20})
    if misspelled:
        sample = ", ".join(list(misspelled)[:5])
        comments.append(f"Possible spelling to double-check: {sample}.")

    total = round(sum(c["score"] for c in criteria), 1)

    if total >= 80:
        comments.insert(0, "Strong piece of writing overall — clear, well-formed and easy to follow.")
    elif total >= 50:
        comments.insert(0, "A solid attempt with room to grow — see the notes below.")
    else:
        comments.insert(0, "This one needs more work — use the notes below as a checklist for next time.")

    return {"score_percent": total, "criteria": criteria, "comments": comments}
