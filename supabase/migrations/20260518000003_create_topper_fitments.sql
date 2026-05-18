-- topper_fitments: the core fitment matrix.
-- Each row says: "This brand/model/year-range topper fits (or doesn't fit) this platform,
-- with this confidence level and these notes."
--
-- IMPORTANT key design: topper_brand + topper_model_series + year range is the real key.
-- The same model series name in different production years can have different mounting hardware.
-- e.g., LEER 100XR pre-2015 ≠ LEER 100XR post-2015 — different clamp system.
--
-- wrap_type encoding from manufacturer language:
--   W = Wraps over bedrails (sits on top of rail)
--   X = sits inside (eXtended below) rails
--   U = Universal fit
--
-- fit_type values:
--   OEM              = manufacturer explicitly confirms this fit
--   cross_cab        = same generation, different cab style (usually minor sealing difference)
--   cross_generation = same brand/bed length, different body generation (expect gaps or hardware mismatch)
--   with_modification = will fit but requires drilling, adapter, or custom clamp
--   incompatible     = confirmed does not fit (recorded to prevent bad purchases)
--   universal        = brand markets as fitting multiple platforms
--
-- confidence scale:
--   100 = OEM manufacturer-confirmed
--    85 = different cab style, same generation (minor cosmetic/sealing issues)
--    70 = same brand/length, different generation (gap or different mounting needed)
--    50 = fits with custom modifications
--     0 = will not fit

CREATE TABLE topper_fitments (
  id                          SERIAL      PRIMARY KEY,
  topper_brand                TEXT        NOT NULL,
  topper_model_series         TEXT        NOT NULL,
  topper_production_year_start INTEGER,
  topper_production_year_end   INTEGER,    -- NULL = currently in production
  fits_platform_id            TEXT        REFERENCES bed_platforms(platform_id),
  confidence                  INTEGER     CHECK (confidence >= 0 AND confidence <= 100),
  fit_type                    TEXT        CHECK (fit_type IN (
                                'OEM', 'cross_cab', 'cross_generation',
                                'with_modification', 'incompatible', 'universal'
                              )),
  wrap_type                   TEXT        CHECK (wrap_type IN ('W', 'X', 'U')),
  fit_notes                   TEXT,        -- free text; SEO content + user-facing nuance
  mounting_clamp_type         TEXT,
  required_modifications      TEXT,
  source_urls                 TEXT,        -- pipe-separated list of source URLs
  verified_by                 TEXT        CHECK (verified_by IN (
                                'manufacturer', 'retailer', 'forum',
                                'owner_report', 'personal_verification'
                              )),
  created_at                  TIMESTAMPTZ DEFAULT NOW(),
  updated_at                  TIMESTAMPTZ DEFAULT NOW()
);

-- Primary query: given a platform_id, find all fitting toppers.
CREATE INDEX idx_topper_fitments_platform ON topper_fitments (fits_platform_id);

-- Secondary: browse by brand.
CREATE INDEX idx_topper_fitments_brand ON topper_fitments (topper_brand, topper_model_series);

-- Partial index to quickly find high-confidence fitments only.
CREATE INDEX idx_topper_fitments_confident ON topper_fitments (fits_platform_id, confidence)
  WHERE confidence >= 70;
