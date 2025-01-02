-- src/gened/migrations/20241219--codehelp--add_query_tracking.sql
-- Rana Moeez Hassan

BEGIN;

-- Check if the column 'queries_used' exists in the 'users' table
PRAGMA table_info(users);
-- If the column does not exist, add it
ALTER TABLE users ADD COLUMN queries_used INTEGER DEFAULT 0;

-- Check if the column 'max_queries' exists in the 'classes' table
PRAGMA table_info(classes);
-- If the column does not exist, add it
ALTER TABLE classes ADD COLUMN max_queries INTEGER DEFAULT 50;

COMMIT;