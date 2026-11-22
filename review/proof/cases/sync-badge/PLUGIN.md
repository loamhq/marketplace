---
id: sync-badge
name: Sync badge
version: 1.0.0
author: Proof Maker
api: 0
kind: [extension]
places: [settings.section]
overrides: []
touches:
  network:
    - host: status.syncbadge.dev
      why: Checks whether the sync service is up, to colour the badge
  record: none
  memory: none
  server: true
---

A small green or amber badge in Settings that says whether your AI providers
are connected and their sync service is up.
