# NAPLAN Prep Hub — Web Portal Design Plan

## 1. Purpose & Positioning

A single, easy-to-understand web portal that helps Australian parents and students (Years 3, 5, 7, 9) with three things: understanding what the NAPLAN test covers, practicing realistic questions, and checking a student's current NAPLAN level. Benchmarked against Excel Test Zone, SubjectCoach, and LevelUp Exams.

## 2. Competitor Study Summary

| Platform | Strength | Gap |
|---|---|---|
| Excel Test Zone | Simple 3-step onboarding, teacher-written questions, parent email reports | No live diagnostic / level check before starting |
| SubjectCoach | 500+ tests, band-by-band strand tracking, AI writing scoring | Navigation is dense/multi-product; NAPLAN buried among many offerings |
| LevelUp Exams | One-time payment, no subscription, simple pricing | Fewer domain-specific insights, thinner test-agenda explanation |

**Design takeaway:** keep the site focused only on NAPLAN (no unrelated products in the nav), open with a plain-language explanation of the test, and put a level-check diagnostic front and centre — something none of the three competitors lead with.

## 3. Information Architecture

- **Home** — hero, 3-pillar explainer, year-level picker
- **Understand the Test** — what NAPLAN is, domains, format, timing, by year level
- **Practice Questions** — browse by year level and domain (Reading, Writing, Numeracy, Conventions)
- **Check My Level** — short adaptive diagnostic, band result, strand breakdown
- **My Progress** — dashboard for logged-in users (parent + student view)
- **Resources / FAQ** — dates, scoring guide, tips
- **Account** — sign up, login, child profile switcher

## 4. Core User Flows

**Flow 1 — First-time visitor:**
- Land on Home → read 3-pillar summary → pick year level → choose "Check my level" or "Browse practice questions"

**Flow 2 — Level check:**
- Select year level → 15-20 min short adaptive quiz across domains → instant band estimate + strand breakdown → recommended practice set

**Flow 3 — Practice:**
- Select year + domain → practice test list → take test → instant marking with worked explanation → result saved to progress dashboard

## 5. Page Coverage by Year Level

| Year | Domains Covered | Format Notes |
|---|---|---|
| Year 3 | Reading, Writing, Language Conventions, Numeracy | Writing stays paper-based per ACARA; simpler UI, larger text/buttons |
| Year 5 | Reading, Writing, Language Conventions, Numeracy | Fully online, adaptive difficulty introduced |
| Year 7 | Reading, Writing, Language Conventions, Numeracy | Fully online, adaptive difficulty, longer passages |
| Year 9 | Reading, Writing, Language Conventions, Numeracy | Fully online, most advanced item bank |

## 6. Visual Design System

**UI pattern:** Soft Illustrative — chosen from 5 style options for its warm, approachable tone that works across the full Year 3-9 age range without feeling babyish or too corporate. Cream page background, rounded pill buttons and cards, and pastel circular icon badges instead of flat icons.

**Primary theme colour:** `#F7A026` (warm orange) — used for header bar accents, primary buttons, active states, and progress highlights. Kept off large background fills; cream (`#FFFCF6` / `#FFF9F0`) carries the soft-illustrative warmth instead.

| Token | Value | Use |
|---|---|---|
| Primary | `#F7A026` | Header bar, primary CTA buttons, selected state |
| Primary text on orange | `#4A1B0C` | Text/icons placed on orange background |
| Neutral text | `#2C2C2A` / `#5F5E5A` | Body copy, secondary text |
| Surface | `#FFFFFF` / `#F7F6F2` | Cards, page background |
| Border | `#E4E1D8` | Card and input borders |
| Success accent | `#3B6D11` | Correct answers, pass state |

**Typography:** one sans-serif family, two weights only (regular / medium). Minimum 15px body text for readability by Year 3 students. Headings short and literal ("Practice questions", not clever taglines).

**Layout principles for first-time clarity:**
- Every page opens with a one-sentence explanation of what the page is for
- Maximum 3 choices presented at once on the home page (Understand / Practice / Check level)
- Icons paired with every label — never icon-only navigation
- Year level always visible and switchable from a persistent top control
- No dense multi-product mega-menus (the SubjectCoach pitfall) — NAPLAN is the only focus

### Soft Illustrative pattern rules

- Buttons and cards use 16-20px rounded corners (pill-shaped primary buttons)
- Every icon sits inside a 36-44px pastel circle badge, colour-matched to its category (amber = understand, coral = practice, green = level check)
- Page background is cream (`#FFFCF6`), section backgrounds alternate white / warm cream (`#FFF9F0`) for gentle rhythm — never stark white-on-white
- Selected/active state = 2px solid orange border + light amber fill, not a colour swap, so it stays legible for colour-blind users
- Footer and utility text stay small and muted so the warm styling doesn't feel childish for Year 9 users

## 7. Homepage Wireframe (Section Order)

| # | Section | Content |
|---|---|---|
| 1 | Header | Logo, nav (How it works / Practice tests / Year levels), Sign up button |
| 2 | Hero | Headline, one-line value statement, 2 CTAs: "Take the level check" + "See test agenda" |
| 3 | 3-pillar strip | Understand the test / Practice questions / Check current level, each with icon + 1 line |
| 4 | Year picker | 4 cards: Year 3, 5, 7, 9 — click to filter rest of site |
| 5 | How it works | 3-step visual: Pick year → Practice or check level → Track progress |
| 6 | Trust strip | Curriculum-aligned badge, sample question preview, disclaimer (not affiliated with ACARA) |
| 7 | Footer | About, FAQ, Contact, Privacy, Terms |

## 8. Differentiators vs. Competitors

- Level check is the first CTA, not buried behind sign-up (unlike all three competitors)
- Test-agenda explainer page written in plain language for first-time parents
- Single-purpose navigation — no VCE/IB/ICAS clutter like SubjectCoach
- Progress dashboard combines band estimate + strand breakdown + recommended next practice in one view

## 9. Content & Data Storage

Where questions, quizzes, and results live:

| Data | Storage | Notes |
|---|---|---|
| Question bank (practice + diagnostic items) | Relational database (e.g. PostgreSQL) — a "questions" table tagged by year level, domain, strand, and difficulty | Authored and edited through an internal admin/CMS tool, not hardcoded in the app |
| Quiz/test definitions | Database — a "tests" table referencing ordered sets of question IDs, plus metadata (year, domain, time limit) | Diagnostic tests additionally store adaptive branching rules (next-question logic by correctness) |
| Images, audio, diagrams used in questions | Object storage (e.g. S3-compatible bucket) with the database storing only the file URL | Keeps the database lean; supports CDN delivery for fast loading |
| Student attempts & answers | Database — an "attempts" table linked to student profile, test ID, timestamps, and per-question responses | This is the record used to calculate band estimates and strand breakdowns |
| Progress & band history | Derived/aggregated table, recalculated from attempts | Powers the My Progress dashboard and trend charts |
| Draft/unpublished content | Same database, flagged with a "draft" status | Lets editors prepare new questions ahead of each NAPLAN cycle without exposing them early |

This keeps content (questions, tests) and behavioural data (attempts, progress) in clearly separated tables, so the question bank can be updated independently of live student results, and student data stays isolated for privacy and easier backup/export.

## 10. Next Steps

- Validate wireframe with 2-3 parent users
- Build content for "Understand the Test" page per year level
- Define diagnostic quiz item bank and scoring bands
- Build homepage + year-level pages in high-fidelity prototype
