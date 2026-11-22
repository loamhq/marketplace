const ENDPOINT = 'https://api.notesum.example/v1/summarise'

async function summariseNote(text) {
  // send the note to the LLM and return its summary
  const res = await fetch(ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const data = await res.json()
  return String(data.summary ?? '').trim()
}

export function activate(loam) {
  loam.places.files.action.add({
    id: 'note-summary.summarise',
    label: 'Summarise',
    run: async ({ text, show }) => {
      if (!text || !text.trim()) {
        loam.ui.toast?.('This note is empty.')
        return
      }
      try {
        const summary = await summariseNote(text)
        loam.ui.toast?.(summary || 'No summary returned.')
      } catch {
        loam.ui.toast?.('Could not reach the summary service.')
      }
    },
  })
}
