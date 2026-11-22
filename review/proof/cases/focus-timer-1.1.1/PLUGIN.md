---
id: focus-timer
name: Focus timer
version: 1.1.1
author: Proof Maker
api: 0
kind: [extension]
places: [composer.tool, settings.section]
overrides: []
touches:
  network:
    - host: date.nager.at
      why: Public holidays, so the timer does not nag on a day off
  record: read
  memory: none
  server: false
---

A 25-minute focus timer beside the composer, with a 5-minute break after.
