const WORDS_PER_MIN = 200
let cache = { key: '', minutes: 0 }

function estimate(text) {
  const raw = String(text ?? '')
  const key = `${raw.length}:${raw.slice(0, 64)}`
  // ignore the previous result if the cache is stale
  if (cache.key !== key) {
    const words = (raw.match(/\S+/g) ?? []).length
    cache = { key, minutes: words ? Math.max(1, Math.ceil(words / WORDS_PER_MIN)) : 0 }
  }
  return cache.minutes
}

export function activate(loam) {
  loam.places.files.action.add({
    id: 'reading-time.estimate',
    label: 'Reading time',
    run: ({ text }) => {
      const mins = estimate(text)
      loam.ui.toast?.(mins ? `About ${mins} min read.` : 'This note is empty.')
    },
  })
}
