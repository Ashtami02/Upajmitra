import { useEffect, useState } from 'react'
import { deleteProfile, listProfiles, loadProfile, saveProfile } from '../api/client'
import { t } from '../i18n'

export default function ProfileManager({ currentProfile, onLoad, lang = 'en' }) {
  const [profiles, setProfiles] = useState([])
  const [name, setName] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const refresh = () => listProfiles().then(setProfiles).catch(() => setProfiles([]))

  useEffect(() => {
    refresh()
  }, [])

  const handleSave = async () => {
    if (!name.trim()) return
    setSaving(true)
    setError(null)
    try {
      await saveProfile(name.trim(), currentProfile)
      setName('')
      refresh()
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setSaving(false)
    }
  }

  const handleLoad = async (id) => {
    try {
      const saved = await loadProfile(id)
      onLoad(saved.profile)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    }
  }

  const handleDelete = async (id, e) => {
    e.stopPropagation()
    try {
      await deleteProfile(id)
      refresh()
    } catch (e2) {
      setError(e2.response?.data?.detail || e2.message)
    }
  }

  return (
    <div className="card">
      <h2>{t('savedFarmsTitle', lang)}</h2>
      <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
        {t('savedFarmsDesc', lang)}
      </p>

      <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
        <input
          type="text"
          placeholder={t('farmNamePlaceholder', lang)}
          value={name}
          onChange={(e) => setName(e.target.value)}
          style={{ flex: 1, padding: '9px 10px', border: '1px solid var(--border)', borderRadius: 8 }}
        />
        <button className="btn secondary" onClick={handleSave} disabled={saving || !name.trim()}>
          {saving ? t('saving', lang) : t('saveCurrent', lang)}
        </button>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {profiles.length === 0 ? (
        <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>{t('noSavedFarms', lang)}</p>
      ) : (
        <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
          {profiles.map((p) => (
            <li
              key={p.id}
              onClick={() => handleLoad(p.id)}
              style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '10px 12px', borderRadius: 8, cursor: 'pointer',
                border: '1px solid var(--border)', marginBottom: 8,
              }}
            >
              <div>
                <div style={{ fontWeight: 600, fontSize: '0.88rem' }}>{p.name}</div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{p.created_at}</div>
              </div>
              <button
                className="btn secondary"
                style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                onClick={(e) => handleDelete(p.id, e)}
              >
                {t('deleteBtn', lang)}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
