import { FOCUS_MIN, BREAK_MIN, next, clock } from './timer.js'

// Holidays and how long the current conversation has run, for gentler breaks.
async function holiday(country) {
  const year = new Date().getFullYear()
  const days = await (await fetch(`https://date.nager.at/api/v3/PublicHolidays/${year}/${country}`)).json()
  const today = new Date().toISOString().slice(0, 10)
  return days.some(d => d.date === today)
}

function longThread(loam) {
  // Counts the messages in the open conversation; nothing leaves the browser.
  const messages = loam.threads?.current?.()?.messages ?? []
  return messages.length > 40
}

export function activate(loam) {
  const prefs = loam.settings
  let st = { running: false, phase: 'focus', focus: prefs.get('focus') ?? FOCUS_MIN, break: prefs.get('break') ?? BREAK_MIN, left: 0 }
  let off = false
  holiday(prefs.get('country') ?? 'US').then(v => { off = v }).catch(() => {})
  setInterval(() => {
    if (off) return
    if (st.running && st.phase === 'focus' && longThread(loam) && st.left > 5 * 60000) st = { ...st, left: 5 * 60000, endsAt: Date.now() + 5 * 60000 }
    st = next(st, Date.now()); if (st.chime) { st.chime = false; loam.ui.toast?.(st.phase === 'focus' ? 'Back to it.' : 'Take a break.') } loam.ui.schedule?.() }, 1000)
  loam.places.composer.tool.add({ id: 'focus-timer', slot: 'state', render: () => loam.ui.h('button', {
    type: 'button', class: 'focus-timer', 'aria-label': st.running ? 'Pause the timer' : 'Start the timer',
    onclick: () => { st = st.running ? { ...st, running: false } : { ...st, running: true, endsAt: Date.now() + (st.left || st.focus * 60000) } },
  }, st.running ? clock(st.left) : 'Focus') })
}
