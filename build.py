#!/usr/bin/env python3
"""Check the listings, and build list.json from them.

  python3 build.py          check every listings/*.json and write list.json
  python3 build.py --check  check only; exit 1 if any listing breaks a rule,
                            or if list.json is not what the listings make

Each listing is one file, `listings/<id>.json`, so a pull request that asks
for a listing adds one file and can be opened from GitHub's own new-file page
with nothing to merge by hand. `list.json` is what every Loam reads; it is
built from the listings when a pull request is merged (the workflow in
.github/workflows/list.yml), never edited by hand.

**Only a reviewed listing is listed.** Loam's reviewer
(.github/workflows/review.yml, review/) writes `notes/<id>.json` when it
passes a listing: the link it reviewed, the commit that link named then, and
Loam's note. A listing goes into list.json only when its note is for its own
`link`, and goes there with `review` (that commit and that note), so every
Loam installs exactly the commit that was reviewed even if a tag is moved
later. A listing with no note, or a note for another link, is left out until
it is reviewed; no hand edit can list something the reviewer did not pass.
The one exception is review/kept.json: listings that were on the list before
the reviewer and that its first review refused, kept exactly as they were
(same link, no note) until a new version of each passes.

The rules are the ones a Loam applies when it reads the list
(lib/loam_marketplace.py in loamhq/loam, `check_entry`): a listing that breaks
one is left out there, so it is refused here first. Python 3.9+, no packages.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FORMAT = 1
ID = re.compile(r"^[a-z][a-z0-9-]*$")
KINDS = ("theme", "extension", "app", "agent", "skill")
LIMITS = {"name": 60, "author": 60, "description": 200}
FIELDS = ("id", "name", "description", "author", "kind", "version", "link", "homepage",
          "featured", "cover", "cover_dark", "readme", "image")
# What list.json carries besides: `creator`, the whole of an `author` given
# as an object, while `author` there is the name alone, so a Loam that reads
# only a name still lists it.
OUT_FIELDS = FIELDS[:4] + ("creator",) + FIELDS[4:]
# A folder of a GitHub repository at a tag or a full commit: .../tree/<ref>[/<folder>]
LINK = re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/tree/([^/?#]+)(/[^?#]*)?$")
SHA = re.compile(r"^[0-9a-f]{40}$")
BRANCHES = {"main", "master", "trunk", "develop", "dev"}
VERSION = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.+-]+)?$")
# A picture inside the plugin's folder at its link, as a theme's cover is named.
IMAGE = re.compile(r"^(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+\.(?:webp|avif|jpe?g|png)$", re.I)
# A Markdown file inside the plugin's folder: the README its page shows.
README = re.compile(r"^(?:[A-Za-z0-9_-][A-Za-z0-9_.-]*/)*[A-Za-z0-9_-][A-Za-z0-9_.-]*\.(?:md|markdown)$", re.I)
LINKS_MAX = 8
LABEL_MAX = 40
URL_MAX = 300
MAILTO = re.compile(r"^mailto:[^@/?#\s]+@[^@/?#\s]+\.[^@/?#\s]+$", re.I)
HTTPS = re.compile(r"^https://[^/\s?#]+[^\s]*$")


def is_cover(value) -> bool:
    """A cover: a picture in the plugin's folder, or an https address of one."""
    return isinstance(value, str) and len(value) <= URL_MAX and bool(
        IMAGE.match(value) or HTTPS.match(value))


