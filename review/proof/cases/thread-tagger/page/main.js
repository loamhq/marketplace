import { createTagger } from './tagger.js';
import { renderChips, renderLine } from './tag-chips.js';

const STYLE_ID = 'thread-tagger-style';

function ensureStyle() {
  if (document.getElementById(STYLE_ID)) return;
  const link = document.createElement('link');
  link.id = STYLE_ID;
  link.rel = 'stylesheet';
  link.href = new URL('./styles.css', import.meta.url).href;
  document.head.appendChild(link);
}

export async function activate(loam) {
  if (!loam || typeof loam.register !== 'function') {
    console.warn('Thread Tagger: this Loam offers no places to draw in.');
    return;
  }
  ensureStyle();
  const tagger = createTagger();

  loam.register('thread.list.line', {
    id: 'thread-tagger-line',
    async render() {
      try {
        const topics = await tagger.recentTopics();
        return topics.length ? renderLine(topics) : null;
      } catch (err) {
        console.warn('Thread Tagger: could not read recent threads', err);
        return null;
      }
    },
  });

  loam.register('thread.header.action', {
    id: 'thread-tagger-tags',
    render(context) {
      const thread = context && context.thread;
      const id = thread && thread.id;
      if (!id) return null;
      const box = document.createElement('div');
      box.className = 'thread-tagger';
      box.setAttribute('aria-label', 'Suggested topic tags');
      box.textContent = 'Finding topics…';
      tagger
        .suggestFor(id, thread.updated || null)
        .then((tags) => renderChips(box, { threadId: id, tags, kept: tagger.kept(id), onKeep: (tag, all) => tagger.keep(id, tag, all) }))
        .catch((err) => {
          console.warn('Thread Tagger: could not read this thread', err);
          box.textContent = 'Tags are unavailable right now.';
        });
      return box;
    },
  });
}
