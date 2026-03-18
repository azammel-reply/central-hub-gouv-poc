"""
scripts/generate_dashboard.py
------------------------------
Generates a static HTML dashboard from scores.csv and violations_flat.csv.
Replicates the LV NEO Data Integration Governance dashboard layout.

Usage:
  python3 scripts/generate_dashboard.py \
    --scores-file results/scores.csv \
    --violations-file results/violations_flat.csv \
    --output results/dashboard.html
"""

import argparse
import csv
import os
import sys
from datetime import datetime
from pathlib import Path


def read_csv(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def generate_html(scores: list[dict], violations: list[dict]) -> str:
    # --- KPI calculations ---
    total_apis = len(scores)
    if total_apis == 0:
        return "<h1>No data</h1>"

    avg_score = sum(int(r["numerical_score"]) for r in scores) / total_apis
    compliant_count = sum(1 for r in scores if r["compliant"] == "True")
    compliance_rate = (compliant_count / total_apis * 100) if total_apis else 0

    # --- Grade breakdown ---
    grade_counts = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0}
    for r in scores:
        g = r.get("grade", "E")
        grade_counts[g] = grade_counts.get(g, 0) + 1

    # --- Top violations ---
    violation_totals: dict[str, int] = {}
    for v in violations:
        rule = v.get("rule", "")
        occ = int(v.get("occurrences", 0))
        violation_totals[rule] = violation_totals.get(rule, 0) + occ
    top_violations = sorted(violation_totals.items(), key=lambda x: x[1], reverse=True)[:10]

    # --- Top / Bottom APIs ---
    sorted_by_score = sorted(scores, key=lambda x: int(x["numerical_score"]), reverse=True)
    top_apis = sorted_by_score[:10]
    bottom_apis = sorted_by_score[-10:][::-1] if len(sorted_by_score) > 10 else sorted_by_score[::-1]

    # --- Grade colors ---
    grade_colors = {
        "A": "#22c55e", "B": "#84cc16", "C": "#eab308", "D": "#f97316", "E": "#ef4444"
    }

    # --- Build API table rows ---
    def api_table_rows(api_list: list[dict]) -> str:
        rows = ""
        for r in api_list:
            score_val = int(r.get("numerical_score", 0))
            grade = r.get("grade", "E")
            gc = grade_colors.get(grade, "#ef4444")
            rows += f"""<tr>
                <td>{r.get('service_name','')}</td>
                <td>{r.get('version','')}</td>
                <td>{r.get('domain','')}</td>
                <td>{r.get('region','')}</td>
                <td class="score-cell">{score_val}</td>
                <td><span class="grade-badge" style="background:{gc}">{grade}</span></td>
                <td>{r.get('total_issues','0')}</td>
                <td>{r.get('operations_count','0')}</td>
                <td>{r.get('rank','')}</td>
                <td class="date-cell">{r.get('updated_date','')}</td>
            </tr>"""
        return rows

    # --- Build violations table rows ---
    violations_rows = ""
    for rule, occ in top_violations:
        violations_rows += f"<tr><td>{rule}</td><td class='occ-cell'>{occ:,}</td></tr>"

    # --- Grade chart data ---
    grade_labels = list(grade_counts.keys())
    grade_values = list(grade_counts.values())
    grade_bar_colors = [grade_colors[g] for g in grade_labels]

    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API Design Governance — SCOR Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
    <style>
        :root {{
            --bg: #0f172a;
            --surface: #1e293b;
            --surface2: #334155;
            --text: #f1f5f9;
            --text2: #94a3b8;
            --accent: #3b82f6;
            --accent2: #8b5cf6;
            --green: #22c55e;
            --yellow: #eab308;
            --red: #ef4444;
            --orange: #f97316;
            --border: #475569;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', -apple-system, system-ui, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            padding: 24px;
        }}
        .header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 28px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border);
        }}
        .header h1 {{
            font-size: 1.6rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent), var(--accent2));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .header .timestamp {{ color: var(--text2); font-size: 0.85rem; }}

        /* KPI Cards */
        .kpi-row {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }}
        .kpi-card {{
            background: var(--surface);
            border-radius: 12px;
            padding: 20px 24px;
            text-align: center;
            border: 1px solid var(--border);
            transition: transform 0.2s;
        }}
        .kpi-card:hover {{ transform: translateY(-2px); }}
        .kpi-card .label {{ color: var(--text2); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; }}
        .kpi-card .value {{ font-size: 2.2rem; font-weight: 800; margin: 8px 0 0; }}
        .kpi-card .value.green {{ color: var(--green); }}
        .kpi-card .value.yellow {{ color: var(--yellow); }}
        .kpi-card .value.red {{ color: var(--red); }}
        .kpi-card .value.accent {{ color: var(--accent); }}

        /* Grid layout */
        .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }}
        .grid-3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin-bottom: 24px; }}

        .card {{
            background: var(--surface);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid var(--border);
        }}
        .card h2 {{
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 16px;
            color: var(--text);
        }}

        /* Tables */
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.82rem;
        }}
        th {{
            text-align: left;
            padding: 8px 10px;
            background: var(--surface2);
            color: var(--text2);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.7rem;
            letter-spacing: 0.04em;
            border-bottom: 2px solid var(--border);
        }}
        td {{
            padding: 7px 10px;
            border-bottom: 1px solid var(--border);
            color: var(--text);
        }}
        tr:hover td {{ background: rgba(59, 130, 246, 0.06); }}
        .score-cell {{ font-weight: 700; }}
        .occ-cell {{ font-weight: 700; text-align: right; color: var(--yellow); }}
        .date-cell {{ color: var(--text2); font-size: 0.78rem; }}

        .grade-badge {{
            display: inline-block;
            padding: 2px 10px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 0.78rem;
            color: #fff;
        }}

        /* Chart container */
        .chart-container {{
            position: relative;
            height: 250px;
        }}

        /* Responsive */
        @media (max-width: 900px) {{
            .kpi-row {{ grid-template-columns: repeat(2, 1fr); }}
            .grid-2, .grid-3 {{ grid-template-columns: 1fr; }}
        }}

        /* Full-width card */
        .full-width {{ margin-bottom: 24px; }}
    </style>
