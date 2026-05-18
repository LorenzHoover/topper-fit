-- truck_models: user-facing truck specs that resolve to a bed_platform.
-- This is the lookup table the user's year/make/model/trim/cab input gets matched against.
-- Many truck_models rows point to the same platform_id because one physical
-- bed configuration covers many model-year/trim combinations.
--
-- VIN decode caveats (important for the UI):
--   - vin_decodable_trim: whether VIN reliably encodes trim level
--   - vin_decodable_bed:  whether VIN reliably encodes bed length / cab style
--   Both are yes/no/partial per make. Toyota in particular doesn't encode bed in VIN.
--   The UI must prompt for missing fields even after VIN decode.

CREATE TABLE truck_models (
  id                  SERIAL      PRIMARY KEY,
  year                INTEGER     NOT NULL,
  make                TEXT        NOT NULL,
  model               TEXT        NOT NULL,
  trim                TEXT,                    -- NULL means "all trims" for this row
  cab_style           TEXT,
  bed_length_label    TEXT,                    -- user-facing label e.g. "5.5 ft", "6.5 ft", "8 ft"
  platform_id         TEXT        REFERENCES bed_platforms(platform_id),
  vin_decodable_trim  TEXT        DEFAULT 'partial' CHECK (vin_decodable_trim IN ('yes', 'no', 'partial')),
  vin_decodable_bed   TEXT        DEFAULT 'partial' CHECK (vin_decodable_bed  IN ('yes', 'no', 'partial')),
  notes               TEXT,
  source_urls         TEXT,
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Primary lookup path: user enters year + make + model, we resolve to platform_id.
CREATE INDEX idx_truck_models_ymm ON truck_models (year, make, model);
CREATE INDEX idx_truck_models_platform ON truck_models (platform_id);
