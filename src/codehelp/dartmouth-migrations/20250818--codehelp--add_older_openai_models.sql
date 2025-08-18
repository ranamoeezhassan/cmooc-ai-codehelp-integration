-- SPDX-FileCopyrightText: 2024.1 
--
-- SPDX-License-Identifier: AGPL-3.0-only

BEGIN;

-- Add new GPT-4.1 models
INSERT OR IGNORE INTO models(name, shortname, model, active) VALUES
    ('OpenAI GPT-4.1', 'GPT-4.1', 'gpt-4.1', 1),
    ('OpenAI GPT-4.1 Mini', 'GPT-4.1-mini', 'gpt-4.1-mini', 1),
    ('OpenAI GPT-4.1 Nano', 'GPT-4.1-nano', 'gpt-4.1-nano', 1);


COMMIT;
