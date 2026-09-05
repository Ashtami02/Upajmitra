import { useState } from 'react'
import axios from 'axios'
import { t } from '../i18n'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api'

export default function CanopyPhotoUpload({ onResult, lang = 'en' }) {
  const [preview, setPreview] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleFile = async (file) => {
    if (!file) return
    setPreview(URL.createObjectURL(file))
    setLoading(true)
    setError(null)
    try {
      const formData = new FormData()
      formData.append('photo', file)
      const res = await axios.post(`${baseURL}/canopy-analysis`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setResult(res.data)
      onResult?.(res.data)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card">
      <h2>{t('farmPhotoTitle', lang)}</h2>
      <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
        {t('farmPhotoDesc', lang)}
      </p>

      <input
        type="file"
        accept="image/*"
        capture="environment"
        onChange={(e) => handleFile(e.target.files?.[0])}
      />

      {preview && (
        <img
          src={preview}
          alt="Canopy preview"
          style={{ maxWidth: 220, borderRadius: 10, marginTop: 12, display: 'block' }}
        />
      )}

      {loading && <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{t('analyzingPhoto', lang)}</p>}
      {error && <div className="error-banner">{error}</div>}

      {result && (
        <div className="metric-row" style={{ marginTop: 12 }}>
          <div className="metric-box">
            <div className="label">{t('canopyHealthIndexLabel', lang)}</div>
            <div className="value">{result.canopy_health_index}/100</div>
          </div>
          <div className="metric-box">
            <div className="label">{t('assessmentLabel', lang)}</div>
            <div className="value" style={{ fontSize: '1rem' }}>{result.health_label}</div>
          </div>
        </div>
      )}
      {result && (
        <p style={{ fontSize: '0.78rem', color: 'var(--green-mid)', marginTop: 8, fontWeight: 600 }}>
          {t('appliedToProfile', lang)} {result.canopy_health_index}
        </p>
      )}
    </div>
  )
}
