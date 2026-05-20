-- manufacturer_platform_codes: maps our canonical platform_id to each
-- manufacturer's internal code for the same physical bed.
--
-- Why this table exists:
--   Manufacturers don't agree on platform naming. LEER calls a 2021+ F-150
--   short bed "56FF21". SnugPro calls it "(F9)". Ranch has no code at all.
--   This join table lets us cross-reference without mangling our platform slugs,
--   and without inventing a universal standard that nobody uses.
--
-- Also useful for:
--   - Tying LEER parts/diagrams to our canonical platform
--   - Detecting when two manufacturers describe the same physical truck
--   - Eventual "this LEER code = that Ranch platform" matching

CREATE TABLE IF NOT EXISTS manufacturer_platform_codes (
  id                   SERIAL        PRIMARY KEY,
  platform_id          TEXT          NOT NULL REFERENCES bed_platforms(platform_id),
  manufacturer         TEXT          NOT NULL,  -- 'LEER', 'ATC', 'Ranch', 'SnugPro', etc.
  manufacturer_code    TEXT          NOT NULL,  -- e.g. '56FF21', 'C9', 'TU', 'F9'
  code_type            TEXT,                    -- 'model_id' / 'chassis_code' / 'internal'
  source_pdf           TEXT,                    -- filename of the PDF this came from
  notes                TEXT,
  created_at           TIMESTAMPTZ   DEFAULT NOW(),

  -- A manufacturer won't assign the same code to two different platforms
  UNIQUE (platform_id, manufacturer, manufacturer_code)
);

CREATE INDEX IF NOT EXISTS idx_mfr_codes_platform   ON manufacturer_platform_codes (platform_id);
CREATE INDEX IF NOT EXISTS idx_mfr_codes_mfr_code   ON manufacturer_platform_codes (manufacturer, manufacturer_code);

-- RLS: public read only — same pattern as other tables.
ALTER TABLE manufacturer_platform_codes ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "public can read manufacturer_platform_codes" ON manufacturer_platform_codes;
CREATE POLICY "public can read manufacturer_platform_codes"
  ON manufacturer_platform_codes FOR SELECT USING (true);
