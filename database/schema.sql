-- NAPLAN Prep Hub — database schema
-- Target: SQL Server, database "naplan-portal"
-- Matches design plan section 9 (Content & Data Storage):
--   questions / tests / test_questions  = content (question bank + quiz definitions)
--   attempts / attempt_answers          = behavioural data (kept separate from content)

IF DB_ID('naplan-portal') IS NULL
BEGIN
    RAISERROR('Database "naplan-portal" does not exist. Create it first (CREATE DATABASE [naplan-portal]).', 16, 1);
END
GO

USE [naplan-portal];
GO

-- ------------------------------------------------------------------
-- Reference tables
-- ------------------------------------------------------------------

IF OBJECT_ID('dbo.year_levels', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.year_levels (
        year_level_id   INT PRIMARY KEY,   -- 3, 5, 7, 9
        label           NVARCHAR(20) NOT NULL
    );
END
GO

IF OBJECT_ID('dbo.domains', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.domains (
        domain_id       INT IDENTITY(1,1) PRIMARY KEY,
        code            NVARCHAR(10) NOT NULL UNIQUE,   -- R, W, LC, N
        name            NVARCHAR(50) NOT NULL           -- Reading, Writing, Language Conventions, Numeracy
    );
END
GO

-- ------------------------------------------------------------------
-- Content: question bank
-- ------------------------------------------------------------------

IF OBJECT_ID('dbo.questions', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.questions (
        question_id     INT IDENTITY(1,1) PRIMARY KEY,
        year_level_id   INT NOT NULL FOREIGN KEY REFERENCES dbo.year_levels(year_level_id),
        domain_id       INT NOT NULL FOREIGN KEY REFERENCES dbo.domains(domain_id),
        strand          NVARCHAR(50) NULL,              -- e.g. Number, Geometry, Grammar, Comprehension
        difficulty      TINYINT NOT NULL DEFAULT 2,      -- 1 = easy, 2 = medium, 3 = hard
        question_type   NVARCHAR(20) NOT NULL DEFAULT 'multiple_choice', -- multiple_choice, short_answer, drag_drop
        prompt          NVARCHAR(MAX) NOT NULL,
        option_a        NVARCHAR(500) NULL,
        option_b        NVARCHAR(500) NULL,
        option_c        NVARCHAR(500) NULL,
        option_d        NVARCHAR(500) NULL,
        correct_answer  NVARCHAR(500) NOT NULL,
        explanation     NVARCHAR(MAX) NULL,
        media_url       NVARCHAR(500) NULL,              -- object storage URL for images/audio
        status          NVARCHAR(10) NOT NULL DEFAULT 'draft', -- draft, published
        created_at      DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );
END
GO

-- content_year tags a question with the practice "edition" it belongs to
-- (e.g. 2023-2026), so the bank can be filtered to a rolling window of
-- the most recent editions and pruned as older editions age out.
IF COL_LENGTH('dbo.questions', 'content_year') IS NULL
BEGIN
    ALTER TABLE dbo.questions ADD content_year INT NULL;
END
GO

-- ------------------------------------------------------------------
-- Content: quiz / test definitions
-- ------------------------------------------------------------------

IF OBJECT_ID('dbo.tests', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.tests (
        test_id         INT IDENTITY(1,1) PRIMARY KEY,
        year_level_id   INT NOT NULL FOREIGN KEY REFERENCES dbo.year_levels(year_level_id),
        domain_id       INT NULL FOREIGN KEY REFERENCES dbo.domains(domain_id), -- NULL for mixed-domain diagnostics
        title           NVARCHAR(200) NOT NULL,
        test_type       NVARCHAR(20) NOT NULL DEFAULT 'practice', -- practice, diagnostic
        time_limit_mins INT NOT NULL DEFAULT 20,
        status          NVARCHAR(10) NOT NULL DEFAULT 'draft',
        created_at      DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );
END
GO

-- content_year tags a test/quiz with its practice edition, mirroring
-- dbo.questions.content_year.
IF COL_LENGTH('dbo.tests', 'content_year') IS NULL
BEGIN
    ALTER TABLE dbo.tests ADD content_year INT NULL;
END
GO

IF OBJECT_ID('dbo.test_questions', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.test_questions (
        test_id         INT NOT NULL FOREIGN KEY REFERENCES dbo.tests(test_id),
        question_id     INT NOT NULL FOREIGN KEY REFERENCES dbo.questions(question_id),
        sequence_no     INT NOT NULL,
        PRIMARY KEY (test_id, question_id)
    );
END
GO

-- ------------------------------------------------------------------
-- Behavioural data: kept in separate tables from content
-- ------------------------------------------------------------------

IF OBJECT_ID('dbo.students', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.students (
        student_id      INT IDENTITY(1,1) PRIMARY KEY,
        display_name    NVARCHAR(100) NOT NULL,
        year_level_id   INT NOT NULL FOREIGN KEY REFERENCES dbo.year_levels(year_level_id),
        email           NVARCHAR(255) NULL,
        password_hash   NVARCHAR(255) NULL,
        created_at      DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );
    CREATE UNIQUE INDEX UX_students_email ON dbo.students(email) WHERE email IS NOT NULL;
END
GO

-- Guarded ALTERs so login/history work on a DB where dbo.students already
-- existed before the auth feature was added (mirrors the content_year
-- pattern above) — see database/migrate_auth.sql for the one-off migration
-- this codifies for future fresh-schema runs.
IF COL_LENGTH('dbo.students', 'email') IS NULL
BEGIN
    ALTER TABLE dbo.students ADD email NVARCHAR(255) NULL;
END
GO

IF COL_LENGTH('dbo.students', 'password_hash') IS NULL
BEGIN
    ALTER TABLE dbo.students ADD password_hash NVARCHAR(255) NULL;
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UX_students_email')
BEGIN
    CREATE UNIQUE INDEX UX_students_email ON dbo.students(email) WHERE email IS NOT NULL;
END
GO

IF OBJECT_ID('dbo.attempts', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.attempts (
        attempt_id      INT IDENTITY(1,1) PRIMARY KEY,
        student_id      INT NOT NULL FOREIGN KEY REFERENCES dbo.students(student_id),
        test_id         INT NOT NULL FOREIGN KEY REFERENCES dbo.tests(test_id),
        started_at      DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        completed_at    DATETIME2 NULL,
        score            DECIMAL(5,2) NULL,
        band_estimate   NVARCHAR(50) NULL
    );
END
GO

IF OBJECT_ID('dbo.attempt_answers', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.attempt_answers (
        attempt_answer_id INT IDENTITY(1,1) PRIMARY KEY,
        attempt_id      INT NOT NULL FOREIGN KEY REFERENCES dbo.attempts(attempt_id),
        question_id     INT NOT NULL FOREIGN KEY REFERENCES dbo.questions(question_id),
        student_answer  NVARCHAR(MAX) NULL,      -- MAX so full writing-task essays fit, not just short MC answers
        is_correct      BIT NULL,
        written_score   DECIMAL(5,2) NULL,      -- rubric score (0-100) for open-response/writing answers
        written_feedback NVARCHAR(MAX) NULL,     -- JSON: {score_percent, criteria[], comments[]}
        answered_at     DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );
END
GO

-- Guarded ALTERs for the writing-assessment feature, same pattern as
-- content_year / students.email above (existing table predates this).
IF COL_LENGTH('dbo.attempt_answers', 'written_score') IS NULL
BEGIN
    ALTER TABLE dbo.attempt_answers ADD written_score DECIMAL(5,2) NULL;
END
GO

IF COL_LENGTH('dbo.attempt_answers', 'written_feedback') IS NULL
BEGIN
    ALTER TABLE dbo.attempt_answers ADD written_feedback NVARCHAR(MAX) NULL;
END
GO

-- Widen student_answer from the original NVARCHAR(500) — writing-task
-- essays routinely exceed that and were failing every submit with a
-- truncation error (COL_LENGTH returns -1 once it's already NVARCHAR(MAX)).
IF COL_LENGTH('dbo.attempt_answers', 'student_answer') <> -1
BEGIN
    ALTER TABLE dbo.attempt_answers ALTER COLUMN student_answer NVARCHAR(MAX) NULL;
END
GO

PRINT 'Schema created successfully.';
