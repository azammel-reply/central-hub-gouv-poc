# Central API Governance Hub — V2 (Runtime Edition)

[![Dashboard V2](https://github.com/azammel-reply/central-hub-gouv-poc/actions/workflows/aggregate-dashboard.yml/badge.svg?branch=feature/kong-runtime-v2)](https://github.com/azammel-reply/central-hub-gouv-poc/actions/workflows/aggregate-dashboard.yml)
[![V2 Dashboard Live](https://img.shields.io/badge/Dashboard_V2-Live-blue?logo=github)](https://azammel-reply.github.io/central-hub-gouv-poc/v2/dashboard.html)
[![V1 Dashboard](https://img.shields.io/badge/Dashboard_V1-Stable-gray?logo=github)](https://azammel-reply.github.io/central-hub-gouv-poc/dashboard.html)

> **V2** extends the governance hub beyond design-time API linting. It correlates **Spectral/OWASP** compliance scores with **live runtime data** from **Kong Konnect** — real traffic analytics, active plugins, and security posture — delivering a single pane of glass for API governance.

---

## Architecture

```
            ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
            │  poc-api-1   │   │  poc-api-2   │   │  poc-api-3   │
            │  Petstore    │   │  HTTPBin     │   │  User Mgmt   │
            │  Grade A     │   │  Grade E     │   │  Grade ?     │
            │  ✅ On Kong   │   │  ✅ On Kong   │   │  ❌ Design    │
            └──────┬───────┘   └──────┬───────┘   └──────┬───────┘
                   │                  │                   │
                   └── Spectral JSON ─┼── Spectral JSON ──┘
                                      ▼
                   ┌─────────────────────────────────────┐
                   │      central-hub-gouv-poc (V2)      │
                   │                                     │
                   │  incoming-reports/*.json  ← linting │
                   │  scripts/compute_scores.py          │
                   │  scripts/fetch_konnect_runtime.py   │  ← NEW V2
                   │  scripts/generate_dashboard.py      │
                   │  templates/dashboard_template.html   │
                   └──────────────┬──────────────────────┘
                                  │
                     ┌────────────┼────────────┐
                     ▼            ▼             ▼
               Kong Konnect    Scoring       GitHub Pages
               Analytics API   Engine        /v2/dashboard.html
               (7D traffic)   (OWASP)
```

---

## V2 vs V1 — What's New

| Feature | V1 (main) | V2 (this branch) |
|---------|-----------|-------------------|
| Spectral/OWASP linting | ✅ | ✅ |
| Scoring & grading (A→E) | ✅ | ✅ |
| Kong Runtime status | ❌ | ✅ Active / Inactive / Design Only |
| Kong Plugins display | ❌ | ✅ rate-limiting, key-auth, oidc... |
| Real traffic analytics | ❌ | ✅ Success / Error counts (7 days) |
| Cursor-based pagination | ❌ | ✅ Up to 50K requests |
| `KONG_PAT` as GitHub Secret | ❌ | ✅ No hardcoded tokens |
| 3rd API (Design Only) | ❌ | ✅ poc-api-3 |

---

## Connected Projects

| Repository | API | Kong? | Description |
|-----------|-----|-------|-------------|
| [poc-api-1](https://github.com/azammel-reply/poc-api-1) | Petstore (OAS 2.0) | ✅ `poc-api-1` on Konnect | Best-practice API, Grade A. Proxied through Kong with `rate-limiting` plugin. |
| [poc-api-2](https://github.com/azammel-reply/poc-api-2) | HTTPBin (OAS 2.0) | ✅ `poc-api-2` on Konnect | Intentionally insecure API, Grade E. Protected by `key-auth` + `cors` plugins. |
| [poc-api-3](https://github.com/azammel-reply/poc-api-3) | User Management (OAS 3.0) | ❌ Design Only | Internal IAM API, not deployed on Kong. Demonstrates pure design-time governance. |

### How each API flows into the dashboard

```
poc-api-1 / poc-api-2 / poc-api-3
    │
    │  1. Push to main triggers Spectral lint (GitHub Actions)
    │  2. Results JSON pushed to central-hub incoming-reports/
    │     └── poc-api-3 pushes to branch: feature/kong-runtime-v2 (V2 only)
    │
    ▼
central-hub-gouv-poc (Aggregate Dashboard workflow)
    │
    │  3. compute_scores.py → scores.csv + violations_flat.csv
    │  4. fetch_konnect_runtime.py → kong_runtime.json  ← V2 only
    │  5. generate_dashboard.py → dashboard.html
    │
    ▼
GitHub Pages /v2/dashboard.html
```

---

## How the Runtime Integration Works

### `fetch_konnect_runtime.py` — The V2 Engine

This script bridges the gap between design-time linting and live operations by querying **two Kong Konnect APIs**:

#### Step 1: Analytics API (Traffic Data)

```
POST https://eu.api.konghq.com/v2/api-requests
Body: {"size": 1000, "time_range": {"type": "relative", "time_range": "7D"}}
```

- Returns individual request logs for the **last 7 days**
- Uses **cursor-based pagination** to fetch ALL requests (up to 50 pages × 1000 = 50K requests)
- Each log contains:
  - `gateway_service`: `"<control_plane_id>:<service_id>"` — composite key identifying the Kong service
  - `response_http_status`: `"200"`, `"401"`, etc. — string, not integer
- The script splits status codes: `< 400` = ✅ Success, `>= 400` = ❌ Error

#### Step 2: Admin API (Service Metadata)

```
GET https://eu.api.konghq.com/v2/control-planes/{CP_ID}/core-entities/services
GET .../{service_id}/plugins
```

- Lists all services registered on the control plane
- For each service, fetches its active plugins
- **Matching**: The service `id` (UUID) from the Admin API matches the extracted `service_id` from the Analytics API — this is how traffic counts are linked to named services

#### Step 3: Output

Produces `results/kong_runtime.json`:

```json
{
  "poc-api-1": {
    "kong_runtime_status": "Active",
    "kong_plugins": ["rate-limiting"],
    "kong_is_secure": false,
    "kong_thirty_day_traffic": "4 OK / 0 ERR"
  },
  "poc-api-2": {
    "kong_runtime_status": "Active",
    "kong_plugins": ["key-auth", "cors"],
    "kong_is_secure": true,
    "kong_thirty_day_traffic": "0 OK / 3 ERR"
  }
}
```

APIs **not on Kong** (like poc-api-3) won't appear in this JSON, and the dashboard renders them as `Design Only` with no traffic data.

---

## Project Structure

```
central-hub-gouv-poc/
├── .github/workflows/
│   └── aggregate-dashboard.yml       # CI/CD: score + runtime + deploy
├── scripts/
│   ├── scoring_rules.py              # Scoring config (penalties, grades)
│   ├── compute_scores.py             # Scoring engine (CSV output)
│   ├── fetch_konnect_runtime.py      # V2: Kong Konnect runtime fetcher
│   └── generate_dashboard.py         # Dashboard HTML generator
├── templates/
│   └── dashboard_template.html       # HTML/CSS/JS dashboard template
├── incoming-reports/                  # Raw Spectral JSON from API repos
│   ├── poc-api-1@1.0.1.json
│   ├── poc-api-2@1.0.0.json          # (Note: poc-api-2 renamed as 2.2.1)
│   └── poc-api-3@1.0.0.json          # V2 branch only
├── rulesets/
│   └── owasp23-ruleset.spectral.yml  # Central OWASP ruleset
├── results/                           # .gitignored — generated at CI time
└── README.md
```

---

## GitHub Secrets

| Secret | Where | Purpose |
|--------|-------|---------|
| `HUB_PAT` | poc-api-1, poc-api-2, poc-api-3 | GitHub PAT (`ghp_...`) to push lint results to central-hub |
| `KONG_PAT` | central-hub-gouv-poc | Kong Konnect PAT (`kpat_...`) for Admin + Analytics API calls |

> ⚠️ **No tokens are hardcoded in source code.** `fetch_konnect_runtime.py` reads `KONG_PAT` from the environment and prints a warning if missing.

---

## Kong Konnect Configuration

| Parameter | Value |
|-----------|-------|
| Region | `eu` (Europe) |
| Control Plane | `aez-dp-no-prod` |
| Control Plane ID | `6993903a-af80-4ead-9909-29f956e5d88e` |
| Analytics Endpoint | `POST https://eu.api.konghq.com/v2/api-requests` |
| Admin Endpoint | `GET https://eu.api.konghq.com/v2/control-planes/{CP_ID}/core-entities/...` |
| Analytics Window | Last 7 days (`time_range: "7D"`) |
| Pagination | Cursor-based, 1000/page, max 50 pages (50K requests) |

---

## Local Development

```bash
# 1. Set your Kong PAT
export KONG_PAT=kpat_your_kong_pat_here

# 2. Score the incoming reports
cd scripts
python compute_scores.py --results-dir ../incoming-reports --output-dir ../results

# 3. Fetch Kong runtime data (requires KONG_PAT)
python fetch_konnect_runtime.py

# 4. Generate the dashboard
python generate_dashboard.py \
  --scores-file ../results/scores.csv \
  --violations-file ../results/violations_flat.csv \
  --kong-file ../results/kong_runtime.json \
  --output ../results/dashboard.html

# 5. Open in browser
open ../results/dashboard.html
```

---

## Onboarding a New API

### Design-Only API (no Kong)

1. Create a repo with your OpenAPI spec at `specs/openapi.yaml`
2. Copy the workflow from [poc-api-3/.github/workflows/lint-and-push.yml](https://github.com/azammel-reply/poc-api-3)
3. **Important**: If V2 only, set the workflow to clone `-b feature/kong-runtime-v2`:
   ```yaml
   git clone -b feature/kong-runtime-v2 https://${HUB_PAT}@github.com/azammel-reply/central-hub-gouv-poc.git hub-repo
   ```
4. Add secret `HUB_PAT` (GitHub PAT with `repo` scope)
5. Push to `main` → API appears on V2 dashboard as **"Design Only"**

### Runtime API (on Kong)

1. Same steps as above
2. Also create a Kong Service + Route on the `aez-dp-no-prod` control plane
3. The `fetch_konnect_runtime.py` script will **automatically discover** it via the Admin API
4. Dashboard shows: runtime status, plugins, and real traffic counts

---

## Scoring Mechanism

Starting from **100 points**, penalties are deducted per **unique rule violated** (not per occurrence):

| Severity | Penalty | Example |
|----------|---------|---------|
| Error | -20 pts | Blockers |
| Warning | -10 pts | OWASP rules |
| Info | -2 pts | Informational |
| Hint | -1 pt | Design advice |

### Grades

| Score | Grade | Status |
|-------|-------|--------|
| ≥ 85 | **A** | Excellent |
| ≥ 70 | **B** | Good |
| ≥ 50 | **C** | Fair |
| ≥ 30 | **D** | Critical |
| < 30 | **E** | Unacceptable |

> **Deduplication**: 50 endpoints missing the same rule = 1 penalty, not 50. This prevents endpoint volume from skewing the score.

---

## CI/CD Pipeline (V2)

```yaml
# aggregate-dashboard.yml (simplified)
jobs:
  build-dashboard:
    steps:
      - Checkout Code
      - Setup Python 3.12
      - pip install pandas
      - python compute_scores.py          # → scores.csv, violations_flat.csv
      - python fetch_konnect_runtime.py   # → kong_runtime.json (uses KONG_PAT secret)
      - python generate_dashboard.py      # → dashboard.html
      - Deploy to GitHub Pages /v2/       # peaceiris/actions-gh-pages
```

---

## Branching Strategy

```
main                    → Production V1 dashboard (design-time only)
                           Deployed to: /dashboard.html
                           APIs: poc-api-1, poc-api-2

feature/kong-runtime-v2 → V2 dashboard (design + runtime)
                           Deployed to: /v2/dashboard.html
                           APIs: poc-api-1, poc-api-2, poc-api-3
```

Both dashboards coexist on GitHub Pages. V1 remains stable for production demos while V2 is the development frontier.
