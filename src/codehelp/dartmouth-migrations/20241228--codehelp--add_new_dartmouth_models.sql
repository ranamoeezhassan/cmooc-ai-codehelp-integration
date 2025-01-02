-- src/gened/migrations/20241227--codehelp--add_new_dartmouth_models.sql
-- Rana Moeez Hassan

PRAGMA foreign_keys = OFF;

BEGIN;

UPDATE models SET active = 0;

-- Add only new models not covered by update_dartmouth_models.sql
INSERT INTO models(name, shortname, model, active) VALUES
    ('CodeLlama 13B', 'codellama-13b', '/api/ai/tgi/codellama-13b-instruct-hf/generate', 1),
    ('Llama 3 8B Instruct', 'llama-3-8b', '/api/ai/tgi/llama-3-8b-instruct/generate', 1),
    ('Llama 3-1 8B', 'llama-3-1-8b', '/api/ai/tgi/llama-3-1-8b-instruct/generate', 1),
    ('CodeLlama 13B Python', 'codellama-13b-py', '/api/ai/tgi/codellama-13b-python-hf/generate', 1);

COMMIT;

PRAGMA foreign_keys = ON;