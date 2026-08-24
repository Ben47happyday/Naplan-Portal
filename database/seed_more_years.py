"""
Adds Year 3, Year 7 and Year 9 practice questions/tests to naplan-portal
(Year 5 is already covered by seed_data.py). Questions are original,
written to match current NAPLAN format and difficulty by year level:
  - Year 3: simplest format, Writing stays paper-based in the real test
  - Year 7 & 9: numeracy split into calculator / non-calculator strands,
    matching the real NAPLAN Online structure for these year levels

Usage:
    python seed_more_years.py
"""

from config import get_connection

# (domain_code, strand, difficulty, prompt, a, b, c, d, correct, explanation)
QUESTIONS_BY_YEAR = {
    3: [
        ("R", "Comprehension", 1,
         "Tom packed his bag and ran to catch the bus before it left without him. Why did Tom run?",
         "To catch the bus before it left", "To play a game", "To find his dog", "To buy a snack",
         "To catch the bus before it left",
         "The sentence says Tom ran to catch the bus before it left."),
        ("R", "Vocabulary", 1,
         "The elephant was enormous, towering over the other animals in the zoo. What does 'enormous' mean?",
         "Very small", "Very big", "Very loud", "Very fast",
         "Very big",
         "'Enormous' means extremely large in size."),
        ("LC", "Grammar", 1,
         "Choose the correct sentence.",
         "The dog wagged it's tail.", "The dog wagged its tail.",
         "The dog wagged its' tail.", "The dog wagged their tail.",
         "The dog wagged its tail.",
         "'Its' (no apostrophe) shows possession; 'it's' means 'it is'."),
        ("LC", "Spelling", 1,
         "Which word is spelled correctly?",
         "Freind", "Friend", "Frend", "Freand",
         "Friend",
         "Remember: 'i before e except after c' — friend follows the usual rule."),
        ("N", "Place value", 1,
         "What is the value of the 7 in 573?",
         "7", "70", "700", "7000",
         "70",
         "The 7 is in the tens place, so its value is 70."),
        ("N", "Fractions", 1,
         "What is 1/2 + 1/4?",
         "1/4", "2/6", "3/4", "1/2",
         "3/4",
         "Convert 1/2 to 2/4, then add 1/4 to get 3/4."),
        ("N", "Shape", 1,
         "How many sides does a hexagon have?",
         "5", "6", "7", "8",
         "6",
         "A hexagon always has 6 sides."),
        ("W", "Narrative", 1,
         "Write a few sentences describing your favourite place to play. (open response)",
         None, None, None, None,
         "Open response — scored by rubric",
         "Writing tasks are scored on structure, ideas, language and grammar, not a single correct answer."),
    ],
    7: [
        ("R", "Persuasive technique", 2,
         "A persuasive text about reducing plastic waste states: 'Every piece of plastic you refuse today is "
         "one less piece choking our oceans tomorrow.' Which technique is the author mainly using?",
         "Emotive language", "Statistical evidence", "A formal citation", "A rhetorical question",
         "Emotive language",
         "Words like 'choking our oceans' appeal to emotion rather than presenting facts or data."),
        ("R", "Inference", 2,
         "In the passage, the character 'clenched his fists and stared at the floor' after hearing the news. "
         "What does this suggest about how he felt?",
         "Excited", "Frustrated or angry", "Relieved", "Confused",
         "Frustrated or angry",
         "Clenched fists and an averted gaze are physical signs of frustration or anger."),
        ("LC", "Grammar", 2,
         "Choose the correct sentence.",
         "Each of the students have to submit their assignment.",
         "Each of the students has to submit their assignment.",
         "Each of the student has to submit their assignment.",
         "Each of the students has to submitted their assignment.",
         "Each of the students has to submit their assignment.",
         "'Each' is singular, so it takes the singular verb 'has', even though 'students' is plural."),
        ("LC", "Spelling", 2,
         "Which word is spelled correctly?",
         "Definately", "Definitely", "Definitly", "Defenitely",
         "Definitely",
         "A commonly misspelled word — remember it contains 'finite': defi-NITE-ly."),
        ("N", "Algebra (non-calculator)", 2,
         "Solve for x: 3x + 5 = 20",
         "3", "5", "15", "25",
         "5",
         "Subtract 5 from both sides to get 3x = 15, then divide by 3 to get x = 5."),
        ("N", "Probability (non-calculator)", 2,
         "A bag contains 4 red and 6 blue marbles. What is the probability of picking a red marble, "
         "written as a fraction in simplest form?",
         "4/10", "2/5", "4/6", "1/2",
         "2/5",
         "4 red out of 10 total marbles simplifies to 2/5."),
        ("N", "Geometry (calculator)", 2,
         "A rectangle has a length of 12 cm and a width of 7 cm. What is its area?",
         "19 cm²", "38 cm²", "84 cm²", "168 cm²",
         "84 cm²",
         "Area of a rectangle = length × width = 12 × 7 = 84 cm²."),
        ("W", "Persuasive", 2,
         "Write a persuasive paragraph arguing whether students should have longer lunch breaks. (open response)",
         None, None, None, None,
         "Open response — scored by rubric",
         "Writing tasks are scored on structure, ideas, language and grammar, not a single correct answer."),
    ],
    9: [
        ("R", "Author's purpose", 3,
         "'While solar panels require an initial investment, the long-term savings and environmental benefits "
         "make them a wise choice for most households.' What is the author's main purpose in this sentence?",
         "To entertain", "To persuade", "To narrate an event", "To describe without opinion",
         "To persuade",
         "The sentence argues in favour of solar panels, aiming to convince the reader."),
        ("R", "Tone", 3,
         "A film reviewer wrote: 'the plot meandered aimlessly, leaving the audience checking their watches.' "
         "What is the reviewer's tone?",
         "Enthusiastic", "Critical", "Neutral", "Encouraging",
         "Critical",
         "Phrases like 'meandered aimlessly' and 'checking their watches' express a negative, critical tone."),
        ("LC", "Punctuation", 3,
         "Choose the correctly punctuated sentence.",
         "I have three favourite subjects, maths, art and science.",
         "I have three favourite subjects: maths, art and science.",
         "I have three favourite subjects; maths, art and science.",
         "I have three favourite subjects maths, art and science.",
         "I have three favourite subjects: maths, art and science.",
         "A colon introduces a list after an independent clause."),
        ("LC", "Spelling", 3,
         "Which word is spelled correctly?",
         "Occurence", "Occurrance", "Occurrence", "Occurrense",
         "Occurrence",
         "Occurrence has a double 'r' and a double 'c' — a frequently misspelled word."),
        ("N", "Geometry (non-calculator)", 3,
         "A right-angled triangle has legs of 6 cm and 8 cm. What is the length of the hypotenuse?",
         "10 cm", "12 cm", "14 cm", "48 cm",
         "10 cm",
         "By the Pythagorean theorem, hypotenuse² = 6² + 8² = 100, so hypotenuse = 10 cm."),
        ("N", "Algebra (non-calculator)", 3,
         "If 2(x - 3) = 14, what is the value of x?",
         "4", "7", "10", "11",
         "10",
         "Divide both sides by 2 to get x - 3 = 7, then add 3 to get x = 10."),
        ("N", "Statistics (calculator)", 3,
         "A class of 20 students has a mean test score of 72. If one more student joins with a score of 93, "
         "what is the new mean?",
         "72", "72.5", "73", "93",
         "73",
         "New total = (72 × 20) + 93 = 1533. New mean = 1533 ÷ 21 = 73."),
        ("W", "Narrative", 3,
         "Write a narrative opening (3-4 sentences) that immediately creates tension or suspense. (open response)",
         None, None, None, None,
         "Open response — scored by rubric",
         "Writing tasks are scored on structure, ideas, language and grammar, not a single correct answer."),
    ],
}

