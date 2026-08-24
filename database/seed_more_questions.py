"""
Adds a second practice set (Reading, Language Conventions, Numeracy) for
every year level already seeded (3, 5, 7, 9), so each domain has more than
one practice test to work through. Original questions, matching the
difficulty/format established for each year level in seed_data.py /
seed_more_years.py.

Usage:
    python seed_more_questions.py
"""

from config import get_connection

# (domain_code, strand, difficulty, prompt, a, b, c, d, correct, explanation)
QUESTIONS_BY_YEAR = {
    3: [
        ("R", "Comprehension", 1,
         "The kitten curled up in the warm sunny spot by the window and fell asleep. Where did the kitten fall asleep?",
         "In its bed", "In a sunny spot by the window", "Under the table", "On the porch",
         "In a sunny spot by the window",
         "The sentence directly states the kitten fell asleep in the sunny spot by the window."),
        ("R", "Main idea", 1,
         "Mia forgot her umbrella and got soaked walking home in the rain, so next time she checked the "
         "weather first. Which sentence best describes what the story is about?",
         "Mia learned to check the weather before going out", "Mia enjoyed the rain",
         "Mia bought a new umbrella", "Mia stayed home all day",
         "Mia learned to check the weather before going out",
         "The story shows Mia changing her behaviour after getting caught in the rain."),
        ("LC", "Punctuation", 1,
         "Which sentence uses capital letters correctly?",
         "we went to the Zoo on saturday.", "We went to the zoo on Saturday.",
         "We went to the Zoo on Saturday.", "we Went to the zoo on saturday.",
         "We went to the zoo on Saturday.",
         "Only the first word of the sentence and the day name (Saturday) need capitals."),
        ("LC", "Spelling", 1,
         "Which word is spelled correctly?",
         "Becuase", "Because", "Becaus", "Beacause",
         "Because",
         "Because is a common word worth memorising: be-cause."),
        ("N", "Addition", 1,
         "What is 246 + 137?",
         "373", "383", "383", "393",
         "383",
         "246 + 137 = 383."),
        ("N", "Time", 1,
         "It is 3:15pm. What time will it be in 45 minutes?",
         "3:45pm", "4:00pm", "3:50pm", "4:15pm",
         "4:00pm",
         "45 minutes after 3:15pm is 4:00pm."),
    ],
    5: [
        ("R", "Sequencing", 2,
         "The instructions say: 'Preheat the oven, then bake the muffins for 20 minutes.' What should happen first?",
         "Bake the muffins", "Preheat the oven", "Add the icing", "Cool the muffins",
         "Preheat the oven",
         "The instructions list preheating the oven as the first step."),
        ("R", "Inference", 2,
         "The sky grew dark and the wind picked up speed, rustling the leaves violently. What is most likely about to happen?",
         "A storm", "A sunny afternoon", "A snow day", "A rainbow",
         "A storm",
         "Darkening skies and strong wind are classic signs of an approaching storm."),
        ("LC", "Grammar", 2,
         "Choose the correct sentence.",
         "There going to the park later.", "They're going to the park later.",
         "Their going to the park later.", "There're going to the park later.",
         "They're going to the park later.",
         "'They're' is short for 'they are', which fits the sentence."),
        ("LC", "Spelling", 2,
         "Which word is spelled correctly?",
         "Seperate", "Separate", "Seperete", "Saparate",
         "Separate",
         "Remember: there's 'a rat' in sep-a-rate."),
        ("N", "Multiplication", 2,
         "What is 8 x 7?",
         "48", "54", "56", "64",
         "56",
         "8 x 7 = 56."),
        ("N", "Perimeter", 2,
         "A rectangle has a length of 9 cm and a width of 5 cm. What is its perimeter?",
         "14 cm", "28 cm", "45 cm", "18 cm",
         "28 cm",
         "Perimeter = 2 x (length + width) = 2 x (9 + 5) = 28 cm."),
    ],
    7: [
        ("R", "Evaluating evidence", 2,
         "An advertisement claims: 'Nine out of ten dentists recommend this toothpaste.' What kind of evidence is this?",
         "Anecdotal evidence", "Statistical evidence", "A rhetorical question", "An analogy",
         "Statistical evidence",
         "A proportion like 'nine out of ten' is a statistic used to support the claim."),
        ("R", "Technique", 2,
         "In the story, the narrator says 'I forced a smile, though my stomach was in knots.' What technique is used here?",
         "Simile", "Contrast between action and feeling", "Onomatopoeia", "Alliteration",
         "Contrast between action and feeling",
         "The outward smile contrasts with the inward nervousness, revealing the character's true feelings."),
        ("LC", "Apostrophes", 2,
         "Choose the sentence with the correct use of an apostrophe (several students, all their books).",
         "The students' books were left on the bus.", "The student's books were left on the bus.",
         "The students books were left on the bus.", "The students's books were left on the bus.",
         "The students' books were left on the bus.",
         "For a plural noun ending in s, the possessive apostrophe goes after the s: students'."),
        ("LC", "Spelling", 2,
         "Which word is spelled correctly?",
         "Accomodate", "Acommodate", "Accommodate", "Acomodate",
         "Accommodate",
         "Accommodate has a double c and a double m — a frequently misspelled word."),
        ("N", "Algebra (non-calculator)", 2,
         "Simplify: 4(x + 3) - 2x",
         "2x + 12", "2x + 3", "6x + 12", "2x + 7",
         "2x + 12",
         "4(x + 3) = 4x + 12, then subtract 2x to get 2x + 12."),
        ("N", "Rates (calculator)", 2,
         "A car travels 240 km in 3 hours. What is its average speed in km/h?",
         "60 km/h", "70 km/h", "80 km/h", "90 km/h",
         "80 km/h",
         "Average speed = distance / time = 240 / 3 = 80 km/h."),
    ],
    9: [
        ("R", "Figurative language", 3,
         "The editorial concludes: 'Until governments act decisively, individual efforts will only ever be a "
         "drop in the ocean.' What does 'a drop in the ocean' suggest?",
         "A small, insignificant amount", "A large contribution",
         "An overwhelming success", "A common saying about water",
         "A small, insignificant amount",
         "'A drop in the ocean' is an idiom meaning a tiny, almost negligible amount compared to what's needed."),
        ("R", "Objectivity", 3,
         "Which statement best reflects a balanced, objective report style?",
         "This policy is clearly the worst decision the council has ever made.",
         "The council's new policy has received mixed reactions from residents.",
         "Everyone hates the new policy.", "The policy is obviously going to fail.",
         "The council's new policy has received mixed reactions from residents.",
         "This statement reports differing views without taking a side, unlike the other options."),
        ("LC", "Punctuation", 3,
         "Choose the sentence with correct use of the semicolon.",
         "I have a big test tomorrow; so I need to study.", "I have a big test tomorrow; I need to study.",
         "I have a big test tomorrow, I need to study;", "I have a big test tomorrow: I need to study;",
         "I have a big test tomorrow; I need to study.",
         "A semicolon joins two related independent clauses without a conjunction like 'so'."),
        ("LC", "Spelling", 3,
         "Which word is spelled correctly?",
         "Rythm", "Rhythm", "Rhytmn", "Rhythem",
         "Rhythm",
         "Rhythm is a notoriously tricky word — no vowel sound spelled the way it looks."),
        ("N", "Algebra (non-calculator)", 3,
         "Expand and simplify: (x + 4)(x - 2)",
         "x^2 + 2x - 8", "x^2 - 2x - 8", "x^2 + 6x - 8", "x^2 + 2x + 8",
         "x^2 + 2x - 8",
         "(x + 4)(x - 2) = x^2 - 2x + 4x - 8 = x^2 + 2x - 8."),
        ("N", "Percentages (calculator)", 3,
         "A $120 jacket is discounted by 25%. What is the sale price?",
         "$80", "$90", "$95", "$100",
         "$90",
         "25% of $120 is $30, so the sale price is $120 - $30 = $90."),
    ],
}

