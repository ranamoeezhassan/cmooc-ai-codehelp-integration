-- src/gened/migrations/20241214--codehelp--update_class_api_keys.sql
-- Rana Moeez Hassan

PRAGMA foreign_keys = OFF;
BEGIN;

-- Drop temporary table if it exists
DROP TABLE IF EXISTS __temp_classes_user;
CREATE TABLE __temp_classes_user AS SELECT * FROM classes_user;
DROP TABLE classes_user;
CREATE TABLE classes_user (
    class_id INTEGER PRIMARY KEY,
    dartmouth_key TEXT,
    model_id INTEGER NOT NULL DEFAULT 1,
    link_ident TEXT NOT NULL UNIQUE,
    link_reg_expires DATE NOT NULL,
    creator_user_id INTEGER NOT NULL,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(class_id) REFERENCES classes(id),
    FOREIGN KEY(model_id) REFERENCES models(id),
    FOREIGN KEY(creator_user_id) REFERENCES users(id)
);
INSERT INTO classes_user 
SELECT class_id, openai_key as dartmouth_key, model_id, link_ident, link_reg_expires, creator_user_id, created 
FROM __temp_classes_user;
DROP TABLE __temp_classes_user;

-- Drop temporary table if it exists
DROP TABLE IF EXISTS __temp_consumers;
CREATE TABLE __temp_consumers AS SELECT * FROM consumers;

COMMIT;
PRAGMA foreign_keys = ON;