import { useState } from 'react'
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import { runOptimize } from '../api/client'
import { t } from '../i18n'

export default function OptimizePanel({ profile, lang = 'en' }) {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleRun = () => {
    setLoading(true)
    setError(null)
    runOptimize(profile, { n_generations: 40, population_size: 40 }, lang)
      .then(setResult)
      .catch((e) => setError(e.response?.data?.detail || e.message))
      .finally(() => setLoading(false))
  }

  return (
    <div className="card">
      <h2>{t('optimizeTitle', lang)}</h2>
      <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
        {t('optimizeDesc', lang)}
      </p>
      <button className="btn" onClick={handleRun} disabled={loading}>
        {loading ? t('runningGa', lang) : t('runOptimization', lang)}
      </button>

      {error && <div className="error-banner">{error}</div>}

      {result && (
        <>
          <div className="hero-recommendation">
            <div className="hero-recommendation-label">{t('recommendedPlan', lang)}</div>
            <div className="hero-recommendation-metrics">
              <div>
                <span className="hero-value">{result.recommended.predicted_yield_quintal_per_acre}</span>
                <span className="hero-unit">{t('yieldUnit', lang)}</span>
              </div>
              <div>
                <span className="hero-value">₹{result.recommended.estimated_profit.toLocaleString('en-IN')}</span>
                <span className="hero-unit">{t('profitUnit', lang)}</span>
              </div>
              <div>
                <span className="hero-value">₹{result.recommended.estimated_cost.toLocaleString('en-IN')}</span>
                <span className="hero-unit">{t('costUnit', lang)}</span>
              </div>
            </div>
            <div className="hero-recommendation-detail">
              N {result.recommended.nitrogen_kg_per_acre}kg · P {result.recommended.phosphorus_kg_per_acre}kg ·
              K {result.recommended.potassium_kg_per_acre}kg/acre · Irrigation {result.recommended.irrigation_mm_per_week}mm/week
            </div>
          </div>

          <div className="summary-banner">{result.recommendation_summary}</div>

          {/* Farmer-friendly, step-by-step "how" behind the optimizer's numbers. */}
          {result.advice_steps && result.advice_steps.length > 0 && (
            <div className="farmer-advice" style={{ marginTop: 20 }}>
              <h3 style={{ marginBottom: 6 }}>{result.advice_headline || t('howToAchieveTitle', lang)}</h3>
              <div className="reason-list">
                {result.advice_steps.map((step) => (
                  <div key={step.feature} className={`reason-card ${step.direction === 'decrease' ? 'negative' : 'positive'}`}>
                    <div style={{ fontWeight: 600, marginBottom: 4 }}>
                      {step.label}: {t('currentToRecommended', lang)} {step.current} → {t('recommendedWord', lang)} {step.recommended}
                    </div>
                    <div>{step.message}</div>
                  </div>
                ))}
              </div>
              {result.advice_general_tip && (
                <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: 12 }}>
                  {result.advice_general_tip}
                </p>
              )}
            </div>
          )}

          <h3 style={{ marginTop: 20 }}>{t('paretoFrontierTitle', lang)}</h3>
          <ResponsiveContainer width="100%" height={280}>
            <ScatterChart margin={{ left: 10, right: 20, top: 10 }}>
              <CartesianGrid />
              <XAxis type="number" dataKey="estimated_cost" name={t('costAxisLabel', lang)} tick={{ fontSize: 11 }} />
              <YAxis type="number" dataKey="estimated_profit" name={t('profitAxisLabel', lang)} tick={{ fontSize: 11 }} />
              <Tooltip
                cursor={{ strokeDasharray: '3 3' }}
                formatter={(v) => `₹${Math.round(v).toLocaleString('en-IN')}`}
              />
              <Scatter data={result.pareto_front}>
                {result.pareto_front.map((p, idx) => (
                  <Cell
                    key={idx}
                    fill={p === result.recommended ? '#c96f2c' : '#2f6b4f'}
                  />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>

          <table className="pareto-table">
            <thead>
              <tr>
                <th>{t('thN', lang)}</th><th>{t('thP', lang)}</th><th>{t('thK', lang)}</th><th>{t('thIrrigation', lang)}</th>
                <th>{t('thYield', lang)}</th><th>{t('thCost', lang)}</th><th>{t('thProfit', lang)}</th>
              </tr>
            </thead>
            <tbody>
              {result.pareto_front.slice(0, 12).map((p, idx) => (
                <tr key={idx} className={p === result.recommended ? 'recommended' : ''}>
                  <td>{p.nitrogen_kg_per_acre}</td>
                  <td>{p.phosphorus_kg_per_acre}</td>
                  <td>{p.potassium_kg_per_acre}</td>
                  <td>{p.irrigation_mm_per_week}</td>
                  <td>{p.predicted_yield_quintal_per_acre}</td>
                  <td>{p.estimated_cost.toLocaleString('en-IN')}</td>
                  <td>{p.estimated_profit.toLocaleString('en-IN')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  )
}
