#!/usr/bin/env python3
"""Keep review/config.json pinned to a named Loam release commit (never a branch).

    python3 review/loam_pin.py check [--version X.Y.Z] [--config PATH]
    python3 review/loam_pin.py apply [--version X.Y.Z] [--commit SHA] [--config PATH]

Resolves release tags matching ``x.y.z`` from ``git ls-remote --tags`` on the
configured Loam repository (peeling annotated/signed tags via ``^{}``). Never
pins a branch or an untagged commit.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG = HERE / "config.json"
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
SHA = re.compile(r"^[0-9a-f]{40}$")


def parse_semver(tag: str) -> tuple[int, int, int] | None:
    m = SEMVER.match(tag)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def parse_ls_remote_tags(stdout: str) -> dict[str, str]:
    """Return ``{tag: commit_sha}`` for semver ``x.y.z`` tags, peeled over tag objects."""
    raw: dict[str, str] = {}
    peeled: dict[str, str] = {}
    for line in stdout.splitlines():
        sha, _, ref = line.partition("\t")
        if not ref.startswith("refs/tags/") or not SHA.match(sha):
            continue
        name = ref[10:]
        if name.endswith("^{}"):
            base = name[:-3]
            if parse_semver(base):
                peeled[base] = sha
        elif parse_semver(name):
            raw[name] = sha
    return {tag: peeled.get(tag, sha) for tag, sha in raw.items()}


def release_tags(repo: str) -> dict[str, str]:
    """Query ``git ls-remote --tags`` for ``repo`` (e.g. ``loamhq/loam``)."""
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    args = ["git"]
    tok = os.environ.get("GITHUB_TOKEN") or ""
    if tok:
        basic = base64.b64encode(f"x-access-token:{tok}".encode()).decode()
        args += ["-c", f"http.extraHeader=Authorization: Basic {basic}"]
    done = subprocess.run(
        [*args, "ls-remote", "--tags", f"https://github.com/{repo}.git"],
        capture_output=True, text=True, env=env, timeout=120,
    )
    if done.returncode != 0:
        raise RuntimeError(f"git ls-remote failed for {repo}: {done.stderr.strip()}")
    return parse_ls_remote_tags(done.stdout)


def latest_release(tags: dict[str, str]) -> tuple[str, str]:
    if not tags:
        raise ValueError("no x.y.z release tags found")
    best = max(tags, key=lambda t: parse_semver(t) or (0, 0, 0))
    return best, tags[best]


def resolve_target(repo: str, version: str | None = None, commit: str | None = None,
                   *, tags: dict[str, str] | None = None) -> tuple[str, str]:
    """Resolve ``(version, commit)`` from the repository's release tags."""
    tag_map = release_tags(repo) if tags is None else tags
    if version:
        if not parse_semver(version):
            raise ValueError(f"{version!r} is not a release version (x.y.z)")
        if version not in tag_map:
            raise ValueError(f"github.com/{repo} has no release tag {version!r}")
        resolved = tag_map[version]
        if commit and commit.lower() != resolved:
            raise ValueError(f"tag {version} on github.com/{repo} is {resolved}, not {commit}")
        return version, resolved
    if commit:
        raise ValueError("--commit requires --version")
    return latest_release(tag_map)


def apply_pin(config_path: Path, version: str, commit: str) -> bool:
    """Update ``loam.version`` and ``loam.commit`` in ``config.json``. Return True if changed."""
    if not parse_semver(version):
        raise ValueError(f"{version!r} is not a release version (x.y.z)")
    commit = commit.lower()
    if not SHA.match(commit):
        raise ValueError(f"{commit!r} is not a 40-character commit SHA")
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    loam = cfg.get("loam") or {}
    if loam.get("version") == version and loam.get("commit") == commit:
        return False
    cfg["loam"] = {"repo": loam.get("repo", "loamhq/loam"), "version": version, "commit": commit}
    config_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="loam_pin.py", description=__doc__.splitlines()[0])
    ap.add_argument("action", choices=["check", "apply"])
    ap.add_argument("--version", default="")
    ap.add_argument("--commit", default="")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    args = ap.parse_args(argv)

    cfg_path = Path(args.config)
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    loam = cfg.get("loam") or {}
    repo = loam["repo"]
    cur_ver = loam.get("version") or ""
    cur_sha = loam.get("commit") or ""

    target_ver, target_sha = resolve_target(repo, args.version or None, args.commit or None)
    changed = (cur_ver != target_ver) or (cur_sha != target_sha)

    if args.action == "apply" and changed:
        apply_pin(cfg_path, target_ver, target_sha)

    out = {
        "repo": repo,
        "current_version": cur_ver,
        "current_commit": cur_sha,
        "version": target_ver,
        "commit": target_sha,
        "changed": changed,
    }
    print(json.dumps(out, ensure_ascii=False))
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as fh:
            fh.write(f"changed={'true' if changed else 'false'}\n")
            fh.write(f"version={target_ver}\n")
            fh.write(f"commit={target_sha}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
