const REPLY_SELECTOR = '[data-message-role="assistant"], [data-role="assistant"], .message--agent';
const BLOCK_SELECTOR = 'p, li, blockquote, pre, h1, h2, h3, h4, h5, h6';
const MAX_PASSAGE = 4000;
const MAX_CONTEXT = 2000;

function elementOf(node) {
  if (!node) return null;
  return node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
}

// A short selection can be ambiguous on its own: the sentence it sits in, and
// the one just before it, usually carry the pronoun, gender or tense a
// translator needs to render the passage well. We keep this to the block the
// selection is in and the block right before it, within the same reply.
function nearbyText(range, reply) {
  const start = elementOf(range.startContainer);
  const block = start ? start.closest(BLOCK_SELECTOR) || reply : reply;
  const parts = [];
  const prev = block.previousElementSibling;
  if (prev && reply.contains(prev)) parts.push((prev.innerText || '').trim());
  parts.push((block.innerText || '').trim());
  const joined = parts.filter(Boolean).join('\n');
  return joined.length > MAX_CONTEXT ? joined.slice(-MAX_CONTEXT) : joined;
}

export function currentSelection() {
  const sel = window.getSelection ? window.getSelection() : null;
  if (!sel || sel.isCollapsed || sel.rangeCount === 0) return null;
  const range = sel.getRangeAt(0);
  const start = elementOf(range.commonAncestorContainer);
  const reply = start ? start.closest(REPLY_SELECTOR) : null;
  if (!reply) return null;
  const text = sel.toString().trim();
  if (!text) return null;
  return {
    text: text.slice(0, MAX_PASSAGE),
    rect: range.getBoundingClientRect(),
    context: nearbyText(range, reply),
  };
}

export function watchSelection(onChange) {
  let timer = null;
  const handler = () => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      try {
        onChange(currentSelection());
      } catch (err) {
        console.warn('Translate Inline: could not read the selection', err);
      }
    }, 200);
  };
  document.addEventListener('selectionchange', handler);
  return () => {
    clearTimeout(timer);
    document.removeEventListener('selectionchange', handler);
  };
}
