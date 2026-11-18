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
FIELDS = ("id", "name", "description", "author", "kind", "version", "link", "homepage")
# A folder of a GitHub repository at a tag or a full commit: .../tree/<ref>[/<folder>]
LINK = re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/tree/([^/?#]+)(/[^?#]*)?$")
SHA = re.compile(r"^[0-9a-f]{40}$")
BRANCHES = {"main", "master", "trunk", "develop", "dev"}
VERSION = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.+-]+)?$")


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
    for field, required in (("name", True), ("author", True), ("description", True)):
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
    extra = sorted(set(entry) - set(FIELDS))
    if extra:
        errors.append(f"{name}: unknown fields {', '.join(extra)}")
    if errors:
        return None, errors
    out = {k: entry[k] for k in FIELDS if k in entry}
    for field in LIMITS:
        if field in out:
            out[field] = " ".join(out[field].split())
    out["kind"] = kind
    return out, []


def build(root: Path = HERE) -> tuple[dict, list[str]]:
    entries, errors = [], []
    for path in sorted((root / "listings").glob("*.json")):
        entry, problems = check(path)
        errors += problems
        if entry:
            entries.append(entry)
    entries.sort(key=lambda e: (e["name"].lower(), e["id"]))
    return {"version": FORMAT, "plugins": entries}, errors


def text_of(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str]) -> int:
    root = HERE
    data, errors = build(root)
    for line in errors:
        print(line, file=sys.stderr)
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
