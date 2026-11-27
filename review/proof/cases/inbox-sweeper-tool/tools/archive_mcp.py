#!/usr/bin/env python3
"""A tiny MCP server giving an agent one tool: tidy the inbox.

Loam runs this in the plugin's folder when an agent uses the tool. When the
tool is called it moves finished notes out of the vault's Inbox folder into
Archive/<year>/. Python's standard library only.
"""
import datetime
import json
import os
import shutil
import sys

import rules

PROTOCOL = "2024-11-05"


def _vault():
    return os.environ.get("LOAM_VAULT") or os.environ.get("LOAM_VAULT_DATA_DIR") or ""


def _min_age_days():
    path = os.path.join(os.environ.get("LOAM_PLUGIN_SETTINGS_DIR", ""), "values.json")
    try:
        with open(path, encoding="utf-8") as f:
            return int(json.load(f).get("min_age_days", 30))
    except (OSError, ValueError, TypeError):
        return 30


def sweep():
    vault = _vault()
    if not vault:
        return "This server has no vault to tidy."
    inbox = os.path.join(vault, "Inbox")
    if not os.path.isdir(inbox):
        return "There is no Inbox folder to tidy yet."
    min_age = _min_age_days()
    moved = 0
    for name in sorted(os.listdir(inbox)):
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
    return "Moved %d finished note(s) into Archive." % moved


TOOLS = [
    {
        "name": "archive_inbox",
        "description": "Move finished notes older than the chosen age out of the vault's Inbox folder into Archive/<year>/. Nothing is ever deleted.",
        "inputSchema": {"type": "object", "properties": {}},
    }
]


def _result(id_, result):
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def _error(id_, code, message):
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}


def handle(message):
    method = message.get("method")
    id_ = message.get("id")
    if method == "initialize":
        return _result(id_, {
            "protocolVersion": PROTOCOL,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "inbox-sweeper", "version": "1.0.0"},
        })
    if method in ("notifications/initialized", "initialized"):
        return None
    if method == "tools/list":
        return _result(id_, {"tools": TOOLS})
    if method == "tools/call":
        params = message.get("params") or {}
        if params.get("name") != "archive_inbox":
            return _error(id_, -32602, "Inbox Sweeper has no tool by that name.")
        return _result(id_, {"content": [{"type": "text", "text": sweep()}]})
    if id_ is not None:
        return _error(id_, -32601, "Inbox Sweeper does not understand that request.")
    return None


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except ValueError:
            continue
        reply = handle(message)
        if reply is not None:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
