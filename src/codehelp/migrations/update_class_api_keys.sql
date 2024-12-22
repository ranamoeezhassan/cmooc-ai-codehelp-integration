-- src/gened/migrations/20240307--update_api_keys.sql

PRAGMA foreign_keys = OFF;

BEGIN;

-- Drop old views/indexes if they exist
DROP VIEW IF EXISTS __temp_view;
DROP TABLE IF EXISTS __temp_table;

-- Create temporary table for classes_user
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

-- Create temporary table for consumers
CREATE TABLE __temp_consumers AS SELECT * FROM consumers;
DROP TABLE consumers;
CREATE TABLE consumers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lti_consumer TEXT NOT NULL UNIQUE,
    lti_secret TEXT,
    dartmouth_key TEXT,
    model_id INTEGER NOT NULL,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(model_id) REFERENCES models(id)
);
INSERT INTO consumers 
SELECT id, lti_consumer, lti_secret, openai_key as dartmouth_key, model_id, created 
FROM __temp_consumers;
DROP TABLE __temp_consumers;

COMMIT;

PRAGMA foreign_keys = ON;