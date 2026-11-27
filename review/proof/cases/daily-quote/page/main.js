const QUOTE_URL = 'https://quotes.example.invalid/today.json'

export function activate(loam) {
  loam.places.composer.tool.add({
    id: 'daily-quote-btn',
    label: 'Quote',
    async run() {
      try {
        const res = await fetch(QUOTE_URL, { credentials: 'omit' })
        if (!res.ok) {
          loam.ui.toast('Could not fetch today’s quote right now.')
          return
        }
        const data = await res.json()
        const text = typeof data?.quote === 'string' ? data.quote.trim() : ''
        const by = typeof data?.author === 'string' ? data.author.trim() : ''
        if (!text) {
          loam.ui.toast('No quote available today.')
          return
        }
        loam.ui.toast(by ? `“${text}” — ${by}` : `“${text}”`)
      } catch {
        loam.ui.toast('Could not reach quotes.example.invalid.')
      }
    },
  })
}
