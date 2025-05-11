-- src/gened/migrations/20241227--codehelp--add_mistral_models.sql
-- Rana Moeez Hassan

BEGIN;

-- Add new models with the updated endpoint, ignoring duplicates
INSERT OR IGNORE INTO models(name, shortname, model, active) VALUES
    ('Codestral Mamba', 'codestral-mamba', 'open-codestral-mamba', 1),
    ('Mistral Nemo', 'mistral-nemo', 'open-mistral-nemo', 1);

COMMIT;
