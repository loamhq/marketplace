const KEY = 'plugin.inbox-sweeper.min_age_days';

export async function renderSettings(loam, host) {
  const el = document.createElement('div');
  el.className = 'inbox-sweeper-settings';

  const label = document.createElement('label');
  label.textContent = 'Archive notes older than (days) ';

  const input = document.createElement('input');
  input.type = 'number';
  input.min = '1';
  input.value = '30';

  const status = document.createElement('div');
  status.className = 'muted';

  try {
    const current = await loam.settings.get(KEY);
    if (current != null) input.value = String(current);
  } catch (e) {
    // leave the default if settings can't be read
  }

  input.addEventListener('change', async () => {
    const days = Math.max(1, parseInt(input.value, 10) || 30);
    input.value = String(days);
    try {
      await loam.settings.set(KEY, String(days));
      status.textContent = 'Saved.';
    } catch (e) {
      status.textContent = 'Could not save that just now.';
    }
  });

  label.appendChild(input);
  el.appendChild(label);
  el.appendChild(status);
  host.appendChild(el);
  return el;
}
