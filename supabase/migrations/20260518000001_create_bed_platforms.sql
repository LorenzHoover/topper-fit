-- bed_platforms: one row per distinct physical truck bed configuration.
-- Toppers fit platforms, not individual truck year/make/model rows.
-- A single platform often spans multiple model years and sometimes multiple makes
-- (e.g., Chevy Silverado and GMC Sierra share platforms exactly).
--
-- platform_id is a human-readable slug: {MAKE_SHORT}-{GEN}-{CAB}-{BED}
-- e.g., TUN-1G-AC-SB  (Tundra, 1st gen, Access Cab, Short Bed)
--       F150-12G-SC-SB (F-150, 12th gen, SuperCrew, Short Bed)

CREATE TABLE bed_platforms (
  platform_id                     TEXT PRIMARY KEY,
  nickname                        TEXT,                    -- friendly name for display
  make                            TEXT        NOT NULL,
  model_family                    TEXT        NOT NULL,    -- e.g. "Tundra", "F-150", "Silverado 1500"
  generation                      TEXT,                    -- e.g. "1st", "12th", "4th"
  production_year_start           INTEGER,
  production_year_end             INTEGER,                 -- NULL = still in production
  cab_style                       TEXT,                    -- "Regular Cab", "Access Cab", "Double Cab", "Crew Cab", etc.
  bed_length_class                TEXT,                    -- "Short Bed", "Standard Bed", "Long Bed"
  bed_length_floor_inches         NUMERIC(6,2),            -- interior floor length
  bed_length_rail_inches          NUMERIC(6,2),            -- length measured along top of rail
  bed_width_at_rail_inches        NUMERIC(6,2),            -- inner width at rail level
  bed_width_outer_inches          NUMERIC(6,2),            -- outer body width at bed
  bed_depth_inches                NUMERIC(6,2),            -- rail top to floor
  rail_profile_shape              TEXT,                    -- e.g. "rectangular", "tapered", "rounded"
  rail_cross_section_width_inches NUMERIC(5,2),
  rail_cross_section_height_inches NUMERIC(5,2),
  stake_pockets_present           BOOLEAN,
  stake_pocket_count_per_side     INTEGER,
  stake_pocket_length_inches      NUMERIC(5,2),
  stake_pocket_width_inches       NUMERIC(5,2),
  utility_track_system            TEXT        DEFAULT 'none', -- none, BoxLink, RamBox, MultiPro, Deck_Rail
  cab_back_generation             TEXT,                    -- for cross-generation cab-back compatibility notes
  cab_camera_present              BOOLEAN,
  tailgate_variant                TEXT        DEFAULT 'Standard', -- Standard, MultiFlex, MultiPro, Pro Access, etc.
  notes                           TEXT,
  source_urls                     TEXT,                    -- pipe-separated list of source URLs
  created_at                      TIMESTAMPTZ DEFAULT NOW(),
  updated_at                      TIMESTAMPTZ DEFAULT NOW()
);

-- Most queries hit (make, model_family, cab_style) when resolving a user's truck.
CREATE INDEX idx_bed_platforms_make_model ON bed_platforms (make, model_family);
CREATE INDEX idx_bed_platforms_year_range ON bed_platforms (production_year_start, production_year_end);
