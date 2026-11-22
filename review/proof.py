#!/usr/bin/env python3
"""Run the reviewer proof set through the real prepare + model + decide path.

    python3 review/proof.py [--offline-only] [--loam-dir PATH] [--out REPORT.json] [--summary SUMMARY.md]

Each case in ``review/proof/manifest.json`` runs through:
  1. ``build.check`` on its listing,
  2. ``prepare.folder_packet`` using ``prepare.loam_reader`` at ``config.json``'s
     pinned Loam commit (or ``--loam-dir`` for offline tests),
  3. ``review.ask`` + ``review.shape`` against the configured model (skipped with
     ``--offline-only``), and
  4. ``decide.final`` on the real decision and verdict.

Each case runs once (one round). If a case gets the wrong verdict, only that
flipped case is re-run twice more (3 rounds total) to distinguish a solid
regression from non-determinism, and the run still exits non-zero.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import sys
import tempfile
import time
import urllib.error
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROOF_DIR = HERE / "proof"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

import build  # noqa: E402
import decide  # noqa: E402
import prepare  # noqa: E402
import review  # noqa: E402

RETRYABLE_HTTP = {429, 500, 502, 503, 504}


def load_loam_reader(work: Path, loam_dir: Path | None):
    if loam_dir is not None:
        os.environ.setdefault("LOAM_CONFIG", str(work / "no-loam.toml"))
        sys.path.insert(0, str(loam_dir / "lib"))
        import loam_plugins  # noqa: PLC0415
        return loam_plugins
    return prepare.loam_reader(work)


def build_case_packet(lp, case: dict, prior_note: dict | None = None,
                      prior_folder: Path | None = None) -> tuple[dict, dict, list[str]]:
    listing = case["listing"]
    pid = listing["id"]
    # Validate the listing against build.py's own rules, just as prepare.github does.
    prepare.check_listing(json.dumps(listing), pid)
    folder = PROOF_DIR / "cases" / case["folder"]
    if not folder.is_dir():
        raise RuntimeError(f"missing fixture folder: {folder}")
    packet, meta = prepare.folder_packet(
        lp, folder, listing,
        commit="a" * 40, tag=f"v{listing.get('version', '1.0.0')}",
        prior_folder=prior_folder, prior_note=prior_note,
    )
    decision = {"action": "review", "id": pid, **meta}
    return packet, decision, packet.get("loam_warnings") or []


def check_offline_assertions(case: dict, packet: dict, warnings: list[str]) -> list[str]:
    errs = []
    if case.get("expect_no_loam_warnings") and warnings:
        errs.append(f"unexpected loam_warnings: {warnings}")
    leads = (packet.get("scan") or {}).get("steering_leads") or []
    if case.get("expect_steering_leads") and not leads:
        errs.append("expected at least one steering_lead from prepare.scan, got none")
    return errs


def ask_with_retry(packet: dict, model: str, key: str) -> tuple[dict, dict]:
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            raw, run = review.ask(packet, model, key)
            verdict = review.shape(raw)
            verdict["run"] = run
            return verdict, run
        except urllib.error.HTTPError as exc:
            last_exc = exc
            if exc.code in RETRYABLE_HTTP and attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            return {"verdict": "error", "why": f"the model answered {exc.code}", "run": {"model": model}}, {"model": model}
        except (OSError, TimeoutError) as exc:
            last_exc = exc
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            return {"verdict": "error", "why": str(exc), "run": {"model": model}}, {"model": model}
        except (ValueError, KeyError, TypeError) as exc:
            return {"verdict": "error", "why": f"answer out of shape ({exc})", "run": {"model": model}}, {"model": model}
    return {"verdict": "error", "why": str(last_exc), "run": {"model": model}}, {"model": model}


def evaluate_once(case: dict, packet: dict, decision: dict, model: str, key: str) -> dict:
    verdict, run = ask_with_retry(packet, model, key)
    outcome, extra = decide.final(decision, verdict)
    expected = case["expect"]
    errs = []
    if outcome != expected:
        errs.append(f"expected {expected}, got {outcome}" + (f" ({'; '.join(extra)})" if extra else ""))
    if case.get("expect_steers_review"):
        rulings = verdict.get("steering_lead_rulings") or []
        if not any(r.get("steers_review") is True for r in rulings):
            errs.append("expected at least one steering_lead_rulings entry with steers_review=true")
    return {
        "ok": not errs,
        "errors": errs,
        "expected": expected,
        "model_verdict": verdict.get("verdict"),
        "outcome": outcome,
        "extra": extra,
        "verdict": verdict,
        "run": run,
    }


def run_case(lp, case: dict, model: str, key: str, *, offline_only: bool, confirm_flips: bool,
             prior_note: dict | None = None, prior_folder: Path | None = None) -> dict:
    name = case["name"]
    try:
        packet, decision, warnings = build_case_packet(lp, case, prior_note=prior_note, prior_folder=prior_folder)
    except Exception as exc:
        return {
            "name": name, "ok": False, "expected": case["expect"], "actual": "prepare-error",
            "errors": [str(exc)], "usd": 0.0, "seconds": 0.0, "rounds": [],
        }

    offline_errs = check_offline_assertions(case, packet, warnings)
    leads = (packet.get("scan") or {}).get("steering_leads") or []
    if offline_only:
        return {
            "name": name, "ok": not offline_errs, "expected": case["expect"],
            "actual": "offline-ok" if not offline_errs else "offline-fail",
            "warnings": warnings, "steering_leads": leads,
            "errors": offline_errs, "usd": 0.0, "seconds": 0.0, "rounds": [],
            "decision": decision,
        }

    if offline_errs:
        return {
            "name": name, "ok": False, "expected": case["expect"], "actual": "offline-fail",
            "warnings": warnings, "steering_leads": leads,
            "errors": offline_errs, "usd": 0.0, "seconds": 0.0, "rounds": [],
            "decision": decision,
        }

    first = evaluate_once(case, packet, decision, model, key)
    rounds = [first]
    # Keep to one round per case unless a case flips; on a flip, run 2 confirmation
    # rounds on ONLY this case to show whether it is a solid regression or flaky,
    # while still failing the run.
    if not first["ok"] and confirm_flips:
        for _ in range(2):
            rounds.append(evaluate_once(case, packet, decision, model, key))

    total_usd = round(sum(((r.get("run") or {}).get("usd") or 0.0) for r in rounds), 4)
    total_sec = round(sum(((r.get("run") or {}).get("seconds") or 0.0) for r in rounds), 1)
    ok_count = sum(1 for r in rounds if r["ok"])
    errors = list(first["errors"])
    if len(rounds) > 1:
        errors.append(f"confirmation rounds: {ok_count}/{len(rounds)} matched expected")
    return {
        "name": name,
        "why": case.get("why", ""),
        "ok": first["ok"],
        "expected": case["expect"],
        "actual": first["outcome"],
        "model_verdict": first["model_verdict"],
        "warnings": warnings,
        "steering_leads": leads,
        "steering_lead_rulings": first["verdict"].get("steering_lead_rulings") or [],
        "reasons": first["verdict"].get("reasons") or [],
        "extra": first["extra"],
        "errors": errors,
        "usd": total_usd,
        "seconds": total_sec,
        "rounds": [{"ok": r["ok"], "model_verdict": r["model_verdict"], "outcome": r["outcome"],
                    "usd": (r.get("run") or {}).get("usd"), "seconds": (r.get("run") or {}).get("seconds")}
                   for r in rounds],
        "decision": decision,
        "verdict": first["verdict"],
    }


def write_summary(path: Path, report: dict) -> None:
    lines = [
        f"## Market reviewer proof set (`{report['model']}` · Loam `{report['loam_version'] or report['loam_commit'][:12]}`)",
        "",
        f"**Result:** {report['passed']}/{report['total']} passed · **Cost:** ${report['total_usd']:.4f} · **Standards:** `{report['standards']}`",
        "",
        "| Case | Expected | Actual | Model | Leads | Cost | Time | Status |",
        "|---|---|---|---|---:|---:|---:|---|",
    ]
    for r in report["cases"]:
        status = "PASS" if r["ok"] else "FAIL: " + "; ".join(r.get("errors") or [])
        lines.append(
            f"| `{r['name']}` | {r['expected']} | {r['actual']} | {r.get('model_verdict', '-')} | "
            f"{len(r.get('steering_leads') or [])} | ${r['usd']:.4f} | {r['seconds']:.1f}s | {status} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="proof.py", description=__doc__.splitlines()[0])
    ap.add_argument("--offline-only", action="store_true")
    ap.add_argument("--loam-dir", default="")
    ap.add_argument("--model", default="")
    ap.add_argument("--only", default="")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", default="")
    ap.add_argument("--summary", default="")
    ap.add_argument("--no-confirm-flips", action="store_true")
    args = ap.parse_args(argv)

    cfg = prepare.CONFIG
    model = args.model or cfg["model"]
    key = os.environ.get("GEMINI_API_KEY", "")
    if not args.offline_only and not key:
        print("ERROR: GEMINI_API_KEY is not set (use --offline-only for manifest/scan checks)", file=sys.stderr)
        return 2

    manifest = json.loads((PROOF_DIR / "manifest.json").read_text(encoding="utf-8"))
    cases = manifest["cases"]
    if args.only:
        wanted = {x.strip() for x in args.only.split(",") if x.strip()}
        # Pull in required prior_cases automatically so update cases still work.
        by_name = {c["name"]: c for c in cases}
        for n in list(wanted):
            if n in by_name and by_name[n].get("prior_case"):
                wanted.add(by_name[n]["prior_case"])
        cases = [c for c in cases if c["name"] in wanted]

    work = Path(tempfile.mkdtemp(prefix="loam-proof-"))
    lp = load_loam_reader(work, Path(args.loam_dir) if args.loam_dir else None)

    independent = [c for c in cases if not c.get("prior_case")]
    dependent = [c for c in cases if c.get("prior_case")]

    results_by_name: dict[str, dict] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futs = {
            pool.submit(
                run_case, lp, c, model, key,
                offline_only=args.offline_only,
                confirm_flips=not args.no_confirm_flips,
            ): c["name"]
            for c in independent
        }
        for fut in concurrent.futures.as_completed(futs):
            res = fut.result()
            results_by_name[res["name"]] = res

    by_name = {c["name"]: c for c in cases}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futs = {}
        for c in dependent:
            pname = c["prior_case"]
            pres = results_by_name.get(pname) or {}
            pfolder = PROOF_DIR / "cases" / by_name[pname]["folder"]
            pnote = None
            if not args.offline_only and pres.get("decision") and pres.get("verdict") and pres["verdict"].get("note"):
                pnote = decide.note_record(pres["decision"], pres["verdict"])
            futs[pool.submit(
                run_case, lp, c, model, key,
                offline_only=args.offline_only,
                confirm_flips=not args.no_confirm_flips,
                prior_note=pnote, prior_folder=pfolder,
            )] = c["name"]
        for fut in concurrent.futures.as_completed(futs):
            res = fut.result()
            results_by_name[res["name"]] = res

    ordered = [results_by_name[c["name"]] for c in cases]
    passed = sum(1 for r in ordered if r["ok"])
    failed = len(ordered) - passed
    total_usd = round(sum(r["usd"] for r in ordered), 4)

    for r in ordered:
        tag = "PASS" if r["ok"] else "FAIL"
        extra_s = f"  ({'; '.join(r['errors'])})" if r.get("errors") else ""
        print(f"{tag:4s}  {r['name']:26s} expect={r['expected']:6s} actual={r['actual']:12s} "
              f"leads={len(r.get('steering_leads') or []):2d} ${r['usd']:.4f} {r['seconds']:5.1f}s{extra_s}")

    print(f"\n{'FAILED' if failed else 'OK'}: {passed}/{len(ordered)} passed, {failed} failed, total ${total_usd:.4f}")

    report = {
        "model": model,
        "loam_repo": cfg["loam"]["repo"],
        "loam_version": cfg["loam"].get("version") or "",
        "loam_commit": cfg["loam"]["commit"],
        "standards": decide.standards_hash(),
        "offline_only": args.offline_only,
        "total": len(ordered),
        "passed": passed,
        "failed": failed,
        "total_usd": total_usd,
        "cases": [
            {k: v for k, v in r.items() if k not in ("decision", "verdict")}
            for r in ordered
        ],
    }
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.summary:
        write_summary(Path(args.summary), report)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
