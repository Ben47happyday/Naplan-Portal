# Change notes: edition-tagged question bank (content_year)

**Date:** 2026-07-28
**Area:** `database/` (schema + content). Consumers: `backend/app.py` (Flask API), `stage1-initial-design-craft/` (frontend).
**Status:** Applied directly to the live `naplan-portal` SQL Server database. No application code was touched — this file is the handoff for whoever updates `backend/` and the frontend.

---

## 1. Summary

Two things changed in the database this session:

1. **More practice content for the existing bank** (Years 3/5/7/9 × Reading/Writing/Language Conventions/Numeracy) — a "set 3" was added on top of the pre-existing set 1/set 2 content. This content has `content_year = NULL` (see §2).
2. **A new edition-tagged bulk question bank** was added, organised by a rolling 4-year window of "editions" (2023–2026) crossed with the 4 NAPLAN year levels. Every (edition, year level) combination has **310 questions** (≥ the requested minimum of 300), split across all four domains and chunked into ~20-question quizzes.

None of this content is sourced from real/official NAPLAN papers — it's originally generated, matched to NAPLAN-style strands and difficulty per year level. The edition-year labels (2023–2026) are a content-organisation scheme, not a claim of authenticity.

**Nothing in `backend/` or the frontend currently reads or filters on the new `content_year` column.** That's the integration work this document hands off.

---

## 2. Schema change

`dbo.questions` and `dbo.tests` each gained a nullable column:

```sql
ALTER TABLE dbo.questions ADD content_year INT NULL;
ALTER TABLE dbo.tests     ADD content_year INT NULL;
```

Already applied to the live DB, and captured idempotently in `database/schema.sql` (guarded by `COL_LENGTH(...) IS NULL` checks, so re-running `create_schema.py` is safe).

- `content_year = NULL` → **legacy/evergreen content**: the original set 1/2/3 questions and tests (14 → 24 questions per year level before this bulk build). Not part of any edition.
- `content_year = 2023 | 2024 | 2025 | 2026` → belongs to that edition's bulk-generated bank.

**Decide before shipping UI for this:** should NULL-tagged (legacy) tests/questions keep showing up regardless of which edition a student has selected, or should they be migrated into an edition (e.g. backfilled to 2026) or hidden once edition filtering ships? This wasn't decided as part of this change — recommend treating `content_year IS NULL` as "always visible" (safest, no data loss, no behaviour change for existing users) unless product wants otherwise.

---

## 3. Data volumes

```
Total questions in DB : 5,056
Total tests in DB     : 304

Legacy (content_year IS NULL)     : ~406 questions across 4 year levels
Per edition × year level bucket   : 310 questions (16 buckets: 4 editions × 4 year levels)
  → N: 80, LC: 80, R: 80, W: 70 per bucket
Tests per bucket                  : 16 (4 domains × ~4 quiz-sized sets of ~20 questions each)
```

Verified before handoff: every multiple-choice `correct_answer` is present among its own `option_a`–`option_d`; no empty prompts/answers; every bucket has ≥ 300 questions.

Test titles for the new content follow the pattern:
`"<Domain title> <content_year> - set <n>"`, e.g. `"Numeracy practice 2026 - set 1"`.

---

## 4. New scripts in `database/`

| Script | Purpose |
|---|---|
| `seed_bank_set3.py` | Adds the "set 3" legacy-content expansion (content_year NULL). Idempotent per year level. |
| `generate_bulk_bank.py` | Generates and inserts the edition-tagged bank (2023–2026 × Years 3/5/7/9, 310 Q/bucket). Idempotent per (edition, year level) — skips a bucket if it already has ≥300 questions. **Currently hardcodes `EDITION_YEARS = [2023, 2024, 2025, 2026]`** — when 2027 arrives, add 2027 to that list before re-running (see §6, rolling window). |
| `prune_old_editions.py` | Deletes editions older than the most recent N (default 4), FK-safe (attempt_answers → test_questions → tests → questions). Run this *after* `generate_bulk_bank.py` adds a new edition, to actually enforce the rolling window. Currently a no-op (exactly 4 editions exist). |

Run order for a future "new year" rollover: add the new year to `EDITION_YEARS` in `generate_bulk_bank.py` → `python generate_bulk_bank.py` → `python prune_old_editions.py`.

---

## 5. Required changes in `backend/app.py`

