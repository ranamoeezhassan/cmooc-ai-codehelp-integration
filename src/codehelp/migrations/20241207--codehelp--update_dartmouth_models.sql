-- src/gened/migrations/20241207--codehelp--update_dartmouth_models.sql
-- Rana Moeez Hassan

PRAGMA foreign_keys = OFF;

BEGIN;

-- Update models table with Dartmouth models
UPDATE models SET 
    name='Dartmouth CodeLlama 13B',
    shortname='CodeLlama-13B',
    model='codellama-13b-instruct-hf'
WHERE model='gpt-4o';

UPDATE models SET
    name='Dartmouth Llama 3',
    shortname='Llama-3',
    model='llama-3-1-8b-instruct'
WHERE model='gpt-4o-mini';

COMMIT;

PRAGMA foreign_keys = ON;