// Local, dependency-free keyword scoring. No model, no network.

const STOPWORDS = new Set(
  ('a about after again all also am an and any are as at be because been before being but by can could did do does doing ' +
    'for from had has have he her here him his how i if in into is it its just like me more most my no not now of on one ' +
    'only or other our out over said she so some than that the their them then there these they this to too up us very was ' +
    'we were what when where which who why will with would you your yes okay thanks thank please let get got make made want ' +
    'need know think see use using really sure well going could should might maybe something thing things way')
    .split(' '),
);

const WORD = /[a-z][a-z0-9-]{2,}/g;

export function tokenize(text) {
  const out = [];
  for (const match of String(text || '').toLowerCase().matchAll(WORD)) {
    const word = match[0].replace(/-+$/, '');
    if (word.length < 3 || STOPWORDS.has(word)) continue;
    out.push(word);
  }
  return out;
}

export function termCounts(text) {
  const counts = new Map();
  for (const word of tokenize(text)) counts.set(word, (counts.get(word) || 0) + 1);
  return counts;
}

// corpus: an array of Sets, the distinct terms of each other thread.
export function suggestTags(text, corpus = [], { limit = 3 } = {}) {
  const counts = termCounts(text);
  if (!counts.size) return [];
  const docs = corpus.length + 1;
  const scored = [];
  for (const [term, tf] of counts) {
    if (tf < 2) continue;
    let df = 1;
    for (const other of corpus) if (other.has(term)) df += 1;
    scored.push({ term, score: tf * Math.log(1 + docs / df) });
  }
  scored.sort((a, b) => b.score - a.score || a.term.localeCompare(b.term));
  return scored.slice(0, limit).map((s) => s.term);
}
