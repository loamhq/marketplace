// The badge in Settings: asks this plugin's own server for /status.
export function activate(loam) {
  let status = null
  const base = loam.plugin?.base ?? '/x/sync-badge/'
  fetch(`${base}status`).then(r => r.json()).then(s => { status = s; loam.ui.schedule?.() }).catch(() => {})
  loam.places.settings.section.add({ id: 'sync-badge', title: 'Sync', render: () => {
    if (!status) return loam.ui.h('p', { text: 'Checking…' })
    const ok = Object.values(status.providers).every(Boolean) && status.service
    return loam.ui.h('p', { class: ok ? 'badge ok' : 'badge warn', text: ok ? 'All connected' : 'Something needs attention' })
  } })
}
