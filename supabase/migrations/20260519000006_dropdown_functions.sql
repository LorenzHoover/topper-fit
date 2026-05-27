-- Dropdown helper functions — return DISTINCT values without hitting the
-- PostgREST max_rows cap. Called via supabase.rpc() from the options API route.

CREATE OR REPLACE FUNCTION get_distinct_makes()
RETURNS TABLE(make TEXT)
LANGUAGE sql STABLE SECURITY DEFINER
AS $$
  SELECT DISTINCT make FROM truck_models ORDER BY make;
$$;

CREATE OR REPLACE FUNCTION get_distinct_models(p_make TEXT)
RETURNS TABLE(model TEXT)
LANGUAGE sql STABLE SECURITY DEFINER
AS $$
  SELECT DISTINCT model FROM truck_models
  WHERE make ILIKE p_make
  ORDER BY model;
$$;

CREATE OR REPLACE FUNCTION get_distinct_cabs(p_make TEXT, p_model TEXT, p_year INT DEFAULT NULL)
RETURNS TABLE(cab_style TEXT)
LANGUAGE sql STABLE SECURITY DEFINER
AS $$
  SELECT DISTINCT cab_style FROM truck_models
  WHERE make  ILIKE p_make
    AND model ILIKE p_model
    AND cab_style IS NOT NULL
    AND cab_style != ''
    AND (p_year IS NULL OR year = p_year)
  ORDER BY cab_style;
$$;