</head>
<body>

<div class="header">
    <h1>🛡️ API Design Governance — SCOR Dashboard</h1>
    <span class="timestamp">Generated: {timestamp}</span>
</div>

<!-- KPI Cards -->
<div class="kpi-row">
    <div class="kpi-card">
        <div class="label">Total APIs</div>
        <div class="value accent">{total_apis}</div>
    </div>
    <div class="kpi-card">
        <div class="label">Average Score</div>
        <div class="value {'green' if avg_score >= 70 else 'yellow' if avg_score >= 50 else 'red'}">{avg_score:.0f}/100</div>
    </div>
    <div class="kpi-card">
        <div class="label">Compliance Rate</div>
        <div class="value {'green' if compliance_rate >= 70 else 'yellow' if compliance_rate >= 50 else 'red'}">{compliance_rate:.1f}%</div>
    </div>
    <div class="kpi-card">
        <div class="label">Compliant APIs (A/B/C)</div>
        <div class="value green">{compliant_count}/{total_apis}</div>
    </div>
</div>

<!-- Charts Row -->
<div class="grid-2">
    <div class="card">
        <h2>API Compliance Breakdown</h2>
        <div class="chart-container">
            <canvas id="complianceChart"></canvas>
        </div>
    </div>
    <div class="card">
        <h2>Top Rules Violation</h2>
        <table>
            <thead><tr><th>Rule</th><th style="text-align:right">Total Occurrences</th></tr></thead>
            <tbody>{violations_rows}</tbody>
        </table>
    </div>
</div>

<!-- Top / Bottom APIs -->
<div class="grid-2">
    <div class="card">
        <h2>🏆 Top Quality APIs</h2>
        <table>
            <thead><tr>
                <th>File Name</th><th>Ver</th><th>Domain</th><th>Region</th>
                <th>Score</th><th>Grade</th><th>Issues</th><th>Ops</th><th>Rank</th><th>Updated</th>
            </tr></thead>
            <tbody>{api_table_rows(top_apis)}</tbody>
        </table>
    </div>
    <div class="card">
        <h2>⚠️ Top Bottom APIs</h2>
        <table>
            <thead><tr>
                <th>File Name</th><th>Ver</th><th>Domain</th><th>Region</th>
                <th>Score</th><th>Grade</th><th>Issues</th><th>Ops</th><th>Rank</th><th>Updated</th>
            </tr></thead>
            <tbody>{api_table_rows(bottom_apis)}</tbody>
        </table>
    </div>
</div>

<!-- Full API List -->
<div class="card full-width">
    <h2>📋 API's List</h2>
    <table>
        <thead><tr>
            <th>File Name</th><th>Ver</th><th>Domain</th><th>Region</th>
            <th>Score</th><th>Grade</th><th>Issues</th><th>Ops</th><th>Rank</th><th>Updated</th>
        </tr></thead>
        <tbody>{api_table_rows(sorted_by_score)}</tbody>
    </table>
</div>

<script>
new Chart(document.getElementById('complianceChart'), {{
    type: 'bar',
    data: {{
        labels: {grade_labels},
        datasets: [{{
            label: 'Number of APIs',
            data: {grade_values},
            backgroundColor: {grade_bar_colors},
            borderRadius: 6,
            borderSkipped: false,
        }}]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
            legend: {{ display: false }},
            tooltip: {{
                callbacks: {{
                    label: ctx => ctx.parsed.y + ' APIs'
                }}
            }}
        }},
        scales: {{
            x: {{
                ticks: {{ color: '#94a3b8' }},
                grid: {{ display: false }},
            }},
            y: {{
                ticks: {{ color: '#94a3b8', stepSize: 1 }},
                grid: {{ color: 'rgba(71,85,105,0.3)' }},
                beginAtZero: true,
            }}
        }}
    }}
}});
</script>

</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description="Generate HTML dashboard from scoring CSV")
    parser.add_argument("--scores-file", default="results/scores.csv")
    parser.add_argument("--violations-file", default="results/violations_flat.csv")
    parser.add_argument("--output", default="results/dashboard.html")
    args = parser.parse_args()

    scores = read_csv(args.scores_file)
    violations = read_csv(args.violations_file)

    if not scores:
        print(f"[ERROR] No data in {args.scores_file}")
        sys.exit(1)

    html = generate_html(scores, violations)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        f.write(html)
    print(f"[OK] dashboard.html → {args.output}")


if __name__ == "__main__":
    main()
