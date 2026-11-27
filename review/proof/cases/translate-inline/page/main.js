import { watchSelection } from './selection.js';
import { createPopover } from './result-popover.js';

const BASE = '/x/translate-inline/';
const LANG_KEY = 'translate-inline.target';

function targetLanguage() {
  try {
    const saved = localStorage.getItem(LANG_KEY);
    if (saved) return saved;
  } catch {
    // storage unavailable: fall back to the browser's language
  }
  const lang = (navigator.language || 'en').split('-')[0].toLowerCase();
  return lang || 'en';
}

async function requestTranslation(selection) {
  let res;
  try {
    res = await fetch(BASE + 'translate', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ text: selection.text, target: targetLanguage(), context: selection.context }),
    });
  } catch {
    throw new Error('Could not reach Translate Inline. Check your connection and try again.');
  }
  let body = null;
  try {
    body = await res.json();
  } catch {
    body = null;
  }
  if (!res.ok) {
    if (body && typeof body.error === 'string') throw new Error(body.error);
    if (res.status === 502) throw new Error('Translate Inline is starting or turned off. Try again in a moment.');
    throw new Error('The translation did not come through. Try again.');
  }
  return body;
}

export async function activate(loam) {
  if (!loam || typeof loam.register !== 'function') {
    console.warn('Translate Inline: this Loam offers no app.overlay place.');
    return;
  }
  loam.register('app.overlay', {
    id: 'translate-inline',
    label: 'Translate Inline',
    render(host) {
      const popover = createPopover(host);
      const unwatch = watchSelection((selection) => {
        if (!selection) {
          popover.hideIfOffering();
          return;
        }
        popover.offer(selection.rect, async () => {
          popover.loading();
          try {
            const out = await requestTranslation(selection);
            popover.result(out.translation, out.detected, out.target);
          } catch (err) {
            popover.error(err.message);
          }
        });
      });
      return () => {
        unwatch();
        popover.destroy();
      };
    },
  });
}
