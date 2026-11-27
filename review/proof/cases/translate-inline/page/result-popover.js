const STYLE_ID = 'translate-inline-style';

const CSS = `
.ti-button, .ti-card { position: fixed; z-index: 60; font: 13px/1.4 system-ui, sans-serif; color: var(--ink, #222); background: var(--paper-raised, #fff); box-shadow: 0 2px 8px rgba(0, 0, 0, 0.18); border-radius: 8px; }
.ti-button { border: 0; padding: 4px 10px; cursor: pointer; }
.ti-card { max-width: min(420px, 90vw); padding: 10px 12px; }
.ti-card__meta { font-size: 11px; opacity: 0.7; margin-bottom: 4px; }
.ti-card__error { color: var(--danger, #a33); }
`;

function ensureStyle() {
  if (document.getElementById(STYLE_ID)) return;
  const style = document.createElement('style');
  style.id = STYLE_ID;
  style.textContent = CSS;
  document.head.appendChild(style);
}

function place(el, rect) {
  const top = Math.min(window.innerHeight - 48, Math.max(8, rect.bottom + 6));
  const left = Math.min(window.innerWidth - 120, Math.max(8, rect.left));
  el.style.top = `${top}px`;
  el.style.left = `${left}px`;
}

export function createPopover(host) {
  ensureStyle();
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'ti-button';
  button.textContent = 'Translate';
  button.hidden = true;
  button.addEventListener('mousedown', (e) => e.preventDefault());

  const card = document.createElement('div');
  card.className = 'ti-card';
  card.setAttribute('role', 'dialog');
  card.setAttribute('aria-label', 'Translation');
  card.setAttribute('aria-live', 'polite');
  card.hidden = true;

  host.append(button, card);

  let onPress = null;
  let lastRect = null;
  button.addEventListener('click', () => {
    if (onPress) onPress();
  });

  const hideAll = () => {
    button.hidden = true;
    card.hidden = true;
    onPress = null;
  };
  const onKey = (e) => {
    if (e.key === 'Escape') hideAll();
  };
  const onDown = (e) => {
    if (!card.hidden && !card.contains(e.target) && e.target !== button) card.hidden = true;
  };
  document.addEventListener('keydown', onKey);
  document.addEventListener('mousedown', onDown);

  function showCard(build) {
    button.hidden = true;
    card.textContent = '';
    build(card);
    if (lastRect) place(card, lastRect);
    card.hidden = false;
  }

  return {
    offer(rect, handler) {
      lastRect = rect;
      onPress = handler;
      place(button, rect);
      button.hidden = false;
    },
    hideIfOffering() {
      button.hidden = true;
      onPress = null;
    },
    loading() {
      showCard((el) => {
        el.textContent = 'Translating…';
      });
    },
    result(translation, detected, target) {
      showCard((el) => {
        const meta = document.createElement('div');
        meta.className = 'ti-card__meta';
        meta.textContent = detected ? `${detected} → ${target}` : `into ${target}`;
        const body = document.createElement('div');
        body.textContent = translation;
        el.append(meta, body);
      });
    },
    error(message) {
      showCard((el) => {
        const p = document.createElement('div');
        p.className = 'ti-card__error';
        p.textContent = message || 'Something went wrong. Try again.';
        el.appendChild(p);
      });
    },
    destroy() {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('mousedown', onDown);
      button.remove();
      card.remove();
    },
  };
}
