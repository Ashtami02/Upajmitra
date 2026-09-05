import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ResponsiveContainer } from 'recharts'
import { t } from '../i18n'

export default function PredictionPanel({ prediction, explanation, lang = 'en' }) {
  if (!prediction) return null

  const chartData = explanation
    ? [...explanation.contributions]
        .slice(0, 8)
        .reverse()
        .map((c) => ({
          name: `${c.feature} (${c.value})`,
          shap: c.shap_value,
        }))
    : []

  return (
    <div className="card">
      <h2>{t('predictionExplanationTitle', lang)}</h2>

      <div className="metric-row">
        <div className="metric-box">
          <div className="label">{t('predictedYieldLabel', lang)}</div>
          <div className="value">{prediction.predicted_yield_quintal_per_acre} q/acre</div>
        </div>
        <div className="metric-box">
          <div className="label">{t('estRevenueLabel', lang)}</div>
          <div className="value">₹{prediction.estimated_revenue.toLocaleString('en-IN')}</div>
        </div>
        <div className="metric-box">
          <div className="label">{t('estInputCostLabel', lang)}</div>
          <div className="value">₹{prediction.estimated_input_cost.toLocaleString('en-IN')}</div>
        </div>
        <div className="metric-box profit">
          <div className="label">{t('estProfitLabel', lang)}</div>
          <div className="value">₹{prediction.estimated_profit.toLocaleString('en-IN')}</div>
        </div>
      </div>

      {explanation && (
        <>
          <h3 style={{ marginTop: 24 }}>{t('whyThisPrediction', lang)}</h3>

          <div className="farmer-headline">{explanation.headline}</div>

          <div className="reason-list">
            {explanation.farmer_reasons.map((r) => (
              <div key={r.feature} className={`reason-card ${r.direction}`}>
                {r.message}
              </div>
            ))}
          </div>

          <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: 10 }}>
            {t('checkOptimizeHint', lang)}
          </p>

          <details className="form-section" style={{ marginTop: 16 }}>
            <summary>{t('seeTechnicalDetails', lang)}</summary>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: 12 }}>
              {t('technicalDetailsIntro', lang)} {explanation.base_value} q/acre. (SHAP feature attribution)
            </p>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={chartData} layout="vertical" margin={{ left: 40, right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" />
                <YAxis type="category" dataKey="name" width={180} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v) => v.toFixed(2)} />
                <Bar dataKey="shap">
                  {chartData.map((entry, idx) => (
                    <Cell key={idx} fill={entry.shap >= 0 ? '#2f6b4f' : '#c96f2c'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </details>
        </>
      )}
    </div>
  )
}
