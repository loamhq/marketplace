# The Loam marketplace

The list of Loam plugins (themes, extensions, apps, agents and skills) that
every Loam reads in Settings › Plugins. The plugins themselves are not here:
each builder hosts their own work in their own GitHub repository, and a
listing points to it at a tag. Installing from a listing is the same as
installing from its link: Loam shows what the plugin declares, and installs
it only on its owner's yes.

## Every listing is reviewed by hand

A person reads every listing before it is merged: the plugin's `PLUGIN.md`,
what it declares under `touches` (the hosts it contacts and why, whether it
reads or changes conversation records or shared memory, whether it runs code
on the server), and its code. A listing is merged when:

- it installs from its link on a current Loam, and does what its description says;
- what it declares is what it does: no host it contacts is missing, and
  nothing it reaches is wider than it needs;
- it sends nothing about its owner anywhere they were not told about;
- its repository is public, and the listing names a tag or a full commit, never a branch;
- its description is one plain sentence about what it does for the person
  using it.

Being listed is not a security audit, and a later version is not reviewed
until its listing is updated to point at it. Loam itself confirms every
version, and names anything a new version declares that the last did not.

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

| Field | |
|---|---|
| `id` | the plugin's id, as in its `PLUGIN.md`; the file is named by it |
| `name`, `author` | as the plugin says them, at most 60 characters |
| `description` | one sentence, at most 200 characters |
| `kind` | one or more of `theme`, `extension`, `app`, `agent`, `skill` |
| `version` | optional: the version at the link |
| `link` | the plugin's folder at a tag or a full commit: `https://github.com/<owner>/<repo>/tree/<tag>/<folder>` |
| `homepage` | optional: an https link about it |

A new version is a pull request that changes `link` (and `version`). To be
taken off the list, open a pull request that deletes the file.

## How the list is made

`list.json` is what every Loam reads, at
`https://raw.githubusercontent.com/loamhq/marketplace/main/list.json`. It is
built from `listings/` by `build.py` when a pull request is merged
(`.github/workflows/list.yml`) and is never edited by hand. `python3 build.py
--check` checks every listing against the rules a Loam applies when it reads
the list; the workflow runs it on every pull request.
