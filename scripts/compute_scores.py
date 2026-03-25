"""
dashboard/score_local.py
------------------------
Reads all *.json Spectral results from --results-dir,
computes a NutriDoc-style score per API,
and writes:
  - results/scores.csv
  - results/scores.json
  - results/violations_flat.csv

Usage:
  python3 dashboard/score_local.py \
    --results-dir incoming-reports \
    --output-dir results
"""

import argparse
import csv
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from scoring_rules import (
    GRADE_SCALE,
    OWASP_CATEGORY_MAP,
    SEVERITY_LABELS,
    SEVERITY_WEIGHTS,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-5s  %(message)s",
)
log = logging.getLogger(__name__)


# ── Scoring ──────────────────────────────────────────────────────────────────

def compute_score(issues: list) -> tuple:
    """
    Returns (score, grade, rules_summary).
    Penalty is deduplicated per rule_id: a rule violated 100 times
    penalises only once — but we keep the count for drill-down.
    """
    rules_seen: dict = {}

    for issue in issues:
        rule_id = issue.get("code", "unknown")
        severity = issue.get("severity", 1)

        if rule_id not in rules_seen:
            rules_seen[rule_id] = {
                "rule": rule_id,
                "owasp_category": OWASP_CATEGORY_MAP.get(rule_id, "Other"),
                "severity": severity,
                "severity_label": SEVERITY_LABELS.get(severity, "warning"),
                "occurrences": 0,
                "penalty": SEVERITY_WEIGHTS.get(severity, 5),
            }
        rules_seen[rule_id]["occurrences"] += 1

    total_penalty = sum(r["penalty"] for r in rules_seen.values())
    score = max(0, 100 - total_penalty)

    grade = "E"
    for threshold, g in GRADE_SCALE:
        if score >= threshold:
            grade = g
            break

    rules_summary = sorted(
        rules_seen.values(),
        key=lambda x: x["occurrences"],
        reverse=True,
    )

    return score, grade, rules_summary


# ── File processing ──────────────────────────────────────────────────────────

def process_spectral_file(spectral_file: str) -> dict | None:
    """Parse a Spectral JSON results file and return a scored record."""
    if not os.path.exists(spectral_file):
        return None

    # Protect against JSON bombs / malicious files (limit to 5 MB)
    MAX_SIZE_BYTES = 5 * 1024 * 1024
    file_size = os.path.getsize(spectral_file)
    if file_size > MAX_SIZE_BYTES:
        log.warning("File %s is too large (%d bytes). Ignoring to prevent OOM/JSON bomb.", spectral_file, file_size)
        return None

    with open(spectral_file) as f:
        try:
            issues = json.load(f)
        except json.JSONDecodeError:
            log.warning("Could not parse %s — skipping", spectral_file)
            return None

    if not isinstance(issues, list):
        log.warning("Expected a JSON array in %s — skipping", spectral_file)
        return None

    stem = Path(spectral_file).stem
    
    # Dynamic versioning: extract service name and version from "service@version"
    if "@" in stem:
        service_name, version = stem.split("@", 1)
    else:
        service_name, version = stem, "v1"

    score, grade, rules_summary = compute_score(issues)

    from zoneinfo import ZoneInfo
    updated_date = datetime.fromtimestamp(
        os.path.getmtime(spectral_file), tz=ZoneInfo("Europe/Paris")
    ).strftime("%d/%m/%Y %H:%M:%S")

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service_name": service_name,
        "domain": "unknown",
        "region": "unknown",
        "version": version,
        "spec_file": stem,
        "numerical_score": score,
        "grade": grade,
        "compliant": grade in ("A", "B", "C"),
        "total_issues": len(issues),
        "operations_count": 0,
        "total_rules_violated": len(rules_summary),
        "top_violations": rules_summary,
        "updated_date": updated_date,
    }


# ── Output writers ───────────────────────────────────────────────────────────

def write_csv(records: list, output_dir: str):
    """Write scores.csv — main table."""
    csv_path = os.path.join(output_dir, "scores.csv")
    fields = [
        "timestamp", "service_name", "domain", "region", "version",
        "spec_file", "numerical_score", "grade", "compliant",
        "total_issues", "operations_count", "rank", "updated_date",
    ]
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in records:
            w.writerow({k: r.get(k, "") for k in fields})
    log.info("scores.csv → %s", csv_path)


