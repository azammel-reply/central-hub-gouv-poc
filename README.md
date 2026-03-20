# 🛡️ Central API Governance Hub

[![Dashboard](https://github.com/azammel-reply/central-hub-gouv-poc/actions/workflows/aggregate-dashboard.yml/badge.svg)](https://github.com/azammel-reply/central-hub-gouv-poc/actions/workflows/aggregate-dashboard.yml)
[![Dashboard Live](https://img.shields.io/badge/Dashboard-Live-blue?logo=github)](https://azammel-reply.github.io/central-hub-gouv-poc/dashboard.html)

> Central governance hub that collects API linting results from multiple repositories, scores them against the OWASP API Security Top 10 2023 ruleset, and publishes an automated compliance dashboard.

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  poc-api-1   │     │  poc-api-2   │     │  api-xxx-N   │
│  (Grade A)   │     │  (Grade E)   │     │  (Grade ?)   │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       └────── push JSON ───┼──── push JSON ─────┘
                            ▼
              ┌──────────────────────────┐
              │   central-hub-gouv-poc   │
              │                          │
              │  incoming-reports/*.json  │  ← raw Spectral results
              │  dashboard/config.py     │  ← scoring config
              │  dashboard/score_local.py│  ← scoring engine
              │  dashboard/template.html │  ← HTML template
              │  dashboard/generate.py   │  ← dashboard generator
              │  rulesets/owasp23-*.yml   │  ← central ruleset
              └────────────┬─────────────┘
                           │ GitHub Actions
                           ▼
                 GitHub Pages Dashboard
          azammel-reply.github.io/central-hub-gouv-poc
```

## Enterprise-Grade Resilience

The Governance Hub and its downstream APIs implement advanced structural checks for high-scale enterprise scenarios:

- **Spoke API CI/CD Guardrails**: 
  - **Missing Spec Handling**: Custom `if/exit 0` guards to avoid failing pipelines when specs are moving or absent.
  - **Path-based Execution Filters**: Linting triggers strictly only on `specs/**` file changes.
  - **Checksum Optimization**: Diff comparison blocks redundant commits/pushes for unmodified APIs.
  - **Git Collision Resilience**: Up to 3x `git pull --rebase` exponential retrys against `non-fast-forward` merge blocks when dozens of APIs simultaneously push reports.
- **Hub Version Accumulation Management**:
  - `score_local.py` mathematically parses semantic version fragments (`1.10.0` vs `1.2.0`) from the incoming JSON filenames.
  - It automatically deduplicates and **retains only the latest absolute version** for any API. This guarantees Dashboard accuracy and prevents accumulating "garbage reports" over years.

## How It Works

1. **API repos** (poc-api-1, poc-api-2, ...) run Spectral against the central OWASP ruleset on every push to `main`.
2. Linting results (JSON) are pushed to `incoming-reports/` via a Governance Bot.
3. The **Aggregate Dashboard** workflow detects new/changed JSON files and:
   - Scores each API using a deduplicated penalty system
   - Generates CSV, JSON, and an interactive HTML dashboard
   - Deploys to GitHub Pages automatically

## Scoring Algorithm

| Severity | Penalty per distinct rule violated |
|----------|-----------------------------------|
| Error    | -20 pts |
| Warning  | -5 pts  |
| Info     | -2 pts  |
| Hint     | -1 pt   |

**Grade Scale**: A (≥85) → B (≥70) → C (≥50) → D (≥30) → E (<30)

> A rule violated 100 times only penalises once — but occurrences are tracked for drill-down.

## Onboarding a New API

1. Create a new repository with your OpenAPI spec in `specs/openapi.yaml`.
2. Copy the workflow from [poc-api-1/.github/workflows/lint-and-push.yml](https://github.com/reply-fr/poc-api-1/blob/main/.github/workflows/lint-and-push.yml).
3. Add a GitHub secret `HUB_PAT` — a Personal Access Token with `repo` scope from the hub owner.
4. Push to `main` — the API will appear on the dashboard automatically!

## Project Structure

```
central-hub-gouv-poc/
├── .github/workflows/
│   └── aggregate-dashboard.yml    # CI/CD: score + deploy
├── dashboard/
│   ├── config.py                  # Scoring configuration
│   ├── score_local.py             # Scoring engine
│   ├── generate_dashboard.py      # Dashboard generator
│   └── dashboard_template.html    # HTML/CSS/JS template
├── incoming-reports/              # Raw Spectral JSON results
├── rulesets/
│   └── owasp23-ruleset.spectral.yml  # Central OWASP ruleset
├── results/                       # Generated output (CSV/JSON/HTML)
└── README.md
```

## Local Development

```bash
# Score the incoming reports
cd dashboard
python score_local.py --results-dir ../incoming-reports --output-dir ../results

# Generate the dashboard
python generate_dashboard.py \
  --scores-file ../results/scores.csv \
  --violations-file ../results/violations_flat.csv \
  --output ../results/dashboard.html

# Open in browser
open ../results/dashboard.html
```

## Related Repositories

| Repository | Grade | Description |
|------------|-------|-------------|
| [poc-api-1](https://github.com/reply-fr/poc-api-1) | A | Best-practice OWASP-compliant API |
| [poc-api-2](https://github.com/reply-fr/poc-api-2) | E | Intentionally insecure API |
