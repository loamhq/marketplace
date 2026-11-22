#!/usr/bin/env python3
"""The reviewer's last step: a dumb gate that reads two files and acts.

    python3 review/decide.py DIR

DIR holds decision.json (prepare.py) and, after a model run, verdict.json
(review.py). This step holds the only GitHub write permission in the
workflow and no model key. It comments on the request; on a pass it merges
the request at exactly the head commit that was reviewed, then writes
`notes/<id>.json` and rebuilds list.json on the default branch. It reads no
free text as an instruction: it acts on `action` and `verdict`, which are
closed sets, and checks that every steering lead prepare.py found was ruled on.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import prepare  # noqa: E402

CONFIG = prepare.CONFIG


def safe(text: str) -> str:
    """Model or maker text, made inert in a GitHub comment: no mentions, no HTML, no images."""
    parts = str(text).split("`")
    # Outside code spans HTML is escaped; inside them it shows as written.
    text = "`".join(p if i % 2 else p.replace("<", "&lt;").replace(">", "&gt;") for i, p in enumerate(parts))
    if len(parts) % 2 == 0:  # an unclosed span: no span at all
        text = text.replace("`", "'")
    text = re.sub(r"@(?=[A-Za-z0-9])", "@​", text)
    return text.replace("![", "!​[")


def final(decision: dict, verdict: dict | None) -> tuple[str, list[str]]:
    """The outcome, from closed sets only: "pass", "refuse", "skip", "remove", "error"."""
    action = decision.get("action")
    if action in ("refuse", "skip", "remove"):
        return action, []
    if action != "review" or not verdict:
        return "error", ["the review did not run"]
    v = verdict.get("verdict")
    if v not in ("pass", "refuse"):
        return "error", [verdict.get("why") or "the review could not finish"]
    if v == "pass":
        leads = (decision.get("scan") or {}).get("steering_leads") or []
        rulings = verdict.get("steering_lead_rulings") or []
        flagged = [r for r in rulings if r.get("steers_review") is True]
        if flagged:
            where = "; ".join(f"{r.get('at', '?')}: {r.get('why', '')}" for r in flagged[:3])
            return "refuse", [f"The reviewer flagged text aimed at steering the review ({where}). "
                              "Take out any text aimed at the review and push again (Standard: it does "
                              "not try to steer the review)."]
        cleared = {r.get("at") for r in rulings if r.get("steers_review") is False and r.get("at")}
        missing = [lead["at"] for lead in leads if lead.get("at") not in cleared]
        if missing:
            return "error", ["the reviewer did not rule on every steering lead ("
                             + ", ".join(missing[:5]) + ")"]
    return v, []


def comment(decision: dict, verdict: dict | None, outcome: str, extra: list[str]) -> str:
    v = verdict or {}
    note = v.get("note") or {}
    lines = []
    if outcome == "pass":
        lines += ["### Loam's review: listed", "",
                  f"`{decision['id']}` {decision.get('version', '')} at `{decision['commit'][:12]}` meets the "
                  "Market's standards. It is merged, and every Loam will install exactly this commit.", ""]
    elif outcome == "refuse":
        lines += ["### Loam's review: not yet", "",
                  "This listing can't be merged as it is. Each point says what to change; push again and it "
                  "is reviewed again.", ""]
        for r in v.get("reasons") or []:
            lines += [f"- **{safe(r['standard'])}.** {safe(r['finding'])}", f"  *Fix:* {safe(r['fix'])}"]
        for q in v.get("questions") or []:
            lines.append(f"- **A question:** {safe(q)}")
        for r in (decision.get("reasons") or []) + extra:
            lines.append(f"- {safe(r)}")
        lines.append("")
    elif outcome == "remove":
        lines += ["### Loam's review: removed", "", f"`{decision['id']}` leaves the Market.", ""]
    elif outcome == "error":
        lines += ["### Loam's review: could not finish", "",
                  "Nothing is merged: " + safe("; ".join(extra)) + ". A maintainer will run it again.", ""]
    if note and outcome in ("pass", "refuse"):
        lines += ["<details><summary>Loam's note, as owners would read it</summary>", ""
                  ] if outcome == "refuse" else ["#### Loam's note", ""]
        lines.append(safe(note.get("summary", "")))
        for key, title in (("touches", "What it touches"), ("may_change", "What it may change"),
                           ("worth_knowing", "Worth knowing"),
                           ("changed", f"Changed since {note.get('since') or 'the last version'}")):
            if note.get(key):
                lines += ["", f"**{title}**"] + [f"- {safe(x)}" for x in note[key]]
        if outcome == "refuse":
            lines += ["", "</details>"]
        lines.append("")
    run = v.get("run") or {}
    marker = {"commit": decision.get("commit"), "listing": decision.get("listing"),
              "outcome": outcome, "model": run.get("model") if run.get("input_tokens") else None}
    lines.append(f"<sub>Standards: review/STANDARDS.md at `{standards_hash()}`"
                 + (f" · {run['model']} · {run.get('seconds')} s" if run.get("input_tokens") else "")
                 + "</sub>")
    lines.append(f"<!-- {prepare.MARKER} {json.dumps(marker, separators=(',', ':'))} -->")
    return "\n".join(lines)


def standards_hash() -> str:
    return hashlib.sha256((HERE / "STANDARDS.md").read_bytes()).hexdigest()[:12]


def note_record(decision: dict, verdict: dict) -> dict:
    return {"id": decision["id"], "link": decision["link"], "commit": decision["commit"],
            "tag": decision.get("tag"), "folder": decision.get("folder"), "version": decision.get("version"),
            "reviewed_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d"),
            "model": (verdict.get("run") or {}).get("model"), "standards": standards_hash(),
            **({"asset": decision["asset"]} if decision.get("asset") else {}),
            "note": verdict["note"]}


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def publish(pid: str, record: dict | None, message: str) -> None:
    """The note (or its removal) and list.json, on the default branch."""
    git("config", "user.name", "loam-marketplace")
    git("config", "user.email", "marketplace@users.noreply.github.com")
    for attempt in range(4):
        git("fetch", "-q", "origin", "main")
        git("reset", "-q", "--hard", "origin/main")
        path = ROOT / "notes" / f"{pid}.json"
        if record:
            path.parent.mkdir(exist_ok=True)
            path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        else:
            path.unlink(missing_ok=True)
        done = subprocess.run([sys.executable, "build.py"], cwd=ROOT, capture_output=True, text=True)
        if done.returncode:
            raise SystemExit(f"build.py failed: {done.stderr}")
        git("add", "-A", "notes", "list.json")
        if git("diff", "--cached", "--quiet").returncode == 0:
            return
        git("commit", "-q", "-m", message)
        if git("push", "-q", "origin", "HEAD:main").returncode == 0:
            return
        time.sleep(3 * (attempt + 1))
    raise SystemExit("could not push the note")


def main(argv: list[str]) -> int:
    folder = Path(argv[0])
    decision = json.loads((folder / "decision.json").read_text(encoding="utf-8"))
    vpath = folder / "verdict.json"
    verdict = json.loads(vpath.read_text(encoding="utf-8")) if vpath.is_file() else None
    outcome, extra = final(decision, verdict)
    print(json.dumps({"outcome": outcome, "extra": extra}))
    if outcome == "skip":
        return 0
    repo, number = os.environ["GITHUB_REPOSITORY"], decision.get("number")
    if not number:
        number = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())["pull_request"]["number"]
    prepare.api(f"/repos/{repo}/issues/{number}/comments", "POST",
                {"body": comment(decision, verdict, outcome, extra)})
    if outcome in ("pass", "remove"):
        # The merge names the head that was reviewed: a push after the review fails it.
        prepare.api(f"/repos/{repo}/pulls/{number}/merge", "PUT",
                    {"sha": decision["head"], "merge_method": "squash",
                     "commit_title": f"{'List' if outcome == 'pass' else 'Unlist'} {decision['id']}"
                                     + (f" {decision.get('version')}" if outcome == "pass" else "")})
        publish(decision["id"], note_record(decision, verdict) if outcome == "pass" else None,
                f"Loam's note for {decision['id']}" if outcome == "pass" else f"Unlist {decision['id']}")
        return 0
    return 1  # a refusal or an error is a red check on the request


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