def check_author(name: str, value) -> list[str]:
    """`author` is a name, or {"name", "links": [{"label", "url"}]}."""
    if isinstance(value, str):
        value = {"name": value}
    if not isinstance(value, dict):
        return [f"{name}: `author` is a name, or {{\"name\", \"links\"}}"]
    errors = []
    extra = sorted(set(value) - {"name", "links"})
    if extra:
        errors.append(f"{name}: `author` has unknown fields {', '.join(extra)}")
    who = value.get("name")
    if not isinstance(who, str) or not who.strip():
        errors.append(f"{name}: `author` (or its `name`) is a line of text")
    elif len(" ".join(who.split())) > LIMITS["author"]:
        errors.append(f"{name}: `author` is at most {LIMITS['author']} characters")
    links = value.get("links", [])
    if not isinstance(links, list) or len(links) > LINKS_MAX:
        errors.append(f"{name}: `author.links` is a list of at most {LINKS_MAX}")
        return errors
    for i, link in enumerate(links):
        if not isinstance(link, dict) or set(link) - {"label", "url"}:
            errors.append(f"{name}: `author.links[{i}]` is {{\"label\", \"url\"}}")
            continue
        url, label = link.get("url"), link.get("label", "")
        if not isinstance(url, str) or len(url) > URL_MAX or not (HTTPS.match(url) or MAILTO.match(url)):
            errors.append(f"{name}: `author.links[{i}].url` is an https link or mailto:")
        if not isinstance(label, str) or len(label) > LABEL_MAX:
            errors.append(f"{name}: `author.links[{i}].label` is at most {LABEL_MAX} characters")
    return errors


def check(path: Path) -> tuple[dict | None, list[str]]:
    name = path.name
    try:
        entry = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, [f"{name}: not JSON ({exc})"]
    if not isinstance(entry, dict):
        return None, [f"{name}: a listing is one JSON object"]
    errors = []
    pid = entry.get("id")
    if not isinstance(pid, str) or not ID.match(pid):
        errors.append(f"{name}: `id` is the plugin's id (lower case, digits, dashes)")
    elif name != f"{pid}.json":
        errors.append(f"{name}: the file is named by the id, `{pid}.json`")
    errors += check_author(name, entry.get("author"))
    for field, required in (("name", True), ("description", True)):
        value = entry.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{name}: `{field}` is a line of text")
        elif len(" ".join(value.split())) > LIMITS[field]:
            errors.append(f"{name}: `{field}` is at most {LIMITS[field]} characters")
    kind = entry.get("kind")
    kind = [kind] if isinstance(kind, str) else kind
    if not isinstance(kind, list) or not kind or any(k not in KINDS for k in kind):
        errors.append(f"{name}: `kind` is a list of {', '.join(KINDS)}")
    link = entry.get("link")
    m = LINK.match(link) if isinstance(link, str) else None
    if not m:
        errors.append(f"{name}: `link` is https://github.com/<owner>/<repo>/tree/<tag or commit>/<folder>")
    elif m.group(1) in BRANCHES:
        errors.append(f"{name}: `link` names the branch {m.group(1)!r}; a listing is at a tag or a commit")
    if "version" in entry and not (isinstance(entry["version"], str) and VERSION.match(entry["version"])):
        errors.append(f"{name}: `version` is major.minor.patch")
    if "homepage" in entry and not (isinstance(entry["homepage"], str) and entry["homepage"].startswith("https://")):
        errors.append(f"{name}: `homepage` is an https link")
    if "featured" in entry and entry["featured"] is not True:
        errors.append(f"{name}: `featured` is true, or left out")
    if "image" in entry and not (isinstance(entry["image"], str) and IMAGE.match(entry["image"])):
        errors.append(f"{name}: `image` is a picture in the plugin's folder (.webp, .avif, .jpg or .png)")
    if "image" in entry and "cover" in entry:
        errors.append(f"{name}: `image` is the older name of `cover`; give `cover` alone")
    for field in ("cover", "cover_dark"):
        if field in entry and not is_cover(entry[field]):
            errors.append(f"{name}: `{field}` is a picture in the plugin's folder (.webp, .avif, "
                          f".jpg or .png) or an https link to one")
    if "readme" in entry and not (isinstance(entry["readme"], str) and README.match(entry["readme"])
                                  and ".." not in entry["readme"].split("/")):
        errors.append(f"{name}: `readme` is a Markdown file in the plugin's folder")
    extra = sorted(set(entry) - set(FIELDS))
    if extra:
        errors.append(f"{name}: unknown fields {', '.join(extra)}")
    if errors:
        return None, errors
    out = {k: entry[k] for k in FIELDS if k in entry}
    author = out["author"]
    if isinstance(author, dict):
        out["author"] = author["name"]
        out["creator"] = {"name": " ".join(author["name"].split()),
                          "links": [{"label": " ".join(link.get("label", "").split()), "url": link["url"]}
                                    for link in author.get("links", [])]}
    for field in LIMITS:
        if field in out:
            out[field] = " ".join(out[field].split())
    out["kind"] = kind
    out = {k: out[k] for k in OUT_FIELDS if k in out}
    return out, []


