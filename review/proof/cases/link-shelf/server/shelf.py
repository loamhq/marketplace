import json
import os
import threading
import time
import uuid

DATA_DIR = os.environ.get("LOAM_PLUGIN_DATA", ".")
SHELF_PATH = os.path.join(DATA_DIR, "shelf.json")
_lock = threading.Lock()


def _read():
    try:
        with open(SHELF_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return {"links": []}
    except (OSError, ValueError):
        return {"links": []}
    if not isinstance(data, dict) or not isinstance(data.get("links"), list):
        return {"links": []}
    return data


def _write(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = SHELF_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
    os.replace(tmp, SHELF_PATH)


def all_links():
    with _lock:
        return _read()["links"]


def add_link(url, title, tags):
    link = {
        "id": uuid.uuid4().hex[:12],
        "url": url,
        "title": title,
        "tags": [str(t).strip() for t in tags if str(t).strip()],
        "saved_at": int(time.time()),
    }
    with _lock:
        data = _read()
        data["links"].insert(0, link)
        _write(data)
    return link


def remove_link(link_id):
    with _lock:
        data = _read()
        before = len(data["links"])
        data["links"] = [l for l in data["links"] if l.get("id") != link_id]
        if len(data["links"]) == before:
            return False
        _write(data)
    return True


def search(query):
    query = (query or "").strip().lower()
    links = all_links()
    if not query:
        return links
    out = []
    for link in links:
        hay = " ".join([link.get("title", ""), link.get("url", "")] + link.get("tags", [])).lower()
        if query in hay:
            out.append(link)
    return out
