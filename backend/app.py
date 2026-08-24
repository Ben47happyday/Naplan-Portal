"""
NAPLAN Prep Hub — backend API.

Serves the Stage 1 static frontend and a small JSON API backed by the
naplan-portal SQL Server database (see database/config.py, schema.sql).

Usage:
    python app.py
    -> http://localhost:5000
"""

import json
import os
import sys
from contextlib import contextmanager

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "database"))
from config import get_connection  # noqa: E402
from writing_scorer import score_writing  # noqa: E402

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "stage1-initial-design-craft")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
# Dev-only fallback secret so sessions survive a restart without extra setup.
# Override with a real secret via FLASK_SECRET_KEY before any real deployment.
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-naplan-prep-hub-secret-change-me")


@contextmanager
def db():
    """
    Yields a connection that is ALWAYS closed, even on error — a previous
    version of this file left connections open on any exception, which
    piled up locks on dbo.attempts until every submit started failing.
    """
    conn = get_connection()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ------------------------------------------------------------------
# Static frontend
# ------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


# ------------------------------------------------------------------
# Auth
# ------------------------------------------------------------------

def _current_student(cursor):
    student_id = session.get("student_id")
    if not student_id:
        return None
    cursor.execute(
        "SELECT student_id, display_name, email, year_level_id FROM dbo.students WHERE student_id = ?",
        student_id,
    )
    row = cursor.fetchone()
    if row is None:
        session.clear()
        return None
    return {
        "student_id": row.student_id,
        "display_name": row.display_name,
        "email": row.email,
        "year_level_id": row.year_level_id,
    }


