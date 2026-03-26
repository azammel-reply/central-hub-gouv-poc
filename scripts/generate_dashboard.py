"""
dashboard/generate_dashboard.py
-------------------------------
Generates a static HTML dashboard from scores.csv and violations_flat.csv.
Loads the HTML template from dashboard_template.html and injects data.

Usage:
  python3 scripts/generate_dashboard.py \
    --scores-file results/scores.csv \
    --violations-file results/violations_flat.csv \
    --kong-file results/kong_runtime.json \
    --output results/dashboard.html
"""

import argparse
import csv
import json
import logging
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

from scoring_rules import GRADE_COLORS

logging.basicConfig(level=logging.INFO, format="%(levelname)-5s  %(message)s")
log = logging.getLogger(__name__)

TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "dashboard_template.html"


def read_csv(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def color_class(val: float) -> str:
    """Helper for KPI coloring."""
    if val >= 80:
        return "green"
    if val >= 50:
        return "yellow"
    return "red"


def build_api_rows(api_list: list[dict], kong_data: dict, violations_by_api: dict = None) -> str:
    """Build HTML table rows for an API list, including a hidden details row for rule violations."""
    if violations_by_api == None:
        violations_by_api = {}
    if not api_list:
        return "<tr><td colspan='13' style='text-align:center; padding: 20px; color: var(--text2);'>No APIs to display.</td></tr>"
    rows = ""
    for r in api_list:
        svc = r.get("service_name", "")
        score_val = int(r.get("numerical_score", 0))
        grade = r.get("grade", "E")
        gc = GRADE_COLORS.get(grade, "#ef4444")
        # Build hidden details inside template
        api_violations = violations_by_api.get(svc, [])
        if api_violations:
            details_rows = ""
            for v in api_violations:
                details_rows += f"<tr><td style='padding:10px; border-bottom:1px solid var(--border);'>{v.get('rule')}</td><td style='padding:10px; border-bottom:1px solid var(--border);'>{v.get('severity_label')}</td><td style='padding:10px; border-bottom:1px solid var(--border);'>{v.get('occurrences')}</td><td style='padding:10px; border-bottom:1px solid var(--border);'>-{v.get('penalty')}</td></tr>"
            details_html = f"""<table class="details-table" style="width:100%; border-collapse:collapse; text-align:left;">
                <thead><tr style="background-color:var(--bg-card);"><th style="padding:10px; border-bottom:2px solid var(--border);">Rule</th><th style="padding:10px; border-bottom:2px solid var(--border);">Severity</th><th style="padding:10px; border-bottom:2px solid var(--border);">Occurrences</th><th style="padding:10px; border-bottom:2px solid var(--border);">Penalty</th></tr></thead>
                <tbody>{details_rows}</tbody>
            </table>"""
        else:
            details_html = "<div style='color:var(--text2); padding:20px 0;'>No rule violations recorded.</div>"
            
        
        # Kong Runtime Data
        kd = kong_data.get(svc, {})
        k_status = kd.get("kong_runtime_status", "Unmanaged")
        k_plugins = kd.get("kong_plugins", [])
        k_traffic = kd.get("kong_thirty_day_traffic", "-")
        
        if k_status == "Active":
            status_html = '<span class="grade-badge" style="background:var(--green)">Active</span>'
        elif k_status == "Unmanaged":
            status_html = '<span style="color:var(--text2); font-size:0.8rem;">Design Only</span>'
        else:
            status_html = '<span class="grade-badge" style="background:var(--red)">Inactive</span>'
            
        plugins_html = " ".join([f"<span style='background:var(--surface2); border:1px solid var(--border); border-radius:4px; padding:2px 6px; font-size:10px; display:inline-block; margin:2px;'>{p}</span>" for p in k_plugins]) if k_plugins else "<span style='color:var(--text2)'>None</span>"
        
        rows += f"""<tr class="api-main-row" onclick="showModal(this)" title="Click to view rule violations" style="cursor:pointer;">
            <td>{svc}</td>
            <td>{r.get('version','')}</td>
            <td>{r.get('domain','')}</td>
            <td>{r.get('region','')}</td>
            <td>{status_html}</td>
            <td style="max-width:200px;">{plugins_html}</td>
            <td style="font-family:monospace;">{k_traffic}</td>
            <td class="score-cell">{score_val}</td>
            <td><span class="grade-badge" style="background:{gc}">{grade}</span></td>
            <td>{r.get('total_issues','0')}</td>
            <td>{r.get('operations_count','0')}</td>
            <td>{r.get('rank','')}</td>
            <td class="date-cell">{r.get('updated_date','')}</td>
            <td style="display:none;"><template class="violation-data">{details_html}</template></td>
        </tr>"""
    return rows


def generate_dashboard(scores: list[dict], violations: list[dict], kong_data: dict) -> str:
    """Load the HTML template and inject computed data."""
    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    total_apis = len(scores)
    if total_apis == 0:
        return "<h1>No data</h1>"

    avg_score = sum(int(r["numerical_score"]) for r in scores) / total_apis
    compliant_count = sum(1 for r in scores if r["compliant"] == "True")
    compliance_rate = (compliant_count / total_apis * 100) if total_apis else 0

    # Grade breakdown
    grade_counts = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0}
    for r in scores:
        g = r.get("grade", "E")
        grade_counts[g] = grade_counts.get(g, 0) + 1

    # Top violations (split) and group violations by API
    owasp_totals: dict[str, int] = {}
    design_totals: dict[str, int] = {}
    violations_by_api: dict[str, list] = {}
    
    for v in violations:
        rule = v.get("rule", "")
        occ = int(v.get("occurrences", 0))
        svc = v.get("service_name", "")
        
        if svc:
            violations_by_api.setdefault(svc, []).append(v)
            
        if rule.startswith("owasp:"):
            owasp_totals[rule] = owasp_totals.get(rule, 0) + occ
        else:
            design_totals[rule] = design_totals.get(rule, 0) + occ

    top_owasp = sorted(owasp_totals.items(), key=lambda x: x[1], reverse=True)[:10]
    top_design = sorted(design_totals.items(), key=lambda x: x[1], reverse=True)[:10]

    owasp_rows = ""
    for rule, occ in top_owasp:
        owasp_rows += f"<tr><td>{rule}</td><td class='occ-cell'>{occ:,}</td></tr>"
    
    design_rows = ""
    for rule, occ in top_design:
        design_rows += f"<tr><td>{rule}</td><td class='occ-cell'>{occ:,}</td></tr>"

    # Sorted API lists
    sorted_by_score = sorted(scores, key=lambda x: int(x["numerical_score"]), reverse=True)
    top_apis = [r for r in sorted_by_score if r.get("grade") in ("A", "B", "C")][:10]
    bottom_apis = [r for r in sorted_by_score if r.get("grade") in ("D", "E")]

    # Chart data
    grade_labels = list(grade_counts.keys())
    grade_values = list(grade_counts.values())
    grade_bar_colors = [GRADE_COLORS[g] for g in grade_labels]

    # Replace template placeholders
    replacements = {
        "{{TIMESTAMP}}":          datetime.now(ZoneInfo("Europe/Paris")).strftime("%d/%m/%Y %H:%M"),
        "{{TOTAL_APIS}}":         str(total_apis),
        "{{AVG_SCORE}}":          f"{avg_score:.0f}",
        "{{AVG_SCORE_COLOR}}":    color_class(avg_score),
        "{{COMPLIANCE_RATE}}":    f"{compliance_rate:.1f}",
        "{{COMPLIANCE_COLOR}}":   color_class(compliance_rate),
        "{{COMPLIANT_COUNT}}":    str(compliant_count),
        "{{OWASP_VIOLATIONS_ROWS}}": owasp_rows,
        "{{DESIGN_VIOLATIONS_ROWS}}": design_rows,
        "{{TOP_APIS_ROWS}}":      build_api_rows(top_apis, kong_data, violations_by_api),
        "{{BOTTOM_APIS_ROWS}}":   build_api_rows(bottom_apis, kong_data, violations_by_api),
        "{{ALL_APIS_ROWS}}":      build_api_rows(sorted_by_score, kong_data, violations_by_api),
        "{{GRADE_LABELS}}":       json.dumps(grade_labels),
        "{{GRADE_VALUES}}":       json.dumps(grade_values),
        "{{GRADE_BAR_COLORS}}":   json.dumps(grade_bar_colors),
    }

    html = template
    for placeholder, value in replacements.items():
        html = html.replace(placeholder, value)

    return html


