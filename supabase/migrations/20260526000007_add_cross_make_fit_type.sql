-- Add cross_make fit_type for community-reported fits where the topper was
-- designed for a completely different make/model truck (e.g. F-150 shell on Tundra).
-- Distinct from cross_generation (same truck, different year) and
-- cross_cab (same truck/gen, different cab configuration).

ALTER TABLE topper_fitments
  DROP CONSTRAINT IF EXISTS topper_fitments_fit_type_check;

ALTER TABLE topper_fitments
  ADD CONSTRAINT topper_fitments_fit_type_check
  CHECK (fit_type IN (
    'OEM',               -- manufacturer-confirmed standard fit
    'cross_cab',         -- same generation, different cab style
    'cross_generation',  -- same make/model, different year range
    'cross_make',        -- different make or model entirely (e.g. F-150 shell on Tundra)
    'with_modification', -- fits but requires physical modification
    'incompatible',      -- confirmed does not fit (confidence = 0)
    'universal',         -- universal-mount product (Ranch/ATC U typology)
    'non_custom',        -- fits but not contoured to truck body (SnugPro)
    'future_release',    -- planned / coming soon
    'aliased'            -- fits via another platform's assembly (LEER alias codes)
  ));
