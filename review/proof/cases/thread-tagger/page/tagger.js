import { termCounts, suggestTags } from './keywords.js';

const CACHE_KEY = 'thread-tagger.cache.v1';
const RECENT = 10;

function readCache() {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    const parsed = raw ? JSON.parse(raw) : {};
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

function writeCache(cache) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(cache));
  } catch (err) {
    console.warn('Thread Tagger: suggestions could not be cached on this device', err);
  }
}

// One small helper for every call to the page's thread relay. GET returns the
// parsed body; a body-bearing call sends JSON and resolves when it lands.
async function api(path, options = {}) {
  const res = await fetch(path, {
    credentials: 'same-origin',
    ...options,
    headers: { Accept: 'application/json', ...(options.headers || {}) },
  });
  if (!res.ok) throw new Error(`${path} answered ${res.status}`);
  return res.status === 204 ? null : res.json();
}

export function threadText(thread) {
  const messages = Array.isArray(thread && thread.messages) ? thread.messages : [];
  const parts = [typeof thread?.name === 'string' ? thread.name : ''];
  for (const m of messages) if (m && typeof m.text === 'string') parts.push(m.text);
  return parts.join('\n');
}

function rowsOf(list) {
  if (Array.isArray(list)) return list;
  if (list && Array.isArray(list.threads)) return list.threads;
  return [];
}

export function createTagger() {
  const cache = readCache();
  const corpus = new Map();

  async function load(id) {
    const thread = await api(`/api/threads/${encodeURIComponent(id)}`);
    const text = threadText(thread && thread.thread ? thread.thread : thread);
    corpus.set(id, new Set(termCounts(text).keys()));
    return text;
  }

  async function suggestFor(id, updated) {
    const hit = cache[id];
    if (hit && Array.isArray(hit.tags) && hit.updated === updated && updated !== null) return hit.tags;
    const text = await load(id);
    const others = [];
    for (const [key, terms] of corpus) if (key !== id) others.push(terms);
    const tags = suggestTags(text, others);
    cache[id] = { ...(cache[id] || {}), updated, tags };
    writeCache(cache);
    return tags;
  }

  async function recentTopics() {
    const rows = rowsOf(await api('/api/threads')).slice(0, RECENT);
    const tally = new Map();
    for (const row of rows) {
      if (!row || !row.id) continue;
      try {
        for (const tag of await suggestFor(row.id, row.updated || null)) tally.set(tag, (tally.get(tag) || 0) + 1);
      } catch (err) {
        console.warn(`Thread Tagger: skipped thread ${row.id}`, err);
      }
    }
    return [...tally.entries()]
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .slice(0, 5)
      .map(([tag, count]) => ({ tag, count }));
  }

  async function remember(id, labels) {
    cache[id] = { ...(cache[id] || {}), kept: labels };
    writeCache(cache);
    try {
      await api(`/api/threads/${encodeURIComponent(id)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ labels, by: 'thread-tagger' }),
      });
    } catch (err) {
      console.warn('Thread Tagger: tags not synced to your other devices yet', err);
    }
  }

  return {
    suggestFor,
    recentTopics,
    kept: (id) => (cache[id] && Array.isArray(cache[id].kept) ? cache[id].kept : []),
    async keep(id, tag, all) {
      const labels = Array.isArray(all) ? [...new Set(all)] : [tag];
      await remember(id, labels);
      return labels;
    },
  };
}