**Status: implemented since this was written** — `/api/editions` exists, `list_tests` filters/defaults on `content_year`, `get_test` returns `content_year`, and `_build_feedback()` now filters recommendations to `(t.content_year = ? OR t.content_year IS NULL)` using the current edition. A `check_question` instant-feedback endpoint (`POST /api/questions/<id>/check`) was also added, not originally requested here but complementary. Left the sub-sections below as-written for the historical record.

Read the current file — none of this exists yet. Concrete, minimal changes:

### 5.1 `GET /api/tests` (list_tests, line ~169)
- Accept an optional `content_year` query param; filter `WHERE t.content_year = ?` when provided (and keep existing `year`/`domain`/`type` filters working alongside it).
- **Decide the default when `content_year` is omitted**: options are (a) return everything including legacy+all editions [current behaviour, but now returns 300+ tests per year level instead of ~8 — likely too many for the existing UI], or (b) default to the latest edition (2026) plus legacy (`content_year IS NULL OR content_year = 2026`). Recommend (b) for the default list view, with an explicit edition switch to see older editions.
- Include `content_year` in the returned JSON per test so the frontend can label/group by edition.

### 5.2 `GET /api/tests/<test_id>` (get_test, line ~217)
- Include `content_year` in the response body for display context (e.g. "2025 edition").

### 5.3 New endpoint: list available editions
Nothing currently tells the frontend which editions exist. Add something like:
```
GET /api/editions?year=<year_level>
→ [{"content_year": 2026, "is_legacy": false}, ..., {"content_year": null, "is_legacy": true}]
```
Query: `SELECT DISTINCT content_year FROM dbo.tests WHERE year_level_id = ? AND status='published' ORDER BY content_year DESC`. Used to populate an edition picker in the UI.

### 5.4 `_build_feedback()` (line ~287, "suggested next practice test")
This currently does:
```sql
SELECT TOP 1 t.test_id, t.title FROM dbo.tests t
JOIN dbo.domains d ON d.domain_id = t.domain_id
WHERE t.year_level_id = ? AND d.code = ? AND t.test_type = 'practice' AND t.status = 'published'
ORDER BY NEWID()
```
With 5,056 questions now in play, this will start recommending tests from arbitrary old editions (e.g. a 2023 quiz) as "your suggested next step," which is inconsistent with "content stays current." **Recommend adding `AND (t.content_year = 2026 OR t.content_year IS NULL)`** (or whatever the current default edition is) so recommendations only pull from current/legacy content. This is a real behavioural bug once the new data is live, not just a nice-to-have.

### 5.5 No changes needed to
- `submit_test`, `my_attempts`, `attempt_detail`, auth routes — these key off `test_id`/`question_id`, not year/domain/edition, so they're unaffected by the new column.

---

## 6. Rolling window semantics

"Rolling last 4 years" is enforced operationally, not by a DB constraint (a hardcoded `CHECK (content_year BETWEEN 2023 AND 2026)` would break next year). The window is whatever `EDITION_YEARS` in `generate_bulk_bank.py` says, combined with running `prune_old_editions.py` after adding a new year. If the webportal needs "current edition" at runtime, treat it as `MAX(content_year)` in `dbo.tests`/`dbo.questions`, not a hardcoded year.

---

## 7. Known issues found during this work (pre-existing, NOT caused by this change)

Flagging these since whoever picks up the backend integration will hit them:

1. ~~`create_schema.py` currently fails on the `dbo.students` batch~~ — **Resolved since this was written.** Someone added guarded `ALTER TABLE dbo.students ADD email / password_hash` blocks (see `schema.sql` §students and `migrate_auth.sql`), following the same `COL_LENGTH` pattern used for `content_year` above. Confirmed live: `COL_LENGTH('dbo.students','email')` and `...'password_hash'` both resolve now. No action needed.
2. **Pre-existing "set 2" test titles are mojibake-corrupted** in the DB: `Reading practice � set 2` instead of an en dash. Root cause is an NVARCHAR/encoding mismatch from whatever process inserted them (not from this session's scripts — this session's set 3 and edition-bank titles use plain ASCII hyphens specifically to avoid this). Cosmetic only, but worth a cleanup pass (`UPDATE dbo.tests SET title = REPLACE(title, N'�', N'-') WHERE title LIKE '%�%'` after confirming the actual corrupted byte sequence).

---

## 8. Verification queries (for whoever picks this up)

```sql
-- Confirm rolling window contents
SELECT DISTINCT content_year FROM dbo.questions ORDER BY content_year;

-- Per-bucket counts
SELECT content_year, year_level_id, COUNT(*) FROM dbo.questions
WHERE content_year IS NOT NULL GROUP BY content_year, year_level_id ORDER BY 1, 2;

-- Legacy content still intact
SELECT year_level_id, COUNT(*) FROM dbo.questions WHERE content_year IS NULL GROUP BY year_level_id;
```

