---
id: translate-inline
name: Translate Inline
version: 1.0.0
author: Noor Haddad
api: 0
kind: [extension]
places: [app.overlay]
touches:
  network:
    - host: api.lingvo.example.invalid
      why: sends only the passage you select, to be translated
  record: none
  memory: none
  server: true
keys:
  - provider: lingvo
    name: Lingvo
    why: translates the passage you select
    fields: [{name: LINGVO_API_KEY, label: API key}]
icon: assets/icon.svg
description: Translate a selected passage of any reply into your language without leaving the thread.
---

# Translate Inline

Select a few words or a paragraph in any reply, press Translate, and read it in your own language in a small card beside the text.

## What you can do

- Translate any passage of an agent's reply without copying it anywhere.
- Keep reading the thread while the translation sits beside it.

## How to use it

1. Add your Lingvo key in Settings › Connections › API keys.
2. Select some text in a reply.
3. Press Translate on the small button that appears.

Only the passage you select is sent to Lingvo to be translated, using your own Lingvo key.

---

## Technical details

- Place: `app.overlay`.
- Server: a small Node program (standard library only) at `/x/translate-inline/`, with `GET status` and `POST translate`.
- Network: `api.lingvo.example.invalid`, `POST /v1/translate`, with your key from `LOAM_PLUGIN_KEYS`.
- The target language is your browser's language, saved on this device under `translate-inline.target`.
- Record: none. Memory: none.
