#!/usr/bin/env python3
"""Nightly sweep: move finished inbox notes into Archive/<year>/."""
import datetime
import json
import os
import shutil

import rules


def _vault():
    return os.environ.get("LOAM_VAULT") or os.environ.get("LOAM_VAULT_DATA_DIR") or ""


def _min_age_days():
    path = os.path.join(os.environ.get("LOAM_PLUGIN_SETTINGS_DIR", ""), "values.json")
    try:
        with open(path) as f:
            return int(json.load(f).get("min_age_days", 30))
    except (OSError, ValueError, TypeError):
        return 30


def sweep():
    vault = _vault()
    if not vault:
        return 0
    inbox = os.path.join(vault, "Inbox")
    if not os.path.isdir(inbox):
        return 0
    min_age = _min_age_days()
    moved = 0
    for name in os.listdir(inbox):
        src = os.path.join(inbox, name)
        if not os.path.isfile(src) or not name.endswith(".md"):
            continue
        if not rules.is_finished(src, min_age):
            continue
        year = datetime.date.fromtimestamp(os.path.getmtime(src)).strftime("%Y")
        dest_dir = os.path.join(vault, "Archive", year)
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, name)
        if os.path.exists(dest):
            continue  # never overwrite, never delete
        shutil.move(src, dest)
        moved += 1
    return moved


if __name__ == "__main__":
    sweep()
