"""
scripts/score_local.py
-----------------------
Lit tous les fichiers *_spectral.json dans --results-dir,
calcule un score NutriDoc-style pour chaque spec,
et écrit :
  - results/scores.csv          → source Power BI Desktop (mode local)
  - results/scores.json         → source Power BI via Blob (mode prod)
  - results/violations_flat.csv → table secondaire Power BI Top Rules Violation

Usage :
  python3 scripts/score_local.py \
    --results-dir results \
    --output-dir results

En mode CI/CD (push Azure Blob), utiliser scripts/spectral_to_blob.py à la place.
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml  # pip install pyyaml (optional, for operations_count)
except ImportError:
    yaml = None


# ---------------------------------------------------------------------------
# Mapping règles OWASP → catégorie lisible pour Power BI
# Basé sur les règles de ton owasp23-ruleset.spectral.yml
# ---------------------------------------------------------------------------
OWASP_CATEGORY_MAP = {
    "owasp:api1:2023-no-numeric-ids":                  "API1 - Broken Object Level Auth",
    "owasp:api2:2023-no-http-basic":                   "API2 - Broken Authentication",
    "owasp:api2:2023-no-api-keys-in-url":              "API2 - Broken Authentication",
    "owasp:api2:2023-no-credentials-in-url":           "API2 - Broken Authentication",
    "owasp:api2:2023-auth-insecure-schemes":           "API2 - Broken Authentication",
    "owasp:api2:2023-jwt-best-practices":              "API2 - Broken Authentication",
    "owasp:api2:2023-short-lived-access-tokens":       "API2 - Broken Authentication",
    "owasp:api2:2023-write-restricted":                "API2 - Broken Authentication",
    "owasp:api2:2023-read-restricted":                 "API2 - Broken Authentication",
    "owasp:api3:2023-no-additionalProperties":         "API3 - Broken Object Property Auth",
    "owasp:api3:2023-constrained-additionalProperties":"API3 - Broken Object Property Auth",
    "owasp:api3:2023-no-unevaluatedProperties":        "API3 - Broken Object Property Auth",
    "owasp:api3:2023-constrained-unevaluatedProperties":"API3 - Broken Object Property Auth",
    "owasp:api4:2023-rate-limit":                      "API4 - Unrestricted Resource Consumption",
    "owasp:api4:2023-rate-limit-retry-after":          "API4 - Unrestricted Resource Consumption",
    "owasp:api4:2023-rate-limit-responses-429":        "API4 - Unrestricted Resource Consumption",
    "owasp:api4:2023-array-limit":                     "API4 - Unrestricted Resource Consumption",
    "owasp:api4:2023-string-limit":                    "API4 - Unrestricted Resource Consumption",
    "owasp:api4:2023-string-restricted":               "API4 - Unrestricted Resource Consumption",
    "owasp:api4:2023-integer-limit":                   "API4 - Unrestricted Resource Consumption",
    "owasp:api4:2023-integer-limit-legacy":            "API4 - Unrestricted Resource Consumption",
    "owasp:api4:2023-integer-format":                  "API4 - Unrestricted Resource Consumption",
    "owasp:api5:2023-admin-security-unique":           "API5 - Broken Function Level Auth",
    "owasp:api7:2023-concerning-url-parameter":        "API7 - Server Side Request Forgery",
    "owasp:api8:2023-define-cors-origin":              "API8 - Security Misconfiguration",
    "owasp:api8:2023-no-scheme-http":                  "API8 - Security Misconfiguration",
    "owasp:api8:2023-no-server-http":                  "API8 - Security Misconfiguration",
    "owasp:api8:2023-define-error-validation":         "API8 - Security Misconfiguration",
    "owasp:api8:2023-define-error-responses-401":      "API8 - Security Misconfiguration",
    "owasp:api8:2023-define-error-responses-500":      "API8 - Security Misconfiguration",
    "owasp:api9:2023-inventory-access":                "API9 - Improper Inventory Management",
    "owasp:api9:2023-inventory-environment":           "API9 - Improper Inventory Management",
}

# ---------------------------------------------------------------------------
# Poids de pénalité par sévérité Spectral
# TOUTES tes règles sont en warn (severity=1) — poids à ajuster selon ton SLA
# error=0   → -20 pts (si tu ajoutes des règles error plus tard)
# warning=1 → -5  pts par règle distincte violée
# info=2    → -2  pts
# hint=3    → -1  pt
# ---------------------------------------------------------------------------
SEVERITY_WEIGHTS = {
    0: 20,
    1: 5,
    2: 2,
    3: 1,
}

GRADE_SCALE = [
    (85, "A"),
    (70, "B"),
    (50, "C"),
    (30, "D"),
    (0,  "E"),
]

SEVERITY_LABELS = {0: "error", 1: "warning", 2: "info", 3: "hint"}


def compute_score(issues: list) -> tuple:
    """
    Retourne (score, grade, rules_summary).
    Pénalité dédupliquée par rule_id : une règle violée 100 fois
    ne pénalise qu'une fois — mais on garde le count pour le drill-down.
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



