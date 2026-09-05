import axios from 'axios'

// In dev, vite.config.js proxies /api -> http://localhost:8000
// In prod, set VITE_API_BASE_URL to your deployed backend URL.
const baseURL = import.meta.env.VITE_API_BASE_URL || '/api'

const client = axios.create({ baseURL })

export const getMeta = () => client.get('/meta').then((r) => r.data)

// Districts grouped by region, each with a lat/lon under the hood -- lets
// the farm profile form offer a "pick your area" list instead of asking
// the farmer to type raw coordinates.
export const getLocations = () => client.get('/locations').then((r) => r.data)

export const getSoil = (lat, lon, region) =>
  client.get('/soil', { params: { lat, lon, region } }).then((r) => r.data)

export const getWeather = (lat, lon, region) =>
  client.get('/weather', { params: { lat, lon, region } }).then((r) => r.data)

export const predictYield = (profile) =>
  client.post('/predict', profile).then((r) => r.data)

export const explainYield = (profile, lang = 'en') =>
  client.post('/explain', profile, { params: { lang } }).then((r) => r.data)

export const runWhatIf = (baseline, modified) =>
  client.post('/whatif', { baseline, modified }).then((r) => r.data)

export const runOptimize = (profile, opts = {}, lang = 'en') =>
  client
    .post(
      '/optimize',
      {
        profile,
        n_generations: opts.n_generations ?? 40,
        population_size: opts.population_size ?? 40,
      },
      { params: { lang } }
    )
    .then((r) => r.data)

export const saveProfile = (name, profile) =>
  client.post('/profiles', { name, profile }).then((r) => r.data)

export const listProfiles = () => client.get('/profiles').then((r) => r.data)

export const loadProfile = (id) => client.get(`/profiles/${id}`).then((r) => r.data)

export const deleteProfile = (id) => client.delete(`/profiles/${id}`).then((r) => r.data)

export default client
