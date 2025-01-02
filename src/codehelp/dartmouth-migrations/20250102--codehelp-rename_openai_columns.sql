-- src/gened/migrations/20250102--codehelp-rename_openai_columns.sql

PRAGMA foreign_keys = OFF;
BEGIN;

-- Check if column 'openai_key' exists in 'classes_user' table and rename it to 'dartmouth_key'
CREATE TEMPORARY TABLE temp_table_info AS
SELECT * FROM pragma_table_info('classes_user') WHERE name = 'openai_key';

-- If the column exists, rename it
INSERT INTO temp_table_info (name)
SELECT 'dartmouth_key' WHERE EXISTS (SELECT 1 FROM temp_table_info);

DROP TABLE temp_table_info;

-- Rename column in classes_user table if it exists
ALTER TABLE classes_user RENAME COLUMN openai_key TO dartmouth_key;

-- Check if column 'openai_key' exists in 'consumers' table and rename it to 'dartmouth_key'
CREATE TEMPORARY TABLE temp_table_info AS
SELECT * FROM pragma_table_info('consumers') WHERE name = 'openai_key';

-- If the column exists, rename it
INSERT INTO temp_table_info (name)
SELECT 'dartmouth_key' WHERE EXISTS (SELECT 1 FROM temp_table_info);

DROP TABLE temp_table_info;

-- Rename column in consumers table if it exists
ALTER TABLE consumers RENAME COLUMN openai_key TO dartmouth_key;

COMMIT;
PRAGMA foreign_keys = ON;