def count_operations(spec_path: str) -> int:
    """Count HTTP operations (GET, POST, PUT, DELETE, PATCH) in a YAML spec."""
    if yaml is None:
        return 0
    if not os.path.exists(spec_path):
        return 0
    try:
        with open(spec_path) as f:
            spec = yaml.safe_load(f)
        if not spec or "paths" not in spec:
            return 0
        methods = {"get", "post", "put", "delete", "patch", "options", "head", "trace"}
        count = 0
        for path_item in spec["paths"].values():
            if isinstance(path_item, dict):
                count += sum(1 for m in path_item if m.lower() in methods)
        return count
    except Exception:
        return 0


def process_spectral_file(spectral_file: str, specs_dir: str = "specs") -> dict | None:
    """Parse un fichier *_spectral.json et retourne un record scoré."""
    if not os.path.exists(spectral_file):
        return None

    with open(spectral_file) as f:
        try:
            issues = json.load(f)
        except json.JSONDecodeError:
            print(f"[WARN] Could not parse {spectral_file}")
            return None

    # Déduit le nom du service depuis le nom du fichier
    # pattern attendu : {service_name}_spectral.json
    stem = Path(spectral_file).stem.replace("_spectral", "")

    score, grade, rules_summary = compute_score(issues)

    # Cherche le fichier YAML source pour compter les opérations
    ops_count = 0
    spec_yaml = None
    for ext in (".yaml", ".yml"):
        candidate = Path(specs_dir) / f"{stem}{ext}"
        if candidate.exists():
            spec_yaml = str(candidate)
            break
    if spec_yaml:
        ops_count = count_operations(spec_yaml)

    # Date de dernière modification du fichier spectral
    updated_date = datetime.fromtimestamp(
        os.path.getmtime(spectral_file), tz=timezone.utc
    ).strftime("%d/%m/%Y %H:%M:%S")

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service_name": stem,
        "domain": "unknown",
        "region": "unknown",
        "version": "v1",
        "spec_file": stem,
        "numerical_score": score,
        "grade": grade,
        "compliant": grade in ("A", "B", "C"),
        "total_issues": len(issues),
        "operations_count": ops_count,
        "total_rules_violated": len(rules_summary),
        "top_violations": rules_summary,
        "updated_date": updated_date,
    }


def write_csv(records: list, output_dir: str):
    """Écrit scores.csv — table principale Power BI."""
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
    print(f"[OK] scores.csv → {csv_path}")


def write_violations_csv(records: list, output_dir: str):
    """Écrit violations_flat.csv — table secondaire Top Rules Violation."""
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
    print(f"[OK] violations_flat.csv → {csv_path}")


def write_json(records: list, output_dir: str):
    """Écrit scores.json — pour upload Azure Blob en prod."""
    json_path = os.path.join(output_dir, "scores.json")
    with open(json_path, "w") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    print(f"[OK] scores.json → {json_path}")


def print_summary(records: list):
    """Affiche un résumé console style LV NEO dashboard."""
    print("\n" + "="*56)
    print(f"  SCOR API Quality — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*56)
    total = len(records)
    avg = sum(r["numerical_score"] for r in records) / total if total else 0
    compliant = sum(1 for r in records if r["compliant"])
    print(f"  Total APIs scored  : {total}")
    print(f"  Average score      : {avg:.0f}/100")
    print(f"  Compliance rate    : {compliant}/{total} ({100*compliant//total if total else 0}%)")
    print()
    for r in sorted(records, key=lambda x: x["numerical_score"], reverse=True):
        bar = "█" * (r["numerical_score"] // 10) + "░" * (10 - r["numerical_score"] // 10)
        flag = "✓" if r["compliant"] else "✗"
        print(f"  {flag} [{r['grade']}] {bar} {r['numerical_score']:3d}/100  {r['service_name']}")
    print("="*56 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Score Spectral results → CSV/JSON for Power BI")
    parser.add_argument("--results-dir",    default="results",
                        help="Dossier contenant les *_spectral.json")
    parser.add_argument("--output-dir",     default="results",
                        help="Dossier de sortie pour les CSV/JSON scorés")
    parser.add_argument("--specs-dir",      default="specs",
                        help="Dossier contenant les specs YAML")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    # Trouver tous les *.json
    spectral_files = list(Path(args.results_dir).glob("*.json"))
    if not spectral_files:
        print(f"[ERROR] No *.json found in {args.results_dir}")
        print("Run 'npm run lint:json' first.")
        sys.exit(1)

    records = []
    for sf in sorted(spectral_files):
        record = process_spectral_file(str(sf), specs_dir=args.specs_dir)
        if record:
            records.append(record)
            print(f"[INFO] {record['service_name']:40s} grade={record['grade']}  score={record['numerical_score']:3d}  issues={record['total_issues']}")

    # Compute rank (1 = best score)
    records.sort(key=lambda x: x["numerical_score"], reverse=True)
    for i, r in enumerate(records, 1):
        r["rank"] = i

    if not records:
        print("[ERROR] No records generated.")
        sys.exit(1)

    write_csv(records, args.output_dir)
    write_violations_csv(records, args.output_dir)
    write_json(records, args.output_dir)
    print_summary(records)


if __name__ == "__main__":
    main()
