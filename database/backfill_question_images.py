"""
Attaches an SVG diagram (media_url) to every Numeracy question whose prompt
matches a visual-question pattern (shapes, clocks, coins, rectangles,
triangles, right triangles, bar charts) — across BOTH the edition-tagged
bulk bank (generate_bulk_bank.py) and the older legacy content (seed_data.py,
seed_more_years.py, seed_more_questions.py, seed_bank_set3.py), since both
happen to use near-identical prompt phrasing for these question types.

Detection is regex-based against the already-stored `prompt` text rather
than replaying the generator, so it works uniformly across every content
source without depending on RNG-seed reproducibility.

Diagrams only ever show the quantities GIVEN in the question (never the
value being asked for), so attaching an image cannot leak the answer.

Idempotent: only processes questions where media_url IS NULL, and only
domain 'N' (Numeracy). Re-running after generate_bulk_bank.py adds a new
edition will pick up just the new rows.

Usage:
    python backfill_question_images.py
"""

import os
import re

from config import get_connection
import svg_diagrams as svg

IMAGES_DIR = os.path.join(os.path.dirname(__file__), "..", "stage1-initial-design-craft", "images", "questions")
MEDIA_URL_PREFIX = "/images/questions"

os.makedirs(IMAGES_DIR, exist_ok=True)

# ------------------------------------------------------------------
# Detectors: each takes (prompt, correct_answer) and returns an SVG
# string, or None if it doesn't match.
# ------------------------------------------------------------------

RE_SIDES = re.compile(r"How many sides does an? (\w+) have\?")
RE_WHICH_SHAPE = re.compile(r"Which shape has 4 equal sides and 4 right angles\?")
RE_TIME_ADD = re.compile(r"It is (\d{1,2}):(\d{2})\s*(?:am|pm)?\. What time will it be in")
RE_CLOCK_HANDS = re.compile(r"hour hand is between (\d+) and \d+, and the minute hand is on the (\d+)")
RE_MONEY = re.compile(r"You have (.+)\. How much money")
RE_COIN_VALUE = re.compile(r"(\d+)c coin")
RE_RECT = re.compile(r"A rectangle has a length of (\d+) cm and a width of (\d+) cm\. What is its (perimeter|area)\?")
RE_TRI_ANGLES = re.compile(r"A triangle has angles of (\d+) degrees and (\d+) degrees\.")
RE_TRI_SUM = re.compile(r"How many degrees are in the angles of a triangle in total\?")
RE_PYTHAGORAS = re.compile(r"A right-angled triangle has legs of (\d+) cm and (\d+) cm\. What is the length of the hypotenuse\?")
RE_TRIG = re.compile(r"one angle is (\d+) degrees and the hypotenuse is (\d+) cm\. What is the length of the side opposite")
RE_MEAN_A = re.compile(r"What is the mean of (\d+), (\d+), (\d+) and (\d+)\?")
RE_MEAN_B = re.compile(r"The mean of (\d+), (\d+), (\d+),? and (\d+) is:?")


def detect_shape_sides(prompt, correct):
    m = RE_SIDES.search(prompt)
    if m:
        return svg.shape_svg(m.group(1))
    return None


def detect_which_shape(prompt, correct):
    if RE_WHICH_SHAPE.search(prompt):
        return svg.shape_options_svg(["Rectangle", "Triangle", "Square", "Circle"])
    return None


def detect_time_add(prompt, correct):
    m = RE_TIME_ADD.search(prompt)
    if m:
        return svg.clock_svg(int(m.group(1)), int(m.group(2)))
    return None


def detect_clock_hands(prompt, correct):
    m = RE_CLOCK_HANDS.search(prompt)
    if m:
        return svg.clock_svg(int(m.group(1)), int(m.group(2)) * 5)
    return None


def detect_money(prompt, correct):
    m = RE_MONEY.search(prompt)
    if m:
        coins = [int(c) for c in RE_COIN_VALUE.findall(m.group(1))]
        if coins:
            return svg.coins_svg(coins)
    return None


def detect_rectangle(prompt, correct):
    m = RE_RECT.search(prompt)
    if m:
        length, width, mode = int(m.group(1)), int(m.group(2)), m.group(3)
        return svg.rectangle_svg(length, width, mode)
    return None


def detect_triangle_angles(prompt, correct):
    m = RE_TRI_ANGLES.search(prompt)
    if m:
        return svg.triangle_angles_svg(int(m.group(1)), int(m.group(2)))
    return None


def detect_triangle_sum(prompt, correct):
    if RE_TRI_SUM.search(prompt):
        return svg.triangle_angles_svg("a", "b", "c")
    return None


def detect_pythagoras(prompt, correct):
    m = RE_PYTHAGORAS.search(prompt)
    if m:
        return svg.right_triangle_svg(int(m.group(1)), int(m.group(2)))
    return None


def detect_trig(prompt, correct):
    m = RE_TRIG.search(prompt)
    if m:
        return svg.right_triangle_trig_svg(int(m.group(1)), int(m.group(2)))
    return None


def detect_mean(prompt, correct):
    m = RE_MEAN_A.search(prompt) or RE_MEAN_B.search(prompt)
    if m:
        values = [int(g) for g in m.groups()]
        return svg.bar_chart_svg(values)
    return None


DETECTORS = [
    detect_shape_sides, detect_which_shape, detect_time_add, detect_clock_hands,
    detect_money, detect_rectangle, detect_triangle_angles, detect_triangle_sum,
    detect_pythagoras, detect_trig, detect_mean,
]


def main():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT q.question_id, q.prompt, q.correct_answer
        FROM dbo.questions q
        JOIN dbo.domains d ON d.domain_id = q.domain_id
        WHERE d.code = 'N' AND q.media_url IS NULL
        """
    )
    rows = cursor.fetchall()
    print(f"Scanning {len(rows)} Numeracy questions without an image...")

    matched = 0
    per_detector = {}
    update_cursor = conn.cursor()

    for question_id, prompt, correct in rows:
        svg_content = None
        for detector in DETECTORS:
            svg_content = detector(prompt, correct)
            if svg_content is not None:
                per_detector[detector.__name__] = per_detector.get(detector.__name__, 0) + 1
                break
        if svg_content is None:
            continue

        filename = f"q{question_id}.svg"
        with open(os.path.join(IMAGES_DIR, filename), "w", encoding="utf-8") as f:
            f.write(svg_content)

        media_url = f"{MEDIA_URL_PREFIX}/{filename}"
        update_cursor.execute(
            "UPDATE dbo.questions SET media_url = ? WHERE question_id = ?",
            media_url, question_id,
        )
        matched += 1

    conn.commit()
    conn.close()

    print(f"Attached images to {matched} of {len(rows)} Numeracy questions.")
    for name, count in sorted(per_detector.items(), key=lambda kv: -kv[1]):
        print(f"  {name}: {count}")


if __name__ == "__main__":
    main()
