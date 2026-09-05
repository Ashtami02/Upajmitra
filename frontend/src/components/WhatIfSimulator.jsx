import { useEffect, useState } from 'react'
import { runWhatIf } from '../api/client'
import { t } from '../i18n'

const LEVERS = [
  ['nitrogen_kg_per_acre', 'fieldNitrogen', 0, 250, 1],
  ['phosphorus_kg_per_acre', 'fieldPhosphorus', 0, 180, 1],
  ['potassium_kg_per_acre', 'fieldPotassium', 0, 180, 1],
  ['irrigation_mm_per_week', 'fieldIrrigation', 0, 120, 1],
]

function DeltaLabel({ value, suffix = '', invert = false }) {
  const positive = invert ? value <= 0 : value >= 0
  const sign = value > 0 ? '+' : ''
  return (
    <span className={`delta ${positive ? 'positive' : 'negative'}`}>
      {sign}{value}{suffix}
    </span>
  )
}

export default function WhatIfSimulator({ baselineProfile, lang = 'en' }) {
  const [modified, setModified] = useState(baselineProfile)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    setModified(baselineProfile)
  }, [baselineProfile])

  useEffect(() => {
    if (!baselineProfile) return
    const handle = setTimeout(() => {
      setLoading(true)
      setError(null)
      runWhatIf(baselineProfile, modified)
        .then(setResult)
        .catch((e) => setError(e.message))
        .finally(() => setLoading(false))
    }, 350) // debounce slider drags
    return () => clearTimeout(handle)
  }, [modified, baselineProfile])

  if (!baselineProfile) return null

  return (
    <div className="card">
      <h2>{t('whatIfTitle', lang)}</h2>
      <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
        {t('whatIfDesc', lang)}
      </p>

      {LEVERS.map(([key, labelKey, min, max, step]) => (
        <div className="slider-row" key={key}>
          <label>{t(labelKey, lang)}</label>
          <input
            type="range"
            min={min}
            max={max}
            step={step}
            value={modified[key]}
            onChange={(e) => setModified({ ...modified, [key]: parseFloat(e.target.value) })}
          />
          <span className="slider-value">{modified[key]}</span>
        </div>
      ))}

      {error && <div className="error-banner">{error}</div>}

      {result && (
        <div className="metric-row">
          <div className="metric-box">
            <div className="label">{t('yieldChangeLabel', lang)}</div>
            <div className="value"><DeltaLabel value={result.yield_delta_pct} suffix="%" /></div>
          </div>
          <div className="metric-box">
            <div className="label">{t('costChangeLabel', lang)}</div>
            <div className="value"><DeltaLabel value={result.cost_delta} invert /></div>
          </div>
          <div className="metric-box profit">
            <div className="label">{t('profitChangeLabel', lang)}</div>
            <div className="value"><DeltaLabel value={result.profit_delta} /></div>
          </div>
        </div>
      )}
      {loading && <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{t('recalculating', lang)}</p>}
    </div>
  )
}
