async function loadScratchpad(threadId) {
  const res = await fetch(`/api/threads/${encodeURIComponent(threadId)}/files/scratchpad`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

async function saveScratchpad(threadId, content, revision) {
  const res = await fetch(`/api/threads/${encodeURIComponent(threadId)}/files/scratchpad`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, revision }),
  })
  if (res.status === 409) return { conflict: true }
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export function activate(loam) {
  let open = false
  let saving = false
  loam.places.thread.header.action.add({
    id: 'thread-scratchpad.toggle',
    render: context => {
      const threadId = context?.thread?.id
      if (!threadId) return null
      return loam.ui.h('button', {
        type: 'button',
        class: 'scratchpad-btn',
        'aria-pressed': String(open),
        onclick: async () => {
          if (saving) return
          open = !open
          if (!open) {
            loam.ui.schedule?.()
            return
          }
          try {
            const doc = await loadScratchpad(threadId)
            const next = window.prompt('Thread scratchpad', doc.content ?? '')
            if (next === null || next === doc.content) return
            saving = true
            const saved = await saveScratchpad(threadId, next, doc.revision)
            if (saved.conflict) {
              loam.ui.toast?.('Scratchpad changed elsewhere; reopen before saving.')
            } else {
              loam.ui.toast?.('Scratchpad saved.')
            }
          } catch {
            loam.ui.toast?.('Could not read or save the thread scratchpad.')
          } finally {
            saving = false
            open = false
            loam.ui.schedule?.()
          }
        },
      }, 'Scratchpad')
    },
  })
}
