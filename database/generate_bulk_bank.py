"""
Generates a large, edition-tagged NAPLAN practice question bank and inserts
it into naplan-portal.

Content is organised by "edition year" (a rolling window of the most
recent 4 calendar years) crossed with NAPLAN year level (3, 5, 7, 9).
Each (edition_year, year_level) bucket gets at least MIN_PER_BUCKET
questions spread across Reading, Writing, Language Conventions and
Numeracy.

All content is originally generated here from parametrised templates
and word banks (NOT sourced from real/official NAPLAN papers):
  - Numeracy: every question's correct answer is computed programmatically,
    so correctness is guaranteed by construction.
  - Language Conventions: rule-based sentence/spelling templates with
    word-bank substitution.
  - Reading: short synthetic "micro-passage" templates with comprehension
    questions whose answers are derived directly from the substituted
    template values.
  - Writing: open-response prompts built by combining a genre with a
    topic bank.

Re-running this script is idempotent per edition/year-level bucket: if a
bucket already has >= MIN_PER_BUCKET questions tagged with that
content_year, it is skipped.

Usage:
    python generate_bulk_bank.py
"""

import random

from config import get_connection
import svg_diagrams as svg

EDITION_YEARS = [2023, 2024, 2025, 2026]   # rolling last-4-years window
YEAR_LEVELS = [3, 5, 7, 9]

TARGET_PER_DOMAIN = {"N": 80, "LC": 80, "R": 80, "W": 70}   # sums to 310 (>= 300 min)
MIN_PER_BUCKET = 300

# ------------------------------------------------------------------
# Shared word banks
# ------------------------------------------------------------------

NAMES = [
    "Maya", "Ben", "Priya", "Liam", "Aisha", "Noah", "Chloe", "Ethan", "Zara", "Lucas",
    "Mia", "Oscar", "Ivy", "Leo", "Grace", "Kai", "Ruby", "Finn", "Sofia", "Jack",
    "Amara", "Owen", "Layla", "Miles", "Nina", "Theo", "Ella", "Sam", "Freya", "Arjun",
]

PLACES = [
    "the park", "the beach", "school", "the library", "the farm", "the shopping centre",
    "the museum", "the sports oval", "the classroom", "the garden", "the zoo",
    "the swimming pool", "the campsite", "the airport", "the market",
]

TOPICS = [
    "reducing plastic waste", "school uniforms", "later school start times", "homework load",
    "social media use for teenagers", "recycling programs", "public transport funding",
    "junk food advertising", "daylight saving time", "zoo animal welfare", "fast fashion",
    "video game screen time limits", "urban green spaces", "electric vehicles",
    "student volunteering", "longer lunch breaks", "school sports funding", "banning single-use bags",
    "protecting native wildlife", "healthy canteen menus", "a favourite family tradition", "learning a musical instrument",
    "the best way to spend a weekend", "keeping a pet", "visiting a new city", "growing your own vegetables",
    "the importance of sleep", "a memorable birthday", "trying a new hobby", "helping a neighbour",
    "the changing seasons", "a favourite book or film", "working as part of a team", "overcoming a fear",
]

# (event, reason) pairs used to build "why did X happen" comprehension items
REASON_EVENTS = [
    ("ran to the bus stop", "to catch the bus before it left"),
    ("hid under the table", "because the thunder was so loud"),
    ("packed an extra jumper", "because the forecast said it would be cold"),
    ("watered the plants every morning", "so they would not wilt in the summer heat"),
    ("saved half of her pocket money", "to buy a new bike"),
    ("practised the piano every day", "to prepare for the school concert"),
    ("double-checked the recipe", "to make sure no ingredient was forgotten"),
    ("left home early", "to avoid being late for the exam"),
    ("wore a raincoat", "because dark clouds were forming"),
    ("asked the librarian for help", "because the right book could not be found"),
    ("wrote a list before shopping", "to remember everything that was needed"),
    ("turned off the lights before leaving", "to save electricity"),
    ("brought a spare pair of socks", "because the weather forecast predicted rain"),
    ("set an extra alarm", "to make sure not to oversleep before the trip"),
    ("kept a diary every night", "to remember the details of the holiday"),
]

# (action description, correct emotion, 3 distractor emotions)
INFERENCE_ITEMS = [
    ("slammed the door and stomped up the stairs", "Angry", ["Happy", "Tired", "Confused"]),
    ("clenched fists and stared at the floor", "Frustrated or angry", ["Excited", "Relieved", "Confused"]),
    ("skipped down the hallway, humming a tune", "Happy", ["Nervous", "Bored", "Angry"]),
    ("let out a long sigh and slumped in the chair", "Disappointed", ["Excited", "Proud", "Curious"]),
    ("eyes lit up and jumped out of the seat", "Excited", ["Sad", "Bored", "Calm"]),
    ("voice trembled while reading the note aloud", "Nervous", ["Confident", "Bored", "Amused"]),
    ("kept glancing at the clock and tapping a foot", "Impatient", ["Relaxed", "Sleepy", "Amused"]),
    ("smiled quietly and hugged the certificate", "Proud", ["Embarrassed", "Angry", "Worried"]),
    ("backed away slowly with wide eyes", "Scared", ["Delighted", "Bored", "Proud"]),
    ("crossed both arms and refused to speak", "Upset", ["Cheerful", "Curious", "Relaxed"]),
]

# (text example, correct type)
TEXT_TYPE_ITEMS = [
    ("a brochure listing opening hours, ticket prices and directions to a museum", "Informative"),
    ("a story about a dragon who learns to share its treasure", "Narrative"),
    ("a letter to the council arguing for a new skate park", "Persuasive"),
    ("a set of numbered steps for baking banana bread", "Informative"),
    ("a diary entry describing a character's first day at a new school", "Narrative"),
    ("an advertisement claiming a toothpaste is the best on the market", "Persuasive"),
    ("a weather report listing the forecast for the week", "Informative"),
    ("a poem describing the feeling of the first day of summer", "Poetic"),
]

WRITING_GENRES = [
    ("Narrative", "Write a short narrative (a few sentences) about {topic}. (open response)"),
    ("Persuasive", "Write a persuasive paragraph arguing for or against {topic}. (open response)"),
    ("Informative", "Write a short informative paragraph explaining {topic}. (open response)"),
    ("Discursive", "Write a paragraph discussing both sides of {topic}. (open response)"),
    ("Descriptive", "Write a short descriptive passage about {topic}. (open response)"),
    ("Recount", "Write a recount of a time related to {topic}. (open response)"),
]

WRITING_TOPICS = [
    "your favourite place to visit", "a memorable school event", "whether homework should be compulsory",
    "the importance of recycling", "a time you tried something new", "whether school days should start later",
    "your favourite season and why", "the benefits of team sports", "a character who overcomes a challenge",
    "why reading is important", "a community event worth attending", "whether pets should be allowed at school",
    "an invention that changed daily life", "the value of spending time outdoors", "a lesson learned from a mistake",
    "whether students should choose their own subjects", "a place you would like to explore",
    "the importance of kindness", "a skill you would like to learn", "whether screen time should be limited",
    "a favourite family tradition", "learning a musical instrument", "the best way to spend a weekend",
    "keeping a pet", "visiting a new city", "growing your own vegetables", "the importance of sleep",
    "a memorable birthday", "trying a new hobby", "helping a neighbour", "the changing seasons",
    "a favourite book or film", "working as part of a team", "overcoming a fear", "a rainy day adventure",
    "the best gift you ever received", "a journey you would like to take", "what makes a good friend",
    "an achievement you are proud of", "whether uniforms should be optional", "a tradition from another culture",
]


def mc(rng, strand, difficulty, prompt, correct, wrongs, explanation):
    options = [correct] + list(wrongs)
    rng.shuffle(options)
    return {
        "strand": strand, "difficulty": difficulty, "question_type": "multiple_choice",
        "prompt": prompt, "options": options, "correct": correct, "explanation": explanation,
    }


def open_response(strand, difficulty, prompt, explanation):
    return {
        "strand": strand, "difficulty": difficulty, "question_type": "short_answer",
        "prompt": prompt, "options": None, "correct": "Open response - scored by rubric",
        "explanation": explanation,
    }


def numeric_distractors(rng, correct, deltas, count=3, min_val=0):
    candidates = []
    pool = list(deltas)
    rng.shuffle(pool)
    for d in pool:
        val = correct + d
        if val != correct and val >= min_val and val not in candidates:
            candidates.append(val)
        if len(candidates) >= count:
            break
    extra_pool = [-30, -25, -20, -15, -12, -8, -6, -3, 3, 6, 8, 12, 15, 20, 25, 30]
    rng.shuffle(extra_pool)
    i = 0
    while len(candidates) < count and i < len(extra_pool):
        val = correct + extra_pool[i]
        i += 1
        if val != correct and val >= min_val and val not in candidates:
            candidates.append(val)
    return candidates[:count]


# ------------------------------------------------------------------
# Numeracy patterns
# ------------------------------------------------------------------

