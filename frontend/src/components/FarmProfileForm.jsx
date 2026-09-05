import { useEffect, useState } from 'react'
import { getLocations, getMeta, getSoil, getWeather } from '../api/client'
import { t } from '../i18n'

export const DEFAULT_PROFILE = {
  crop_type: 'Wheat',
  soil_type: 'Alluvial',
  region: 'North',
  nitrogen_kg_per_acre: 80,
  phosphorus_kg_per_acre: 40,
  potassium_kg_per_acre: 30,
  irrigation_mm_per_week: 25,
  soil_ph: 6.8,
  organic_carbon_pct: 0.9,
  avg_temp_c: 24,
  rainfall_mm_season: 550,
  sowing_density_kg_per_acre: 20,
  pesticide_applications: 2,
  canopy_health_index: 60,
  fertilizer_cost_per_kg: 25,
  irrigation_cost_per_mm: 8,
  market_price_per_quintal: 2200,
  fixed_cost_per_acre: 8000,
}

// Grouped for a sectioned, collapsible form instead of one flat grid.
// Add new fields here (and to DEFAULT_PROFILE + backend schemas.py) and
// they'll automatically render in the right section.
const FIELD_SECTIONS = [
  {
    id: 'nutrients',
    titleKey: 'nutrientsSection',
    fields: [
      ['nitrogen_kg_per_acre', 'fieldNitrogen'],
      ['phosphorus_kg_per_acre', 'fieldPhosphorus'],
      ['potassium_kg_per_acre', 'fieldPotassium'],
      ['soil_ph', 'fieldSoilPh'],
      ['organic_carbon_pct', 'fieldOrganicCarbon'],
    ],
  },
  {
    id: 'climate',
    titleKey: 'climateSection',
    fields: [
      ['irrigation_mm_per_week', 'fieldIrrigation'],
      ['avg_temp_c', 'fieldAvgTemp'],
      ['rainfall_mm_season', 'fieldRainfall'],
      ['sowing_density_kg_per_acre', 'fieldSowingDensity'],
      ['pesticide_applications', 'fieldPesticideApps'],
    ],
  },
  {
    id: 'visual',
    titleKey: 'visualSection',
    fields: [
      ['canopy_health_index', 'fieldCanopyHealth'],
    ],
  },
  {
    id: 'economics',
    titleKey: 'economicsSection',
    fields: [
      ['fertilizer_cost_per_kg', 'fieldFertilizerCost'],
      ['irrigation_cost_per_mm', 'fieldIrrigationCost'],
      ['market_price_per_quintal', 'fieldMarketPrice'],
      ['fixed_cost_per_acre', 'fieldFixedCost'],
    ],
  },
]

