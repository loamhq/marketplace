---
id: thread-tagger
name: Thread Tagger
version: 1.0.0
author: Sam Oduya
api: 0
kind: [extension]
places: [thread.list.line, thread.header.action]
touches:
  network: []
  record: read
  memory: none
  server: false
description: Suggests short topic tags for your threads so you can find them again later.
---

# Thread Tagger

Thread Tagger looks at the words in your threads and suggests a few short topic tags for each one, so a long list of chats is easier to scan.

## What you can do

- See the main topics of your recent threads in one line above your agents in Chats.
- See suggested tags under the header of any open thread.
- Press a tag to keep it on that thread.

## How to use it

1. Turn Thread Tagger on in Settings › Plugins.
2. Open Chats to see the topics line, or open a thread to see its tags.
3. Press a suggested tag to keep it.

No AI is used. The tags come from counting words in your browser.

---

## Technical details

- Places: `thread.list.line` and `thread.header.action` (below the header).
- Reads the thread list (`GET /api/threads`) and each thread (`GET /api/threads/<id>`) through the page's own relay.
- Tags are chosen by word frequency, weighted against your other recent threads. Common words are ignored.
- Kept tags are remembered so they show wherever you are signed in.
- Network: none. Memory: none. Server: none.