def n_addition(rng):
    a, b = rng.randint(100, 700), rng.randint(10, 299)
    ans = a + b
    wrongs = numeric_distractors(rng, ans, [10, -10, 1, -1, 100, -100])
    return mc(rng, "Addition", 1, f"What is {a} + {b}?", str(ans), [str(w) for w in wrongs],
               f"{a} + {b} = {ans}.")


def n_subtraction(rng):
    a = rng.randint(300, 999)
    b = rng.randint(10, a - 10)
    ans = a - b
    wrongs = numeric_distractors(rng, ans, [10, -10, 1, -1, 100, -100])
    return mc(rng, "Subtraction", 1, f"What is {a} - {b}?", str(ans), [str(w) for w in wrongs],
               f"{a} - {b} = {ans}.")


def n_multiplication(rng):
    a, b = rng.randint(2, 10), rng.randint(2, 10)
    ans = a * b
    wrongs = numeric_distractors(rng, ans, [a, -a, b, -b, 1, -1])
    return mc(rng, "Multiplication", 1, f"What is {a} x {b}?", str(ans), [str(w) for w in wrongs],
               f"{a} x {b} = {ans}.")


def n_place_value(rng):
    num = rng.randint(100, 999)
    pos = rng.randint(0, 2)
    digit = int(str(num)[pos])
    place = 10 ** (2 - pos)
    value = digit * place
    wrongs = numeric_distractors(rng, value, [digit, -digit if value - digit >= 0 else digit,
                                                value * 10 if place < 100 else max(value // 10, 1),
                                                value + place, value - place])
    return mc(rng, "Place value", 1, f"What is the value of the {digit} in {num}?", str(value),
               [str(w) for w in wrongs], f"The {digit} is in the "
               f"{'hundreds' if pos == 0 else 'tens' if pos == 1 else 'ones'} place, so its value is {value}.")


def n_fractions_simple(rng):
    items = [
        ("1/2", "1/4", "3/4"), ("1/4", "1/4", "1/2"), ("1/3", "1/3", "2/3"),
        ("1/4", "2/4", "3/4"), ("1/8", "3/8", "1/2"), ("2/6", "1/6", "1/2"),
        ("1/5", "2/5", "3/5"), ("3/10", "4/10", "7/10"),
    ]
    a, b, ans = rng.choice(items)
    wrongs = {ans}
    pool = ["1/2", "3/4", "1/4", "2/3", "1/3", "5/8", "7/8", "3/5", "1/5", "9/10"]
    rng.shuffle(pool)
    for w in pool:
        if w not in wrongs:
            wrongs.add(w)
        if len(wrongs) == 4:
            break
    wrongs.discard(ans)
    return mc(rng, "Fractions", 1, f"What is {a} + {b}?", ans, list(wrongs)[:3],
               f"{a} + {b} = {ans}.")


def n_shape(rng):
    shapes = [("triangle", 3), ("square", 4), ("rectangle", 4), ("pentagon", 5),
              ("hexagon", 6), ("heptagon", 7), ("octagon", 8), ("nonagon", 9)]
    shape, sides = rng.choice(shapes)
    all_sides = [s for _, s in shapes]
    wrongs = numeric_distractors(rng, sides, [1, -1, 2, -2, 3], min_val=3)
    return mc(rng, "Shape", 1, f"How many sides does a {shape} have?", str(sides), [str(w) for w in wrongs],
               f"A {shape} always has {sides} sides.")


def n_time(rng):
    hour = rng.randint(1, 12)
    minute = rng.choice([0, 15, 30, 45])
    add = rng.choice([15, 30, 45, 60, 90])
    total_minutes = hour * 60 + minute + add
    nh = (total_minutes // 60) % 12
    if nh == 0:
        nh = 12
    nm = total_minutes % 60
    correct = f"{nh}:{nm:02d}"
    wrong_adds = [add - 15, add + 15, add - 30, add + 30]
    wrongs = set()
    for wa in wrong_adds:
        if wa <= 0 or wa == add:
            continue
        wtot = hour * 60 + minute + wa
        wh = (wtot // 60) % 12
        if wh == 0:
            wh = 12
        wm = wtot % 60
        wrongs.add(f"{wh}:{wm:02d}")
    wrongs.discard(correct)
    while len(wrongs) < 3:
        wrongs.add(f"{rng.randint(1,12)}:{rng.choice([0,15,30,45]):02d}")
        wrongs.discard(correct)
    return mc(rng, "Time", 1, f"It is {hour}:{minute:02d}. What time will it be in {add} minutes?",
               correct, list(wrongs)[:3], f"{add} minutes after {hour}:{minute:02d} is {correct}.")


def n_money(rng):
    coin_values = [5, 10, 20, 50, 100, 200]
    coins = rng.sample(coin_values, 3)
    total = sum(coins)
    correct = f"${total/100:.2f}" if total >= 100 else f"{total}c"
    wrongs_v = numeric_distractors(rng, total, [5, -5, 10, -10, 20], min_val=5)
    wrongs = [f"${w/100:.2f}" if w >= 100 else f"{w}c" for w in wrongs_v]
    coin_text = ", ".join(f"a {c}c coin" for c in coins[:-1]) + f" and a {coins[-1]}c coin"
    return mc(rng, "Money", 1, f"You have {coin_text}. How much money do you have in total?", correct,
               wrongs, f"{' + '.join(str(c) for c in coins)} = {total}c, which is {correct}.")


BAR_GRAPH_THEMES = [
    ("favourite fruit", ["Apples", "Bananas", "Oranges", "Grapes"]),
    ("favourite sport", ["Soccer", "Netball", "Basketball", "Swimming"]),
    ("favourite pet", ["Dogs", "Cats", "Fish", "Birds"]),
    ("favourite colour", ["Blue", "Green", "Red", "Purple"]),
]


def n_bar_graph_read(rng):
    theme, cats = rng.choice(BAR_GRAPH_THEMES)
    values = rng.sample(range(3, 19), len(cats))
    hi, lo = sorted(rng.sample(range(len(cats)), 2), key=lambda i: -values[i])
    diff = values[hi] - values[lo]
    wrongs_v = numeric_distractors(rng, diff, [1, -1, 2, -2, 3], min_val=1)
    item = mc(rng, "Statistics", 1,
              f"The bar graph shows students' {theme}. How many more students chose {cats[hi]} than {cats[lo]}?",
              str(diff), [str(w) for w in wrongs_v],
              f"{values[hi]} - {values[lo]} = {diff}.")
    item["_svg"] = svg.bar_chart_svg(values, cats)
    return item


def n_length_convert(rng):
    if rng.random() < 0.5:
        m = rng.randint(2, 9)
        ans = m * 100
        prompt = f"How many centimetres are in {m} metres?"
        explanation = f"1 metre = 100 cm, so {m} metres = {m} x 100 = {ans} cm."
    else:
        m = rng.randint(2, 9)
        cm = m * 100
        ans = m
        prompt = f"How many metres are in {cm} centimetres?"
        explanation = f"100 cm = 1 metre, so {cm} cm = {cm} ÷ 100 = {ans} m."
    wrongs_v = numeric_distractors(rng, ans, [10, -10, 100, -100, 1], min_val=1)
    return mc(rng, "Measurement", 1, prompt, str(ans), [str(w) for w in wrongs_v], explanation)


def n_money_change(rng):
    price_c = rng.choice([150, 250, 325, 375, 475, 550, 650, 725, 825, 999, 1150, 1450])
    note = rng.choice([n for n in [5, 10, 20, 50] if n * 100 > price_c])
    change_c = note * 100 - price_c
    correct = f"${change_c/100:.2f}"
    wrongs_v = numeric_distractors(rng, change_c, [50, -50, 100, -100, 25], min_val=5)
    wrongs = [f"${w/100:.2f}" for w in wrongs_v]
    return mc(rng, "Money", 1,
              f"An item costs ${price_c/100:.2f}. You pay with a ${note} note. How much change do you get?",
              correct, wrongs, f"${note}.00 - ${price_c/100:.2f} = {correct}.")


N_PATTERNS_Y3 = [n_addition, n_subtraction, n_multiplication, n_place_value,
                  n_fractions_simple, n_shape, n_time, n_money,
                  n_bar_graph_read, n_length_convert, n_money_change]


def n_decimals(rng):
    a = rng.randint(10, 90) / 100
    b = rng.randint(10, 90) / 100
    ans = round(a + b, 2)
    wrongs_v = [round(ans + d, 2) for d in [0.1, -0.1, 0.05, -0.05, 1.0]]
    wrongs = sorted({f"{w:.2f}" for w in wrongs_v if round(w, 2) != ans})[:3]
    while len(wrongs) < 3:
        w = round(ans + rng.choice([0.15, -0.15, 0.2, -0.2]), 2)
        if f"{w:.2f}" not in wrongs and w != ans:
            wrongs.append(f"{w:.2f}")
    return mc(rng, "Decimals", 2, f"What is {a:.2f} + {b:.2f}?", f"{ans:.2f}", wrongs,
               f"{a:.2f} + {b:.2f} = {ans:.2f}.")


def n_perimeter(rng):
    length, width = rng.randint(4, 20), rng.randint(3, 15)
    perimeter = 2 * (length + width)
    wrongs_v = numeric_distractors(rng, perimeter, [length, -length, width, -width, 2])
    return mc(rng, "Perimeter", 2, f"A rectangle has a length of {length} cm and a width of {width} cm. "
               f"What is its perimeter?", f"{perimeter} cm", [f"{w} cm" for w in wrongs_v],
               f"Perimeter = 2 x (length + width) = 2 x ({length} + {width}) = {perimeter} cm.")


def n_area(rng):
    length, width = rng.randint(4, 15), rng.randint(3, 12)
    area = length * width
    wrongs_v = numeric_distractors(rng, area, [length, -length, width, -width, 2 * (length + width)])
    return mc(rng, "Area", 2, f"A rectangle has a length of {length} cm and a width of {width} cm. "
               f"What is its area?", f"{area} cm²", [f"{w} cm²" for w in wrongs_v],
               f"Area = length x width = {length} x {width} = {area} cm².")


def n_angles_triangle(rng):
    a = rng.randint(30, 100)
    b = rng.randint(30, 140 - a) if 140 - a > 30 else 40
    c = 180 - a - b
    wrongs_v = numeric_distractors(rng, c, [10, -10, 5, -5, 20], min_val=1)
    return mc(rng, "Angles", 2, f"A triangle has angles of {a} degrees and {b} degrees. "
               f"What is the size of the third angle?", f"{c} degrees", [f"{w} degrees" for w in wrongs_v],
               f"The angles in a triangle sum to 180 degrees, so the third angle is "
               f"180 - {a} - {b} = {c} degrees.")


def n_mean(rng):
    nums = [rng.randint(2, 20) for _ in range(4)]
    total = sum(nums)
    mean = total / 4
    mean_str = f"{mean:.1f}" if mean != int(mean) else str(int(mean))
    wrongs_v = [mean + d for d in [1, -1, 0.5, -0.5, 2]]
    wrongs = []
    for w in wrongs_v:
        ws = f"{w:.1f}" if w != int(w) else str(int(w))
        if ws != mean_str and ws not in wrongs:
            wrongs.append(ws)
    return mc(rng, "Statistics", 2, f"What is the mean of {nums[0]}, {nums[1]}, {nums[2]} and {nums[3]}?",
               mean_str, wrongs[:3], f"({' + '.join(str(n) for n in nums)}) / 4 = {total} / 4 = {mean_str}.")


def n_multiplication_2digit(rng):
    a, b = rng.randint(11, 40), rng.randint(3, 9)
    ans = a * b
    wrongs_v = numeric_distractors(rng, ans, [a, -a, b, -b, 10])
    return mc(rng, "Multiplication", 2, f"What is {a} x {b}?", str(ans), [str(w) for w in wrongs_v],
               f"{a} x {b} = {ans}.")


def n_division(rng):
    b = rng.randint(3, 9)
    ans = rng.randint(4, 20)
    a = b * ans
    wrongs_v = numeric_distractors(rng, ans, [1, -1, 2, -2, b])
    return mc(rng, "Division", 2, f"What is {a} ÷ {b}?", str(ans), [str(w) for w in wrongs_v],
               f"{a} ÷ {b} = {ans}.")


def n_divisibility(rng):
    d = rng.choice([3, 4, 5, 6, 8, 9])
    correct_num = d * rng.randint(4, 20)
    wrongs = []
    deltas = [1, -1, 2, -2, 3, -3, 4, -4]
    rng.shuffle(deltas)
    for delta in deltas:
        cand = correct_num + delta
        if cand > 0 and cand % d != 0 and cand not in wrongs:
            wrongs.append(cand)
        if len(wrongs) == 3:
            break
    return mc(rng, "Number properties", 2, f"Which of these numbers is divisible by {d}?", str(correct_num),
              [str(w) for w in wrongs],
              f"{correct_num} ÷ {d} = {correct_num // d}, with no remainder.")


def n_divide_pow10(rng):
    power = rng.choice([10, 100, 1000])
    ans = rng.randint(2, 900)
    base = ans * power
    wrongs_v = numeric_distractors(rng, ans, [1, -1, 10, -10, ans * 9 // 10 if ans >= 10 else 1])
    return mc(rng, "Number properties", 2, f"What is {base} ÷ {power}?", str(ans), [str(w) for w in wrongs_v],
              f"{base} ÷ {power} = {ans}.")


def n_time_duration(rng):
    start_h = rng.randint(1, 11)
    start_m = rng.choice([0, 15, 30, 45])
    duration = rng.choice([20, 35, 50, 65, 80, 95, 110, 125])
    total_start = start_h * 60 + start_m
    total_end = total_start + duration
    end_h = (total_end // 60) % 12 or 12
    end_m = total_end % 60
    wrongs_v = numeric_distractors(rng, duration, [15, -15, 30, -30, 5], min_val=5)
    item = mc(rng, "Time", 2,
              f"A movie starts at {start_h}:{start_m:02d} and finishes at {end_h}:{end_m:02d}. "
              f"How long does the movie last, in minutes?",
              str(duration), [str(w) for w in wrongs_v],
              f"From {start_h}:{start_m:02d} to {end_h}:{end_m:02d} is {duration} minutes.")
    item["_svg"] = svg.two_clocks_svg(start_h, start_m, end_h, end_m, "Start", "End")
    return item


N_PATTERNS_Y5 = [n_decimals, n_perimeter, n_area, n_angles_triangle, n_mean,
                  n_multiplication_2digit, n_division, n_fractions_simple,
                  n_divisibility, n_divide_pow10, n_time_duration]


def n_linear_eq(rng):
    x = rng.randint(2, 15)
    a = rng.randint(2, 8)
    b = rng.randint(1, 30)
    c = a * x + b
    wrongs_v = numeric_distractors(rng, x, [1, -1, 2, -2, 3], min_val=1)
    return mc(rng, "Algebra (non-calculator)", 2, f"Solve for x: {a}x + {b} = {c}", str(x),
               [str(w) for w in wrongs_v],
               f"Subtract {b} from both sides to get {a}x = {c - b}, then divide by {a} to get x = {x}.")


def n_ratio(rng):
    r1, r2 = rng.randint(2, 6), rng.randint(2, 6)
    while r2 == r1:
        r2 = rng.randint(2, 6)
    mult = rng.randint(2, 8)
    total1 = r1 * mult
    ans = r2 * mult
    wrongs_v = numeric_distractors(rng, ans, [r2, -r2, mult, -mult, r1])
    return mc(rng, "Ratio (non-calculator)", 2,
               f"A recipe uses flour and sugar in the ratio {r1}:{r2}. If {total1} cups of flour are used, "
               f"how many cups of sugar are needed?", str(ans), [str(w) for w in wrongs_v],
               f"{total1} cups of flour is {mult} times {r1}, so sugar is {mult} times {r2} = {ans} cups.")


def n_probability(rng):
    red = rng.randint(2, 8)
    blue = rng.randint(2, 8)
    total = red + blue
    from math import gcd
    g = gcd(red, total)
    num, den = red // g, total // g
    ans = f"{num}/{den}"
    wrongs = {f"{red}/{total}", f"{blue}/{total}", f"{num}/{den+1}" if den + 1 != den else f"{num+1}/{den}"}
    wrongs.discard(ans)
    while len(wrongs) < 3:
        wrongs.add(f"{rng.randint(1,total-1)}/{total}")
        wrongs.discard(ans)
    return mc(rng, "Probability (non-calculator)", 2,
               f"A bag contains {red} red and {blue} blue marbles. What is the probability of picking a red "
               f"marble, written as a fraction in simplest form?", ans, list(wrongs)[:3],
               f"{red} red out of {total} total marbles simplifies to {ans}.")


def n_percentage(rng):
    price = rng.choice([20, 40, 50, 60, 80, 100, 120, 150, 200])
    pct = rng.choice([10, 20, 25, 50])
    discount = price * pct // 100
    sale = price - discount
    wrongs_v = numeric_distractors(rng, sale, [discount, -discount, pct, -pct, 5])
    return mc(rng, "Percentages (calculator)", 2,
               f"A jacket originally priced at ${price} is on sale for {pct}% off. What is the sale price?",
               f"${sale}", [f"${w}" for w in wrongs_v],
               f"{pct}% of ${price} is ${discount}, so the sale price is ${price} - ${discount} = ${sale}.")


def n_rate(rng):
    speed = rng.randint(40, 100)
    hours = rng.randint(2, 6)
    distance = speed * hours
    wrongs_v = numeric_distractors(rng, speed, [hours, -hours, 10, -10, 5])
    return mc(rng, "Rates (calculator)", 2,
               f"A car travels {distance} km in {hours} hours. What is its average speed in km/h?",
               str(speed), [str(w) for w in wrongs_v],
               f"{distance} ÷ {hours} = {speed} km/h.")


def n_geometry_area_calc(rng):
    length, width = rng.randint(5, 25), rng.randint(4, 20)
    area = length * width
    wrongs_v = numeric_distractors(rng, area, [length, -length, width, -width, 2 * (length + width)])
    return mc(rng, "Geometry (calculator)", 2, f"A rectangle has a length of {length} cm and a width of "
               f"{width} cm. What is its area?", f"{area} cm²", [f"{w} cm²" for w in wrongs_v],
               f"Area of a rectangle = length x width = {length} x {width} = {area} cm².")


def n_simplify_expr(rng):
    a, b, c = rng.randint(2, 6), rng.randint(1, 9), rng.randint(1, 5)
    ans_coeff = a - c
    prompt = f"Simplify: {a}(x + {b}) - {c}x"
    ans = f"{ans_coeff}x + {a*b}" if ans_coeff != 1 else f"x + {a*b}"
    wrongs = [f"{ans_coeff+1}x + {a*b}", f"{ans_coeff}x + {a*b+b}", f"{a+c}x + {a*b}"]
    return mc(rng, "Algebra (non-calculator)", 2, prompt, ans, wrongs,
               f"{a}(x + {b}) = {a}x + {a*b}. Then {a}x - {c}x = {ans_coeff}x, giving {ans}.")


def n_integer_ops(rng):
    a = rng.randint(-20, 20)
    b = rng.randint(-20, 20)
    while b == 0:
        b = rng.randint(-20, 20)
    op = rng.choice(["+", "-"])
    ans = a + b if op == "+" else a - b
    wrongs_v = numeric_distractors(rng, ans, [1, -1, 2 * b, -2 * b, 10, -10], min_val=-100)
    item = mc(rng, "Integers (non-calculator)", 2, f"What is {a} {op} {b}?", str(ans), [str(w) for w in wrongs_v],
              f"{a} {op} {b} = {ans}.")
    item["_svg"] = svg.number_line_svg([a, b])
    return item


def n_coordinate_translation(rng):
    x, y = rng.randint(-6, 6), rng.randint(-6, 6)
    dx, dy = rng.randint(-6, 6), rng.randint(-6, 6)
    while dx == 0 and dy == 0:
        dx, dy = rng.randint(-6, 6), rng.randint(-6, 6)
    nx, ny = x + dx, y + dy
    dir_x = "right" if dx >= 0 else "left"
    dir_y = "up" if dy >= 0 else "down"
    correct = f"({nx}, {ny})"
    wrong_pts = {(x + dx, y), (x, y + dy), (x - dx, y - dy), (nx, y)}
    wrong_pts.discard((nx, ny))
    wrongs = [f"({wx}, {wy})" for wx, wy in list(wrong_pts)[:3]]
    while len(wrongs) < 3:
        cand = f"({nx + rng.choice([1,-1,2])}, {ny + rng.choice([1,-1,2])})"
        if cand not in wrongs and cand != correct:
            wrongs.append(cand)
    item = mc(rng, "Coordinate geometry (non-calculator)", 2,
              f"Point A is at ({x}, {y}). It is translated {abs(dx)} units {dir_x} and {abs(dy)} units {dir_y}. "
              f"What are the coordinates of the translated point?",
              correct, wrongs[:3],
              f"({x} {'+' if dx>=0 else '-'} {abs(dx)}, {y} {'+' if dy>=0 else '-'} {abs(dy)}) = ({nx}, {ny}).")
    item["_svg"] = svg.coordinate_point_svg(x, y, note=f"{abs(dx)} {dir_x}, {abs(dy)} {dir_y}")
    return item


def n_experimental_probability(rng):
    from math import gcd
    trials = rng.choice([20, 25, 40, 50, 60, 80, 100])
    successes = rng.randint(2, trials - 2)
    g = gcd(successes, trials)
    num, den = successes // g, trials // g
    ans = f"{num}/{den}"
    wrongs = {f"{successes}/{trials}", f"{trials - successes}/{trials}"}
    wrongs.discard(ans)
    while len(wrongs) < 3:
        cand = f"{rng.randint(1, den-1) if den > 1 else 1}/{den + rng.choice([1, -1, 2])}"
        wrongs.add(cand)
    wrongs.discard(ans)
    return mc(rng, "Probability (calculator)", 2,
              f"In an experiment, a spinner landed on blue {successes} times out of {trials} spins. "
              f"What is the experimental probability of landing on blue, written as a fraction in simplest form?",
              ans, list(wrongs)[:3],
              f"{successes} out of {trials} simplifies to {ans}.")


N_PATTERNS_Y7 = [n_linear_eq, n_ratio, n_probability, n_percentage, n_rate,
                  n_geometry_area_calc, n_simplify_expr, n_mean,
                  n_integer_ops, n_coordinate_translation, n_experimental_probability]


def n_pythagoras(rng):
    triples = [(3, 4, 5), (6, 8, 10), (5, 12, 13), (8, 15, 17), (9, 12, 15), (7, 24, 25), (12, 16, 20)]
    a, b, c = rng.choice(triples)
    wrongs_v = numeric_distractors(rng, c, [1, -1, a - b if a != b else 2, b - a if a != b else -2, 2])
    return mc(rng, "Geometry (non-calculator)", 3,
               f"A right-angled triangle has legs of {a} cm and {b} cm. What is the length of the hypotenuse?",
               f"{c} cm", [f"{w} cm" for w in wrongs_v],
               f"By the Pythagorean theorem, hypotenuse² = {a}² + {b}² = {c*c}, "
               f"so hypotenuse = {c} cm.")


def n_algebra_solve(rng):
    x = rng.randint(2, 20)
    a = rng.randint(2, 6)
    b = rng.randint(1, 10)
    c = a * (x - b) if rng.random() < 0.5 else None
    if c is not None:
        prompt = f"If {a}(x - {b}) = {c}, what is the value of x?"
        explanation = (f"Divide both sides by {a} to get x - {b} = {c // a}, "
                        f"then add {b} to get x = {x}.")
    else:
        c = a * x + b
        prompt = f"Solve for x: {a}x + {b} = {c}"
        explanation = f"Subtract {b} from both sides to get {a}x = {c-b}, then divide by {a} to get x = {x}."
    wrongs_v = numeric_distractors(rng, x, [1, -1, 2, -2, b], min_val=1)
    return mc(rng, "Algebra (non-calculator)", 3, prompt, str(x), [str(w) for w in wrongs_v], explanation)


def n_stats_new_mean(rng):
    n = rng.randint(15, 30)
    mean = rng.randint(50, 90)
    total = n * mean
    new_score = rng.randint(mean - 20, mean + 20)
    new_total = total + new_score
    denom = n + 1

    def fmt_tenths(t):
        return str(t // 10) if t % 10 == 0 else f"{t / 10:.1f}"

    new_mean_tenths = round(new_total * 10 / denom)
    new_mean_str = fmt_tenths(new_mean_tenths)

    seen_tenths = {new_mean_tenths}
    wrongs = []
    for delta in [mean * 10 - new_mean_tenths, 10, -10, 5, -5, 20, -20, 15, -15, 25]:
        t = new_mean_tenths + delta
        if t > 0 and t not in seen_tenths:
            seen_tenths.add(t)
            wrongs.append(fmt_tenths(t))
        if len(wrongs) == 3:
            break

    return mc(rng, "Statistics (calculator)", 3,
               f"A class of {n} students has a mean test score of {mean}. If one more student joins with a "
               f"score of {new_score}, what is the new mean (to 1 decimal place)?", new_mean_str, wrongs[:3],
               f"New total = ({mean} x {n}) + {new_score} = {new_total}. "
               f"New mean = {new_total} ÷ {n+1} = {new_mean_str}.")


def n_expand_binomial(rng):
    a, b = rng.randint(1, 9), rng.randint(-9, -1)
    prompt = f"Expand and simplify: (x + {a})(x {'- ' + str(-b) if b < 0 else '+ ' + str(b)})"
    coeff = a + b
    const = a * b
    def fmt(coeff, const):
        c_part = f"{'+ ' if coeff >= 0 else '- '}{abs(coeff)}x" if coeff != 0 else ""
        k_part = f"{'+ ' if const >= 0 else '- '}{abs(const)}"
        return f"x² {c_part} {k_part}".replace("  ", " ")
    ans = fmt(coeff, const)
    wrongs = [fmt(coeff + 2, const), fmt(coeff, const + a), fmt(coeff - 2, const)]
    return mc(rng, "Algebra (non-calculator)", 3, prompt, ans, wrongs,
               f"(x + {a})(x + {b}) = x² + {a}x + {b}x + {a*b} = {ans}.")


def n_percentage_compound(rng):
    principal = rng.choice([1000, 1500, 2000, 2500, 3000, 5000])
    rate = rng.choice([2, 3, 4, 5, 6, 8])
    years = 2
    final = round(principal * (1 + rate / 100) ** years)
    wrongs_v = numeric_distractors(rng, final, [principal * rate // 100, -(principal * rate // 100), 10, -10, 25])
    return mc(rng, "Percentages (calculator)", 3,
               f"${principal} is invested at {rate}% p.a. compound interest. What is the value after "
               f"{years} years, to the nearest dollar?", f"${final}", [f"${w}" for w in wrongs_v],
               f"${principal} x (1 + {rate}/100)^{years} = ${final}, since each year the balance grows by "
               f"{rate}% on the previous year's total.")


def n_simultaneous(rng):
    x = rng.randint(2, 15)
    y = rng.randint(1, 15)
    s = x + y
    d = x - y
    wrongs_v = numeric_distractors(rng, x, [1, -1, y, -y, 2], min_val=0)
    return mc(rng, "Simultaneous equations (non-calculator)", 3,
               f"Solve: x + y = {s} and x - y = {d}. What is the value of x?", str(x),
               [str(w) for w in wrongs_v],
               f"Adding both equations gives 2x = {s+d}, so x = {x}.")


def n_trig(rng):
    import math
    angle_opts = [(30, 0.5), (45, math.sqrt(2)/2), (60, math.sqrt(3)/2)]
    angle, sin_val = rng.choice(angle_opts)
    hyp = rng.choice([8, 10, 12, 16, 20])
    opp = round(hyp * sin_val, 1)
    wrongs_v = [round(opp + d, 1) for d in [1.0, -1.0, 2.0]]
    wrongs = [f"{w:.1f} cm" for w in wrongs_v if abs(w - opp) > 0.05]
    while len(wrongs) < 3:
        w = round(opp + rng.choice([1.5, -1.5, 3.0]), 1)
        wrongs.append(f"{w:.1f} cm")
    return mc(rng, "Trigonometry (calculator)", 3,
               f"In a right-angled triangle, one angle is {angle} degrees and the hypotenuse is {hyp} cm. "
               f"What is the length of the side opposite the {angle} degree angle, to 1 decimal place?",
               f"{opp:.1f} cm", wrongs[:3],
               f"opposite = hypotenuse x sin({angle} degrees) = {hyp} x {sin_val:.3f} = {opp:.1f} cm.")


def n_similar_figures(rng):
    small_area = rng.randint(4, 25)
    scale = rng.choice([2, 3, 4, 5])
    large_area = small_area * scale * scale
    wrongs_v = numeric_distractors(rng, large_area, [small_area * scale, -small_area * scale, scale, -scale, small_area])
    item = mc(rng, "Geometry (calculator)", 3,
              f"Two similar rectangles have a scale factor of {scale}. The smaller rectangle has an area of "
              f"{small_area} cm². What is the area of the larger rectangle?",
              f"{large_area} cm²", [f"{w} cm²" for w in wrongs_v],
              f"Area scale factor = (scale factor)² = {scale}² = {scale*scale}. "
              f"{small_area} x {scale*scale} = {large_area} cm².")
    item["_svg"] = svg.similar_figures_svg(f"{small_area} cm²", scale)
    return item


def n_exponent_laws(rng):
    m, n = rng.randint(2, 8), rng.randint(2, 8)
    if rng.random() < 0.5:
        prompt = f"Simplify: a^{m} x a^{n}"
        ans_exp = m + n
        explanation = f"When multiplying powers with the same base, add the exponents: {m} + {n} = {ans_exp}."
        wrongs = {f"a^{m*n}", f"a^{ans_exp+1}", f"a^{abs(m-n)}"}
    else:
        prompt = f"Simplify: (a^{m})^{n}"
        ans_exp = m * n
        explanation = f"When raising a power to a power, multiply the exponents: {m} x {n} = {ans_exp}."
        wrongs = {f"a^{m+n}", f"a^{ans_exp+1}", f"a^{max(ans_exp-1, 1)}"}
    correct = f"a^{ans_exp}"
    wrongs.discard(correct)
    while len(wrongs) < 3:
        wrongs.add(f"a^{ans_exp + rng.choice([2, -2, 3])}")
        wrongs.discard(correct)
    return mc(rng, "Algebra (non-calculator)", 3, prompt, correct, list(wrongs)[:3], explanation)


def n_polynomial_perimeter(rng):
    a, b = rng.randint(1, 9), rng.randint(1, 9)
    length_expr, width_expr = f"(x + {a})", f"(x + {b})"
    const = 2 * (a + b)
    correct = f"4x + {const}"
    wrongs = {f"2x + {const}", f"4x + {a+b}", f"4x + {const+2}"}
    wrongs.discard(correct)
    while len(wrongs) < 3:
        wrongs.add(f"4x + {const + rng.choice([4, -4, 6])}")
        wrongs.discard(correct)
    item = mc(rng, "Algebra (non-calculator)", 3,
              f"A rectangle has side lengths of {length_expr} cm and {width_expr} cm. "
              f"Write an expression for its perimeter.",
              correct, list(wrongs)[:3],
              f"Perimeter = 2(length + width) = 2[(x+{a}) + (x+{b})] = 2(2x + {a+b}) = {correct}.")
    item["_svg"] = svg.rectangle_labeled_svg(f"{length_expr} cm", f"{width_expr} cm")
    return item


N_PATTERNS_Y9 = [n_pythagoras, n_algebra_solve, n_stats_new_mean, n_expand_binomial,
                  n_percentage_compound, n_simultaneous, n_trig, n_ratio,
                  n_similar_figures, n_exponent_laws, n_polynomial_perimeter]

N_PATTERNS = {3: N_PATTERNS_Y3, 5: N_PATTERNS_Y5, 7: N_PATTERNS_Y7, 9: N_PATTERNS_Y9}


# ------------------------------------------------------------------
# Language Conventions patterns
# ------------------------------------------------------------------

SPELLING_WORDS_Y3 = [
    ("Friend", ["Freind", "Frend", "Freand"]), ("Because", ["Becuase", "Becaus", "Beacause"]),
    ("Which", ["Wich", "Whitch", "Whic"]), ("Beautiful", ["Beutiful", "Beautifull", "Beatiful"]),
    ("Different", ["Diffrent", "Diferent", "Differant"]), ("People", ["Poeple", "Peaple", "Peopel"]),
    ("Little", ["Litle", "Littel", "Lital"]), ("Happen", ["Hapen", "Happan", "Happenn"]),
    ("Family", ["Famly", "Familly", "Famaly"]), ("Every", ["Evry", "Evrey", "Everry"]),
    ("School", ["Skool", "Schol", "Schooll"]), ("Morning", ["Mornin", "Mornig", "Morening"]),
    ("Colour", ["Colur", "Coulor", "Collor"]), ("Favourite", ["Favorit", "Favrite", "Favourit"]),
    ("Purple", ["Purpel", "Purpal", "Purpple"]), ("Special", ["Speshal", "Specail", "Speciall"]),
    ("Water", ["Watter", "Wather", "Watr"]), ("Animal", ["Aminal", "Animel", "Anamal"]),
    ("Answer", ["Anwser", "Answar", "Ansewer"]), ("August", ["Augest", "Agust", "Augost"]),
    ("Neighbour", ["Nieghbour", "Neighbor", "Neighbur"]), ("Sudden", ["Suddan", "Sudan", "Suden"]),
    ("Group", ["Groop", "Grup", "Groupe"]), ("Enough", ["Enuf", "Enouph", "Enugh"]),
]
SPELLING_WORDS_Y5 = [
    ("Receive", ["Recieve", "Receve", "Receeve"]), ("Separate", ["Seperate", "Separete", "Seprate"]),
    ("Necessary", ["Neccessary", "Necesary", "Neccesary"]), ("Believe", ["Beleive", "Belive", "Beleve"]),
    ("Environment", ["Enviroment", "Envirnment", "Enviornment"]), ("Government", ["Goverment", "Governmant", "Govermant"]),
    ("Immediately", ["Imediately", "Immediatly", "Imediatley"]), ("Surprise", ["Suprise", "Surprize", "Surprice"]),
    ("Business", ["Buisness", "Busness", "Bussiness"]), ("Knowledge", ["Knowlege", "Knowledg", "Nowledge"]),
    ("February", ["Febuary", "Feburary", "Februrary"]), ("Occasion", ["Ocasion", "Occassion", "Ocassion"]),
    ("Vegetable", ["Vegtable", "Vegetible", "Veggetable"]), ("Character", ["Charecter", "Charactar", "Caracter"]),
    ("Weird", ["Wierd", "Weerd", "Wiered"]), ("Guard", ["Gaurd", "Gard", "Guardd"]),
    ("Height", ["Heigth", "Hight", "Heighth"]), ("Library", ["Libary", "Liberry", "Librery"]),
    ("Mystery", ["Mistery", "Misterey", "Mysterey"]), ("Ordinary", ["Ordinery", "Ordinarry", "Ordinay"]),
    ("Rhyme", ["Rime", "Ryhme", "Rhym"]), ("Twelfth", ["Twelth", "Twelfeth", "Twelvth"]),
]
SPELLING_WORDS_Y7 = [
    ("Definitely", ["Definately", "Definitly", "Defenitely"]), ("Occurrence", ["Occurence", "Occurrance", "Occurrense"]),
    ("Rhythm", ["Rythem", "Rhythem", "Rithm"]), ("Conscience", ["Concience", "Consience", "Conscious"]),
    ("Embarrass", ["Embarass", "Embarras", "Embaras"]), ("Privilege", ["Priviledge", "Privelege", "Priviledg"]),
    ("Maintenance", ["Maintainance", "Maintenence", "Maintanance"]), ("Committee", ["Comittee", "Commitee", "Committe"]),
    ("Existence", ["Existance", "Existense", "Excistence"]), ("Independent", ["Independant", "Indipendent", "Independint"]),
    ("Recommend", ["Recomend", "Reccommend", "Reccomend"]), ("Persistent", ["Persistant", "Presistent", "Persisten"]),
    ("Accommodate", ["Acommodate", "Accomodate", "Accommadate"]), ("Achievement", ["Acheivement", "Achievment", "Acheivment"]),
    ("Correspondence", ["Correspondance", "Corespondence", "Correspondense"]), ("Fluorescent", ["Florescent", "Fluoresent", "Flourescent"]),
    ("Guarantee", ["Garantee", "Guarentee", "Guaranttee"]), ("Harass", ["Harrass", "Haras", "Harres"]),
    ("Millennium", ["Milennium", "Millenium", "Milenium"]), ("Noticeable", ["Noticable", "Noticeble", "Notiseable"]),
    ("Parallel", ["Paralel", "Parrallel", "Paralell"]), ("Vacuum", ["Vaccuum", "Vaccum", "Vacume"]),
]
SPELLING_WORDS_Y9 = [
    ("Occurrence", ["Occurence", "Occurrance", "Occurrense"]), ("Bureaucracy", ["Beaurocracy", "Bureacracy", "Buerocracy"]),
    ("Consensus", ["Concensus", "Consensis", "Concencus"]), ("Millennium", ["Milennium", "Millenium", "Milenium"]),
    ("Questionnaire", ["Questionaire", "Questionnare", "Quiestionnaire"]), ("Liaise", ["Liase", "Liaze", "Leiase"]),
    ("Entrepreneur", ["Entreprenuer", "Enterpreneur", "Entreprener"]), ("Idiosyncrasy", ["Idiosyncracy", "Idiosincrasy", "Idyosyncrasy"]),
    ("Pronunciation", ["Pronounciation", "Pronunciacion", "Pronuntiation"]), ("Supersede", ["Supercede", "Superceed", "Superseed"]),
    ("Ecstasy", ["Ecstacy", "Extasy", "Ecstassy"]), ("Vacuum", ["Vaccuum", "Vaccum", "Vacume"]),
    ("Acquiesce", ["Aquiesce", "Acquiess", "Aquiess"]), ("Camaraderie", ["Camraderie", "Comraderie", "Camaraderi"]),
    ("Discrepancy", ["Discrepency", "Descrepancy", "Discrepensy"]), ("Exacerbate", ["Exasperbate", "Exacurbate", "Exacerbait"]),
    ("Hierarchy", ["Heirarchy", "Hierachy", "Hyerarchy"]), ("Innuendo", ["Inuendo", "Innuendoe", "Inneundo"]),
    ("Nauseous", ["Nauseus", "Nautious", "Nauseious"]), ("Perseverance", ["Perseverence", "Persaverance", "Perseverense"]),
    ("Renaissance", ["Renaisance", "Rennaisance", "Renaissence"]), ("Ubiquitous", ["Ubiquitious", "Ubiqutous", "Ubiquituous"]),
]

GRAMMAR_ITEMS_Y3 = [
    ("The dog wagged {poss} tail.", "its", ["it's", "its'", "their"], "'{correct}' (no apostrophe) shows possession; 'it's' means 'it is'."),
    ("{name} and I went to the park.", "He", ["Him", "Me", "Us"], "Subject pronouns like 'he' are used as the subject of a sentence."),
    ("{name} is the {animal} that {name2} owns.", "This", ["Them", "Those", "Us"], "'This' correctly points to a single, nearby thing."),
]
GRAMMAR_ITEMS_Y5 = [
    ("After the game, {name} went home.", "After the game, {name} went home.",
     ["After the game {name}, went home.", "After, the game {name} went home.", "After the game {name} went, home."],
     "A comma follows an introductory phrase before the main clause begins."),
    ("{name} and {name2} {verb} their homework before dinner.", "finished",
     ["finish", "finishes", "finishing"], "Past tense is needed since the action already happened."),
]
GRAMMAR_ITEMS_Y7 = [
    ("Each of the students {verb} to submit an assignment.", "has",
     ["have", "having", "had to"], "'Each' is singular, so it takes the singular verb 'has', even though the noun after it is plural."),
    ("The {animal}'s bone was buried in the yard.", "The {animal}'s bone was buried in the yard.",
     ["The {animal}s' bone was buried in the yard.", "The {animal}s bone's was buried in the yard.", "The {animal} bones' was buried in the yard."],
     "For one animal, the possessive apostrophe goes before the 's'."),
]
GRAMMAR_ITEMS_Y9 = [
    ("Although it was raining, {name} continued playing.", "Although it was raining",
     ["{name} continued playing", "it was raining", "continued playing"],
     "This subordinate clause cannot stand alone and depends on the main clause."),
    ("I love reading; I especially love {topic}.", "I love reading; I especially love {topic}.",
     ["I love reading; especially {topic}.", "I love reading, I especially love; {topic}.", "I love; reading {topic}."],
     "A semicolon joins two independent clauses that are closely related in meaning."),
]


def lc_spelling(rng, words):
    correct, wrong_spellings = rng.choice(words)
    phrasing = rng.choice(["Which word is spelled correctly?", "Choose the correctly spelled word.",
                            "Identify the correct spelling."])
    return mc(rng, "Spelling", 1, phrasing, correct, list(wrong_spellings),
               f"'{correct}' is the correct spelling.")


def lc_apostrophe(rng):
    subject = rng.choice(["dog", "cat", "student", "teacher", "bird", "athlete"])
    correct = f"The {subject}'s bag was left on the desk."
    wrongs = [f"The {subject}s' bag was left on the desk.", f"The {subject}s bag's was left on the desk.",
              f"The {subject} bags' was left on the desk."]
    return mc(rng, "Punctuation", 2, "Which sentence uses an apostrophe correctly?", correct, wrongs,
               "For a single owner, the possessive apostrophe goes before the 's'.")


def lc_question_mark(rng):
    name = rng.choice(NAMES)
    correct = f"What time does {name} arrive?"
    wrongs = [f"{name} arrives at three.", "Please be on time.", f"{name} is late again."]
    return mc(rng, "Punctuation", 1, "Which sentence needs a question mark?", correct, wrongs,
               "A direct question requires a question mark at the end.")


def lc_homophone(rng):
    pairs = [("wear", ["where", "ware", "were"], "I need to ___ my shoes before we leave."),
             ("there", ["their", "they're", "then"], "Put the bag over ___, next to the door."),
             ("your", ["you're", "yore", "yaw"], "Is this ___ jacket on the chair?"),
             ("its", ["it's", "its'", "his"], "The bird built ___ nest in the tree."),
             ("to", ["too", "two", "toe"], "We are going ___ the shop after school.")]
    correct, wrongs, sentence = rng.choice(pairs)
    return mc(rng, "Homophones", 2, f"Choose the correct word: '{sentence}'", correct, wrongs,
               f"'{correct}' is the word that fits the meaning of the sentence.")


def lc_sentence_type(rng):
    name, name2 = rng.sample(NAMES, 2)
    correct = f"{name} studied hard, and {name2} passed the test."
    wrongs = [f"{name} studied hard.", "Studying hard for the test.", f"{name} studied hard for the test yesterday."]
    return mc(rng, "Sentence types", 2, "Which sentence is a compound sentence?", correct, wrongs,
               "A compound sentence joins two independent clauses with a coordinating conjunction such as 'and'.")


def lc_word_class(rng):
    verbs = ["swerved", "stopped", "accelerated", "braked"]
    verb = rng.choice(verbs)
    correct = "quickly"
    wrongs = ["moving", "car", verb]
    return mc(rng, "Word class", 2, f"In the sentence 'The quickly moving car {verb},' which word is the adverb?",
               correct, wrongs, "'Quickly' describes how the car was moving, making it an adverb.")


MODALITY_ITEMS = [
    ("Will", ["Might", "Could", "May"]),
    ("Must", ["Should", "Could", "Might"]),
    ("Always", ["Usually", "Often", "Sometimes"]),
    ("Definitely", ["Possibly", "Perhaps", "Maybe"]),
    ("Certainly", ["Probably", "Presumably", "Conceivably"]),
    ("Guaranteed", ["Likely", "Probable", "Feasible"]),
]


def lc_modality(rng):
    correct, wrongs = rng.choice(MODALITY_ITEMS)
    return mc(rng, "Modality", 3, "Which word shows the highest level of certainty?", correct, wrongs,
               f"'{correct}' expresses certainty, while the other options only express possibility or likelihood.")


def lc_clause(rng):
    name = rng.choice(NAMES)
    correct = "Although it was raining"
    wrongs = [f"{name} continued playing", "it was raining", "continued playing"]
    return mc(rng, "Clauses", 3, f"Identify the subordinate clause: 'Although it was raining, {name} "
               "continued playing.'", correct, wrongs,
               "This clause cannot stand alone and depends on the main clause for its full meaning.")


def lc_verb_tense_y3(rng):
    name = rng.choice(NAMES)
    correct = f"{name} ran to school."
    wrongs = [f"{name} runs to school.", f"{name} will run to school.", f"{name} is running to school."]
    return mc(rng, "Verb tense", 1, "Which sentence is written in the past tense?", correct, wrongs,
               "The verb form shows the action already happened.")


def lc_noun_type(rng):
    place = rng.choice(["Sydney", "Melbourne", "Perth", "Brisbane"])
    correct = "dog"
    wrongs = [place, "Monday", "Australia"]
    return mc(rng, "Nouns", 1, "Which word is a common noun?", correct, wrongs,
               "A common noun names a general person, place or thing and does not start with a capital letter.")


CONTRACTION_ITEMS = [
    ("It's raining outside.", ["Its raining outside.", "Its' raining outside.", "It is'nt raining outside."], "It's", "it is"),
    ("They're playing in the yard.", ["Their playing in the yard.", "There playing in the yard.", "Theyre playing in the yard."], "They're", "they are"),
    ("You're going to love this book.", ["Your going to love this book.", "Youre going to love this book.", "Yore going to love this book."], "You're", "you are"),
    ("We're leaving after lunch.", ["Were leaving after lunch.", "Wer'e leaving after lunch.", "Weer leaving after lunch."], "We're", "we are"),
    ("I can't find my shoes.", ["I cant find my shoes.", "I ca'nt find my shoes.", "I cann't find my shoes."], "Can't", "cannot"),
    ("She isn't coming to the party.", ["She is'nt coming to the party.", "She isnt coming to the party.", "She isn't' coming to the party."], "Isn't", "is not"),
    ("It's my turn to choose the game.", ["Its my turn to choose the game.", "Its' my turn to choose the game.", "It is'nt my turn to choose the game."], "It's", "it is"),
    ("They're always on time.", ["Their always on time.", "There always on time.", "Theyre always on time."], "They're", "they are"),
]


def lc_contraction(rng):
    correct, wrongs, word, meaning = rng.choice(CONTRACTION_ITEMS)
    return mc(rng, "Punctuation", 1, "Choose the correct sentence.", correct, wrongs,
               f"'{word}' is the contraction of '{meaning}'; an apostrophe replaces the missing letter(s).")


def lc_agreement(rng):
    correct = "Each of the students has to submit an assignment."
    wrongs = ["Each of the students have to submit an assignment.",
              "Each of the student has to submit an assignment.",
              "Each of the students has to submitted an assignment."]
    return mc(rng, "Grammar", 2, "Choose the correct sentence.", correct, wrongs,
               "'Each' is singular, so it takes the singular verb 'has', even though 'students' is plural.")


def lc_comma(rng):
    name = rng.choice(NAMES)
    correct = f"After the game, {name} went home."
    wrongs = [f"After the game {name}, went home.", f"After, the game {name} went home.",
              f"After the game {name} went, home."]
    return mc(rng, "Sentence structure", 2, "Which sentence uses a comma correctly?", correct, wrongs,
               "A comma follows an introductory phrase before the main clause begins.")


def lc_colon(rng):
    topic1, topic2, topic3 = rng.sample(["maths", "art", "science", "music", "history", "drama"], 3)
    correct = f"I have three favourite subjects: {topic1}, {topic2} and {topic3}."
    wrongs = [f"I have three favourite subjects, {topic1}, {topic2} and {topic3}.",
              f"I have three favourite subjects; {topic1}, {topic2} and {topic3}.",
              f"I have three favourite subjects {topic1}, {topic2} and {topic3}."]
    return mc(rng, "Punctuation", 3, "Choose the correctly punctuated sentence.", correct, wrongs,
               "A colon introduces a list after an independent clause.")


LC_PATTERNS_Y3 = [lambda rng: lc_spelling(rng, SPELLING_WORDS_Y3), lc_contraction, lc_noun_type,
                    lc_verb_tense_y3, lc_question_mark]
LC_PATTERNS_Y5 = [lambda rng: lc_spelling(rng, SPELLING_WORDS_Y5), lc_comma, lc_homophone, lc_question_mark,
                    lc_agreement]
LC_PATTERNS_Y7 = [lambda rng: lc_spelling(rng, SPELLING_WORDS_Y7), lc_apostrophe, lc_sentence_type,
                    lc_word_class, lc_agreement]
LC_PATTERNS_Y9 = [lambda rng: lc_spelling(rng, SPELLING_WORDS_Y9), lc_clause, lc_modality, lc_colon,
                    lc_sentence_type]

LC_PATTERNS = {3: LC_PATTERNS_Y3, 5: LC_PATTERNS_Y5, 7: LC_PATTERNS_Y7, 9: LC_PATTERNS_Y9}


# ------------------------------------------------------------------
# Reading patterns
# ------------------------------------------------------------------

def r_why(rng, difficulty):
    name = rng.choice(NAMES)
    event, reason = rng.choice(REASON_EVENTS)
    pool = [r for _, r in REASON_EVENTS if r != reason]
    wrongs = rng.sample(pool, 3)
    prompt = f"{name} {event}. Why did {name} do this?"
    return mc(rng, "Comprehension", difficulty, prompt, reason, wrongs,
               f"The sentence directly states {name} {event} {reason}.")


def r_inference(rng, difficulty):
    name = rng.choice(NAMES)
    action, emotion, distractors = rng.choice(INFERENCE_ITEMS)
    prompt = (f"What can you infer about {name}'s mood from the sentence "
               f"'{name} {action}'?")
    return mc(rng, "Inference", difficulty, prompt, emotion, distractors,
               f"The description of {name} {action} suggests the character felt {emotion.lower()}.")


def r_text_type(rng, difficulty):
    example, correct = rng.choice(TEXT_TYPE_ITEMS)
    pool = [t for _, t in TEXT_TYPE_ITEMS if t != correct]
    wrongs = list(dict.fromkeys(pool))
    rng.shuffle(wrongs)
    prompt = f"{example[0].upper()}{example[1:]} is an example of which type of text?"
    return mc(rng, "Text purpose", difficulty, prompt, correct, wrongs[:3],
               f"This text is written to {'give facts and practical details' if correct == 'Informative' else 'tell a story' if correct == 'Narrative' else 'convince the reader' if correct == 'Persuasive' else 'create imagery and feeling'}, which makes it {correct.lower()}.")


def r_main_idea(rng, difficulty):
    topic = rng.choice(TOPICS)
    place = rng.choice(PLACES)
    correct = f"There are practical ways to make progress on {topic}"
    wrongs = [f"{topic.capitalize()} is not important", f"Only adults can help with {topic}",
               f"{place.capitalize()} should be closed"]
    prompt = (f"An article describes three different ways people can take action on {topic}. "
               f"What is most likely the main idea of the article?")
    return mc(rng, "Main idea", difficulty, prompt, correct, wrongs,
               "The article focuses on practical actions, not just stating the problem exists.")


def r_sequencing(rng, difficulty):
    correct = rng.choice(["First", "Next", "Finally"])
    wrongs_pool = [w for w in ["Blue", "Happy", "Under", "Quietly", "Yesterday"] if w != correct]
    wrongs = rng.sample(wrongs_pool, 3)
    prompt = "Which word would you expect to find at the start of a set of instructions?" if correct == "First" \
        else f"Which word signals a step later in a sequence of instructions?"
    return mc(rng, "Sequencing", difficulty, prompt, correct, wrongs,
               f"'{correct}' is a sequencing word that helps order steps in a process.")


def r_vocabulary(rng, difficulty):
    items = [
        ("enormous", "very big", ["very small", "very loud", "very fast"], "towering over the other animals"),
        ("exhausted", "very tired", ["very happy", "very hungry", "very loud"], "after running the whole race"),
        ("timid", "shy or nervous", ["bold and loud", "very fast", "extremely tall"], "and hid behind the door"),
        ("collapse", "fall down", ["grow taller", "shine brightly", "move sideways"], "and might give way at any moment"),
        ("meandered", "wandered slowly with no clear direction", ["moved in a straight line quickly", "stopped completely", "grew louder"], "through the quiet countryside"),
        ("littered", "scattered carelessly", ["carefully organised", "completely absent", "brightly coloured"], "with empty promises"),
    ]
    word, meaning, wrongs, context = rng.choice(items)
    name = rng.choice(NAMES)
    prompt = f"{name} noticed the {word} {context}. What does '{word}' mean in this sentence?"
    return mc(rng, "Vocabulary", difficulty, prompt, meaning, wrongs,
               f"'{word.capitalize()}' means {meaning}.")


def r_technique(rng, difficulty, level):
    topic = rng.choice(TOPICS)
    if level <= 5:
        prompt = (f"A persuasive text about {topic} states: 'Every small choice you make today shapes a "
                   f"better tomorrow.' Which technique is the author mainly using?")
        correct = "Emotive language"
        wrongs = ["Statistical evidence", "A formal citation", "A rhetorical question"]
        explanation = "The sentence appeals to feelings and values rather than presenting facts or data."
    else:
        prompt = (f"An opinion piece about {topic} states: 'Studies show that most people support this "
                   f"change, and the evidence is overwhelming.' Which technique is the author mainly using?")
        correct = "Statistical/evidence-based appeal"
        wrongs = ["Emotive language", "A rhetorical question", "An anecdote"]
        explanation = "The sentence relies on claimed evidence and data to build credibility, rather than emotion."
    return mc(rng, "Persuasive technique", difficulty, prompt, correct, wrongs, explanation)


def r_authors_purpose(rng, difficulty):
    topic = rng.choice(TOPICS)
    prompt = f"An opinion column arguing in favour of action on {topic} is mainly written to:"
    correct = "Persuade readers to support a change"
    wrongs = ["Entertain readers with a story", "Inform readers of a scientific fact", "Describe a place in detail"]
    return mc(rng, "Author's purpose", difficulty, prompt, correct, wrongs,
               "An opinion column argues a position, aiming to convince readers to agree.")


def r_bias(rng, difficulty):
    topic = rng.choice(TOPICS)
    prompt = (f"A news article about {topic} only quotes people who support one side of the issue. "
               "This is an example of:")
    correct = "Selective bias"
    wrongs = ["Balanced reporting", "Objective analysis", "Chronological structure"]
    return mc(rng, "Bias", difficulty, prompt, correct, wrongs,
               "Only including one side's voices while omitting opposing views shows selective bias.")


R_PATTERNS_Y3 = [lambda rng: r_why(rng, 1), lambda rng: r_inference(rng, 1), lambda rng: r_text_type(rng, 1),
                   lambda rng: r_vocabulary(rng, 1), lambda rng: r_sequencing(rng, 1)]
R_PATTERNS_Y5 = [lambda rng: r_why(rng, 1), lambda rng: r_inference(rng, 2), lambda rng: r_main_idea(rng, 2),
                   lambda rng: r_vocabulary(rng, 2), lambda rng: r_text_type(rng, 1)]
R_PATTERNS_Y7 = [lambda rng: r_inference(rng, 2), lambda rng: r_technique(rng, 2, 7),
                   lambda rng: r_authors_purpose(rng, 2), lambda rng: r_main_idea(rng, 2),
                   lambda rng: r_vocabulary(rng, 2)]
R_PATTERNS_Y9 = [lambda rng: r_bias(rng, 3), lambda rng: r_technique(rng, 3, 9),
                   lambda rng: r_authors_purpose(rng, 3), lambda rng: r_vocabulary(rng, 3),
                   lambda rng: r_inference(rng, 3)]

R_PATTERNS = {3: R_PATTERNS_Y3, 5: R_PATTERNS_Y5, 7: R_PATTERNS_Y7, 9: R_PATTERNS_Y9}


# ------------------------------------------------------------------
# Writing patterns
# ------------------------------------------------------------------

def w_prompt(rng, difficulty, genres):
    genre, template = rng.choice(genres)
    topic = rng.choice(WRITING_TOPICS)
    prompt = template.format(topic=topic)
    return open_response(genre, difficulty, prompt,
                           "Writing tasks are scored on structure, ideas, language and grammar, not a single correct answer.")


W_PATTERNS_Y3 = [lambda rng: w_prompt(rng, 1, WRITING_GENRES[:3])]
W_PATTERNS_Y5 = [lambda rng: w_prompt(rng, 2, WRITING_GENRES[:4])]
W_PATTERNS_Y7 = [lambda rng: w_prompt(rng, 2, WRITING_GENRES)]
W_PATTERNS_Y9 = [lambda rng: w_prompt(rng, 3, WRITING_GENRES)]

W_PATTERNS = {3: W_PATTERNS_Y3, 5: W_PATTERNS_Y5, 7: W_PATTERNS_Y7, 9: W_PATTERNS_Y9}

DOMAIN_PATTERNS = {"N": N_PATTERNS, "LC": LC_PATTERNS, "R": R_PATTERNS, "W": W_PATTERNS}


# ------------------------------------------------------------------
# Generation driver
# ------------------------------------------------------------------

def generate_domain_questions(rng, level, domain_code, target_n):
    patterns = DOMAIN_PATTERNS[domain_code][level]
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
        key = (item["prompt"], item["correct"], tuple(item["options"]) if item["options"] else None)
        if key in seen:
            continue
        seen.add(key)
        results.append(item)
    return results


def get_domain_map(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT domain_id, code FROM dbo.domains")
    return {code: domain_id for domain_id, code in cursor.fetchall()}


def bucket_count(conn, year_level, content_year):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM dbo.questions WHERE year_level_id = ? AND content_year = ?",
        year_level, content_year,
    )
    return cursor.fetchone()[0]


DOMAIN_TITLES = {"N": "Numeracy practice", "LC": "Language conventions", "R": "Reading practice", "W": "Writing prompts"}


def insert_bucket(conn, domain_map, year_level, content_year, domain_code, items):
    cursor = conn.cursor()

    rows = []
    for item in items:
        opts = item["options"] or [None, None, None, None]
        while len(opts) < 4:
            opts.append(None)
        rows.append((
            year_level, domain_map[domain_code], item["strand"], item["difficulty"],
            item["question_type"], item["prompt"], opts[0], opts[1], opts[2], opts[3],
            item["correct"], item["explanation"], content_year,
        ))

    insert_sql = """
        INSERT INTO dbo.questions
            (year_level_id, domain_id, strand, difficulty, question_type,
             prompt, option_a, option_b, option_c, option_d,
             correct_answer, explanation, status, content_year)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'published', ?)
    """
    cursor.executemany(insert_sql, rows)
    conn.commit()

    cursor.execute(
        "SELECT question_id FROM dbo.questions WHERE year_level_id = ? AND domain_id = ? AND content_year = ? "
        "ORDER BY question_id DESC LIMIT ?",
        year_level, domain_map[domain_code], content_year, len(rows),
    )
    ids = [r[0] for r in cursor.fetchall()]
    ids.reverse()
    return ids


def create_tests(conn, domain_map, year_level, content_year, domain_code, question_ids, chunk_size=20):
    cursor = conn.cursor()
    base_title = DOMAIN_TITLES[domain_code]
    for set_no, start in enumerate(range(0, len(question_ids), chunk_size), start=1):
        chunk = question_ids[start:start + chunk_size]
        title = f"{base_title} {content_year} - set {set_no}"
        cursor.execute(
            """
            INSERT INTO dbo.tests (year_level_id, domain_id, title, test_type, time_limit_mins, status, content_year)
            VALUES (?, ?, ?, 'practice', ?, 'published', ?)
            RETURNING test_id
            """,
            year_level, domain_map[domain_code], title, 20, content_year,
        )
        test_id = cursor.fetchone()[0]
        for seq, qid in enumerate(chunk, start=1):
            cursor.execute(
                "INSERT INTO dbo.test_questions (test_id, question_id, sequence_no) VALUES (?, ?, ?)",
                test_id, qid, seq,
            )
    conn.commit()


def main():
    conn = get_connection()
    domain_map = get_domain_map(conn)

    grand_total_q = 0
    grand_total_t = 0

    for content_year in EDITION_YEARS:
        for level in YEAR_LEVELS:
            existing = bucket_count(conn, level, content_year)
            if existing >= MIN_PER_BUCKET:
                print(f"Edition {content_year}, Year {level}: already has {existing} questions - skipping.")
                continue

            bucket_total = 0
            for domain_code, target_n in TARGET_PER_DOMAIN.items():
                dom_rng = random.Random(f"{content_year}-{level}-{domain_code}")
                items = generate_domain_questions(dom_rng, level, domain_code, target_n)
                qids = insert_bucket(conn, domain_map, level, content_year, domain_code, items)
                create_tests(conn, domain_map, level, content_year, domain_code, qids)
                bucket_total += len(items)
                grand_total_t += -(-len(qids) // 20)  # ceil division for test count

            grand_total_q += bucket_total
            print(f"Edition {content_year}, Year {level}: seeded {bucket_total} questions.")

    conn.close()
    print(f"Done. Total new questions: {grand_total_q}, total new tests: {grand_total_t}.")


if __name__ == "__main__":
    main()
