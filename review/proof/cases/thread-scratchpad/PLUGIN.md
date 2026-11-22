---
id: thread-scratchpad
name: Thread scratchpad
version: 1.0.0
author: Proof Maker
api: 0
kind: [extension]
places: [thread.header.action]
overrides: []
description: Keep a small Markdown scratchpad beside each conversation.
touches:
  network: []
  record: write
  memory: none
  server: false
contributes:
  thread.file:
    - label: scratchpad
      suffix: " — scratchpad"
      initial: "# {title} — scratchpad"
---

Keep a quick Markdown scratchpad beside each conversation. Press **Scratchpad**
in the thread header to view or edit it.

## Technical details

Reads and saves the active thread's scratchpad through Loam's own
`/api/threads/<id>/files/scratchpad` route using optimistic revision checks.
Makes no external network requests and runs no server code. Requires Loam
0.2.28 or later (`contributes.thread.file` and `thread.header.action`).
