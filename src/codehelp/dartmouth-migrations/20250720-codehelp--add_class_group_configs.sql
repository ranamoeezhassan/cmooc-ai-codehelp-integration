-- SPDX-FileCopyrightText: 2025 Rana Moeez Hassan
--
-- SPDX-License-Identifier: AGPL-3.0-only

-- Migration: Add class_group_configs table for group configuration per class
-- Date: 2025-07-20

BEGIN;

CREATE TABLE IF NOT EXISTS class_group_configs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id    INTEGER NOT NULL,
    group_num   INTEGER NOT NULL, -- 1-based index for group
    prompt      TEXT NOT NULL,
    num_groups  INTEGER NOT NULL, -- total number of groups for this class
    created     DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated     DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(class_id) REFERENCES classes(id)
);

COMMIT;