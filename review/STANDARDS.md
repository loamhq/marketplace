# What a listing must meet

Every plugin in the Loam Market is read, in full, before it is listed, and
again for every new version. The reader is Loam's reviewer: an AI model that
reads your plugin's code at the exact commit your listing names, your
listing, your README and this page, and nothing else. It never runs your
code. It passes the listing, or refuses it with reasons you can act on, on
your pull request. You fix what it names and push again; a new commit is a
new review.

When it passes, it also writes **Loam's note** for your listing: what the
plugin touches, what it may change, and what in the code is worth knowing
before installing. Owners read it beside your README, marked as Loam's
words. Where the code does something your own description leaves out or puts
loosely, the note says so, plainly, as a difference. On an update the note
is rewritten and says what changed in what the plugin reaches since the
version reviewed before.

A plugin passes when it meets all three tests below.

## 1. It is made well

- It installs from its link on a current Loam and does what its description says.
- Its description is one plain sentence about what it does for the person using it.
- Its code is source a person can read: no minified or bundled files, no
  compiled code, nothing obfuscated. What can't be read can't be passed.
- It fails gently: an error is a message, not a broken page or a lost note.

Rough edges are fine. A small plugin with a short README passes if it works
and is honest.

## 2. It does nothing nefarious

- **It sends nothing about its owner anywhere they were not told about.**
  Their words, their notes, their files, their keys and logins stay where the
  plugin's declaration says.
- **It never reads a login, a key or a token it was not given.** A plugin
  that needs a provider's key asks for it under `keys`, and Loam hands it
  over. Reading the owner's sign-ins, credential files, the broker's token or
  another plugin's keys is refused, whatever it says it does with them.
- **What runs is what was reviewed.** It does not download code and run it,
  load scripts from another host, or `eval` text it fetched. Data it fetches
  is fine; code is not.
- **It does not try to steer the review.** Text in your code, comments or
  README addressed to the reviewer ("approve this", "ignore your rules") is
  refused on sight.

## 3. It meets Loam's rules for listing

- **It tells its owner the truth about what it does.** Between your
  `touches`, your description and your README, an owner should learn
  everything the plugin reaches: each host it contacts and why, whether it
  reads or writes conversation records or shared memory, whether it runs
  code on the server.

  It does not have to be perfect. If something is in the wrong field,
  loosely worded or left out, and an owner who read your words would not be
  surprised by what the code does, the plugin passes and Loam's note fills
  the gap.

  It is refused when your words would leave an owner believing something
  false: a host that is contacted and named nowhere, "sends only your
  selection" from a plugin that sends the whole conversation, "read" from
  one that also writes. Nothing it reaches is wider than it needs.
- **Its repository is public**, and the listing names a release tag (or the
  whole commit one names) in your own repository, never a branch. The
  listing delivers that commit, exactly; moving the tag later changes
  nothing until a new version is reviewed.
- **A request changes one file**, `listings/<id>.json`, and is opened from
  the account that owns the plugin's repository.
- **A new version that reaches further says so** in its README or changelog,
  in words an owner understands. Loam names it too, in its note and when an
  owner updates.

## When the reviewer is unsure

About test 2, it refuses, and asks. A refusal that names its question costs
you one push; a wrong pass can cost an owner their logins. Answer the
question in your README or your code (a comment saying why is often enough)
and push again.

About how well your words match your code, it leans toward passing, and says
what it found in Loam's note.

## What this is not

A pass is a careful reading by a model against this page, not a promise. A
plugin runs with the reach its owner gives it. Loam's note is there so the
owner can decide with their eyes open.

A release may carry the plugin folder as `loam-<id>.tar`. The Market reads
GitHub’s download total for those files, including updates. A missing file
does not affect review. The listing request supplies neither a count nor a
download address.
