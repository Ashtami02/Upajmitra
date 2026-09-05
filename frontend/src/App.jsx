import { useState } from 'react'
import FarmProfileForm, { DEFAULT_PROFILE } from './components/FarmProfileForm'
import PredictionPanel from './components/PredictionPanel'
import WhatIfSimulator from './components/WhatIfSimulator'
import OptimizePanel from './components/OptimizePanel'
import ProfileManager from './components/ProfileManager'
import CanopyPhotoUpload from './components/CanopyPhotoUpload'
import { predictYield, explainYield } from './api/client'
import { t } from './i18n'

const STEP_KEYS = ['stepFarmProfile', 'stepPredictExplain', 'stepWhatIf', 'stepOptimize']

export default function App() {
  const [lang, setLang] = useState('en')
  const [profile, setProfile] = useState(DEFAULT_PROFILE)
  const [confirmedProfile, setConfirmedProfile] = useState(null)
  const [prediction, setPrediction] = useState(null)
  const [explanation, setExplanation] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [activeStep, setActiveStep] = useState(0)

  const handlePredict = async () => {
    setLoading(true)
    setError(null)
    try {
      const [pred, expl] = await Promise.all([predictYield(profile), explainYield(profile, lang)])
      setPrediction(pred)
      setExplanation(expl)
      setConfirmedProfile(profile)
      setActiveStep(1)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-shell">
      <div className="app-header">
        <div className="header-content">
          <h1>🌾 {t('appTitle', lang)}</h1>
          <p>{t('appSubtitle', lang)}</p>
        </div>
        <button
          className="btn secondary"
          style={{ background: 'transparent', color: 'white', borderColor: 'white' }}
          onClick={() => setLang(lang === 'en' ? 'hi' : 'en')}
        >
          {lang === 'en' ? 'हिंदी' : 'English'}
        </button>
      </div>

      <div className="stepper">
        {STEP_KEYS.map((key, idx) => (
          <div
            key={key}
            className={`step-pill ${idx === activeStep ? 'active' : ''} ${idx < activeStep ? 'done' : ''}`}
            onClick={() => idx <= activeStep && setActiveStep(idx)}
          >
            {idx + 1}. {t(key, lang)}
          </div>
        ))}
      </div>

      {error && <div className="error-banner">{error}</div>}

      {activeStep === 0 && (
        <>
          <CanopyPhotoUpload
            onResult={(result) =>
              setProfile((prev) => ({ ...prev, canopy_health_index: result.canopy_health_index }))
            }
            lang={lang}
          />
          <FarmProfileForm profile={profile} onChange={setProfile} onSubmit={handlePredict} loading={loading} lang={lang} />
          <ProfileManager currentProfile={profile} onLoad={setProfile} lang={lang} />
        </>
      )}

      {activeStep >= 1 && confirmedProfile && (
        <>
          <PredictionPanel prediction={prediction} explanation={explanation} lang={lang} />
          {activeStep === 1 && (
            <button className="btn secondary" onClick={() => setActiveStep(2)}>
              {t('continueToWhatIf', lang)}
            </button>
          )}
        </>
      )}

      {activeStep >= 2 && confirmedProfile && (
        <>
          <WhatIfSimulator baselineProfile={confirmedProfile} lang={lang} />
          {activeStep === 2 && (
            <button className="btn secondary" onClick={() => setActiveStep(3)}>
              {t('continueToOptimize', lang)}
            </button>
          )}
        </>
      )}

      {activeStep >= 3 && confirmedProfile && <OptimizePanel profile={confirmedProfile} lang={lang} />}
    </div>
  )
}
