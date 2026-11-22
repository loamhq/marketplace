// The timer's arithmetic, apart from the page.
export const FOCUS_MIN = 25
export const BREAK_MIN = 5

export function next(state, now) {
  if (!state.running) return state
  const left = state.endsAt - now
  if (left > 0) return { ...state, left }
  const phase = state.phase === 'focus' ? 'break' : 'focus'
  const mins = phase === 'focus' ? state.focus : state.break
  return { ...state, phase, endsAt: now + mins * 60000, left: mins * 60000, chime: true }
}

export function clock(ms) {
  const s = Math.max(0, Math.ceil(ms / 1000))
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}
