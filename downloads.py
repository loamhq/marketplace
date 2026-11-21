"""GitHub release metadata for the Market. The collector never requests asset bytes."""
import http.client
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote


def api(path):
    headers = {"Accept": "application/vnd.github+json"}
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request("https://api.github.com" + path, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as answer:
        return json.load(answer)


def pages(path):
    page = 1
    while True:
        rows = api(f"{path}?per_page=100&page={page}")
        if not isinstance(rows, list):
            raise ValueError("Expected a page of release metadata")
        yield from rows
        if len(rows) < 100:
            return
        page += 1


def release_asset(repo, tag, pid):
    """Optional transport hint. Installation independently verifies the reviewed tree."""
    try:
        release = api(f"/repos/{repo}/releases/tags/{quote(tag, safe='')}")
        for asset in pages(f"/repos/{repo}/releases/{int(release['id'])}/assets"):
            digest = asset.get("digest") or ""
            if (asset["name"] == f"loam-{pid}.tar" and asset["state"] == "uploaded"
                    and re.fullmatch(r"sha256:[0-9a-f]{64}", digest)):
                return {"tag": tag, "sha256": digest[7:]}
    except (OSError, ValueError, KeyError, http.client.HTTPException):
        pass
    return None


def collect(root):
    path = root / "stats.json"
    stats = json.loads(path.read_text()) if path.exists() else {"version": 1, "plugins": {}}
    if stats["version"] != 1:
        raise ValueError("Unknown stats format")
    for entry in json.loads((root / "list.json").read_text())["plugins"]:
        pid = entry["id"]
        repo = "/".join(entry["link"].split("/")[3:5])
        counters = stats["plugins"].setdefault(pid, {"assets": {}, "downloads": 0})["assets"]
        try:
            for release in pages(f"/repos/{repo}/releases"):
                if release["draft"]:
                    continue
                for asset in pages(f"/repos/{repo}/releases/{int(release['id'])}/assets"):
                    if asset["name"] == f"loam-{pid}.tar" and asset["state"] == "uploaded":
                        key = str(int(asset["id"]))
                        counters[key] = max(counters.get(key, 0), int(asset["download_count"]))
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise
            # A removed or private repository retains its observed counters.
        stats["plugins"][pid]["downloads"] = sum(counters.values())
    path.write_text(json.dumps(stats, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    collect(Path(__file__).resolve().parent)