def generate_index_redirect(dashboard_filename: str = "dashboard.html") -> str:
    """Generate an index.html that redirects to the dashboard."""
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="refresh" content="0; url={dashboard_filename}">
    <title>Redirecting...</title>
</head>
<body>
    <p>Redirecting to <a href="{dashboard_filename}">dashboard</a>...</p>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description="Generate HTML dashboard")
    parser.add_argument("--scores-file",     default="results/scores.csv")
    parser.add_argument("--violations-file", default="results/violations_flat.csv")
    parser.add_argument("--kong-file",       default="results/kong_runtime.json")
    parser.add_argument("--output",          default="results/dashboard.html")
    args = parser.parse_args()

    scores = read_csv(args.scores_file)
    violations = read_csv(args.violations_file)
    
    kong_data = {}
    if os.path.exists(args.kong_file):
        with open(args.kong_file, "r", encoding="utf-8") as f:
            kong_data = json.load(f)

    if not scores:
        log.error("No data in %s", args.scores_file)
        sys.exit(1)

    # Generate dashboard
    html = generate_dashboard(scores, violations, kong_data)
    output_dir = os.path.dirname(args.output) or "."
    os.makedirs(output_dir, exist_ok=True)

    with open(args.output, "w") as f:
        f.write(html)
    log.info("dashboard.html → %s", args.output)

    # Generate index.html redirect
    index_path = os.path.join(output_dir, "index.html")
    with open(index_path, "w") as f:
        f.write(generate_index_redirect())
    log.info("index.html → %s", index_path)


if __name__ == "__main__":
    main()
