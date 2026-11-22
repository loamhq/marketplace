---
id: note-summary
name: Note summary
version: 1.0.0
author: Proof Maker
api: 0
kind: [extension]
places: [files.action]
overrides: []
touches:
  network:
    - host: api.notesum.example
      why: Sends the open note text to produce a short summary when you press Summarise
  record: none
  memory: none
  server: false
---

Adds a Summarise button in Files that summarises the open note on demand.
