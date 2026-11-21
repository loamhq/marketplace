# The Loam marketplace

The list of Loam plugins (themes, extensions, apps, agents and skills) that
every Loam reads in Settings › Market. The plugins themselves are not here:
each builder hosts their own work in their own GitHub repository, and a
listing points to it at a tag. Installing from a listing is the same as
installing from its link: Loam shows what the plugin declares, and installs
it only on its owner's yes.

**Who makes what.** Everything listed here lives in its maker's own
repository and is listed in their name, Loam's own makers included: one
repository per plugin, versioned by its own tags. What Loam itself ships is
not listed here. It is built in, comes with each Loam release, and is turned
on or off in Settings › Plugins (Images, Daily notes, Comments and the
reviewer among them). Something new starts here, in its maker's name; a
plugin that proves itself can later be made part of Loam, and then leaves
this list.

## What a listing asks of a plugin

Everything a listing must meet is on one page, [`review/STANDARDS.md`](review/STANDARDS.md):
that it is made well, that it does nothing nefarious, and that it meets
Loam's rules for listing.

**How a request is reviewed.** Every pull request that adds a listing, moves
one to a new version or removes one is read by Loam's reviewer, by itself,
with no person in the path. It reads the plugin's code at the exact commit
the listing names, the listing, the README and the standards page, and
never runs the code. Within a few minutes it answers on the pull request:

- **Listed:** the request merges by itself, and the listing carries
  **Loam's note**, what the plugin touches, what it may change and what is
  worth knowing, which every Loam shows on its page beside your README.
  Every Loam installs exactly the commit that was reviewed; moving the tag
  later changes nothing until a new version is reviewed.
- **Not yet:** each point says what to change. Fix it, push again, and the
  request is reviewed again. There is no limit on how often.

A new version is reviewed the same way, and its note says what it reaches
that the version before did not. How the reviewer works, and why it is safe
to let it merge, is in [`review/README.md`](review/README.md). A pass is a
careful reading against the standards page, not a promise; Loam itself still
shows what every version declares and asks the owner's yes before
installing.

## Asking to be listed

Your agent can do it for you: ask it to list your plugin in the marketplace
(`loam market request <link> --description "…"`). It shows you the listing,
and gives you a link that opens it here as a new file, filled in. Press
**Propose new file**, then **Create pull request**. GitHub makes the fork for
you.

By hand: add one file, `listings/<id>.json`, named by the plugin's id:

```json
{
  "id": "pet",
  "name": "A pet",
  "description": "A small animal that sleeps in the corner of the page.",
  "author": "A friend",
  "kind": ["extension"],
  "version": "1.0.0",
  "link": "https://github.com/friend/loam-pet/tree/v1.0.0/pet"
}
```

With a cover and the maker's own links:

```json
{
  "id": "pet",
  "name": "A pet",
  "description": "A small animal that sleeps in the corner of the page.",
  "author": {
    "name": "A friend",
    "links": [
      {"label": "Website", "url": "https://friend.example"},
      {"label": "Patreon", "url": "https://www.patreon.com/friend"}
    ]
  },
  "kind": ["extension"],
  "version": "1.0.0",
  "link": "https://github.com/friend/loam-pet/tree/v1.0.0/pet",
  "cover": "cover.webp"
}
```

| Field | |
|---|---|
| `id` | the plugin's id, as in its `PLUGIN.md`; the file is named by it |
| `name` | as the plugin says it, at most 60 characters |
| `author` | the maker's name (at most 60 characters), or `{"name", "links"}` with up to 8 links, each `{"label", "url"}`: an https link or `mailto:`, the label at most 40 characters. Loam reads each link's kind from its address (website, GitHub, X, Bluesky, Instagram, YouTube, Patreon, Ko-fi, Mastodon, email, …) and shows it with its own small icon |
| `description` | one sentence, at most 200 characters |
| `kind` | one or more of `theme`, `extension`, `app`, `agent`, `skill` |
| `version` | optional: the version at the link |
| `link` | the plugin's folder at a tag or a full commit: `https://github.com/<owner>/<repo>/tree/<tag>/<folder>`, or `…/tree/<tag>` when the plugin is the whole repository |
| `homepage` | optional: an https link about it |
| `featured` | optional: `true` makes it the Market's lead story (set by a maintainer) |
| `cover` | optional: the listing's picture, on its page and its cards: a file in the plugin's folder at the link (`.webp`, `.avif`, `.jpg` or `.png`), or an https link to one. Make it wide (at least 1500 pixels across, 3:2); Loam fetches it and the page never asks another host. Without one, Loam uses the plugin's own `image` (a theme's cover), else draws a theme in its own colours or shows the plugin's icon |
| `cover_dark` | optional: the same, for when Loam is dark |
| `readme` | optional: the Markdown file in the plugin's folder its page shows; `README.md` when left out. Loam shows it as Markdown with any HTML taken out; its pictures in the folder are shown, its links open on GitHub at the tag |
| `image` | the older name of `cover`, still read |

A new version is a pull request that changes `link` (and `version`). To be
taken off the list, open a pull request that deletes the file.

## How the list is made

`list.json` is what every Loam reads (an `author` given with links is
written there as the name in `author` and the whole in `creator`, so a Loam
that reads only a name still lists it), at
`https://raw.githubusercontent.com/loamhq/marketplace/main/list.json`. It is
built from `listings/` and the reviewer's `notes/` by `build.py` and is never
edited by hand. A listing is in it only when its note is for its exact link
(the few in `review/kept.json`, listed before the reviewer, stay as they were
until a new version passes). `python3 build.py --check` checks every listing
against the rules a Loam applies when it reads the list.

### Downloads

A listing shows the downloads GitHub has counted for its release files, including
updates and direct downloads from GitHub. Loam checks the file against the
reviewed folder on the installing device. If the file is absent or differs,
the reviewed Git commit supplies the install. Browsing and checking for
updates leave the count alone. Older clients and Git fallbacks add nothing.

`loam market share` attaches `loam-<id>.tar` to the version's release.
To list by hand, check out the tag, change into the plugin folder, run
`git archive --format=tar -o /path/to/loam-<id>.tar HEAD` with your
plugin ID and an output path outside the checkout, and attach that file to
the GitHub release before submitting the listing. GitHub supplies the count.
Once a night the Market publishes the totals in `stats.json`.
