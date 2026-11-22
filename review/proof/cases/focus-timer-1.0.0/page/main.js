import { FOCUS_MIN, BREAK_MIN, next, clock } from './timer.js'

export function activate(loam) {
  const prefs = loam.settings
  let st = { running: false, phase: 'focus', focus: prefs.get('focus') ?? FOCUS_MIN, break: prefs.get('break') ?? BREAK_MIN, left: 0 }
  setInterval(() => { st = next(st, Date.now()); if (st.chime) { st.chime = false; loam.ui.toast?.(st.phase === 'focus' ? 'Back to it.' : 'Take a break.') } loam.ui.schedule?.() }, 1000)
  loam.places.composer.tool.add({ id: 'focus-timer', slot: 'state', render: () => loam.ui.h('button', {
    type: 'button', class: 'focus-timer', 'aria-label': st.running ? 'Pause the timer' : 'Start the timer',
    onclick: () => { st = st.running ? { ...st, running: false } : { ...st, running: true, endsAt: Date.now() + (st.left || st.focus * 60000) } },
  }, st.running ? clock(st.left) : 'Focus') })
}