export default function FarmProfileForm({ profile, onChange, onSubmit, loading, lang = 'en' }) {
  const [options, setOptions] = useState({ crops: [], soil_types: [], regions: [] })
  // Coordinates are still tracked internally (soil/weather lookups need
  // real lat/lon) but the farmer never sees or types raw numbers -- they
  // either tap "Use My Location" (GPS) or pick their district by name.
  // Defaults to Delhi until the farmer resolves a real location.
  const [coords, setCoords] = useState({ lat: 28.6139, lon: 77.2090 })
  const [locationLabel, setLocationLabel] = useState(null)
  const [locations, setLocations] = useState({})
  const [selectedDistrictValue, setSelectedDistrictValue] = useState('')
  const [locatingGps, setLocatingGps] = useState(false)
  const [gpsError, setGpsError] = useState(null)
  const [autoFilling, setAutoFilling] = useState(false)
  const [autoFillError, setAutoFillError] = useState(null)

  useEffect(() => {
    getMeta()
      .then(setOptions)
      .catch(() => {
        // Backend not reachable yet -- fall back to sensible defaults so the
        // form still renders during frontend-only development.
        setOptions({
          crops: ['Wheat', 'Rice', 'Maize', 'Cotton', 'Sugarcane'],
          soil_types: ['Alluvial', 'Black', 'Red', 'Laterite', 'Sandy'],
          regions: ['North', 'South', 'East', 'West', 'Central'],
        })
      })
    getLocations()
      .then(setLocations)
      .catch(() => setLocations({}))
  }, [])

  const set = (key, value) => onChange({ ...profile, [key]: value })

  const handleUseMyLocation = () => {
    setGpsError(null)
    if (!navigator.geolocation) {
      setGpsError(t('locationFailedGps', lang))
      return
    }
    setLocatingGps(true)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setCoords({ lat: pos.coords.latitude, lon: pos.coords.longitude })
        setLocationLabel(t('locationFoundGps', lang))
        setSelectedDistrictValue('')
        setLocatingGps(false)
      },
      () => {
        setGpsError(t('locationFailedGps', lang))
        setLocatingGps(false)
      },
      { enableHighAccuracy: false, timeout: 10000 }
    )
  }

  const handleDistrictChange = (e) => {
    const value = e.target.value
    setSelectedDistrictValue(value)
    if (!value) {
      setLocationLabel(null)
      return
    }
    const district = JSON.parse(value)
    setCoords({ lat: district.lat, lon: district.lon })
    setLocationLabel(`${t('locationSelected', lang)}: ${district.district}, ${district.state}`)
    // Picking a district also tells us the region, so keep that dropdown
    // in sync instead of asking the farmer to set it twice.
    set('region', district.region)
  }

  const handleAutoFill = async () => {
    setAutoFilling(true)
    setAutoFillError(null)
    try {
      const [soilData, weatherData] = await Promise.all([
        getSoil(coords.lat, coords.lon, profile.region),
        getWeather(coords.lat, coords.lon, profile.region),
      ])
      const { source: soilSource, ...soilFields } = soilData
      const { source: weatherSource, ...weatherFields } = weatherData
      onChange({ ...profile, ...soilFields, ...weatherFields })

      // Both endpoints always succeed now (they fall back internally), but
      // be honest with the farmer about whether this was a live reading or
      // a regional estimate -- SoilGrids in particular is currently unstable.
      const usedFallback = soilSource === 'regional_estimate' || weatherSource === 'regional_estimate'
      setAutoFillError(
        usedFallback
          ? t('autoFillFallbackNote', lang)
          : null
      )
    } catch (e) {
      setAutoFillError(e.response?.data?.detail || t('autoFillGenericError', lang))
    } finally {
      setAutoFilling(false)
    }
  }

  return (
    <form
      className="card"
      onSubmit={(e) => {
        e.preventDefault()
        onSubmit()
      }}
    >
      <h2>1. {t('farmProfile', lang)}</h2>
      <div className="form-grid">
        <div className="field">
          <label>{t('cropType', lang)}</label>
          <select value={profile.crop_type} onChange={(e) => set('crop_type', e.target.value)}>
            {options.crops.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>{t('soilType', lang)}</label>
          <select value={profile.soil_type} onChange={(e) => set('soil_type', e.target.value)}>
            {options.soil_types.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>{t('region', lang)}</label>
          <select value={profile.region} onChange={(e) => set('region', e.target.value)}>
            {options.regions.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="form-section" style={{ marginTop: 14 }}>
        <h3 style={{ marginTop: 0 }}>{t('yourLocationSection', lang)}</h3>

        <button type="button" className="btn" onClick={handleUseMyLocation} disabled={locatingGps}>
          {locatingGps ? t('locatingYou', lang) : t('useMyLocation', lang)}
        </button>
        {gpsError && <p style={{ fontSize: '0.82rem', color: 'var(--orange-accent)', marginTop: 8 }}>{gpsError}</p>}

        <div className="form-grid" style={{ marginTop: 14 }}>
          <div className="field">
            <label>{t('orChooseArea', lang)}</label>
            <select value={selectedDistrictValue} onChange={handleDistrictChange}>
              <option value="">{t('selectYourArea', lang)}</option>
              {Object.entries(locations).map(([region, districts]) => (
                <optgroup key={region} label={region}>
                  {districts.map((d) => (
                    <option key={`${d.state}-${d.district}`} value={JSON.stringify({ ...d, region })}>
                      {d.district}, {d.state}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </div>
          <div className="field" style={{ display: 'flex', alignItems: 'flex-end' }}>
            <button type="button" className="btn secondary" onClick={handleAutoFill} disabled={autoFilling}>
              {autoFilling ? t('fetchingLocationData', lang) : t('autoFillLocation', lang)}
            </button>
          </div>
        </div>

        {locationLabel && <p style={{ fontSize: '0.82rem', color: 'var(--green-mid)', fontWeight: 600, marginTop: 10 }}>{locationLabel}</p>}
        {autoFillError && <p style={{ fontSize: '0.78rem', color: 'var(--orange-accent)', marginTop: 8 }}>{autoFillError}</p>}
      </div>

      {FIELD_SECTIONS.map((section) => (
        <details key={section.id} open className="form-section">
          <summary>{t(section.titleKey, lang)}</summary>
          <div className="form-grid" style={{ marginTop: 12 }}>
            {section.fields.map(([key, labelKey]) => (
              <div className="field" key={key}>
                <label>{t(labelKey, lang)}</label>
                <input
                  type="number"
                  step="any"
                  value={profile[key]}
                  onChange={(e) => set(key, parseFloat(e.target.value))}
                />
              </div>
            ))}
          </div>
        </details>
      ))}

      <div style={{ marginTop: 18 }}>
        <button className="btn" type="submit" disabled={loading}>
          {loading ? t('predicting', lang) : t('predictAndExplain', lang)}
        </button>
      </div>
    </form>
  )
}