@app.route("/api/auth/signup", methods=["POST"])
def signup():
    body = request.get_json(force=True) or {}
    display_name = (body.get("display_name") or "").strip()
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    year_level = body.get("year_level")

    if not display_name or not email or not password:
        return jsonify({"error": "Name, email and password are required."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400
    if year_level not in (3, 5, 7, 9):
        return jsonify({"error": "Please choose a valid year level."}), 400

    with db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM dbo.students WHERE email = ?", email)
        if cursor.fetchone():
            return jsonify({"error": "An account with that email already exists."}), 409

        password_hash = generate_password_hash(password)
        cursor.execute(
            """
            INSERT INTO dbo.students (display_name, year_level_id, email, password_hash)
            OUTPUT INSERTED.student_id
            VALUES (?, ?, ?, ?)
            """,
            display_name, year_level, email, password_hash,
        )
        student_id = cursor.fetchone()[0]
        conn.commit()

    session["student_id"] = student_id
    return jsonify({
        "student_id": student_id,
        "display_name": display_name,
        "email": email,
        "year_level_id": year_level,
    })


@app.route("/api/auth/login", methods=["POST"])
def login():
    body = request.get_json(force=True) or {}
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""

    with db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT student_id, display_name, email, year_level_id, password_hash "
            "FROM dbo.students WHERE email = ?",
            email,
        )
        row = cursor.fetchone()

    if row is None or not row.password_hash or not check_password_hash(row.password_hash, password):
        return jsonify({"error": "Incorrect email or password."}), 401

    session["student_id"] = row.student_id
    return jsonify({
        "student_id": row.student_id,
        "display_name": row.display_name,
        "email": row.email,
        "year_level_id": row.year_level_id,
    })


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/auth/me")
def me():
    with db() as conn:
        cursor = conn.cursor()
        student = _current_student(cursor)
    if student is None:
        return jsonify({"error": "Not logged in"}), 401
    return jsonify(student)


# ------------------------------------------------------------------
# Tests / questions
# ------------------------------------------------------------------

def _current_edition(cursor):
    """Latest content_year in play — the rolling window's newest edition."""
    cursor.execute("SELECT MAX(content_year) FROM dbo.tests")
    return cursor.fetchone()[0]


@app.route("/api/editions")
def list_editions():
    """Editions available for a year level, newest first, legacy (NULL) last."""
    year = request.args.get("year", type=int)

    sql = "SELECT DISTINCT content_year FROM dbo.tests WHERE status = 'published'"
    params = []
    if year is not None:
        sql += " AND year_level_id = ?"
        params.append(year)

    with db() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        current_edition = _current_edition(cursor)

    editions = sorted((r[0] for r in rows), key=lambda y: (y is None, -(y or 0)))
    return jsonify([
        {"content_year": y, "is_legacy": y is None, "is_current": y == current_edition}
        for y in editions
    ])


@app.route("/api/tests")
def list_tests():
    """List tests, optionally filtered by year level, domain code, type and edition.

    content_year param: an integer to see one specific edition only, "all" to
    see everything (legacy + every edition), or omitted to default to the
    current edition plus legacy (evergreen) content — otherwise a year level
    would return 300+ tests instead of a manageable practice list.
    """
    year = request.args.get("year", type=int)
    domain_code = request.args.get("domain")
    test_type = request.args.get("type")
    content_year_param = request.args.get("content_year")

    sql = """
        SELECT t.test_id, t.title, t.test_type, t.time_limit_mins, t.content_year,
               d.code AS domain_code, d.name AS domain_name,
               COUNT(tq.question_id) AS question_count
        FROM dbo.tests t
        LEFT JOIN dbo.domains d ON t.domain_id = d.domain_id
        JOIN dbo.test_questions tq ON tq.test_id = t.test_id
        WHERE t.status = 'published'
    """
    params = []
    if year is not None:
        sql += " AND t.year_level_id = ?"
        params.append(year)
    if domain_code:
        sql += " AND d.code = ?"
        params.append(domain_code)
    if test_type:
        sql += " AND t.test_type = ?"
        params.append(test_type)

    with db() as conn:
        cursor = conn.cursor()

        if content_year_param is None:
            current_edition = _current_edition(cursor)
            sql += " AND (t.content_year = ? OR t.content_year IS NULL)"
            params.append(current_edition)
        elif content_year_param == "legacy":
            sql += " AND t.content_year IS NULL"
        elif content_year_param != "all":
            sql += " AND t.content_year = ?"
            params.append(int(content_year_param))
        # content_year=all -> no extra filter

        sql += " GROUP BY t.test_id, t.title, t.test_type, t.time_limit_mins, t.content_year, d.code, d.name"
        sql += " ORDER BY t.test_id"

        cursor.execute(sql, params)
        rows = cursor.fetchall()

    return jsonify([
        {
            "test_id": r.test_id,
            "title": r.title,
            "test_type": r.test_type,
            "time_limit_mins": r.time_limit_mins,
            "content_year": r.content_year,
            "domain_code": r.domain_code,
            "domain_name": r.domain_name,
            "question_count": r.question_count,
        }
        for r in rows
    ])


@app.route("/api/tests/<int:test_id>")
def get_test(test_id):
    """Return a test's metadata and its questions, without answers/explanations."""
    with db() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT t.test_id, t.title, t.test_type, t.time_limit_mins, t.content_year,
                   d.code AS domain_code, d.name AS domain_name
            FROM dbo.tests t
            LEFT JOIN dbo.domains d ON t.domain_id = d.domain_id
            WHERE t.test_id = ? AND t.status = 'published'
            """,
            test_id,
        )
        test_row = cursor.fetchone()
        if test_row is None:
            return jsonify({"error": "Test not found"}), 404

        cursor.execute(
            """
            SELECT q.question_id, q.question_type, q.prompt, q.media_url,
                   q.option_a, q.option_b, q.option_c, q.option_d,
                   d.name AS domain_name, tq.sequence_no
            FROM dbo.test_questions tq
            JOIN dbo.questions q ON q.question_id = tq.question_id
            JOIN dbo.domains d ON d.domain_id = q.domain_id
            WHERE tq.test_id = ?
            ORDER BY tq.sequence_no
            """,
            test_id,
        )
        question_rows = cursor.fetchall()

    return jsonify({
        "test_id": test_row.test_id,
        "title": test_row.title,
        "test_type": test_row.test_type,
        "time_limit_mins": test_row.time_limit_mins,
        "content_year": test_row.content_year,
        "domain_code": test_row.domain_code,
        "domain_name": test_row.domain_name,
        "questions": [
            {
                "question_id": q.question_id,
                "question_type": q.question_type,
                "prompt": q.prompt,
                "media_url": q.media_url,
                "domain_name": q.domain_name,
                "options": [
                    {"key": key, "text": val}
                    for key, val in (
                        ("A", q.option_a), ("B", q.option_b),
                        ("C", q.option_c), ("D", q.option_d),
                    )
                    if val is not None
                ],
            }
            for q in question_rows
        ],
    })


def _band_estimate(percent_correct):
    if percent_correct >= 80:
        return "Exceeding expected standard"
    if percent_correct >= 50:
        return "At expected standard"
    return "Working towards expected standard"


def _build_feedback(cursor, attempt_id, year_level_id):
    """Per-domain accuracy breakdown, a couple of plain-language comments,
    and a suggested next practice test targeting the weakest domain."""
    cursor.execute(
        """
        SELECT d.code, d.name, aa.is_correct, aa.written_score
        FROM dbo.attempt_answers aa
        JOIN dbo.questions q ON q.question_id = aa.question_id
        JOIN dbo.domains d ON d.domain_id = q.domain_id
        WHERE aa.attempt_id = ?
        """,
        attempt_id,
    )

    domain_stats = {}
    for code, name, is_correct, written_score in cursor.fetchall():
        if is_correct is None:
            continue
        # Writing questions get their real rubric score; multiple-choice
        # questions map correctness to 100/0 — both land on the same scale.
        question_score = float(written_score) if written_score is not None else (100 if is_correct else 0)
        stat = domain_stats.setdefault(code, {"name": name, "score_sum": 0.0, "total": 0})
        stat["total"] += 1
        stat["score_sum"] += question_score

    domain_accuracy = [
        {
            "domain_code": code,
            "domain_name": stat["name"],
            "accuracy": round(stat["score_sum"] / stat["total"], 1),
        }
        for code, stat in domain_stats.items() if stat["total"] > 0
    ]
    domain_accuracy.sort(key=lambda d: d["accuracy"])

    comments = []
    suggestions = []

    if not domain_accuracy:
        comments.append("This task isn't auto-scored — it'll need to be reviewed against the writing rubric.")
        return {"comments": comments, "domain_accuracy": domain_accuracy, "suggestions": suggestions}

    overall = round(sum(d["accuracy"] for d in domain_accuracy) / len(domain_accuracy), 1)
    if overall >= 80:
        comments.append(f"Great work — {overall}% overall shows a strong grasp of this material.")
    elif overall >= 50:
        comments.append(f"Solid effort — {overall}% overall. The fundamentals are there, with room to sharpen up.")
    else:
        comments.append(f"{overall}% overall shows there's real ground to cover here — that's exactly what practice is for.")

    worst, best = domain_accuracy[0], domain_accuracy[-1]
    if len(domain_accuracy) > 1 and worst["accuracy"] < best["accuracy"]:
        comments.append(
            f"{worst['domain_name']} was the toughest area this time ({worst['accuracy']}%), "
            f"while {best['domain_name']} looked strongest ({best['accuracy']}%)."
        )

    current_edition = _current_edition(cursor)
    cursor.execute(
        """
        SELECT TOP 1 t.test_id, t.title
        FROM dbo.tests t
        JOIN dbo.domains d ON d.domain_id = t.domain_id
        WHERE t.year_level_id = ? AND d.code = ? AND t.test_type = 'practice' AND t.status = 'published'
          AND (t.content_year = ? OR t.content_year IS NULL)
        ORDER BY NEWID()
        """,
        year_level_id, worst["domain_code"], current_edition,
    )
    rec = cursor.fetchone()
    if rec:
        comments.append(f'Suggested next step: try "{rec.title}" to build up {worst["domain_name"]}.')
        suggestions.append({"test_id": rec.test_id, "title": rec.title, "domain_name": worst["domain_name"]})

    return {"comments": comments, "domain_accuracy": domain_accuracy, "suggestions": suggestions}


@app.route("/api/tests/<int:test_id>/submit", methods=["POST"])
def submit_test(test_id):
    """Score a submitted attempt, store it against the logged-in student, and
    return instant results plus coaching feedback. Login is required so the
    attempt can be recorded to the student's history."""
    with db() as conn:
        cursor = conn.cursor()
        student = _current_student(cursor)
        if student is None:
            return jsonify({"error": "login_required", "message": "Please log in to submit answers."}), 401

        body = request.get_json(force=True) or {}
        answers = body.get("answers") or {}

        cursor.execute("SELECT year_level_id FROM dbo.tests WHERE test_id = ?", test_id)
        test_row = cursor.fetchone()
        if test_row is None:
            return jsonify({"error": "Test not found"}), 404

        cursor.execute(
            """
            SELECT question_id, correct_answer, explanation, question_type
            FROM dbo.questions
            WHERE question_id IN (
                SELECT question_id FROM dbo.test_questions WHERE test_id = ?
            )
            """,
            test_id,
        )
        answer_key = {
            row.question_id: (row.correct_answer, row.explanation, row.question_type)
            for row in cursor.fetchall()
        }

        cursor.execute(
            "INSERT INTO dbo.attempts (student_id, test_id, completed_at) "
            "OUTPUT INSERTED.attempt_id VALUES (?, ?, SYSUTCDATETIME())",
            student["student_id"], test_id,
        )
        attempt_id = cursor.fetchone()[0]

        results = []
        scored_count = 0
        correct_count = 0
        score_sum = 0.0

        for question_id, (correct_answer, explanation, question_type) in answer_key.items():
            student_answer = answers.get(str(question_id), answers.get(question_id))
            is_writing = question_type == "short_answer" and correct_answer.startswith("Open response")
            written_score = None
            writing_assessment = None

            if is_writing:
                writing_assessment = score_writing(student_answer, test_row.year_level_id)
                written_score = writing_assessment["score_percent"]
                is_correct = written_score >= 50  # "meets standard" threshold, for domain-accuracy rollups
                scored_count += 1
                score_sum += written_score
                if is_correct:
                    correct_count += 1
            else:
                is_correct = (student_answer is not None and
                              str(student_answer).strip().lower() == str(correct_answer).strip().lower())
                scored_count += 1
                score_sum += 100 if is_correct else 0
                if is_correct:
                    correct_count += 1

            cursor.execute(
                "INSERT INTO dbo.attempt_answers "
                "(attempt_id, question_id, student_answer, is_correct, written_score, written_feedback) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                attempt_id, question_id, student_answer, is_correct,
                written_score, json.dumps(writing_assessment) if writing_assessment else None,
            )
            results.append({
                "question_id": question_id,
                "student_answer": student_answer,
                "correct_answer": None if is_writing else correct_answer,
                "is_correct": is_correct,
                "explanation": explanation,
                "writing_assessment": writing_assessment,
            })

        percent = round(score_sum / scored_count, 1) if scored_count else None
        band = _band_estimate(percent) if percent is not None else "Not auto-scored"

        cursor.execute(
            "UPDATE dbo.attempts SET score = ?, band_estimate = ? WHERE attempt_id = ?",
            percent, band, attempt_id,
        )

        feedback = _build_feedback(cursor, attempt_id, test_row.year_level_id)
        conn.commit()

    return jsonify({
        "attempt_id": attempt_id,
        "score_percent": percent,
        "band_estimate": band,
        "correct_count": correct_count,
        "scored_count": scored_count,
        "results": results,
        "feedback": feedback,
    })


# ------------------------------------------------------------------
# Profile / history
# ------------------------------------------------------------------

@app.route("/api/me/attempts")
def my_attempts():
    with db() as conn:
        cursor = conn.cursor()
        student = _current_student(cursor)
        if student is None:
            return jsonify({"error": "login_required"}), 401

        cursor.execute(
            """
            SELECT a.attempt_id, a.completed_at, a.score, a.band_estimate,
                   t.title, t.test_type, d.name AS domain_name
            FROM dbo.attempts a
            JOIN dbo.tests t ON t.test_id = a.test_id
            LEFT JOIN dbo.domains d ON d.domain_id = t.domain_id
            WHERE a.student_id = ?
            ORDER BY a.completed_at DESC
            """,
            student["student_id"],
        )
        rows = cursor.fetchall()

    return jsonify([
        {
            "attempt_id": r.attempt_id,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "score_percent": float(r.score) if r.score is not None else None,
            "band_estimate": r.band_estimate,
            "test_title": r.title,
            "test_type": r.test_type,
            "domain_name": r.domain_name,
        }
        for r in rows
    ])


@app.route("/api/attempts/<int:attempt_id>")
def attempt_detail(attempt_id):
    with db() as conn:
        cursor = conn.cursor()
        student = _current_student(cursor)
        if student is None:
            return jsonify({"error": "login_required"}), 401

        cursor.execute(
            """
            SELECT a.attempt_id, a.student_id, a.completed_at, a.score, a.band_estimate,
                   t.title, t.year_level_id
            FROM dbo.attempts a
            JOIN dbo.tests t ON t.test_id = a.test_id
            WHERE a.attempt_id = ?
            """,
            attempt_id,
        )
        attempt_row = cursor.fetchone()
        if attempt_row is None or attempt_row.student_id != student["student_id"]:
            return jsonify({"error": "Not found"}), 404

        cursor.execute(
            """
            SELECT q.prompt, aa.student_answer, aa.is_correct, q.correct_answer, q.explanation,
                   aa.written_feedback
            FROM dbo.attempt_answers aa
            JOIN dbo.questions q ON q.question_id = aa.question_id
            WHERE aa.attempt_id = ?
            ORDER BY aa.attempt_answer_id
            """,
            attempt_id,
        )
        answer_rows = cursor.fetchall()

        feedback = _build_feedback(cursor, attempt_id, attempt_row.year_level_id)

    return jsonify({
        "attempt_id": attempt_row.attempt_id,
        "test_title": attempt_row.title,
        "completed_at": attempt_row.completed_at.isoformat() if attempt_row.completed_at else None,
        "score_percent": float(attempt_row.score) if attempt_row.score is not None else None,
        "band_estimate": attempt_row.band_estimate,
        "results": [
            {
                "prompt": a.prompt,
                "student_answer": a.student_answer,
                "is_correct": a.is_correct,
                "correct_answer": None if a.written_feedback else a.correct_answer,
                "explanation": a.explanation,
                "writing_assessment": json.loads(a.written_feedback) if a.written_feedback else None,
            }
            for a in answer_rows
        ],
        "feedback": feedback,
    })


# ------------------------------------------------------------------
# Numeracy: instant per-question checking + skill (strand) practice
# ------------------------------------------------------------------

@app.route("/api/questions/<int:question_id>/check", methods=["POST"])
def check_question(question_id):
    """Instant right/wrong + explanation for one question, without creating
    an attempt. Powers immediate feedback while practicing (pick, check,
    retry) ahead of the final Submit that records the full attempt."""
    with db() as conn:
        cursor = conn.cursor()
        if _current_student(cursor) is None:
            return jsonify({"error": "login_required"}), 401

        body = request.get_json(force=True) or {}
        student_answer = body.get("answer")

        cursor.execute(
            "SELECT correct_answer, explanation FROM dbo.questions WHERE question_id = ?",
            question_id,
        )
        row = cursor.fetchone()

    if row is None:
        return jsonify({"error": "Question not found"}), 404

    is_correct = (student_answer is not None and
                  str(student_answer).strip().lower() == str(row.correct_answer).strip().lower())
    return jsonify({
        "is_correct": is_correct,
        "correct_answer": row.correct_answer,
        "explanation": row.explanation,
    })


@app.route("/api/numeracy-strands")
def numeracy_strands():
    """Skill areas available for Numeracy practice (e.g. Fractions, Angles),
    each with a question-bank count, for skill-based practice."""
    year = request.args.get("year", type=int)
    if year is None:
        return jsonify({"error": "year is required"}), 400

    with db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT q.strand, COUNT(*) AS n
            FROM dbo.questions q
            JOIN dbo.domains d ON d.domain_id = q.domain_id
            WHERE d.code = 'N' AND q.year_level_id = ? AND q.status = 'published' AND q.strand IS NOT NULL
            GROUP BY q.strand
            HAVING COUNT(*) >= 5
            ORDER BY n DESC
            """,
            year,
        )
        rows = cursor.fetchall()

    return jsonify([{"strand": r.strand, "question_count": r.n} for r in rows])


@app.route("/api/numeracy/practice-set", methods=["POST"])
def numeracy_practice_set():
    """Spin up (or reuse) a short ad-hoc practice quiz for one numeracy
    skill/strand, pulling randomly from the whole question bank for that
    strand+year — not tied to any single edition. Returns a normal test_id
    so the existing quiz-taking, scoring and history flow just works."""
    body = request.get_json(force=True) or {}
    year = body.get("year_level")
    strand = (body.get("strand") or "").strip()
    limit = min(max(int(body.get("limit", 10)), 5), 20)

    if year not in (3, 5, 7, 9) or not strand:
        return jsonify({"error": "year_level and strand are required"}), 400

    with db() as conn:
        cursor = conn.cursor()
        if _current_student(cursor) is None:
            return jsonify({"error": "login_required"}), 401

        title = f"Skill practice: {strand}"
        cursor.execute(
            """
            SELECT test_id FROM dbo.tests
            WHERE year_level_id = ? AND title = ? AND test_type = 'skill_practice' AND status = 'published'
            """,
            year, title,
        )
        existing = cursor.fetchone()
        if existing:
            return jsonify({"test_id": existing[0]})

        cursor.execute("SELECT domain_id FROM dbo.domains WHERE code = 'N'")
        numeracy_domain_id = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT TOP (?) question_id FROM dbo.questions
            WHERE year_level_id = ? AND domain_id = ? AND strand = ? AND status = 'published'
            ORDER BY NEWID()
            """,
            limit, year, numeracy_domain_id, strand,
        )
        question_ids = [r[0] for r in cursor.fetchall()]
        if not question_ids:
            return jsonify({"error": "No questions found for that skill yet"}), 404

        cursor.execute(
            """
            INSERT INTO dbo.tests (year_level_id, domain_id, title, test_type, time_limit_mins, status)
            OUTPUT INSERTED.test_id
            VALUES (?, ?, ?, 'skill_practice', ?, 'published')
            """,
            year, numeracy_domain_id, title, max(10, limit * 2),
        )
        test_id = cursor.fetchone()[0]
        for seq, qid in enumerate(question_ids, start=1):
            cursor.execute(
                "INSERT INTO dbo.test_questions (test_id, question_id, sequence_no) VALUES (?, ?, ?)",
                test_id, qid, seq,
            )
        conn.commit()

    return jsonify({"test_id": test_id})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
