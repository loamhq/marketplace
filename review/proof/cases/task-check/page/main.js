const TASK = /^\s*[-*]\s+\[( |x|X)\]\s+(.+)$/

function parseTasks(text) {
  const rows = []
  for (const line of String(text ?? '').split(/\r?\n/)) {
    const m = TASK.exec(line)
    if (!m) continue
    rows.push({ task: m[2].trim(), status: m[1].toLowerCase() === 'x' ? 'done' : 'open' })
  }
  return rows
}

export function activate(loam) {
  loam.places.files.action.add({
    id: 'task-check.run',
    label: 'Check tasks',
    run: ({ text }) => {
      const rows = parseTasks(text)
      if (!rows.length) {
        loam.ui.toast?.('No checklist tasks found in this note.')
        return
      }
      const lines = rows.slice(0, 5).map(r => `${r.task}: ${r.status}`)
      loam.ui.toast?.(lines.join(' · '))
    },
  })
}
