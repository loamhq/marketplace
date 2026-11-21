#!/usr/bin/env python3
"""The reviewer's first step: every check that needs no model, then the packet.

    python3 review/prepare.py github --out DIR     in the workflow, for the pull request
    python3 review/prepare.py local LISTING --out DIR [--prior NOTE]   for trying it here

It runs with the marketplace's own files checked out at the base branch (this
file, build.py, the standards, notes/), never the pull request's. What the
pull request brings is read as data through GitHub's API: its list of files,
and the one listing file at its head commit. The plugin is downloaded as a
tarball of the maker's repository at the commit its link names, and nothing
in it is run. Python 3.11+, no packages.

It writes into DIR:
  decision.json   {"action": "review"|"refuse"|"remove", "reasons": [...], ...}
  packet.json     what the model reads (only when the action is "review")

"refuse" here is a refusal without a model call: the reasons are plain, for
the maker. Each check is a function with a test in review/test_review.py.
"""

from __future__ import annotations

import base64
import difflib
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CONFIG = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
LIMITS = CONFIG["limits"]
API = os.environ.get("GITHUB_API_URL", "https://api.github.com")
LISTING_FILE = re.compile(r"^listings/([a-z][a-z0-9-]*)\.json$")
LINK = re.compile(r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/tree/([^/?#]+)((?:/[^?#]*)?)$")
SHA = re.compile(r"^[0-9a-f]{40}$")
MARKER = "loam-review:"
BOT = "github-actions[bot]"

# Files the reviewer cannot read, so cannot pass: compiled or packed code.
COMPILED = re.compile(r"\.(?:wasm|so|dylib|dll|exe|node|jar|class|pyc|pyo|bin|o|a)$", re.I)
PICTURES = re.compile(r"\.(?:webp|avif|jpe?g|png|gif|ico|woff2?|ttf|otf|mp3|ogg|wav|m4a)$", re.I)
CODE = re.compile(r"\.(?:js|mjs|cjs|ts|jsx|tsx|py|sh|bash|rb|pl|php|go|rs)$", re.I)
MAGIC_EXEC = (b"\x7fELF", b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe", b"\x00asm")


class Refuse(Exception):
    """A plain reason the maker can act on; no model is asked."""


# ---------------------------------------------------------------- GitHub

def _token() -> str | None:
    return os.environ.get("GITHUB_TOKEN") or None


def api(path: str, method: str = "GET", body=None, raw: bool = False, accept: str | None = None):
    url = path if path.startswith("https://") else f"{API}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Accept": accept or "application/vnd.github+json", "User-Agent": "loam-market-review",
        "X-GitHub-Api-Version": "2022-11-28", **({"Authorization": f"Bearer {_token()}"} if _token() else {}),
        **({"Content-Type": "application/json"} if data else {})})
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 - https only
        got = resp.read()
        return got if raw else (json.loads(got) if got else None)


def api_status(path: str) -> int:
    try:
        api(path, raw=True)
        return 200
    except urllib.error.HTTPError as exc:
        return exc.code


def pages(path: str, limit: int = 10) -> list:
    out = []
    for n in range(1, limit + 1):
        sep = "&" if "?" in path else "?"
        got = api(f"{path}{sep}per_page=100&page={n}")
        out += got
        if len(got) < 100:
            break
    return out


# ---------------------------------------------------------------- the request

def check_files(files: list[dict]) -> tuple[str, str]:
    """A request changes one file, its own listing: (id, status)."""
    names = [f.get("filename", "") for f in files]
    if len(files) != 1:
        others = ", ".join(sorted(names)[:8]) or "nothing"
        raise Refuse(f"A listing request changes exactly one file, `listings/<id>.json`. This one "
                     f"changes {len(files)}: {others}. Open a pull request with your listing alone.")
    f = files[0]
    m = LISTING_FILE.match(f.get("filename", ""))
    if not m or f.get("status") not in ("added", "modified", "removed"):
        raise Refuse(f"A listing request changes only `listings/<id>.json`; this one changes "
                     f"`{f.get('filename')}` ({f.get('status')}). Nothing else in this repository "
                     f"is changed by a pull request.")
    return m.group(1), f["status"]


def check_listing(text: str, pid: str) -> dict:
    """The listing against the marketplace's own rules (build.py at the base)."""
    sys.path.insert(0, str(ROOT))
    import build  # noqa: PLC0415 - the base branch's build.py
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"{pid}.json"
        path.write_text(text, encoding="utf-8")
        entry, errors = build.check(path)
    if errors:
        raise Refuse("The listing breaks the marketplace's rules (see the README):\n"
                     + "\n".join(f"- {e}" for e in errors))
    return json.loads(text)


def parse_link(link: str) -> dict:
    m = LINK.match(link)
    if not m:
        raise Refuse("`link` is https://github.com/<owner>/<repo>/tree/<tag or commit>/<folder>.")
    owner, repo, ref, path = m.groups()
    return {"owner": owner, "repo": repo, "ref": ref, "path": path.strip("/")}


def check_public(src: dict, self_repo: str | None) -> dict:
    full = f"{src['owner']}/{src['repo']}"
    try:
        info = api(f"/repos/{full}")
    except urllib.error.HTTPError as exc:
        raise Refuse(f"github.com/{full} cannot be read ({exc.code}). The repository must be public.") from None
    # The marketplace's own repository is public, so allowing it adds nothing
    # here; it lets a private copy of this repository try the workflow.
    if info.get("private") and info.get("full_name", "").lower() != (self_repo or "").lower():
        raise Refuse(f"github.com/{full} is private. A listed plugin's repository is public, "
                     f"so every owner can read what they install.")
    if info.get("archived"):
        raise Refuse(f"github.com/{full} is archived; list a plugin its maker still keeps.")
    return info


def _refs(full: str) -> dict:
    """The repository's own tags (peeled) and branches, from git itself. A
    commit that only a fork has is reachable through the parent's address,
    but no ref here names it, so it is never accepted."""
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    args = ["git"]
    if _token():
        basic = base64.b64encode(f"x-access-token:{_token()}".encode()).decode()
        args += ["-c", f"http.extraHeader=Authorization: Basic {basic}"]
    done = subprocess.run([*args, "ls-remote", f"https://github.com/{full}.git"],
                          capture_output=True, text=True, env=env, timeout=120)
    if done.returncode:
        raise Refuse(f"github.com/{full} could not be read by git.")
    tags, heads = {}, {}
    for line in done.stdout.splitlines():
        sha, _, name = line.partition("\t")
        if name.startswith("refs/tags/"):
            tag = name[10:]
            if tag.endswith("^{}"):
                tags[tag[:-3]] = sha
            else:
                tags.setdefault(tag, sha)
        elif name.startswith("refs/heads/"):
            heads[name[11:]] = sha
    return {"tags": tags, "heads": heads}


def pin(src: dict, refs: dict) -> tuple[str, str, str]:
    """(commit, tag, folder): the one commit this listing will deliver. A
    tag's peeled commit; a whole commit only if one of the repository's own
    tags names it. Never a branch."""
    segs = [src["ref"], *[p for p in src["path"].split("/") if p]]
    for i in range(len(segs), 0, -1):
        name, rest = "/".join(segs[:i]), "/".join(segs[i:])
        if name in refs["tags"]:
            return refs["tags"][name], name, rest
        if name in refs["heads"]:
            raise Refuse(f"`link` names the branch `{name}`, which moves. Name a release tag, or "
                         f"the whole commit a release tag names.")
    ref = src["ref"].lower()
    if SHA.match(ref):
        named = sorted(t for t, s in refs["tags"].items() if s == ref)
        if not named:
            raise Refuse(f"`link` names the commit {ref[:12]}, which no tag in "
                         f"github.com/{src['owner']}/{src['repo']} names. Tag the release in your "
                         f"own repository and link the tag (or that commit).")
        return ref, named[0], src["path"]
    raise Refuse(f"github.com/{src['owner']}/{src['repo']} has no tag `{src['ref']}`.")


def check_maker(author: str, association: str, src: dict, prior: dict | None) -> None:
    """Who may ask: the repository's owner (or a public member of the
    organisation that owns it), or one of the marketplace's maintainers. A
    listing that exists already may not be moved to another repository."""
    maintainer = association in ("OWNER", "MEMBER", "COLLABORATOR")
    if prior:
        was = parse_link(prior["link"])
        if (was["owner"].lower(), was["repo"].lower()) != (src["owner"].lower(), src["repo"].lower()) \
                and not maintainer:
            raise Refuse(f"`{prior['id']}` is listed from github.com/{was['owner']}/{was['repo']}; a "
                         f"request cannot move it to another repository. Ask a maintainer.")
    if maintainer or author.lower() == src["owner"].lower():
        return
    if api_status(f"/orgs/{src['owner']}/public_members/{author}") == 204:
        return
    raise Refuse(f"Open the request from the account that owns github.com/{src['owner']}/"
                 f"{src['repo']} (or, for an organisation, as one of its public members), so "
                 f"the listing is the maker's own.")


# ---------------------------------------------------------------- the plugin

def download(src: dict, commit: str, into: Path) -> Path:
    """The repository at ``commit``, unpacked under ``into``: regular files
    and folders only, nothing outside, nothing executable kept as such."""
    full = f"{src['owner']}/{src['repo']}"
    url = f"{API}/repos/{full}/tarball/{commit}"
    req = urllib.request.Request(url, headers={"User-Agent": "loam-market-review",
                                               **({"Authorization": f"Bearer {_token()}"} if _token() else {})})
    with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310
        data = resp.read(LIMITS["repo_tarball_bytes"] + 1)
    if len(data) > LIMITS["repo_tarball_bytes"]:
        raise Refuse(f"github.com/{full} at {commit[:12]} is larger than "
                     f"{LIMITS['repo_tarball_bytes'] >> 30} GB packed, more than the reviewer's "
                     f"machine can download and unpack. Keep the plugin in a repository of its own.")
    links = []
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for member in tar.getmembers():
            parts = Path(member.name).parts
            if len(parts) < 2 or ".." in parts or member.name.startswith("/"):
                continue
            rel = Path(*parts[1:])
            target = into / rel
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(tar.extractfile(member).read())
            elif member.issym() or member.islnk():
                links.append(str(rel))
    (into / ".loam-links.json").write_text(json.dumps(links))
    return into


def read_files(folder: Path) -> tuple[list[dict], list[dict], list[str]]:
    """(text files with content, other files by name and size, refusals)."""
    texts, others, problems = [], [], []
    files = sorted(p for p in folder.rglob("*") if p.is_file())
    total = 0
    for p in files:
        rel = p.relative_to(folder).as_posix()
        data = p.read_bytes()
        if COMPILED.search(rel) or any(data.startswith(m) for m in MAGIC_EXEC if len(m) == 4) \
                or (data.startswith(b"MZ") and b"\x00" in data[:512]):
            problems.append(f"`{rel}` is compiled code. The reviewer reads source; a listed "
                            f"plugin carries none it cannot read.")
            continue
        if PICTURES.search(rel):
            others.append({"path": rel, "bytes": len(data)})
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            problems.append(f"`{rel}` is not text, a picture, a font or a sound, so it cannot be "
                            f"reviewed. Take it out, or ship it as source.")
            continue
        if CODE.search(rel) and any(len(line) > LIMITS["minified_line"] for line in text.splitlines()):
            problems.append(f"`{rel}` is minified or bundled (a line longer than "
                            f"{LIMITS['minified_line']} characters). List the source a person can read.")
            continue
        total += len(data)
        texts.append({"path": rel, "text": text})
    return texts, others, problems


def loam_reader(work: Path):
    """Loam's own manifest reader (lib/loam_plugins.py), at the commit named
    in config.json: the checks a Loam makes when it installs, run here."""
    lib = work / "loam"
    if not lib.exists():
        cfg = CONFIG["loam"]
        download({"owner": cfg["repo"].split("/")[0], "repo": cfg["repo"].split("/")[1]},
                 cfg["commit"], lib)
    os.environ.setdefault("LOAM_CONFIG", str(work / "no-loam.toml"))
    sys.path.insert(0, str(lib / "lib"))
    import loam_plugins  # noqa: PLC0415
    return loam_plugins


def check_manifest(lp, folder: Path, pid: str, version: str | None) -> tuple[dict, dict, list[str]]:
    try:
        found = lp.read_folder(folder, None)
    except lp.ManifestError as exc:
        raise Refuse(f"Loam cannot read the plugin's PLUGIN.md: {exc}.") from None
    manifest = found["manifest"]
    if manifest["id"] != pid:
        raise Refuse(f"The plugin at the link is `{manifest['id']}`, not `{pid}`.")
    if version and manifest["version"] != version:
        raise Refuse(f"The listing says version {version}; the plugin at the link is {manifest['version']}.")
    raw = (folder / "PLUGIN.md").read_text(encoding="utf-8") if (folder / "PLUGIN.md").is_file() else ""
    head = raw.split("\n---", 1)[0]
    if not re.search(r"^touches\s*:", head, re.M):
        raise Refuse("`PLUGIN.md` declares no `touches`. Say what it reaches (network hosts and "
                     "why, record, memory, server), even when the answer is nothing.")
    return manifest, lp.declaration(manifest, found["has"]), found["warnings"]


# ---------------------------------------------------------------- what a scan can see

URL = re.compile(r"""(?:https?|wss?)://([A-Za-z0-9.-]+\.[A-Za-z]{2,})""")
DYNAMIC = re.compile(r"\beval\s*\(|\bnew\s+Function\s*\(|\bimport\s*\(\s*[^'\"\s)]|createElement\s*\(\s*['\"]script|"
                     r"\bWebAssembly\b|\bexec\s*\(|child_process|subprocess|os\.system|\bspawn\s*\(|"
                     r"__import__|importlib|\bcompile\s*\(")
SECRETS = re.compile(r"credentials|oauth|access_token|refresh_token|api[_-]?key|secrets?\.env|keys\.env|wake\.env|"
                     r"\.config/|\.claude|\.codex|\.gemini|GITHUB_TOKEN|BROKER_TOKEN|document\.cookie|"
                     r"localStorage|sessionStorage|\.ssh|id_rsa|Authorization", re.I)
ADDRESSED = re.compile(r"\b(?:reviewer|reviewing (?:model|agent|ai)|language model|LLM|AI (?:review|assistant|model)|"
                       r"ignore (?:all |any |the |your |previous |prior )|pre-?approved|system prompt|"
                       r"you must (?:approve|pass)|output (?:a )?pass|verdict)\b", re.I)
# A standalone JS regex matching a first-person model introduction contains a
# role noun as data. Keep the full source in the review packet. Only this
# closed grammar qualifies, so additional prose on the line is still scanned.
ROLE_NOUN = r"(?:ai|assistant|language model|llm)"
MODEL_INTRO_PATTERN = re.compile(
    r"\s*/\^as an? \((?:\?:)?" + ROLE_NOUN + r"(?:\|" + ROLE_NOUN + r")*\)\\b/i?,?\s*", re.I)

SAFE_HOSTS = {"www.w3.org", "w3.org", "schemas.openxmlformats.org", "purl.org", "json-schema.org"}


def scan(texts: list[dict], decl: dict) -> dict:
    """Facts for the reviewer, found by reading, not judged: hosts named in
    code against the declared ones, code that runs other code, words about
    logins and keys, and text addressed to a reviewer."""
    declared = {h["host"].lower() for h in decl["touches"].get("network") or []}
    hosts: dict[str, list[str]] = {}
    dynamic, secrets, addressed = [], [], []
    for f in texts:
        for n, line in enumerate(f["text"].splitlines(), 1):
            where = f"{f['path']}:{n}"
            if CODE.search(f["path"]) or f["path"].endswith((".html", ".css", ".json", ".md")):
                for host in URL.findall(line):
                    host = host.lower()
                    if host not in SAFE_HOSTS and (CODE.search(f["path"]) or f["path"].endswith((".html", ".css"))):
                        hosts.setdefault(host, []).append(where)
            if CODE.search(f["path"]) or f["path"].endswith(".html"):
                if DYNAMIC.search(line):
                    dynamic.append(f"{where}: {line.strip()[:160]}")
                if SECRETS.search(line):
                    secrets.append(f"{where}: {line.strip()[:160]}")
            if ADDRESSED.search(line) and not (
                    f["path"].endswith((".js", ".mjs", ".cjs")) and MODEL_INTRO_PATTERN.fullmatch(line)):
                addressed.append(f"{where}: {line.strip()[:200]}")
    return {
        "hosts_in_code": [{"host": h, "declared": h in declared, "at": at[:5]} for h, at in sorted(hosts.items())],
        "undeclared_hosts": sorted(h for h in hosts if h not in declared),
        "code_that_runs_code": dynamic[:40],
        "logins_and_keys": secrets[:40],
        "addressed_to_a_reviewer": addressed[:40],
    }


def diff_of(before: list[dict], after: list[dict]) -> str:
    old = {f["path"]: f["text"] for f in before}
    new = {f["path"]: f["text"] for f in after}
    out = []
    for path in sorted(set(old) | set(new)):
        if old.get(path) == new.get(path):
            continue
        out += difflib.unified_diff((old.get(path) or "").splitlines(), (new.get(path) or "").splitlines(),
                                    f"a/{path}" if path in old else "/dev/null",
                                    f"b/{path}" if path in new else "/dev/null", lineterm="")
    text = "\n".join(out)
    return text


def plugin_at(lp, src: dict, commit: str, folder_path: str, pid: str, version, work: Path, tag: str):
    repo_dir = download(src, commit, work / f"repo-{commit[:12]}")
    folder = repo_dir / folder_path if folder_path else repo_dir
    if not folder.is_dir():
        raise Refuse(f"github.com/{src['owner']}/{src['repo']} has no folder `{folder_path}` at {tag}.")
    links = [l for l in json.loads((repo_dir / ".loam-links.json").read_text())
             if not folder_path or l.startswith(folder_path + "/")]
    if links:
        raise Refuse("The plugin's folder holds symbolic links (" + ", ".join(links[:5]) + "). "
                     "A listed plugin is plain files.")
    manifest, decl, warnings = check_manifest(lp, folder, pid, version)
    texts, others, problems = read_files(folder)
    if problems:
        raise Refuse("\n".join(f"- {p}" for p in problems))
    return manifest, decl, warnings, texts, others


# ---------------------------------------------------------------- the packet

def build_packet(listing: dict, prior_note: dict | None, work: Path,
                 previous_listing: dict | None = None) -> tuple[dict, dict]:
    """The packet for the model and the facts for the decision. Raises Refuse."""
    pid = listing["id"]
    src = parse_link(listing["link"])
    check_public(src, os.environ.get("GITHUB_REPOSITORY"))
    refs = _refs(f"{src['owner']}/{src['repo']}")
    commit, tag, folder_path = pin(src, refs)
    lp = loam_reader(work)
    manifest, decl, warnings, texts, others = plugin_at(lp, src, commit, folder_path, pid,
                                                        listing.get("version"), work, tag)
    readme_name = listing.get("readme") or "README.md"
    readme = next((f["text"] for f in texts if f["path"] == readme_name), None)
    facts = scan(texts, decl)
    update = None
    # A listing kept from before review still has a released version to
    # compare against. Its previous declaration comes from that release.
    baseline = prior_note or previous_listing
    if baseline and (baseline.get("commit") != commit if prior_note
                     else baseline["link"] != listing["link"]):
        psrc = parse_link(baseline["link"])
        prefs = refs if (psrc["owner"], psrc["repo"]) == (src["owner"], src["repo"]) \
            else _refs(f"{psrc['owner']}/{psrc['repo']}")
        try:
            pcommit, _, ppath = pin(psrc, prefs)
        except Refuse:
            pcommit = None
            ppath = psrc["path"]
        pcommit = baseline.get("commit") or pcommit
        try:
            if pcommit is None:
                raise Refuse("the previous listing no longer names a released commit")
            pman, pdecl, _, ptexts, _ = plugin_at(lp, psrc, pcommit, ppath, pid, None, work,
                                                  baseline.get("version") or pcommit[:12])
            update = {"from_version": pman["version"], "from_commit": pcommit,
                      "declared_before": pdecl, "declares_more_now": lp.added(pdecl, decl),
                      "diff": diff_of(ptexts, texts), "previous_note": baseline.get("note")}
        except Refuse as exc:
            update = {"from_version": baseline.get("version"), "from_commit": pcommit,
                      "unreadable": str(exc), "previous_note": prior_note.get("note")}
    packet = {
        "listing": listing, "repository": f"{src['owner']}/{src['repo']}", "tag": tag, "commit": commit,
        "folder": folder_path, "manifest": {k: manifest.get(k) for k in ("id", "name", "version", "author", "kind", "places", "overrides", "description")},
        "declaration": decl, "loam_warnings": warnings, "readme": readme,
        "files": texts, "other_files": others, "scan": facts, "update": update,
    }
    fit(packet)
    meta = {"id": pid, "commit": commit, "tag": tag, "folder": folder_path, "link": listing["link"],
            "version": manifest["version"], "scan": facts,
            "update_from": update.get("from_version") if update else None}
    import downloads
    asset = downloads.release_asset(f"{src['owner']}/{src['repo']}", tag, pid)
    if asset:
        meta["asset"] = asset
    return packet, meta


def fit(packet: dict) -> None:
    """The one bound: what the model can read at once. A diff that does not
    fit is left out first (the declarations before and after still go); a
    plugin that alone does not fit is refused, saying so."""
    size = lambda: len(json.dumps(packet, ensure_ascii=False).encode())  # noqa: E731
    if size() <= LIMITS["context_bytes"]:
        return
    if packet.get("update") and packet["update"].get("diff"):
        packet["update"]["diff"] = None
        packet["update"]["diff_left_out"] = "too large to read with the plugin; read the declarations"
        if size() <= LIMITS["context_bytes"]:
            return
    raise Refuse(f"The plugin's folder is {size() / 1e6:.1f} MB of text, more than the reviewing model "
                 f"can read at once (about {LIMITS['context_bytes'] / 1e6:.1f} MB). Leave generated "
                 f"data, vendored libraries and fixtures out of the plugin's folder, or split it "
                 f"into smaller plugins, and push again.")


def prior_note_of(pid: str) -> dict | None:
    path = ROOT / "notes" / f"{pid}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def listing_hash(text: str) -> str:
    return hashlib.sha256(json.dumps(json.loads(text), sort_keys=True).encode()).hexdigest()[:16]


def github(out: Path) -> dict:
    # REVIEW_EVENT_PATH: a replay names its event (the runner keeps GITHUB_EVENT_PATH its own).
    event = json.loads(Path(os.environ.get("REVIEW_EVENT_PATH") or os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    pr = event["pull_request"]
    repo = os.environ["GITHUB_REPOSITORY"]
    number, head = pr["number"], pr["head"]["sha"]
    author, assoc = pr["user"]["login"], pr.get("author_association") or "NONE"
    base = {"number": number, "head": head, "author": author}
    if pr["base"]["ref"] != event["repository"]["default_branch"]:
        raise Refuse(f"A listing request is made against `{event['repository']['default_branch']}`.")
    pid, status = check_files(pages(f"/repos/{repo}/pulls/{number}/files", 3))
    base["id"] = pid
    prior = None
    prior_path = ROOT / "listings" / f"{pid}.json"
    if prior_path.is_file():
        prior = json.loads(prior_path.read_text(encoding="utf-8"))
    if status == "removed":
        if not prior:
            raise Refuse(f"`{pid}` is not listed.")
        check_maker(author, assoc, parse_link(prior["link"]), None)
        return {**base, "action": "remove"}
    got = api(f"/repos/{repo}/contents/listings/{pid}.json?ref={head}")
    text = base64.b64decode(got["content"]).decode("utf-8")
    listing = check_listing(text, pid)
    check_maker(author, assoc, parse_link(listing["link"]), prior)
    # No limit on submissions (the owner, 2026-11-19): every push is reviewed.
    key = listing_hash(text)
    work = Path(tempfile.mkdtemp(prefix="review-"))
    packet, meta = build_packet(listing, prior_note_of(pid), work, previous_listing=prior)
    (out / "packet.json").write_text(json.dumps(packet, ensure_ascii=False), encoding="utf-8")
    return {**base, **meta, "listing": key, "action": "review"}


def local(listing_path: Path, prior: Path | None, out: Path) -> dict:
    text = listing_path.read_text(encoding="utf-8")
    pid = str(json.loads(text).get("id"))
    listing = check_listing(text, pid)
    work = Path(tempfile.mkdtemp(prefix="review-"))
    prior_note = json.loads(prior.read_text(encoding="utf-8")) if prior else None
    packet, meta = build_packet(listing, prior_note, work)
    (out / "packet.json").write_text(json.dumps(packet, ensure_ascii=False), encoding="utf-8")
    return {"id": pid, **meta, "listing": listing_hash(text), "action": "review"}


def main(argv: list[str]) -> int:
    out = Path(argv[argv.index("--out") + 1])
    out.mkdir(parents=True, exist_ok=True)
    try:
        if argv[0] == "github":
            decision = github(out)
        else:
            prior = Path(argv[argv.index("--prior") + 1]) if "--prior" in argv else None
            decision = local(Path(argv[1]), prior, out)
    except Refuse as exc:
        decision = {"action": "refuse", "reasons": [str(exc)]}
        try:
            event = json.loads(Path(os.environ.get("REVIEW_EVENT_PATH") or os.environ.get("GITHUB_EVENT_PATH", "/dev/null")).read_text() or "{}")
            pr = event.get("pull_request") or {}
            decision.update(number=pr.get("number"), head=(pr.get("head") or {}).get("sha"))
        except (OSError, ValueError):
            pass
    (out / "decision.json").write_text(json.dumps(decision, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in decision.items() if k != "scan"}, ensure_ascii=False))
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as fh:
            fh.write(f"action={decision['action']}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
