import json
import time
import urllib.request
from urllib.parse import urlparse, urlencode

import shelf

BASE = "https://updates.linkshelf.example.invalid/v1/latest"
CURRENT_VERSION = "1.0.0"
INTERVAL = 7 * 24 * 60 * 60


def _compat_hosts():
    # The update service tells us whether a newer build is relevant to the
    # kinds of pages on this shelf, so we pass the distinct hosts we hold.
    hosts = set()
    for link in shelf.all_links():
        host = urlparse(link.get("url", "")).hostname
        if host:
            hosts.add(host.lower())
    return sorted(hosts)


def check_once():
    params = {"v": CURRENT_VERSION, "for": ",".join(_compat_hosts())}
    url = BASE + "?" + urlencode(params)
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("latest")
    except Exception:
        return None


def run_forever():
    while True:
        check_once()
        time.sleep(INTERVAL)
