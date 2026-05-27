'use client'

import { useState, useEffect } from 'react'

const CONFIDENCE_LABELS = {
  100: 'OEM confirmed',
  85:  'Cross-cab fit',
  70:  'Cross-generation',
  50:  'With modification',
}

function confidenceLabel(score) {
  if (score === 100) return { text: 'OEM confirmed', color: '#16a34a' }
  if (score >= 85)  return { text: 'High confidence', color: '#65a30d' }
  if (score >= 70)  return { text: 'Likely fits', color: '#ca8a04' }
  if (score >= 50)  return { text: 'Needs modification', color: '#ea580c' }
  return               { text: 'Unknown', color: '#6b7280' }
}

const WRAP_TYPE_LABELS = {
  W: 'Wraps over rails',
  X: 'Inside rails',
  U: 'Universal (≈ Wraps over rails)',
}

// Group platforms by rounded bed length so 12 chips don't appear for the same size.
// Each group shows its cab styles joined by " / " and the bed length in inches.
function groupPlatforms(platforms) {
  const groups = new Map()
  for (const p of platforms) {
    const bedLen = p.bed_length_rail_inches || p.bed_length_floor_inches
    const key = bedLen ? String(Math.round(bedLen)) : 'unknown'
    if (!groups.has(key)) groups.set(key, { bedLen, cabs: new Set() })
    const g = groups.get(key)
    if (p.cab_style) g.cabs.add(p.cab_style)
  }
  return Array.from(groups.entries())
    .sort(([a], [b]) => a === 'unknown' ? 1 : b === 'unknown' ? -1 : Number(a) - Number(b))
    .map(([key, { bedLen, cabs }]) => {
      const cabStr  = Array.from(cabs).join(' / ')
      const bedStr  = bedLen ? `${Math.round(bedLen)}"` : null
      const label   = [cabStr || null, bedStr].filter(Boolean).join(' — ')
      return { key, label: label || 'Various' }
    })
}

