#!/usr/bin/env python3
"""Decide whether a push to main can skip a duplicate model proof run.

Outputs ``skip=true`` ONLY when:
  1. HEAD is the merge commit of a merged pull request from THIS repository
     (never a fork),
  2. That pull request's head commit has a completed ``proof`` check-run with
     conclusion ``success``, AND
  3. The git blob hashes of every watched reviewer file at HEAD match the
     merged pull request's head commit identically.

On any direct push, conflict resolution touching reviewer files, failed/missing
proof check, fork PR, or API error: fails closed and outputs ``skip=false``.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import prepare  # noqa: E402

WATCHED_EXACT = {
    "build.py",
    ".github/workflows/review.yml",
    ".github/workflows/review-tests.yml",
    ".github/workflows/review-proof.yml",
    ".github/workflows/loam-pin.yml",
}


def is_watched(path: str) -> bool:
    return path.startswith("review/") or path in WATCHED_EXACT


def hash_entries(entries: list[tuple[str, str]]) -> str:
    """Deterministic SHA-256 over sorted ``(path, blob_sha)`` of watched files."""
    h = hashlib.sha256()
    for path, sha in sorted(entries):
        if is_watched(path):
            h.update(f"{path}\0{sha}\n".encode("utf-8"))
    return h.hexdigest()


def local_tree_hash(ref: str = "HEAD", cwd: Path = ROOT) -> str:
    done = subprocess.run(["git", "ls-tree", "-r", ref], cwd=cwd, capture_output=True, text=True, check=True)
    entries = []
    for line in done.stdout.splitlines():
        meta, _, path = line.partition("\t")
        parts = meta.split()
        if len(parts) >= 3 and parts[1] == "blob":
            entries.append((path, parts[2]))
    return hash_entries(entries)


def remote_tree_hash(repo: str, sha: str, api_fn=None) -> str | None:
    api_fn = api_fn or prepare.api
    tree = api_fn(f"/repos/{repo}/git/trees/{sha}?recursive=1")
    if not isinstance(tree, dict) or tree.get("truncated"):
        return None
    entries = [(item["path"], item["sha"]) for item in tree.get("tree") or [] if item.get("type") == "blob"]
    return hash_entries(entries)


def should_skip(repo: str, head_sha: str, head_hash: str, *, api_fn=None) -> tuple[bool, str]:
    api_fn = api_fn or prepare.api
    pulls = api_fn(f"/repos/{repo}/commits/{head_sha}/pulls") or []
    for pr in pulls:
        if not pr.get("merged_at"):
            continue
        head_repo = ((pr.get("head") or {}).get("repo") or {}).get("full_name", "")
        base_repo = ((pr.get("base") or {}).get("repo") or {}).get("full_name", "")
        if head_repo.lower() != repo.lower() or base_repo.lower() != repo.lower():
            continue
        pr_sha = (pr.get("head") or {}).get("sha") or ""
        if not pr_sha:
            continue
        checks = (api_fn(f"/repos/{repo}/commits/{pr_sha}/check-runs") or {}).get("check_runs") or []
        proof_ok = any(
            c.get("name") == "proof" and c.get("status") == "completed" and c.get("conclusion") == "success"
            for c in checks
        )
        if not proof_ok:
            continue
        pr_hash = remote_tree_hash(repo, pr_sha, api_fn=api_fn)
        if pr_hash and pr_hash == head_hash:
            return True, f"PR #{pr['number']} ({pr_sha[:12]}) already passed proof for identical reviewer tree {head_hash[:12]}"
    return False, "no matching proved same-repo PR found"


def main() -> int:
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    head_sha = os.environ.get("GITHUB_SHA") or subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    skip, reason = False, "missing repository"
    if repo:
        try:
            head_hash = local_tree_hash("HEAD")
            skip, reason = should_skip(repo, head_sha, head_hash)
        except Exception as exc:
            skip, reason = False, f"dedupe check fell back to running proof ({exc})"
    print(f"skip={'true' if skip else 'false'}")
    print(f"proof_dedupe: skip={skip} ({reason})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