def write_violations_csv(records: list, output_dir: str):
    """Write violations_flat.csv — per-rule detail table."""
    csv_path = os.path.join(output_dir, "violations_flat.csv")
    fields = [
        "service_name", "domain", "region", "grade",
        "rule", "owasp_category", "severity_label", "occurrences", "penalty",
    ]
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in records:
            for v in r.get("top_violations", []):
                w.writerow({
                    "service_name":   r["service_name"],
                    "domain":         r["domain"],
                    "region":         r["region"],
                    "grade":          r["grade"],
                    "rule":           v["rule"],
                    "owasp_category": v["owasp_category"],
                    "severity_label": v["severity_label"],
                    "occurrences":    v["occurrences"],
                    "penalty":        v["penalty"],
                })
    log.info("violations_flat.csv → %s", csv_path)


def write_json(records: list, output_dir: str):
    """Write scores.json — machine-readable output."""
    json_path = os.path.join(output_dir, "scores.json")
    with open(json_path, "w") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    log.info("scores.json → %s", json_path)


def print_summary(records: list):
    """Print a console summary."""
    total = len(records)
    avg = sum(r["numerical_score"] for r in records) / total if total else 0
    compliant = sum(1 for r in records if r["compliant"])

    print(f"\n{'='*56}")
    print(f"  API Governance — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*56}")
    print(f"  Total APIs scored  : {total}")
    print(f"  Average score      : {avg:.0f}/100")
    print(f"  Compliance rate    : {compliant}/{total} ({100*compliant//total if total else 0}%)")
    print()
    for r in sorted(records, key=lambda x: x["numerical_score"], reverse=True):
        bar = "█" * (r["numerical_score"] // 10) + "░" * (10 - r["numerical_score"] // 10)
        flag = "✓" if r["compliant"] else "✗"
        print(f"  {flag} [{r['grade']}] {bar} {r['numerical_score']:3d}/100  {r['service_name']}")
    print(f"{'='*56}\n")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Score Spectral results → CSV/JSON")
    parser.add_argument("--results-dir", default="incoming-reports")
    parser.add_argument("--output-dir",  default="results")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    # Find all *.json (skip .gitkeep and non-JSON)
    spectral_files = sorted(
        p for p in Path(args.results_dir).glob("*.json")
        if p.suffix == ".json"
    )
    if not spectral_files:
        log.error("No *.json found in %s", args.results_dir)
        sys.exit(1)

    records = []
    for sf in spectral_files:
        record = process_spectral_file(str(sf))
        if record:
            records.append(record)
            
    # Filter to keep only the latest semantic version per service
    def parse_version(v_str: str) -> tuple:
        nums = re.findall(r'\d+', str(v_str))
        return tuple(int(n) for n in nums) if nums else (0,)

    latest_records: dict[str, dict] = {}
    for r in records:
        svc = r["service_name"]
        curr_ver = parse_version(r["version"])
        
        if svc not in latest_records:
            latest_records[svc] = r
        else:
            existing_ver = parse_version(latest_records[svc]["version"])
            if curr_ver > existing_ver:
                latest_records[svc] = r
            elif curr_ver == existing_ver:
                # Same semantic version, compare updated dates
                if r["updated_date"] > latest_records[svc]["updated_date"]:
                    latest_records[svc] = r

    final_records = list(latest_records.values())

    for record in final_records:
        log.info(
            "%-40s version=%-6s grade=%s  score=%3d  issues=%d",
            record["service_name"], record["version"], record["grade"],
            record["numerical_score"], record["total_issues"],
        )

    # Compute rank (1 = best score)
    final_records.sort(key=lambda x: int(x["numerical_score"]), reverse=True)
    for i, r in enumerate(final_records, 1):
        r["rank"] = i

    if not final_records:
        log.error("No records generated.")
        sys.exit(1)

    write_csv(final_records, args.output_dir)
    write_violations_csv(final_records, args.output_dir)
    write_json(final_records, args.output_dir)
    print_summary(final_records)


if __name__ == "__main__":
    main()
