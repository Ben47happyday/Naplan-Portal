-- NAPLAN Prep Hub — database schema
-- Target: PostgreSQL, connected via DATABASE_URL (see config.py)
-- Matches design plan section 9 (Content & Data Storage):
--   questions / tests / test_questions  = content (question bank + quiz definitions)
--   attempts / attempt_answers          = behavioural data (kept separate from content)
--
-- Ported from the original SQL Server schema. Objects live under a "dbo"
-- schema (rather than Postgres's default "public") purely so every
-- dbo.<table> reference already written throughout the app/scripts keeps
-- working unchanged. Safe to run repeatedly: every statement is guarded
-- with IF NOT EXISTS.

CREATE SCHEMA IF NOT EXISTS dbo;

-- Needed for gen_random_uuid() on Postgres < 13 (a no-op, and harmless,
-- on 13+ where the function is built in).
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ------------------------------------------------------------------
-- Reference tables
-- ------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS dbo.year_levels (
    year_level_id   INT PRIMARY KEY,   -- 3, 5, 7, 9
    label           VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS dbo.domains (
    domain_id       INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code            VARCHAR(10) NOT NULL UNIQUE,   -- R, W, LC, N
    name            VARCHAR(50) NOT NULL           -- Reading, Writing, Language Conventions, Numeracy
);

-- ------------------------------------------------------------------
-- Content: question bank
-- ------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS dbo.questions (
    question_id     INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    year_level_id   INT NOT NULL REFERENCES dbo.year_levels(year_level_id),
    domain_id       INT NOT NULL REFERENCES dbo.domains(domain_id),
    strand          VARCHAR(50) NULL,              -- e.g. Number, Geometry, Grammar, Comprehension
    difficulty      SMALLINT NOT NULL DEFAULT 2,    -- 1 = easy, 2 = medium, 3 = hard
    question_type   VARCHAR(20) NOT NULL DEFAULT 'multiple_choice', -- multiple_choice, short_answer, drag_drop
    prompt          TEXT NOT NULL,
    option_a        VARCHAR(500) NULL,
    option_b        VARCHAR(500) NULL,
    option_c        VARCHAR(500) NULL,
    option_d        VARCHAR(500) NULL,
    correct_answer  VARCHAR(500) NOT NULL,
    explanation     TEXT NULL,
    media_url       VARCHAR(500) NULL,              -- object storage URL for images/audio
    status          VARCHAR(10) NOT NULL DEFAULT 'draft', -- draft, published
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- content_year tags a question with the practice "edition" it belongs
    -- to (e.g. 2023-2026), so the bank can be filtered to a rolling window
    -- of the most recent editions and pruned as older editions age out.
    content_year    INT NULL
);

ALTER TABLE dbo.questions ADD COLUMN IF NOT EXISTS content_year INT NULL;

-- ------------------------------------------------------------------
-- Content: quiz / test definitions
-- ------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS dbo.tests (
    test_id         INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    year_level_id   INT NOT NULL REFERENCES dbo.year_levels(year_level_id),
    domain_id       INT NULL REFERENCES dbo.domains(domain_id), -- NULL for mixed-domain diagnostics
    title           VARCHAR(200) NOT NULL,
    test_type       VARCHAR(20) NOT NULL DEFAULT 'practice', -- practice, diagnostic
    time_limit_mins INT NOT NULL DEFAULT 20,
    status          VARCHAR(10) NOT NULL DEFAULT 'draft',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- content_year tags a test/quiz with its practice edition, mirroring
    -- dbo.questions.content_year.
    content_year    INT NULL
);

ALTER TABLE dbo.tests ADD COLUMN IF NOT EXISTS content_year INT NULL;

CREATE TABLE IF NOT EXISTS dbo.test_questions (
    test_id         INT NOT NULL REFERENCES dbo.tests(test_id),
    question_id     INT NOT NULL REFERENCES dbo.questions(question_id),
    sequence_no     INT NOT NULL,
    PRIMARY KEY (test_id, question_id)
);

-- ------------------------------------------------------------------
-- Behavioural data: kept in separate tables from content
-- ------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS dbo.students (
    student_id      INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    display_name    VARCHAR(100) NOT NULL,
    year_level_id   INT NOT NULL REFERENCES dbo.year_levels(year_level_id),
    email           VARCHAR(255) NULL,
    password_hash   VARCHAR(255) NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE dbo.students ADD COLUMN IF NOT EXISTS email VARCHAR(255) NULL;
ALTER TABLE dbo.students ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255) NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_students_email ON dbo.students(email) WHERE email IS NOT NULL;

CREATE TABLE IF NOT EXISTS dbo.attempts (
    attempt_id      INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    student_id      INT NOT NULL REFERENCES dbo.students(student_id),
    test_id         INT NOT NULL REFERENCES dbo.tests(test_id),
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ NULL,
    score           DECIMAL(5,2) NULL,
    -- Widened from an original VARCHAR(20) in the SQL Server version: band
    -- labels like "Working towards expected standard" (33 chars) didn't
    -- fit and every submit failed with a truncation error.
    band_estimate   VARCHAR(50) NULL
);

CREATE TABLE IF NOT EXISTS dbo.attempt_answers (
    attempt_answer_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    attempt_id      INT NOT NULL REFERENCES dbo.attempts(attempt_id),
    question_id     INT NOT NULL REFERENCES dbo.questions(question_id),
    -- TEXT so full writing-task essays fit, not just short MC answers.
    student_answer  TEXT NULL,
    is_correct      BOOLEAN NULL,
    written_score   DECIMAL(5,2) NULL,      -- rubric score (0-100) for open-response/writing answers
    written_feedback TEXT NULL,             -- JSON: {score_percent, criteria[], comments[]}
    answered_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE dbo.attempt_answers ADD COLUMN IF NOT EXISTS written_score DECIMAL(5,2) NULL;
ALTER TABLE dbo.attempt_answers ADD COLUMN IF NOT EXISTS written_feedback TEXT NULL;

-- ------------------------------------------------------------------
-- Marketing: B2B lead outreach (separate domain from students/content —
-- receivers are tutoring-centre/agent leads, not NAPLAN students).
-- Send/open/click are kept as separate event tables (not counters on
-- campaign_sends) so every engagement event is recorded for analysis,
-- mirroring the attempts/attempt_answers behavioural-data pattern above.
-- ------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS dbo.campaign_receivers (
    receiver_id      INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    org_name         VARCHAR(200) NOT NULL,
    email            VARCHAR(255) NOT NULL,
    phone            VARCHAR(50) NULL,
    address          VARCHAR(300) NULL,
    region           VARCHAR(100) NULL,
    source           VARCHAR(100) NULL,        -- e.g. 'naplan_sydney_agent_leads.csv'
    selection_reason VARCHAR(500) NULL,
    is_unsubscribed  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_campaign_receivers_email ON dbo.campaign_receivers(email);

CREATE TABLE IF NOT EXISTS dbo.campaigns (
    campaign_id      INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name             VARCHAR(200) NOT NULL,
    subject_template VARCHAR(300) NOT NULL,
    template_path    VARCHAR(300) NOT NULL,
    sender_email     VARCHAR(255) NOT NULL,
    learn_more_url   VARCHAR(500) NULL,
    status           VARCHAR(20) NOT NULL DEFAULT 'draft',  -- draft, sending, completed
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS dbo.campaign_sends (
    send_id          INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    campaign_id      INT NOT NULL REFERENCES dbo.campaigns(campaign_id),
    receiver_id      INT NOT NULL REFERENCES dbo.campaign_receivers(receiver_id),
    tracking_token   UUID NOT NULL DEFAULT gen_random_uuid(),  -- embedded in pixel/redirect URLs
    status           VARCHAR(10) NOT NULL DEFAULT 'sent',      -- sent, failed (matches marketing/*_sent_log.csv status values)
    error_detail     VARCHAR(1000) NULL,
    sent_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_campaign_sends_tracking_token ON dbo.campaign_sends(tracking_token);

CREATE TABLE IF NOT EXISTS dbo.campaign_opens (
    open_id          INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    send_id          INT NOT NULL REFERENCES dbo.campaign_sends(send_id),
    opened_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    ip_address       VARCHAR(45) NULL,
    user_agent       VARCHAR(500) NULL
);

CREATE TABLE IF NOT EXISTS dbo.campaign_clicks (
    click_id         INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    send_id          INT NOT NULL REFERENCES dbo.campaign_sends(send_id),
    clicked_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    target_url       VARCHAR(500) NULL,
    ip_address       VARCHAR(45) NULL,
    user_agent       VARCHAR(500) NULL
);

-- Run via: python create_schema.py  (see database/config.py for connection)
