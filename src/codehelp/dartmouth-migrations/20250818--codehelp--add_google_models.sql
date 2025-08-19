-- SPDX-FileCopyrightText: 2025 
--
-- SPDX-License-Identifier: AGPL-3.0-only

BEGIN;

-- Add Google models
INSERT OR IGNORE INTO models(name, shortname, model, active) VALUES
    ('Google Gemini-2.5-Pro', 'Gemini-2.5-Pro', 'gemini-2.5-pro', 1),
    ('Google Gemini-2.5-Flash', 'Gemini-2.5-Flash', 'gemini-2.5-flash', 1),
    ('Google Gemini-2.5-Flash-Lite', 'Gemini-2.5-Flash-Lite', 'gemini-2.5-flash-lite', 1);

COMMIT;