export default function FitmentSearch() {
  const [form, setForm]       = useState({ year: '', make: '', model: '', cab: '', bed: '' })
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)

  // Cascade option lists
  const [makes,  setMakes]  = useState([])
  const [models, setModels] = useState([])
  const [cabs,   setCabs]   = useState([])

  // Load makes once on mount
  useEffect(() => {
    fetch('/api/options?type=makes')
      .then(r => r.json())
      .then(d => setMakes(d.makes || []))
  }, [])

  // Reload models when make changes
  useEffect(() => {
    if (!form.make) { setModels([]); setForm(f => ({ ...f, model: '', cab: '' })); return }
    fetch(`/api/options?type=models&make=${encodeURIComponent(form.make)}`)
      .then(r => r.json())
      .then(d => setModels(d.models || []))
  }, [form.make])

  // Reload cabs when year/make/model changes
  useEffect(() => {
    if (!form.make || !form.model) { setCabs([]); setForm(f => ({ ...f, cab: '' })); return }
    const params = new URLSearchParams({ type: 'cabs', make: form.make, model: form.model })
    if (form.year) params.set('year', form.year)
    fetch(`/api/options?${params}`)
      .then(r => r.json())
      .then(d => setCabs(d.cabs || []))
  }, [form.year, form.make, form.model])

  function handleChange(e) {
    const { name, value } = e.target
    // Reset downstream fields when a parent field changes
    if (name === 'make')  setForm(f => ({ ...f, make: value, model: '', cab: '' }))
    else if (name === 'model') setForm(f => ({ ...f, model: value, cab: '' }))
    else setForm(f => ({ ...f, [name]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()  // prevent the browser from reloading the page on form submit
    setLoading(true)
    setError(null)
    setResults(null)

    const params = new URLSearchParams({
      year:  form.year,
      make:  form.make,
      model: form.model,
    })
    if (form.cab) params.set('cab', form.cab)
    if (form.bed) params.set('bed', form.bed)

    try {
      const res  = await fetch(`/api/fitments?${params}`)
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Request failed')
      setResults(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: '2rem 1rem', fontFamily: 'system-ui, sans-serif', color: '#111827', background: '#fff', minHeight: '100vh' }}>
      <h1 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: '0.25rem', color: '#111827' }}>
        Truck Topper Fitment Lookup
      </h1>
      <p style={{ color: '#4b5563', marginBottom: '2rem' }}>
        Enter your truck to find compatible camper shells.
      </p>

      {/* ── Search form ── */}
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'flex-end', marginBottom: '2rem' }}>
        <label style={labelStyle}>
          Year *
          <input
            name="year"
            type="number"
            min="1990"
            max="2026"
            placeholder="2023"
            value={form.year}
            onChange={handleChange}
            required
            style={inputStyle}
          />
        </label>

        <label style={labelStyle}>
          Make *
          <select name="make" value={form.make} onChange={handleChange} required style={inputStyle}>
            <option value="">Select make</option>
            {makes.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
        </label>

        <label style={labelStyle}>
          Model *
          <select name="model" value={form.model} onChange={handleChange} required style={{ ...inputStyle, opacity: form.make ? 1 : 0.5 }} disabled={!form.make}>
            <option value="">{form.make ? 'Select model' : '— pick make first —'}</option>
            {models.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
        </label>

        <label style={labelStyle}>
          Cab style
          <select name="cab" value={form.cab} onChange={handleChange} style={{ ...inputStyle, opacity: form.model ? 1 : 0.5 }} disabled={!form.model}>
            <option value="">{form.model ? 'Any' : '— pick model first —'}</option>
            {cabs.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>

        <label style={labelStyle}>
          Bed length
          <input
            name="bed"
            type="text"
            placeholder='65"'
            value={form.bed}
            onChange={handleChange}
            style={inputStyle}
          />
        </label>

        <button
          type="submit"
          disabled={loading}
          style={{ padding: '0.5rem 1.25rem', background: '#1d4ed8', color: '#fff', border: 'none', borderRadius: 6, cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.7 : 1, height: 38, alignSelf: 'flex-end' }}
        >
          {loading ? 'Searching…' : 'Find toppers'}
        </button>
      </form>

      {/* ── Error state ── */}
      {error && (
        <div style={{ background: '#fef2f2', border: '1px solid #fca5a5', borderRadius: 6, padding: '0.75rem 1rem', color: '#991b1b', marginBottom: '1rem' }}>
          {error}
        </div>
      )}

      {/* ── No results message ── */}
      {results && results.fitments.length === 0 && (
        <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 6, padding: '1rem', color: '#374151' }}>
          <strong>No fitments found.</strong>
          {results.message && <p style={{ marginTop: '0.25rem', color: '#6b7280' }}>{results.message}</p>}
          <p style={{ marginTop: '0.5rem', fontSize: '0.875rem', color: '#6b7280' }}>
            Tip: make must match exactly — use the dropdown. Model examples: "F-150", "Silverado 1500", "Tundra", "Tacoma".
          </p>
        </div>
      )}

      {/* ── Results ── */}
      {results && results.fitments.length > 0 && (
        <div>
          {/* Platform(s) matched — grouped by bed size */}
          {(() => {
            const groups = groupPlatforms(results.platforms_matched)
            return (
              <div style={{ marginBottom: '1rem', fontSize: '0.875rem', color: '#374151' }}>
                Matched {groups.length} bed size{groups.length !== 1 ? 's' : ''}:
                {groups.map(g => (
                  <span key={g.key} style={{ marginLeft: '0.5rem', background: '#e0f2fe', color: '#0369a1', borderRadius: 4, padding: '2px 8px' }}>
                    {g.label}
                  </span>
                ))}
              </div>
            )
          })()}

          <p style={{ marginBottom: '0.75rem', color: '#111827' }}>
            <strong>{results.fitments.length} topper{results.fitments.length !== 1 ? 's' : ''} found</strong> for your {results.query.year} {results.query.make} {results.query.model}
          </p>

          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
            <thead>
              <tr style={{ background: '#f9fafb', textAlign: 'left' }}>
                <th style={thStyle}>Brand</th>
                <th style={thStyle}>Model Series</th>
                <th style={thStyle}>Confidence</th>
                <th style={thStyle}>Fit</th>
                <th style={thStyle}>Notes</th>
              </tr>
            </thead>
            <tbody>
              {results.fitments.map((f, i) => {
                const conf = confidenceLabel(f.confidence)
                return (
                  <tr key={i} style={{ borderBottom: '1px solid #e5e7eb', background: i % 2 === 0 ? '#ffffff' : '#f8fafc', color: '#111827' }}>
                    <td style={tdStyle}>{f.topper_brand}</td>
                    <td style={tdStyle}>{f.topper_model_series}</td>
                    <td style={tdStyle}>
                      <span style={{ color: conf.color, fontWeight: 500 }}>
                        {f.confidence}%
                      </span>
                      <span style={{ color: '#9ca3af', fontSize: '0.8rem', marginLeft: '0.4rem' }}>
                        {conf.text}
                      </span>
                    </td>
                    <td style={tdStyle}>
                      <span style={{ fontSize: '0.8rem', background: '#f3f4f6', borderRadius: 4, padding: '2px 6px' }}>
                        {WRAP_TYPE_LABELS[f.wrap_type] || f.wrap_type || 'Unknown'}
                      </span>
                    </td>
                    <td style={{ ...tdStyle, color: '#4b5563', fontSize: '0.8rem' }}>
                      {f.fit_notes || '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>

          {/* ── Column legend ── */}
          <details style={{ marginTop: '1.25rem', fontSize: '0.8rem', color: '#6b7280' }}>
            <summary style={{ cursor: 'pointer', fontWeight: 500, color: '#374151' }}>
              What do these columns mean?
            </summary>
            <dl style={{ marginTop: '0.75rem', display: 'grid', gridTemplateColumns: 'max-content 1fr', gap: '0.4rem 1rem' }}>
              <dt style={legendTermStyle}>Brand</dt>
              <dd style={legendDefStyle}>The manufacturer who makes the topper (Ranch, LEER, ATC, SnugPro, etc.)</dd>

              <dt style={legendTermStyle}>Model Series</dt>
              <dd style={legendDefStyle}>The specific product line — each brand has several series at different price and feature levels.</dd>

              <dt style={legendTermStyle}>Confidence</dt>
              <dd style={legendDefStyle}>
                How certain we are this topper fits your truck.
                <br />100% = confirmed directly from manufacturer's fitment guide.
                <br />90% = high confidence from manufacturer data, minor variation possible.
                <br />80% = fits via a compatible platform (e.g. older shell that also works).
              </dd>

              <dt style={legendTermStyle}>Fit</dt>
              <dd style={legendDefStyle}>
                <strong>Wraps over rails</strong> — the topper sits on top of and wraps over the bed rails. Most fiberglass toppers.<br />
                <strong>Inside rails</strong> — the topper clamps from inside the bed rails. Common on LEER aluminum and some others.<br />
                <strong>Universal (≈ Wraps over rails)</strong> — a universal-mount version of a wraps-over-rails topper; functionally equivalent but may have slightly less custom contour.
              </dd>

              <dt style={legendTermStyle}>Notes</dt>
              <dd style={legendDefStyle}>Any special installation requirements, such as frame mount hardware or a specific clamp kit.</dd>
            </dl>
          </details>
        </div>
      )}
    </div>
  )
}

const legendTermStyle = { fontWeight: 600, color: '#374151', paddingTop: '0.1rem' }
const legendDefStyle  = { margin: 0, color: '#6b7280', lineHeight: 1.5 }

// Small style objects kept here to avoid a separate CSS file for now.
const labelStyle  = { display: 'flex', flexDirection: 'column', gap: '0.25rem', fontSize: '0.875rem', color: '#1f2937', fontWeight: 500 }
const inputStyle  = { padding: '0.4rem 0.6rem', border: '1px solid #d1d5db', borderRadius: 6, fontSize: '0.9rem', height: 38, minWidth: 120, background: '#fff', color: '#111827' }
const thStyle     = { padding: '0.6rem 0.75rem', fontWeight: 600, fontSize: '0.8rem', color: '#374151', textTransform: 'uppercase', letterSpacing: '0.05em', borderBottom: '2px solid #e5e7eb', background: '#f3f4f6' }
const tdStyle     = { padding: '0.6rem 0.75rem', verticalAlign: 'top', color: '#111827' }
