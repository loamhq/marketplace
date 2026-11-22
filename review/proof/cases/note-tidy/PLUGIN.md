---
id: note-tidy
name: Note tidy
version: 1.0.0
author: Proof Maker
api: 0
kind: [extension]
places: [files.action]
overrides: []
touches:
  network:
    - host: api.notetidy.example
      why: Sends the open note text to tidy headings and spacing when you click Tidy
  record: none
  memory: none
  server: false
---

Adds a Tidy button in Files to clean up headings and spacing in the open note.
