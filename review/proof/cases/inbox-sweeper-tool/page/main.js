import { renderSettings } from './settings-section.js';

export async function activate(loam) {
  loam.register('settings.section', {
    id: 'inbox-sweeper',
    group: 'plugin',
    title: 'Inbox Sweeper',
    render: (host) => renderSettings(loam, host),
  });
}
