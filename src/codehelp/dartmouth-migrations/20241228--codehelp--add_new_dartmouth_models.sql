-- src/gened/migrations/20241227--codehelp--add_new_dartmouth_models.sql
-- Rana Moeez Hassan
PRAGMA foreign_keys = OFF;
BEGIN;

-- Deactivate existing models and activate new models in one statement
UPDATE models 
SET active = CASE 
                WHEN name IN ('CodeLlama 13B', 'Llama 3 8B Instruct', 'Llama 3-1 8B', 'CodeLlama 13B Python') THEN 1
                ELSE 0
             END;

-- Add new models with the updated endpoint, ignoring duplicates
INSERT OR IGNORE INTO models(name, shortname, model, active) VALUES
    ('CodeLlama 13B', 'codellama-13b', '/api/ai/tgi/codellama-13b-instruct-hf/v1/chat/completions', 1),
    ('Llama 3 8B Instruct', 'llama-3-8b', '/api/ai/tgi/llama-3-8b-instruct/v1/chat/completions', 1),
    ('Llama 3-1 8B', 'llama-3-1-8b', '/api/ai/tgi/llama-3-1-8b-instruct/v1/chat/completions', 1),
    ('CodeLlama 13B Python', 'codellama-13b-py', '/api/ai/tgi/codellama-13b-python-hf/v1/chat/completions', 1);

-- Optional: Update existing records to use the new endpoint for models that still need to be active
UPDATE models
SET model = REPLACE(model, '/generate', '/v1/chat/completions')
WHERE model LIKE '%/generate';

COMMIT;
PRAGMA foreign_keys = ON;