DOMAIN_TITLES = {
    "R": "Reading practice — set 1",
    "W": "Writing prompt",
    "LC": "Language conventions — set 1",
    "N": "Numeracy practice — set 1",
}


def get_domain_map(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT domain_id, code FROM dbo.domains")
    return {code: domain_id for domain_id, code in cursor.fetchall()}


def year_already_seeded(conn, year_level_id):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM dbo.questions WHERE year_level_id = ?", year_level_id)
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


def seed_tests(conn, domain_map, question_ids, year_level_id):
    cursor = conn.cursor()

    for code, title in DOMAIN_TITLES.items():
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

    cursor.execute(
        """
        INSERT INTO dbo.tests (year_level_id, domain_id, title, test_type, time_limit_mins, status)
        OUTPUT INSERTED.test_id
        VALUES (?, NULL, ?, 'diagnostic', ?, 'published')
        """,
        year_level_id, f"Year {year_level_id} level check", 20,
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
    domain_map = get_domain_map(conn)

    total_questions = 0
    total_tests = 0
    for year_level_id, questions in QUESTIONS_BY_YEAR.items():
        if year_already_seeded(conn, year_level_id):
            print(f"Year {year_level_id} already has questions — skipping.")
            continue
        question_ids = seed_questions(conn, domain_map, year_level_id, questions)
        seed_tests(conn, domain_map, question_ids, year_level_id)
        n = sum(len(v) for v in question_ids.values())
        total_questions += n
        total_tests += len(question_ids) + 1
        print(f"Year {year_level_id}: seeded {n} questions and {len(question_ids) + 1} tests.")

    conn.close()
    print(f"Done. Total: {total_questions} questions, {total_tests} tests.")


if __name__ == "__main__":
    main()
