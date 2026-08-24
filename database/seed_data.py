"""
Seeds naplan-portal with reference data plus sample quizzes and questions
for Year 5, across all four NAPLAN domains (Reading, Writing, Language
Conventions, Numeracy) — matching the Stage 1 practice/understand pages.

Usage:
    python seed_data.py
"""

from config import get_connection

YEAR_LEVELS = [(3, "Year 3"), (5, "Year 5"), (7, "Year 7"), (9, "Year 9")]

DOMAINS = [
    ("R", "Reading"),
    ("W", "Writing"),
    ("LC", "Language Conventions"),
    ("N", "Numeracy"),
]

# (domain_code, strand, difficulty, prompt, a, b, c, d, correct, explanation)
QUESTIONS_Y5 = [
    ("R", "Comprehension", 1,
     "In the passage, why did the fox return to the farmyard at night?",
     "To find food", "To sleep", "To play", "To hide from the farmer",
     "To find food",
     "The passage states the fox was hungry and the hens had been left unlocked."),
    ("R", "Inference", 2,
     "What can you infer about the character's mood from the sentence 'She slammed the door and stomped up the stairs'?",
     "Happy", "Angry", "Tired", "Confused",
     "Angry",
     "Slamming a door and stomping are actions that show frustration or anger."),
    ("LC", "Grammar", 1,
     "Choose the correct sentence.",
     "Him and me went to the park.", "He and I went to the park.",
     "Me and him went to the park.", "I and he went to the park.",
     "He and I went to the park.",
     "Subject pronouns 'he' and 'I' are correct when used as the subject of a sentence."),
    ("LC", "Spelling", 1,
     "Which word is spelled correctly?",
     "Recieve", "Receive", "Receve", "Receeve",
     "Receive",
     "Remember the rule: 'i before e except after c' — receive follows the 'after c' exception."),
    ("N", "Number", 1,
     "What is 3/4 + 1/8?",
     "4/12", "7/8", "1/2", "5/8",
     "7/8",
     "Convert 3/4 to 6/8, then add 1/8 to get 7/8."),
    ("N", "Geometry", 2,
     "How many degrees are in the angles of a triangle in total?",
     "90", "180", "270", "360",
     "180",
     "The interior angles of any triangle always sum to 180 degrees."),
    ("N", "Statistics", 2,
     "The mean of 4, 8, 6, and 10 is:",
     "6", "7", "8", "9",
     "7",
     "(4+8+6+10) / 4 = 28 / 4 = 7."),
    ("W", "Persuasive", 1,
     "Write a short paragraph persuading your school to add a new sport. (open response)",
     None, None, None, None,
     "Open response — scored by rubric",
     "Writing tasks are scored on structure, ideas, language and grammar, not a single correct answer."),
]


def get_or_create_ref_data(conn):
    cursor = conn.cursor()

    for year_id, label in YEAR_LEVELS:
        cursor.execute(
            "IF NOT EXISTS (SELECT 1 FROM dbo.year_levels WHERE year_level_id = ?) "
            "INSERT INTO dbo.year_levels (year_level_id, label) VALUES (?, ?)",
            year_id, year_id, label,
        )

    for code, name in DOMAINS:
        cursor.execute(
            "IF NOT EXISTS (SELECT 1 FROM dbo.domains WHERE code = ?) "
            "INSERT INTO dbo.domains (code, name) VALUES (?, ?)",
            code, code, name,
        )

    conn.commit()

    cursor.execute("SELECT domain_id, code FROM dbo.domains")
    domain_map = {code: domain_id for domain_id, code in cursor.fetchall()}
    return domain_map


def seed_questions(conn, domain_map, year_level_id=5):
    cursor = conn.cursor()
    inserted_ids = {}  # domain_code -> list of question_id

    for (code, strand, diff, prompt, a, b, c, d, correct, explanation) in QUESTIONS_Y5:
        domain_id = domain_map[code]
        cursor.execute(
            """
            INSERT INTO dbo.questions
                (year_level_id, domain_id, strand, difficulty, question_type,
                 prompt, option_a, option_b, option_c, option_d,
                 correct_answer, explanation, status)
            OUTPUT INSERTED.question_id
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'published')
            """,
            year_level_id, domain_id, strand, diff,
            "short_answer" if a is None else "multiple_choice",
            prompt, a, b, c, d, correct, explanation,
        )
        qid = cursor.fetchone()[0]
        inserted_ids.setdefault(code, []).append(qid)

    conn.commit()
    return inserted_ids


def seed_tests(conn, domain_map, question_ids, year_level_id=5):
    cursor = conn.cursor()

    # One practice test per domain
    domain_titles = {
        "R": "Reading practice — set 1",
        "W": "Writing prompt — persuasive",
        "LC": "Language conventions — set 1",
        "N": "Numeracy practice — set 1",
    }

    for code, title in domain_titles.items():
        if code not in question_ids:
            continue
        cursor.execute(
            """
            INSERT INTO dbo.tests (year_level_id, domain_id, title, test_type, time_limit_mins, status)
            OUTPUT INSERTED.test_id
            VALUES (?, ?, ?, 'practice', ?, 'published')
            """,
            year_level_id, domain_map[code], title, 20,
        )
        test_id = cursor.fetchone()[0]
        for seq, qid in enumerate(question_ids[code], start=1):
            cursor.execute(
                "INSERT INTO dbo.test_questions (test_id, question_id, sequence_no) VALUES (?, ?, ?)",
                test_id, qid, seq,
            )

    # One mixed-domain diagnostic ("Check my level")
    cursor.execute(
        """
        INSERT INTO dbo.tests (year_level_id, domain_id, title, test_type, time_limit_mins, status)
        OUTPUT INSERTED.test_id
        VALUES (?, NULL, ?, 'diagnostic', ?, 'published')
        """,
        year_level_id, "Year 5 level check", 20,
    )
    diag_test_id = cursor.fetchone()[0]
    seq = 1
    for code_ids in question_ids.values():
        for qid in code_ids:
            cursor.execute(
                "INSERT INTO dbo.test_questions (test_id, question_id, sequence_no) VALUES (?, ?, ?)",
                diag_test_id, qid, seq,
            )
            seq += 1

    conn.commit()


def main():
    conn = get_connection()
    domain_map = get_or_create_ref_data(conn)
    question_ids = seed_questions(conn, domain_map, year_level_id=5)
    seed_tests(conn, domain_map, question_ids, year_level_id=5)
    conn.close()
    total_questions = sum(len(v) for v in question_ids.values())
    print(f"Seeded {total_questions} questions and {len(question_ids) + 1} tests (including 1 diagnostic).")


if __name__ == "__main__":
    main()
