-- Migration: Rename prompt column to expanded and add raw column in class_group_configs table

-- Step 1: Create new table with the desired structure
CREATE TABLE IF NOT EXISTS class_group_configs_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER NOT NULL,
    group_num INTEGER NOT NULL,
    expanded TEXT NOT NULL,
    raw TEXT NOT NULL DEFAULT '',
    num_groups INTEGER NOT NULL,
    created DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(class_id) REFERENCES classes(id)
);

-- Step 2: Copy data from old table to new table (prompt -> expanded, raw defaults to empty)
INSERT INTO class_group_configs_new (id, class_id, group_num, expanded, raw, num_groups, created, updated)
SELECT id, class_id, group_num, prompt, '', num_groups, created, updated
FROM class_group_configs;

-- Step 3: Drop the old table
DROP TABLE class_group_configs;

-- Step 4: Rename the new table to the original name
ALTER TABLE class_group_configs_new RENAME TO class_group_configs;