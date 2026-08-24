"""
Adds a third practice set of original NAPLAN-style questions across all
four year levels (3, 5, 7, 9) and all four domains (Reading, Writing,
Language Conventions, Numeracy) to naplan-portal.

Complements seed_data.py (Year 5 set 1) and seed_more_years.py
(Years 3/7/9 set 1); a "set 2" already exists in the database for
R/LC/N. This script adds "set 3" for R/LC/N plus a second Writing
prompt per year level (a different genre from set 1's).

Note: plain hyphens are used instead of em dashes in titles/text to
avoid an existing NVARCHAR encoding issue with non-ASCII punctuation.

Usage:
    python seed_bank_set3.py
"""

from config import get_connection

# (domain_code, strand, difficulty, prompt, a, b, c, d, correct, explanation)
QUESTIONS_SET3_BY_YEAR = {
    3: [
        ("R", "Comprehension", 1,
         "Ben forgot his lunchbox at home, so his teacher gave him a sandwich from the staffroom. "
         "Why was Ben given a sandwich?",
         "Because he forgot his lunchbox", "Because he was hungry after sport",
         "Because it was his birthday", "Because his teacher likes him",
         "Because he forgot his lunchbox",
         "The text states Ben forgot his lunchbox, so his teacher gave him food."),
        ("R", "Vocabulary", 1,
         "The puppy was exhausted after chasing the ball all afternoon. What does 'exhausted' mean?",
         "Very tired", "Very happy", "Very hungry", "Very loud",
         "Very tired",
         "'Exhausted' means extremely tired, often from physical effort."),
        ("R", "Sequencing", 1,
         "Which word would you expect to find at the start of a set of instructions?",
         "First", "Finally", "Meanwhile", "Suddenly",
         "First",
         "'First' signals the beginning of a sequence of steps."),
        ("LC", "Punctuation", 1,
         "Choose the correct sentence.",
         "Its raining outside.", "It's raining outside.",
         "Its' raining outside.", "It is'nt raining outside.",
         "It's raining outside.",
         "'It's' is the contraction of 'it is'; an apostrophe replaces the missing letter."),
        ("LC", "Nouns", 1,
         "Which word is a common noun?",
         "Sydney", "dog", "Monday", "Australia",
         "dog",
         "A common noun names a general person, place or thing and does not start with a capital letter."),
        ("LC", "Verb tense", 1,
         "Which sentence is written in the past tense?",
         "She runs to school.", "She will run to school.",
         "She ran to school.", "She is running to school.",
         "She ran to school.",
         "'Ran' is the past tense form of the verb 'run'."),
        ("N", "Addition", 1,
         "Sam has 245 marbles. He gives away 78. How many does he have left?",
         "167", "177", "163", "323",
         "167",
         "245 - 78 = 167."),
        ("N", "Time", 1,
         "What time is shown when the hour hand is between 3 and 4, and the minute hand is on the 6?",
         "3:15", "3:30", "4:30", "3:45",
         "3:30",
         "The minute hand on the 6 means 30 minutes past the hour, and the hour hand between 3 and 4 means it is 3:30."),
        ("N", "Shape", 1,
         "Which shape has 4 equal sides and 4 right angles?",
         "Rectangle", "Triangle", "Square", "Circle",
         "Square",
         "A square has 4 equal sides and 4 right angles; a rectangle's sides are not all equal."),
        ("W", "Informative", 1,
         "Write a few sentences explaining how to make your favourite snack. (open response)",
         None, None, None, None,
         "Open response - scored by rubric",
         "Writing tasks are scored on structure, ideas, language and grammar, not a single correct answer."),
    ],
    5: [
        ("R", "Main idea", 2,
         "A newspaper article describes three different ways students can reduce plastic waste at school. "
         "What is most likely the main idea of the article?",
         "Plastic is bad for the environment", "Students can take action to reduce plastic waste at school",
         "The ocean has too much plastic", "Schools should ban all plastic",
         "Students can take action to reduce plastic waste at school",
         "The article focuses on practical actions students can take, not just the problem itself."),
        ("R", "Vocabulary in context", 2,
         "The old bridge creaked and swayed as the wind grew stronger, looking as though it might collapse "
         "at any moment. What does 'collapse' mean in this sentence?",
         "Fall down", "Grow taller", "Shine brightly", "Move sideways",
         "Fall down",
         "'Collapse' means to fall down or give way suddenly."),
        ("R", "Text purpose", 1,
         "A brochure listing opening hours, ticket prices and directions to a museum is an example of which "
         "type of text?",
         "Narrative", "Persuasive", "Informative", "Poetic",
         "Informative",
         "The brochure's purpose is to give facts and practical details, which makes it informative."),
        ("LC", "Sentence structure", 2,
         "Which sentence uses a comma correctly?",
         "After the game, we went for ice cream.", "After the game we, went for ice cream.",
         "After, the game we went for ice cream.", "After the game we went, for ice cream.",
         "After the game, we went for ice cream.",
         "A comma follows an introductory phrase before the main clause begins."),
        ("LC", "Homophones", 2,
         "Choose the correct word: 'I need to ___ my shoes before we leave.'",
         "where", "wear", "ware", "were",
         "wear",
         "'Wear' means to have clothing or shoes on your body."),
        ("LC", "Punctuation", 1,
         "Which sentence needs a question mark?",
         "What time does the bus leave", "The bus leaves at three",
         "Please be on time", "The bus is late again",
         "What time does the bus leave",
         "A direct question requires a question mark at the end."),
        ("N", "Decimals", 2,
         "What is 0.4 + 0.35?",
         "0.39", "0.7", "0.75", "3.9",
         "0.75",
         "0.40 + 0.35 = 0.75."),
        ("N", "Perimeter", 2,
         "A rectangle has a length of 9 cm and a width of 5 cm. What is its perimeter?",
         "14 cm", "28 cm", "45 cm", "40 cm",
         "28 cm",
         "Perimeter = 2 x (length + width) = 2 x (9 + 5) = 28 cm."),
        ("N", "Data", 2,
         "A tally shows 5 students like apples, 3 like bananas, and 7 like oranges. How many students were "
         "surveyed in total?",
         "12", "15", "10", "16",
         "15",
         "5 + 3 + 7 = 15 students in total."),
        ("W", "Narrative", 2,
         "Continue this story opening in a few sentences: 'The old chest in the attic had been locked for "
         "years, until today.' (open response)",
         None, None, None, None,
         "Open response - scored by rubric",
         "Writing tasks are scored on structure, ideas, language and grammar, not a single correct answer."),
    ],
    7: [
        ("R", "Text structure", 2,
         "A recipe for banana bread lists ingredients followed by numbered steps. This structure is used "
         "mainly to help the reader:",
         "Feel emotion", "Follow the process in order",
         "Compare two opinions", "Remember character names",
         "Follow the process in order",
         "Numbered steps guide the reader through a process in the correct sequence."),
        ("R", "Figurative language", 2,
         "'The classroom was a zoo before the teacher arrived.' This sentence is an example of:",
         "Simile", "Metaphor", "Onomatopoeia", "Alliteration",
         "Metaphor",
         "The sentence directly states the classroom 'was' a zoo, comparing them without using 'like' or 'as'."),
        ("R", "Author's purpose", 2,
         "An opinion column arguing that school days should start later is mainly written to:",
         "Entertain readers with a story", "Inform readers of a scientific fact",
         "Persuade readers to support a change", "Describe a place in detail",
         "Persuade readers to support a change",
         "An opinion column argues a position, aiming to convince readers to agree."),
        ("LC", "Punctuation", 2,
         "Which sentence uses an apostrophe correctly?",
         "The dogs' bone was buried in the yard.", "The dog's bone was buried in the yard.",
         "The dogs bone's was buried in the yard.", "The dog bones' was buried in the yard.",
         "The dog's bone was buried in the yard.",
         "For one dog, the possessive apostrophe goes before the 's': dog's."),
        ("LC", "Sentence types", 2,
         "Which sentence is a compound sentence?",
         "She studied hard.", "She studied hard, and she passed the test.",
         "Studying hard for the test.", "She studied hard for the test yesterday.",
         "She studied hard, and she passed the test.",
         "A compound sentence joins two independent clauses with a coordinating conjunction such as 'and'."),
        ("LC", "Word class", 2,
         "In the sentence 'The quickly moving car swerved,' which word is the adverb?",
         "quickly", "moving", "car", "swerved",
         "quickly",
         "'Quickly' describes how the car was moving, making it an adverb."),
        ("N", "Ratio (non-calculator)", 2,
         "A recipe uses flour and sugar in the ratio 3:2. If 12 cups of flour are used, how many cups of "
         "sugar are needed?",
         "6", "8", "9", "18",
         "8",
         "12 cups of flour is 4 times 3, so sugar is 4 times 2 = 8 cups."),
        ("N", "Percentages (calculator)", 2,
         "A jacket originally priced at $80 is on sale for 25% off. What is the sale price?",
         "$20", "$55", "$60", "$65",
         "$60",
         "25% of $80 is $20, so the sale price is $80 - $20 = $60."),
        ("N", "Linear equations (non-calculator)", 2,
         "Solve for y: 2y - 7 = 11",
         "2", "7", "9", "18",
         "9",
         "Add 7 to both sides to get 2y = 18, then divide by 2 to get y = 9."),
        ("W", "Discursive", 2,
         "Write a short paragraph discussing both sides of whether homework should be compulsory. (open response)",
         None, None, None, None,
         "Open response - scored by rubric",
         "Writing tasks are scored on structure, ideas, language and grammar, not a single correct answer."),
    ],
    9: [
        ("R", "Bias", 3,
         "A news article about a new shopping centre only quotes local business owners who support the "
         "development. This is an example of:",
         "Balanced reporting", "Selective bias", "Objective analysis", "Chronological structure",
         "Selective bias",
         "Only including supportive voices while omitting opposing views shows selective bias."),
        ("R", "Connotation", 3,
         "In the sentence 'The politician's speech was littered with empty promises,' the word 'littered' "
         "suggests:",
         "The speech was well-organised", "The promises were numerous and worthless",
         "The speech was short", "The politician was honest",
         "The promises were numerous and worthless",
         "'Littered' has a negative connotation, implying the promises were scattered carelessly and had no value."),
        ("R", "Text comparison", 3,
         "Two articles report the same event, but one uses statistics and expert quotes while the other uses "
         "personal anecdotes. The first article is most likely aiming to:",
         "Entertain", "Persuade through emotion",
         "Persuade through evidence and credibility", "Narrate a personal story",
         "Persuade through evidence and credibility",
         "Statistics and expert quotes build credibility and are a logical, evidence-based persuasive technique."),
        ("LC", "Clauses", 3,
         "Identify the subordinate clause: 'Although it was raining, the match continued.'",
         "Although it was raining", "the match continued",
         "it was raining", "the match",
         "Although it was raining",
         "The clause beginning with 'Although' cannot stand alone and depends on the main clause."),
        ("LC", "Punctuation", 3,
         "Which sentence uses a semicolon correctly?",
         "I love reading; especially mystery novels.", "I love reading; I especially love mystery novels.",
         "I love reading, I especially love; mystery novels.", "I love; reading mystery novels.",
         "I love reading; I especially love mystery novels.",
         "A semicolon joins two independent clauses that are closely related in meaning."),
        ("LC", "Modality", 3,
         "Which word shows the highest level of certainty?",
         "Might", "Could", "Will", "May",
         "Will",
         "'Will' expresses certainty, while 'might', 'could' and 'may' express possibility."),
        ("N", "Trigonometry (calculator)", 3,
         "In a right-angled triangle, one angle is 30 degrees and the hypotenuse is 10 cm. What is the length "
         "of the side opposite the 30 degree angle, to 1 decimal place?",
         "5.0 cm", "8.7 cm", "3.3 cm", "10.0 cm",
         "5.0 cm",
         "opposite = hypotenuse x sin(30 degrees) = 10 x 0.5 = 5.0 cm."),
        ("N", "Simultaneous equations (non-calculator)", 3,
         "Solve: x + y = 10 and x - y = 2. What is the value of x?",
         "4", "6", "8", "12",
         "6",
         "Adding both equations gives 2x = 12, so x = 6."),
        ("N", "Compound interest (calculator)", 3,
         "$2000 is invested at 5% p.a. compound interest. What is the value after 2 years, to the nearest "
         "dollar?",
         "$2100", "$2200", "$2205", "$2500",
         "$2205",
         "2000 x 1.05^2 = 2205, since each year the balance grows by 5% on the previous year's total."),
        ("W", "Persuasive", 3,
         "Write an opening paragraph for a persuasive speech arguing that students should have a say in "
         "school policy decisions. (open response)",
         None, None, None, None,
         "Open response - scored by rubric",
         "Writing tasks are scored on structure, ideas, language and grammar, not a single correct answer."),
    ],
}

DOMAIN_TITLES_SET3 = {
    "R": "Reading practice - set 3",
    "LC": "Language conventions - set 3",
    "N": "Numeracy practice - set 3",
    "W": "Writing prompt 2",
}


def get_domain_map(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT domain_id, code FROM dbo.domains")
    return {code: domain_id for domain_id, code in cursor.fetchall()}


def set3_already_seeded(conn, year_level_id):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM dbo.tests WHERE year_level_id = ? AND title LIKE 'Reading practice - set 3%'",
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

    for code, title in DOMAIN_TITLES_SET3.items():
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
    for year_level_id, questions in QUESTIONS_SET3_BY_YEAR.items():
        if set3_already_seeded(conn, year_level_id):
            print(f"Year {year_level_id} already has set 3 - skipping.")
            continue
        question_ids = seed_questions(conn, domain_map, year_level_id, questions)
        seed_tests(conn, domain_map, question_ids, year_level_id)
        n = sum(len(v) for v in question_ids.values())
        total_questions += n
        total_tests += len(question_ids)
        print(f"Year {year_level_id}: seeded {n} questions and {len(question_ids)} tests.")

    conn.close()
    print(f"Done. Total: {total_questions} questions, {total_tests} tests.")


if __name__ == "__main__":
    main()
