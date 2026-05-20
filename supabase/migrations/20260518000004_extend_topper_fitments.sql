-- Extend topper_fitments with manufacturer-specific detail columns.
-- Motivation: LEER uses compound fit codes, SnugPro uses symbol codes —
-- a single confidence integer can't preserve that data. These columns hold
-- the raw manufacturer specifics while confidence remains the user-facing score.
-- All new columns are nullable so existing Ranch rows are unaffected.

-- ── New columns (IF NOT EXISTS guards let this re-run safely) ─────────────────

ALTER TABLE topper_fitments
  ADD COLUMN IF NOT EXISTS has_custom_fit          BOOLEAN,
  ADD COLUMN IF NOT EXISTS has_skirted_sides       BOOLEAN,
  ADD COLUMN IF NOT EXISTS door_type               TEXT,
  ADD COLUMN IF NOT EXISTS clamp_type_required     TEXT,
  ADD COLUMN IF NOT EXISTS bed_size_class          TEXT,
  ADD COLUMN IF NOT EXISTS model_id_alias          TEXT,
  ADD COLUMN IF NOT EXISTS camera_compatible       BOOLEAN,
  ADD COLUMN IF NOT EXISTS source_effective_date   DATE;

-- ── Expand fit_type constraint ────────────────────────────────────────────────
-- Drop the old constraint (Postgres auto-named it based on table+column).
-- IF EXISTS guards against re-running this migration.
ALTER TABLE topper_fitments
  DROP CONSTRAINT IF EXISTS topper_fitments_fit_type_check;

ALTER TABLE topper_fitments
  ADD CONSTRAINT topper_fitments_fit_type_check
  CHECK (fit_type IN (
    -- original values (Ranch data uses these)
    'OEM',                -- manufacturer-confirmed standard fit
    'cross_cab',          -- same generation, different cab style
    'cross_generation',   -- same bed length, different generation
    'with_modification',  -- fits but requires modification
    'incompatible',       -- confirmed does not fit (confidence = 0)
    'universal',          -- universal-mount (Ranch/ATC U typology)
    -- new values for LEER / SnugPro / forum data
    'non_custom',         -- fits but not contoured to truck (SnugPro text)
    'future_release',     -- planned / coming soon (SnugPro O, LEER placeholder)
    'aliased'             -- fits via another platform's assembly (LEER Model ID alias)
  ));

-- Back-fill source_effective_date for existing Ranch rows.
UPDATE topper_fitments
SET source_effective_date = '2025-07-01'
WHERE topper_brand = 'Ranch'
  AND source_effective_date IS NULL;
