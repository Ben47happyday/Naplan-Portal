"""
Keeps the question bank to a rolling window of the 4 most recent content
editions (content_year on dbo.questions / dbo.tests). Run this after
seeding a new edition with generate_bulk_bank.py (e.g. once a year, after
adding the new year) to drop editions older than the window so the bank
never grows unbounded and never serves out-of-date editions.

Deletes, in FK-safe order, any content_year older than the 4 most recent
distinct content_years currently present: attempt_answers referencing
those questions, test_questions, tests, then questions. Behavioural data
for other students' completed attempts on pruned tests is left alone
(attempts/attempt rows themselves aren't deleted, only their answer
detail rows tied to pruned questions) since attempts belong to the
student's history, not the content bank.

Usage:
    python prune_old_editions.py            # keep the 4 most recent editions
    python prune_old_editions.py --keep 3    # override the window size
"""

import argparse

from config import get_connection


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", type=int, default=4, help="number of most recent editions to keep")
    args = parser.parse_args()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT DISTINCT content_year FROM dbo.questions WHERE content_year IS NOT NULL ORDER BY content_year DESC"
    )
    years = [r[0] for r in cursor.fetchall()]
    keep_years = years[:args.keep]
    prune_years = years[args.keep:]

    if not prune_years:
        print(f"Nothing to prune. Current editions: {years}. Keeping most recent {args.keep}.")
        conn.close()
        return

    print(f"Keeping editions: {keep_years}")
    print(f"Pruning editions: {prune_years}")

    placeholders = ",".join("?" for _ in prune_years)

    cursor.execute(
        f"""
        DELETE FROM dbo.attempt_answers aa
        USING dbo.questions q
        WHERE q.question_id = aa.question_id AND q.content_year IN ({placeholders})
        """,
        *prune_years,
    )
    print(f"Deleted {cursor.rowcount} attempt_answers rows.")

    cursor.execute(
        f"""
        DELETE FROM dbo.test_questions tq
        USING dbo.tests t
        WHERE t.test_id = tq.test_id AND t.content_year IN ({placeholders})
        """,
        *prune_years,
    )
    print(f"Deleted {cursor.rowcount} test_questions rows.")

    cursor.execute(f"DELETE FROM dbo.tests WHERE content_year IN ({placeholders})", *prune_years)
    print(f"Deleted {cursor.rowcount} tests.")

    cursor.execute(f"DELETE FROM dbo.questions WHERE content_year IN ({placeholders})", *prune_years)
    print(f"Deleted {cursor.rowcount} questions.")

    conn.commit()
    conn.close()
    print("Prune complete.")


if __name__ == "__main__":
    main()
