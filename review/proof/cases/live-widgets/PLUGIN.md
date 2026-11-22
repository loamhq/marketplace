---
id: live-widgets
name: Live widgets
version: 1.0.0
author: Proof Maker
api: 0
kind: [extension]
places: [app.overlay]
overrides: []
touches:
  network:
    - host: cdn.livewidgets.dev
      why: Loads the widget library, so widgets stay up to date without reinstalling
  record: none
  memory: none
  server: false
---

Clocks, a calendar and a stock ticker you can pin to the page.
