-- NAPLAN Prep Hub — migration: fix band_estimate truncation bug, add login
-- credentials to dbo.students so students can have an account with history.
--
-- SQL Server-only historical record, kept for reference. Superseded by
-- database/schema.sql, which now creates band_estimate/email/password_hash
-- with their final shapes directly — a fresh PostgreSQL install never
-- needs this file. Do not run this against Postgres.

USE [naplan-portal];
GO

-- Bug fix: band_estimate strings like "Working towards expected standard"
-- (33 chars) didn't fit in NVARCHAR(20), causing every submit to fail.
ALTER TABLE dbo.attempts ALTER COLUMN band_estimate NVARCHAR(50) NULL;
GO

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

PRINT 'Auth migration applied successfully.';
