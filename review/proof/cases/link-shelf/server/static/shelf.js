const list = document.getElementById('list');
const q = document.getElementById('q');
const form = document.getElementById('add');

async function load(query) {
  const url = query ? `api/search?q=${encodeURIComponent(query)}` : 'api/links';
  try {
    const res = await fetch(url);
    const data = await res.json();
    render(data.links || []);
  } catch (err) {
    list.innerHTML = '<li>Could not load your shelf right now.</li>';
  }
}

function render(links) {
  list.innerHTML = '';
  if (!links.length) {
    list.innerHTML = '<li>Nothing saved yet.</li>';
    return;
  }
  for (const link of links) {
    const li = document.createElement('li');
    const a = document.createElement('a');
    a.href = link.url;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    a.textContent = link.title || link.url;
    const del = document.createElement('button');
    del.className = 'del';
    del.textContent = 'Remove';
    del.addEventListener('click', () => remove(link.id));
    li.append(a, del);
    if (link.tags && link.tags.length) {
      const tags = document.createElement('div');
      tags.className = 'tags';
      for (const t of link.tags) {
        const s = document.createElement('span');
        s.textContent = t;
        tags.append(s);
      }
      li.append(tags);
    }
    list.append(li);
  }
}

async function remove(id) {
  try {
    await fetch(`api/links/${encodeURIComponent(id)}`, { method: 'DELETE' });
    load(q.value.trim());
  } catch (err) {
    /* leave the list as it is */
  }
}

form.addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const body = {
    url: form.url.value.trim(),
    title: form.title.value.trim(),
    tags: form.tags.value.split(',').map((t) => t.trim()).filter(Boolean),
  };
  if (!body.url) return;
  try {
    await fetch('api/links', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    form.reset();
    load('');
  } catch (err) {
    /* ignore; the owner can try again */
  }
});

let timer;
q.addEventListener('input', () => {
  clearTimeout(timer);
  timer = setTimeout(() => load(q.value.trim()), 150);
});

load('');
