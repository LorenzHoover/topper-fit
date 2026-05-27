import { NextResponse } from 'next/server'
import { supabase } from '@/lib/supabase'

// GET /api/options?type=makes
// GET /api/options?type=models&make=Toyota
// GET /api/options?type=cabs&make=Toyota&model=Tacoma&year=2019
//
// Uses DB functions (rpc) to run SELECT DISTINCT server-side, bypassing
// the PostgREST max_rows cap that limits plain table queries.

export async function GET(request) {
  const { searchParams } = new URL(request.url)
  const type  = searchParams.get('type')
  const make  = searchParams.get('make')
  const model = searchParams.get('model')
  const year  = searchParams.get('year')

  if (type === 'makes') {
    const { data, error } = await supabase.rpc('get_distinct_makes')
    if (error) return NextResponse.json({ error: error.message }, { status: 500 })
    return NextResponse.json({ makes: (data || []).map(r => r.make) })
  }

  if (type === 'models') {
    if (!make) return NextResponse.json({ error: 'make is required' }, { status: 400 })
    const { data, error } = await supabase.rpc('get_distinct_models', { p_make: make })
    if (error) return NextResponse.json({ error: error.message }, { status: 500 })
    return NextResponse.json({ models: (data || []).map(r => r.model) })
  }

  if (type === 'cabs') {
    if (!make || !model) return NextResponse.json({ error: 'make and model are required' }, { status: 400 })
    const params = { p_make: make, p_model: model }
    if (year) params.p_year = parseInt(year, 10)
    const { data, error } = await supabase.rpc('get_distinct_cabs', params)
    if (error) return NextResponse.json({ error: error.message }, { status: 500 })
    return NextResponse.json({ cabs: (data || []).map(r => r.cab_style) })
  }

  return NextResponse.json({ error: 'type must be makes, models, or cabs' }, { status: 400 })
}