SET_TITLES = {
    "R": "Reading practice — set 2",
    "LC": "Language conventions — set 2",
    "N": "Numeracy practice — set 2",
}


def get_domain_map(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT domain_id, code FROM dbo.domains")
    return {code: domain_id for domain_id, code in cursor.fetchall()}


def set_two_already_seeded(conn, year_level_id):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM dbo.tests WHERE year_level_id = ? AND title LIKE '%set 2%'",
        year_level_id,
    )
    return cursor.fetchone()[0] > 0


def seed_questions(conn, domain_map, year_level_id, questions):
    cursor = conn.cursor()
    inserted_ids = {}

    for (code, strand, diff, prompt, a, b, c, d, correct, explanation) in questions:
        domain_id = domain_map[code]
        cursor.execute(
            """
            INSERT INTO dbo.questions
                (year_level_id, domain_id, strand, difficulty, question_type,
                 prompt, option_a, option_b, option_c, option_d,
                 correct_answer, explanation, status)
            OUTPUT INSERTED.question_id
            VALUES (?, ?, ?, ?, 'multiple_choice', ?, ?, ?, ?, ?, ?, ?, 'published')
            """,
            year_level_id, domain_id, strand, diff,
            prompt, a, b, c, d, correct, explanation,
        )
        qid = cursor.fetchone()[0]
        inserted_ids.setdefault(code, []).append(qid)

    conn.commit()
    return inserted_ids


def seed_tests(conn, domain_map, question_ids, year_level_id):
    cursor = conn.cursor()

    for code, title in SET_TITLES.items():
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

    conn.commit()


def main():
    conn = get_connection()
    domain_map = get_domain_map(conn)

    total_questions = 0
    total_tests = 0
    for year_level_id, questions in QUESTIONS_BY_YEAR.items():
        if set_two_already_seeded(conn, year_level_id):
            print(f"Year {year_level_id} already has a 'set 2' — skipping.")
            continue
        question_ids = seed_questions(conn, domain_map, year_level_id, questions)
        seed_tests(conn, domain_map, question_ids, year_level_id)
        n = sum(len(v) for v in question_ids.values())
        total_questions += n
        total_tests += len(question_ids)
        print(f"Year {year_level_id}: seeded {n} questions and {len(question_ids)} new tests.")

    conn.close()
    print(f"Done. Total: {total_questions} questions, {total_tests} tests.")


if __name__ == "__main__":
    main()
