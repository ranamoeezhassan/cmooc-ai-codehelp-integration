-- SPDX-FileCopyrightText: 2025 
--
-- SPDX-License-Identifier: AGPL-3.0-only

BEGIN;

-- Add new GPT-5 models
INSERT OR IGNORE INTO models(name, shortname, model, active) VALUES
    ('OpenAI GPT-5', 'GPT-5', 'gpt-5', 1),
    ('OpenAI GPT-5 Mini', 'GPT-5-mini', 'gpt-5-mini', 1),
    ('OpenAI GPT-5 Nano', 'GPT-5-nano', 'gpt-5-nano', 1);

-- Reactivate existing OpenAI models
UPDATE models 
SET active = 1 
WHERE shortname IN ('GPT-4o', 'GPT-4o-mini', 'GPT-3.5');

COMMIT;
