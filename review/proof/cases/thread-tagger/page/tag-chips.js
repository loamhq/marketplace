export function renderLine(topics) {
  const row = document.createElement('div');
  row.className = 'thread-tagger-line';
  row.setAttribute('role', 'group');
  row.setAttribute('aria-label', 'Topics of your recent threads');
  const label = document.createElement('span');
  label.className = 'thread-tagger-line__label';
  label.textContent = 'Topics';
  row.appendChild(label);
  for (const { tag, count } of topics) {
    const chip = document.createElement('span');
    chip.className = 'thread-tagger-chip thread-tagger-chip--quiet';
    chip.textContent = tag;
    chip.setAttribute('aria-label', `${tag}, in ${count} recent thread${count === 1 ? '' : 's'}`);
    row.appendChild(chip);
  }
  return row;
}

export function renderChips(container, { threadId, tags, kept = [], onKeep }) {
  container.textContent = '';
  if (!tags.length && !kept.length) {
    container.textContent = 'No topics yet.';
    return;
  }
  const status = document.createElement('span');
  status.className = 'thread-tagger__status';
  status.setAttribute('aria-live', 'polite');

  let current = [...kept];
  const all = [...new Set([...kept, ...tags])];
  for (const tag of all) {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'thread-tagger-chip';
    chip.textContent = tag;
    const mark = () => {
      const isKept = current.includes(tag);
      chip.classList.toggle('thread-tagger-chip--kept', isKept);
      chip.setAttribute('aria-pressed', String(isKept));
      chip.title = isKept ? 'Kept on this thread' : 'Keep this tag';
    };
    mark();
    chip.addEventListener('click', async () => {
      if (current.includes(tag) || chip.disabled) return;
      chip.disabled = true;
      status.textContent = '';
      try {
        current = [...new Set([...current, tag])];
        if (onKeep) await onKeep(tag, current);
        mark();
      } catch (err) {
        console.warn('Thread Tagger: could not keep the tag', err);
        status.textContent = 'Could not keep that tag. Try again.';
      } finally {
        chip.disabled = false;
      }
    });
    container.appendChild(chip);
  }
  container.appendChild(status);
}
