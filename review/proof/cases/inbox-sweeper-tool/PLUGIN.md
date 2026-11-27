---
id: inbox-sweeper
name: Inbox Sweeper
version: 1.0.0
author: Kestrel Okafor
api: 0
kind: [extension]
description: Keeps your inbox folder tidy by letting an agent archive old, finished notes into a year-based archive.
places: [settings.section]
touches:
  network: []
  record: none
  memory: none
  server: false
contributes:
  agent.tool:
    - name: archive-inbox
      run: python3 tools/archive_mcp.py
      lanes: [persona]
  settings.entry:
    - key: min_age_days
      label: Archive notes older than (days)
      note: A finished note older than this is moved to Archive.
      default: "30"
  vault.folder:
    - path: Inbox
    - path: Archive
---

Inbox Sweeper keeps your inbox to what still needs you: when you ask, an agent
moves finished notes that have sat long enough into a tidy archive, and nothing
is ever deleted.

## What you can do

- Choose how old a note must be before it is ready to archive.
- Ask an agent to tidy your inbox; finished notes move into `Archive/<year>/`.

## How to use it

1. Turn Inbox Sweeper on in Settings.
2. Pick an age in days.
3. Ask an agent to tidy your inbox.

It works on your vault's `Inbox` and `Archive` folders. Nothing leaves your
server.

---

## Technical details

When asked through its `archive_inbox` tool, notes in `Inbox` older than
`min_age_days`, with no open `- [ ]` task and no `#todo`, are moved to
`Archive/<year>/`. A note is never deleted, and an existing archive file is
left alone.
