"""
Tops up every existing (content_year, year_level) bucket with a batch of
NEW, originally-authored Numeracy question patterns covering skill areas
that were under-represented in the original bulk bank: bar-graph reading,
metric length conversion, money change, divisibility, dividing by powers
of ten, time duration, integer arithmetic, coordinate translations,
experimental probability, similar-figure area scaling, exponent laws, and
polynomial perimeter expressions.

All prompts/answers are computed programmatically here (not sourced from
any third-party question bank). Diagrams are attached directly at insert
time (rather than via the regex backfill) since we already know exactly
which item needs which image.

Idempotent: skips a (content_year, year_level) bucket if it already has a
"topic variety" test for that bucket.

Usage:
    python add_numeracy_topic_variety.py
"""

import os
import random

from config import get_connection
from generate_bulk_bank import (
    EDITION_YEARS, YEAR_LEVELS, get_domain_map,
    n_bar_graph_read, n_length_convert, n_money_change,
    n_divisibility, n_divide_pow10, n_time_duration,
    n_integer_ops, n_coordinate_translation, n_experimental_probability,
    n_similar_figures, n_exponent_laws, n_polynomial_perimeter,
)

IMAGES_DIR = os.path.join(os.path.dirname(__file__), "..", "stage1-initial-design-craft", "images", "questions")
MEDIA_URL_PREFIX = "/images/questions"
os.makedirs(IMAGES_DIR, exist_ok=True)

TOPIC_PATTERNS = {
    3: [n_bar_graph_read, n_length_convert, n_money_change],
    5: [n_divisibility, n_divide_pow10, n_time_duration],
    7: [n_integer_ops, n_coordinate_translation, n_experimental_probability],
    9: [n_similar_figures, n_exponent_laws, n_polynomial_perimeter],
}

TARGET_PER_BUCKET = 30
TEST_TITLE_MARKER = "topic variety"


def generate_items(rng, patterns, target_n):
    seen = set()
    results = []
    i = 0
    attempts = 0
    max_attempts = target_n * 60
    while len(results) < target_n and attempts < max_attempts:
        func = patterns[i % len(patterns)]
        item = func(rng)
        attempts += 1
        i += 1
        key = (item["prompt"], item["correct"])
        if key in seen:
            continue
        seen.add(key)
        results.append(item)
    return results


def bucket_already_done(conn, year_level, content_year):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM dbo.tests WHERE year_level_id = ? AND content_year = ? AND title LIKE ?",
        year_level, content_year, f"%{TEST_TITLE_MARKER}%",
    )
    return cursor.fetchone()[0] > 0


def insert_items(conn, domain_map, year_level, content_year, items):
    cursor = conn.cursor()
    question_ids = []
    for item in items:
        media_url = None
        svg_content = item.get("_svg")
        opts = item["options"] or [None, None, None, None]
        while len(opts) < 4:
            opts.append(None)

        cursor.execute(
            """
            INSERT INTO dbo.questions
                (year_level_id, domain_id, strand, difficulty, question_type,
                 prompt, option_a, option_b, option_c, option_d,
                 correct_answer, explanation, status, content_year)
            OUTPUT INSERTED.question_id
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'published', ?)
            """,
            year_level, domain_map["N"], item["strand"], item["difficulty"],
            item["question_type"], item["prompt"], opts[0], opts[1], opts[2], opts[3],
            item["correct"], item["explanation"], content_year,
        )
        question_id = cursor.fetchone()[0]

        if svg_content:
            filename = f"q{question_id}.svg"
            with open(os.path.join(IMAGES_DIR, filename), "w", encoding="utf-8") as f:
                f.write(svg_content)
            media_url = f"{MEDIA_URL_PREFIX}/{filename}"
            cursor.execute("UPDATE dbo.questions SET media_url = ? WHERE question_id = ?", media_url, question_id)

        question_ids.append(question_id)

    conn.commit()
    return question_ids


def create_topic_variety_test(conn, domain_map, year_level, content_year, question_ids):
    cursor = conn.cursor()
    title = f"Numeracy practice {content_year} - {TEST_TITLE_MARKER}"
    cursor.execute(
        """
        INSERT INTO dbo.tests (year_level_id, domain_id, title, test_type, time_limit_mins, status, content_year)
        OUTPUT INSERTED.test_id
        VALUES (?, ?, ?, 'practice', ?, 'published', ?)
        """,
        year_level, domain_map["N"], title, 20, content_year,
    )
    test_id = cursor.fetchone()[0]
    for seq, qid in enumerate(question_ids, start=1):
        cursor.execute(
            "INSERT INTO dbo.test_questions (test_id, question_id, sequence_no) VALUES (?, ?, ?)",
            test_id, qid, seq,
        )
    conn.commit()


def main():
    conn = get_connection()
    domain_map = get_domain_map(conn)

    total_q = 0
    total_img = 0

    for content_year in EDITION_YEARS:
        for level in YEAR_LEVELS:
            if bucket_already_done(conn, level, content_year):
                print(f"Edition {content_year}, Year {level}: topic variety already present - skipping.")
                continue

            rng = random.Random(f"{content_year}-{level}-topicvariety")
            patterns = TOPIC_PATTERNS[level]
            items = generate_items(rng, patterns, TARGET_PER_BUCKET)
            qids = insert_items(conn, domain_map, level, content_year, items)
            create_topic_variety_test(conn, domain_map, level, content_year, qids)

            n_images = sum(1 for item in items if item.get("_svg"))
            total_q += len(items)
            total_img += n_images
            print(f"Edition {content_year}, Year {level}: added {len(items)} questions ({n_images} with diagrams).")

    conn.close()
    print(f"Done. Total new questions: {total_q}, total with diagrams: {total_img}.")


if __name__ == "__main__":
    main()