NOTE_LISTS = ("touches", "may_change", "worth_knowing", "changed")
NOTE_ITEMS, NOTE_ITEM_MAX, SUMMARY_MAX = 8, 400, 600


def _text(value, limit: int) -> str | None:
    return " ".join(value.split())[:limit] if isinstance(value, str) and value.strip() else None


def review_of(root: Path, pid: str, link: str) -> tuple[dict | None, str | None]:
    """The reviewer's record for the listing at ``link``, as list.json
    carries it, or why the listing waits (not reviewed, or reviewed at
    another link)."""
    path = root / "notes" / f"{pid}.json"
    if not path.is_file():
        return None, f"{pid}: not reviewed yet"
    try:
        note = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, f"{pid}: its note is not JSON ({exc})"
    if not isinstance(note, dict) or note.get("link") != link:
        return None, f"{pid}: its note is for another link; the listing waits for its review"
    if not isinstance(note.get("commit"), str) or not SHA.match(note["commit"]):
        return None, f"{pid}: its note names no whole commit"
    body = note.get("note") if isinstance(note.get("note"), dict) else {}
    out_note = {"summary": _text(body.get("summary"), SUMMARY_MAX) or ""}
    for field in NOTE_LISTS:
        items = [t for t in (_text(x, NOTE_ITEM_MAX) for x in body.get(field) or []
                             if isinstance(body.get(field), list)) if t][:NOTE_ITEMS]
        if items:
            out_note[field] = items
    if _text(body.get("since"), 40):
        out_note["since"] = _text(body.get("since"), 40)
    review = {"commit": note["commit"], "note": out_note}
    folder = note.get("folder")
    if isinstance(folder, str) and (folder == "" or (re.match(r"^[A-Za-z0-9_./-]+$", folder)
                                                     and ".." not in folder.split("/"))):
        review["folder"] = folder
    for field in ("version", "reviewed_at"):
        if _text(note.get(field), 40):
            review[field] = _text(note.get(field), 40)
    return review, None


def kept_as_before(root: Path, pid: str, link: str) -> bool:
    """A listing that was on the list before the reviewer, and that the
    first review refused, stays listed as it was, at exactly the link it had
    then and with no note, until a new version of it passes
    (review/kept.json). Any other link for it waits for its review."""
    path = root / "review" / "kept.json"
    try:
        kept = json.loads(path.read_text(encoding="utf-8")).get("listings", {})
    except (OSError, ValueError, AttributeError):
        return False
    return isinstance(kept, dict) and kept.get(pid) == link


def build(root: Path = HERE, waiting: list | None = None) -> tuple[dict, list[str]]:
    entries, errors = [], []
    for path in sorted((root / "listings").glob("*.json")):
        entry, problems = check(path)
        errors += problems
        if entry:
            review, why = review_of(root, entry["id"], entry["link"])
            if why and kept_as_before(root, entry["id"], entry["link"]):
                entries.append(entry)
                continue
            if why:
                if waiting is not None:
                    waiting.append(why)
                continue
            entry["review"] = review
            entries.append(entry)
    entries.sort(key=lambda e: (e["name"].lower(), e["id"]))
    return {"version": FORMAT, "plugins": entries}, errors


def text_of(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str]) -> int:
    root = HERE
    waiting: list[str] = []
    data, errors = build(root, waiting)
    for line in errors:
        print(line, file=sys.stderr)
    for line in waiting:
        print(f"left out: {line}", file=sys.stderr)
    if "--check" in argv:
        current = (root / "list.json").read_text(encoding="utf-8") if (root / "list.json").is_file() else ""
        if errors:
            return 1
        if current and current != text_of(data):
            # On a pull request list.json is built after the merge, so it is
            # expected to lag; on main it must match.
            print("list.json is not what the listings make (it is built on merge)",
                  file=sys.stderr)
            return 1 if "--strict" in argv else 0
        print(f"{len(data['plugins'])} listings, all well formed")
        return 0
    if errors:
        return 1
    (root / "list.json").write_text(text_of(data), encoding="utf-8")
    print(f"list.json: {len(data['plugins'])} listings")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
