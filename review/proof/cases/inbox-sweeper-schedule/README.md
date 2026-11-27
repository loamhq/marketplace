# Inbox Sweeper

Moves old, finished notes out of your inbox folder into a tidy archive, so your
inbox only holds what still needs you.

## What you can do

- Choose how old a note must be before it is archived.
- Let Inbox Sweeper move finished notes into `Archive/<year>/` automatically.

## How to use it

1. Turn Inbox Sweeper on in Settings › Plugins.
2. Open its settings and pick an age in days.
3. Leave it — nothing is ever deleted, only moved.

Inbox Sweeper tidies your vault's `Inbox` and `Archive` folders for you.
Nothing leaves your server.

---

## Technical details

- A `settings.section` sets `min_age_days`.
- On Loam's nightly schedule, notes in `Inbox` older than that, with no open
  `- [ ]` tasks and no `#todo`, are moved to `Archive/<year>/`. A note is never
  deleted, and an existing archive file is left alone.
