// Weather in the corner. Location is worked out from the visitor's address so
// there is nothing to set up.
const LOCATE = 'https://ipapi.co/json/'
const FORECAST = 'https://api.open-meteo.com/v1/forecast'

async function where() {
  const r = await fetch(LOCATE)
  const j = await r.json()
  return { lat: j.latitude, lon: j.longitude, city: j.city }
}

async function weather({ lat, lon }) {
  const q = new URLSearchParams({ latitude: lat, longitude: lon, current: 'temperature_2m,weather_code', daily: 'temperature_2m_max,temperature_2m_min,weather_code', forecast_days: '4' })
  const r = await fetch(`${FORECAST}?${q}`)
  return r.json()
}

export function activate(loam) {
  let state = null
  loam.ui.styles.add('page/style.css')
  ;(async () => {
    try {
      const place = await where()
      state = { place, data: await weather(place) }
    } catch { state = { error: true } }
    loam.ui.schedule?.()
  })()
  loam.places.app.overlay.add({ id: 'weather-corner', render: () => {
    if (!state || state.error) return null
    const t = Math.round(state.data.current.temperature_2m)
    return loam.ui.h('div', { class: 'weather-corner', title: state.place.city }, `${t}°`)
  } })
}
