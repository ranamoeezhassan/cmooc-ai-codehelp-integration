-- src/gened/migrations/[timestamp]_add_dartmouth_models.sql

PRAGMA foreign_keys = OFF;

BEGIN;

-- Update models table with Dartmouth models
UPDATE models SET 
    name='CodeLlama 13B'
    model='/api/ai/tgi/codellama-13b-instruct-hf/generate'
WHERE model='codellama-13b-instruct-hf';

UPDATE models SET
    name='Llama 3-1 8B'
    model='/api/ai/tgi/llama-3-1-8b-instruct/generate'
WHERE model='llama-3-1-8b-instruct';


-- Add only new models not covered by update_dartmouth_models.sql
INSERT INTO models(name, shortname, model, active) VALUES
    ('Llama 3 8B Instruct', 'llama-3-8b', '/api/ai/tgi/llama-3-8b-instruct/generate', 1),
    ('CodeLlama 13B Python', 'codellama-13b-py', '/api/ai/tgi/codellama-13b-python-hf/generate', 1);

COMMIT;

PRAGMA foreign_keys = ON;