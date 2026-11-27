---
id: link-shelf
name: Link Shelf
version: 1.0.0
author: tomas-lind
api: 0
kind: [app]
description: Save links from your threads to a shelf and find them again by title or tag.
touches:
  network:
    - host: updates.linkshelf.example.invalid
      why: checks whether a newer version of Link Shelf is out
  record: none
  memory: none
  server: true
server:
  run: python3 server/main.py
icon: assets/icon.svg
---

# Link Shelf

Save a link once and find it again. Link Shelf keeps a tidy shelf of the
pages you want to come back to, with a title and the tags you choose.

## What you can do

- Save any link with a title and a few tags.
- Search your shelf by title, address or tag.

## How to use it

1. Open Link Shelf from Apps.
2. Paste a link, give it a title and tags, and press Save.
3. Type in the search box to pull anything back up.

Your shelf is kept on this server, in Link Shelf's own data folder.

---

## Technical details

The server serves its page under `/x/link-shelf/` and a small JSON API, and
keeps your links in `LOAM_PLUGIN_DATA/shelf.json`. Once a week it asks
`updates.linkshelf.example.invalid` whether a newer version is out.
