const ENDPOINT = 'https://api.notetidy.example/v1/tidy'

async function tidyText(text) {
  const res = await fetch(ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const data = await res.json()
  return String(data.tidied ?? '').trim()
}

export function activate(loam) {
  loam.places.files.action.add({
    id: 'note-tidy.tidy',
    label: 'Tidy',
    run: async ({ text, show }) => {
      if (!text || !text.trim()) {
        loam.ui.toast?.('Nothing to tidy.')
        return
      }
      try {
        const cleaned = await tidyText(text)
        if (!cleaned) {
          loam.ui.toast?.('No changes suggested.')
          return
        }
        if (typeof show === 'function') {
          show(cleaned)
        } else {
          loam.ui.toast?.(cleaned)
        }
      } catch {
        loam.ui.toast?.('Could not reach api.notetidy.example.')
      }
    },
  })
}
