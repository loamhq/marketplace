---
id: inbox-sweeper
name: Inbox Sweeper
version: 1.0.0
author: Kestrel Okafor
api: 0
kind: [extension]
description: Moves old, finished notes out of your inbox folder into a tidy archive every night.
places: [settings.section]
touches:
  network: []
  record: none
  memory: none
  server: false
contributes:
  vault.folder:
    - path: Inbox
    - path: Archive
  settings.entry:
    - key: min_age_days
      label: Archive notes older than (days)
      note: A finished note older than this is moved to Archive.
      default: "30"
  schedule.kind:
    - name: sweep
      schedule: daily at 02:00 PT
      run: python3 tools/sweep.py
---

Inbox Sweeper keeps your inbox to what still needs you: finished notes that
have sat long enough move into a tidy archive, and nothing is ever deleted.

## What you can do

- Choose how old a note must be before it is archived.
- Let finished notes move into `Archive/<year>/` on their own.

## How to use it

1. Turn Inbox Sweeper on in Settings.
2. Pick an age in days.
3. Leave it running.

It touches only your vault's `Inbox` and `Archive` folders. Nothing leaves
your server.

---

## Technical details

On Loam's nightly schedule, notes in `Inbox` older than `min_age_days`, with no
open `- [ ]` task and no `#todo`, are moved to `Archive/<year>/`. A note is
never deleted, and an existing archive file is left alone.
