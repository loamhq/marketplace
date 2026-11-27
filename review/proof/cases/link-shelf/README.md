# Link Shelf

Save a link once and find it again. Link Shelf keeps a tidy shelf of the
pages you want to come back to, with a title and tags you choose, and a
search box to pull one back up.

## What you can do

- Save any link with a title and a few tags.
- Search your shelf by title, address or tag.
- Remove a link when you no longer need it.

## How to use it

1. Open Link Shelf from Apps.
2. Paste a link, give it a title and tags, and press Save.
3. Type in the search box to find anything you saved.

Your shelf is kept on this server, in Link Shelf's own data folder.

---

## Technical details

- **Server.** A small Python server (standard library only) serves the page
  under `/x/link-shelf/` and a JSON API: `GET /api/links`,
  `GET /api/search?q=`, `POST /api/links`, `DELETE /api/links/<id>`.
- **Storage.** Links live in `LOAM_PLUGIN_DATA/shelf.json`, written
  atomically.
- **Network.** Once a week the server asks
  `updates.linkshelf.example.invalid` whether a newer version of Link Shelf
  has been published.
- **Permissions.** No record, memory or key access.
