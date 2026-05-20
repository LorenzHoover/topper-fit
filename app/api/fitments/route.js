import { NextResponse } from 'next/server'
import { supabase } from '@/lib/supabase'

// GET /api/fitments?year=2023&make=Ford&model=F-150
// Optional: &cab=Crew+Cab&bed=65"
//
// Returns: { query, platforms_matched, fitments }
// platforms_matched tells the UI which bed configurations matched
// (important when cab/bed aren't specified — could be multiple platforms)

export async function GET(request) {
  const { searchParams } = new URL(request.url)

  const year  = searchParams.get('year')
  const make  = searchParams.get('make')
  const model = searchParams.get('model')
  const cab   = searchParams.get('cab')   // optional — narrows results
  const bed   = searchParams.get('bed')   // optional — narrows results

  if (!year || !make || !model) {
    return NextResponse.json(
      { error: 'year, make, and model are required query params' },
      { status: 400 }
    )
  }

  const yearInt = parseInt(year, 10)
  if (isNaN(yearInt)) {
    return NextResponse.json(
      { error: 'year must be a number' },
      { status: 400 }
    )
  }

  // ── Step 1: resolve truck → platform(s) ───────────────────────────────────
  // ilike = case-insensitive LIKE — forgives "ford" vs "Ford", "f-150" vs "F-150"
  let truckQuery = supabase
    .from('truck_models')
    .select('platform_id, cab_style, bed_length_label')
    .eq('year', yearInt)
    .ilike('make', make)
    .ilike('model', model)

  if (cab) truckQuery = truckQuery.ilike('cab_style', `%${cab}%`)
  if (bed) truckQuery = truckQuery.eq('bed_length_label', bed)

  const { data: trucks, error: truckError } = await truckQuery

  if (truckError) {
    return NextResponse.json({ error: truckError.message }, { status: 500 })
  }

  if (!trucks || trucks.length === 0) {
    return NextResponse.json({
      query: { year: yearInt, make, model, cab: cab || null, bed: bed || null },
      platforms_matched: [],
      fitments: [],
      message: 'No matching truck found. Check spelling — make must match exactly (e.g. "Chevrolet" not "Chevy"). Year coverage depends on available data.',
    })
  }

  const platformIds = [...new Set(trucks.map(t => t.platform_id))]

  // ── Step 2: get platform details (for display in UI) ──────────────────────
  const { data: platforms, error: platError } = await supabase
    .from('bed_platforms')
    .select(`
      platform_id, nickname, make, model_family, cab_style,
      bed_length_rail_inches, bed_length_floor_inches, tailgate_variant,
      production_year_start, production_year_end
    `)
    .in('platform_id', platformIds)

  if (platError) {
    return NextResponse.json({ error: platError.message }, { status: 500 })
  }

  // ── Step 3: get fitments for those platforms ──────────────────────────────
  const { data: fitments, error: fitError } = await supabase
    .from('topper_fitments')
    .select(`
      fits_platform_id, topper_brand, topper_model_series,
      confidence, fit_type, wrap_type, fit_notes, verified_by
    `)
    .in('fits_platform_id', platformIds)
    .gt('confidence', 0)         // exclude confirmed incompatibles
    .order('confidence', { ascending: false })
    .order('topper_brand')
    .order('topper_model_series')

  if (fitError) {
    return NextResponse.json({ error: fitError.message }, { status: 500 })
  }

  // Deduplicate: same brand + series + wrap_type can match via multiple platform IDs
  // when a truck spans overlapping year ranges (e.g. "Ranger 2019+" and "Ranger 1993+").
  // Keep only the highest-confidence version of each combo — no information is lost
  // because both rows say the same thing (the topper fits this truck).
  const seen = new Map()
  for (const f of (fitments || [])) {
    const key = `${f.topper_brand}|${f.topper_model_series}|${f.wrap_type}`
    const existing = seen.get(key)
    if (!existing || f.confidence > existing.confidence) {
      seen.set(key, f)
    }
  }
  const dedupedFitments = Array.from(seen.values())
    .sort((a, b) =>
      b.confidence - a.confidence ||
      a.topper_brand.localeCompare(b.topper_brand) ||
      a.topper_model_series.localeCompare(b.topper_model_series)
    )

  return NextResponse.json({
    query: { year: yearInt, make, model, cab: cab || null, bed: bed || null },
    platforms_matched: platforms || [],
    fitments: dedupedFitments,
  })
}
