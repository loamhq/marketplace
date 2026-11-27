# Inbox Sweeper

Keeps your inbox folder tidy: an agent can move old, finished notes out of your
inbox into a year-based archive whenever you ask, and nothing is ever deleted.

## What you can do

- Choose how old a note must be before it counts as ready to archive.
- Ask any of your agents to tidy your inbox: "tidy my inbox" moves finished
  notes into `Archive/<year>/`.

## How to use it

1. Turn Inbox Sweeper on in Settings › Plugins.
2. Open its settings and pick an age in days.
3. Ask an agent to tidy your inbox when it is getting full.

Inbox Sweeper works on your vault's `Inbox` and `Archive` folders. Nothing
leaves your server.

---

## Technical details

- A `settings.section` sets `min_age_days`.
- The `archive_inbox` agent tool moves notes in `Inbox` older than that, with
  no open `- [ ]` tasks and no `#todo`, into `Archive/<year>/`. A note is never
  deleted, and an existing archive file is left alone.