---

## 9. Update 2026-07-28 (later same day): Numeracy diagrams + interactive option highlight

Follow-up requested: "focus on math/numeracy questions, add more image and questions [a] student can interact with in practice quiz." Scope was Numeracy specifically (Reading/Writing/LC are text-based and weren't touched).

### 9.1 What changed
- **`database/svg_diagrams.py`** (new) — pure functions generating small self-contained SVG diagrams: regular polygons/shapes, an analog clock face, coins, a labelled rectangle (perimeter/area), a triangle with angle labels, a right triangle (Pythagoras/trig), and a bar chart.
  - **Design rule, load-bearing:** every diagram shows only the values *given* in the question, never the value being asked for (e.g. a Pythagoras diagram labels the two legs and marks the hypotenuse "?"). This means attaching an image can never leak the answer. Keep this rule if you extend the generator.
- **`database/backfill_question_images.py`** (new) — regex-detects visual question types directly against the stored `prompt` text (not by replaying the generator's RNG), so it works uniformly across both the edition-tagged bulk bank *and* the older legacy content in `seed_data.py` / `seed_more_years.py` / `seed_more_questions.py` / `seed_bank_set3.py`, which happen to use near-identical prompt phrasing for these patterns. Renders each matched question's SVG to `stage1-initial-design-craft/images/questions/q<question_id>.svg` and sets `dbo.questions.media_url` to `/images/questions/q<question_id>.svg`.
  - Idempotent: only touches Numeracy (`domain code = 'N'`) rows where `media_url IS NULL`.
  - **Run this after every `generate_bulk_bank.py` run** (e.g. next year's edition rollover) to backfill images for the newly-added questions — it's not called automatically by `generate_bulk_bank.py`.
  - Result of this run: 450 of 1,312 Numeracy questions matched (the rest — addition, subtraction, decimals, algebra, ratio, probability, rates, etc. — are correctly left without an image; there's nothing to usefully draw). Breakdown: rectangle (perimeter/area) 123, mean/bar-chart 81, Pythagoras 42, clock (time-add) 41, shape-sides 40, trig 40, money/coins 40, triangle-angles 40, plus 3 one-off legacy prompts (clock-hands phrasing, triangle-angle-sum phrasing, "which shape" phrasing).
- **`backend/app.py`** — `get_test`'s question SELECT and JSON response now include `media_url` (was previously selected nowhere, so no app-layer change existed for it before this).
- **`stage1-initial-design-craft/js/quiz.js`** — `renderQuestion()` now renders `<img src="{media_url}">` above the prompt when present. Also added a `change` listener on each question's option list that adds an `option-row--selected` class to the chosen radio's row (visual highlight), on top of the existing `check-btn` instant-feedback interaction (that endpoint, `POST /api/questions/<id>/check`, was added by whoever did the §5 backend work, not by this update).
- **`stage1-initial-design-craft/css/style.css`** — `.question-diagram` (image container) and `.option-row--selected` (highlight state) rules added.

### 9.2 Verified
- Ran the backend locally and drove `quiz.html` in a real browser: confirmed a heptagon diagram, an analog clock, and a labelled Pythagoras right-triangle (legs 5 cm/12 cm, hypotenuse marked "?") all render correctly at `/images/questions/q<id>.svg`, that selecting an option highlights its row, and that "Check answer" still returns correct/incorrect against the same question.
- Spot-checked DB state: 450 `dbo.questions` rows now have a non-null `media_url`; 450 corresponding `.svg` files exist on disk; counts match exactly.

### 9.3 Nothing further required for this to work
Unlike §5, this update's frontend/backend pieces were implemented as part of the same change (not left as a handoff) — `media_url` flows DB → `get_test` → `quiz.js` → `<img>` with no missing link. Static serving needed no new Flask route since `app.py` already serves the whole `stage1-initial-design-craft/` tree at `static_url_path=""`.

### 9.4 Possible future extension (not done, out of scope for this pass)
The result-review screen (`renderResults`/`renderWritingResult` in `quiz.js`) does not currently show the diagram when reviewing a submitted attempt — only the live quiz view does. If that's wanted, thread `q.media_url` through the same way `q.prompt` already is in `renderResults`.

## 10. Update 2026-07-29: Numeracy topic-variety expansion (12 new original patterns)

Follow-up request: user pointed at IXL's Australian maths topic index (`au.ixl.com/maths`) as inspiration and asked to "focus on math/numerous questions, add more image and questions [a] student can interact with." **No content was scraped from IXL or any third party** — the site's topic *category labels* (e.g. "bar graphs", "divisibility rules", "coordinate translations", "similar figure areas") were used only to identify skill-area gaps in our own generator; every prompt, answer, distractor and diagram below is originally authored and computed here.

### 10.1 New Numeracy patterns (`database/generate_bulk_bank.py`)
Added 3 new pattern functions per NAPLAN year level, appended to the existing `N_PATTERNS_Y*` lists (existing patterns untouched, so this only adds variety, not regressions):
- **Year 3**: `n_bar_graph_read` (bar-chart reading, diagram), `n_length_convert` (m ⟷ cm), `n_money_change` (change from a note)
- **Year 5**: `n_divisibility`, `n_divide_pow10` (÷10/100/1000), `n_time_duration` (elapsed time, two-clock diagram)
- **Year 7**: `n_integer_ops` (negative-number arithmetic, number-line diagram), `n_coordinate_translation` (grid diagram), `n_experimental_probability`
- **Year 9**: `n_similar_figures` (area scale factor, diagram), `n_exponent_laws` (index laws), `n_polynomial_perimeter` (algebraic rectangle, diagram)

Each was fuzz-tested 300 iterations (random seed) confirming exactly 4 unique MC options every time and valid SVG output. **Bug found and fixed during this**: `n_integer_ops` initially called `numeric_distractors(...)` without `min_val`, which defaults to `0` — since integer-arithmetic answers can be negative, this silently starved the distractor pool down to 1–2 wrongs instead of 3. Fixed by passing `min_val=-100`. **Lesson for future patterns with negative correct answers: always pass an explicit negative `min_val` to `numeric_distractors`.**

### 10.2 New diagram types (`database/svg_diagrams.py`)
Added `two_clocks_svg` (start/end clock faces for duration questions), `number_line_svg` (marks only the given operands, never the sum), `coordinate_point_svg` (grid with only the *starting* point plotted — the translated/destination point is deliberately never drawn, so it can't be measured off the grid), `similar_figures_svg` (small rectangle labelled with the given dimension, large one labelled "?", scale factor captioned), and `rectangle_labeled_svg` (fixed-size rectangle with arbitrary text/algebraic side labels, for the polynomial-perimeter question). Same "never leak the answer" rule as §9.1 was applied throughout and re-verified live in-browser (see 10.4).

### 10.3 New insertion script (`database/add_numeracy_topic_variety.py`)
`generate_bulk_bank.py`'s bucket loop skips any `(content_year, year_level)` bucket once it has ≥300 questions — since every bucket already did, simply adding patterns there wouldn't insert anything new. This script tops up each of the 16 existing buckets separately: generates 30 questions per bucket (10 per pattern, deterministic RNG seeded per bucket), inserts them with `content_year` set correctly, writes any diagram SVGs directly (no regex backfill needed — the script knows exactly which item needs which image), and groups them into a new test titled `"Numeracy practice {content_year} - topic variety"`.
- Idempotent: skips a bucket if a test with `topic variety` in the title already exists for it.
- **Re-run this (or extend `TOPIC_PATTERNS`/`TARGET_PER_BUCKET`) after adding more patterns in future** — it won't touch buckets it's already topped up.
- Result of this run: 480 new questions (30 x 16 buckets), 246 with an attached diagram. Verified: `stage1-initial-design-craft/images/questions/` file count went from 450 → 696, matching the 246 new `media_url` rows exactly.

### 10.4 Verified
- DB reconciliation: 16 new "topic variety" tests, 480 linked questions, 246 with non-null `media_url`, strand counts all add up correctly.
- Static file serving: spot-checked `/images/questions/q5057.svg` returns `200 image/svg+xml`.
- Live browser check (signed-in session) against three of the new tests: Year 3 bar-graph question rendered correctly with all four category bars visible and labelled, and the asked-for difference (not a bar height) as the correct option; Year 7 number-line diagram (integer addition) and coordinate-grid diagram (translation, point A plotted, destination correctly *not* drawn) both rendered correctly; Year 9 similar-figures diagram (small rectangle "22 cm²", large rectangle "?", "scale factor x3" caption) rendered correctly with the right answer (198 cm²) among the options.
- No further wiring needed: these new questions flow through the exact same `media_url` → `get_test` → `quiz.js` → `<img>` path already in place from §9, so nothing else required a code change.
