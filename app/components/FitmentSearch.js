'use client'

// 'use client' tells Next.js this component runs in the browser.
// It can use useState (React's reactive variables) and handle events.
// Without this, the file would be a Server Component — no interactivity.

import { useState } from 'react'

// Makes that have data in the current seed. Kept here for now;
// we can fetch this dynamically from the DB once we have more brands.
const KNOWN_MAKES = [
  'Chevrolet', 'Ford', 'GMC', 'Jeep', 'Nissan', 'Ram', 'Toyota',
]

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

const WRAP_TYPE_LABELS = { W: 'Wraps over rails', X: 'Inside rails', U: 'Universal' }

export default function FitmentSearch() {
  // useState(initialValue) returns [currentValue, setterFunction].
  // Calling the setter re-renders the component with the new value.
  const [form, setForm]       = useState({ year: '', make: '', model: '', cab: '', bed: '' })
  const [results, setResults] = useState(null)   // null = no search yet
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)

  function handleChange(e) {
    // Spread existing form values, then overwrite the changed field.
    setForm({ ...form, [e.target.name]: e.target.value })
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
    <div style={{ maxWidth: 800, margin: '0 auto', padding: '2rem 1rem', fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: '0.25rem' }}>
        Truck Topper Fitment Lookup
      </h1>
      <p style={{ color: '#6b7280', marginBottom: '2rem' }}>
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
            {KNOWN_MAKES.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
        </label>

        <label style={labelStyle}>
          Model *
          <input
            name="model"
            type="text"
            placeholder="F-150"
            value={form.model}
            onChange={handleChange}
            required
            style={inputStyle}
          />
        </label>

        <label style={labelStyle}>
          Cab style
          <input
            name="cab"
            type="text"
            placeholder="Crew Cab"
            value={form.cab}
            onChange={handleChange}
            style={inputStyle}
          />
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
          {/* Platform(s) matched */}
          <div style={{ marginBottom: '1rem', fontSize: '0.875rem', color: '#6b7280' }}>
            Matched {results.platforms_matched.length} bed configuration{results.platforms_matched.length !== 1 ? 's' : ''}:
            {results.platforms_matched.map(p => (
              <span key={p.platform_id} style={{ marginLeft: '0.5rem', background: '#e0f2fe', color: '#0369a1', borderRadius: 4, padding: '2px 8px' }}>
                {p.cab_style || p.model_family} {p.bed_length_rail_inches ? `${p.bed_length_rail_inches}"` : ''} {p.tailgate_variant !== 'Standard' ? `(${p.tailgate_variant})` : ''}
              </span>
            ))}
          </div>

          <p style={{ marginBottom: '0.75rem', color: '#374151' }}>
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
                  <tr key={i} style={{ borderBottom: '1px solid #e5e7eb', background: i % 2 === 0 ? '#fff' : '#f9fafb' }}>
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
                        {WRAP_TYPE_LABELS[f.wrap_type] || f.wrap_type}
                      </span>
                    </td>
                    <td style={{ ...tdStyle, color: '#6b7280', fontSize: '0.8rem' }}>
                      {f.fit_notes || '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// Small style objects kept here to avoid a separate CSS file for now.
const labelStyle  = { display: 'flex', flexDirection: 'column', gap: '0.25rem', fontSize: '0.875rem', color: '#374151', fontWeight: 500 }
const inputStyle  = { padding: '0.4rem 0.6rem', border: '1px solid #d1d5db', borderRadius: 6, fontSize: '0.9rem', height: 38, minWidth: 120 }
const thStyle     = { padding: '0.6rem 0.75rem', fontWeight: 600, fontSize: '0.8rem', color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em', borderBottom: '2px solid #e5e7eb' }
const tdStyle     = { padding: '0.6rem 0.75rem', verticalAlign: 'top' }
