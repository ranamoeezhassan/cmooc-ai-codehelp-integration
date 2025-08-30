-- Add algorea_id column to queries table with default value
ALTER TABLE queries ADD COLUMN algorea_id TEXT DEFAULT 'no_set_id';
