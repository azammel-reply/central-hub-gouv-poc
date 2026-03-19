# Central API Governance Hub

Welcome to the **API Governance Hub**. This central repository acts as the single source of truth for our enterprise API design standards. 

It serves two main functions:
1. **Central Rulesets**: Hosts the Spectral linting rules (`rulesets/enterprise-rules.spectral.yml`) that all API teams must adhere to.
2. **Global Dashboard**: Acts as a drop-zone for linting reports from all microservices, automatically generating a global compliance dashboard.

---

## 🛡️ Enterprise API Rules

The rules are maintained in the `rulesets/` directory. By hosting them centrally, we ensure all microservices follow the same naming conventions, security standards, and documentation requirements.

### Using the Central Rules locally
To test your API specification locally against the central ruleset, run:
```bash
npx spectral lint my-api-spec.yaml -r https://raw.githubusercontent.com/scor/central-hub-gouv-poc/main/rulesets/enterprise-rules.spectral.yml
```

---

## 🚀 How to Integrate Your Microservice

To have your API appear on the Global Compliance Dashboard, you must push your linter results to this repository during your CI/CD pipeline.

### Step-by-Step Integration (GitHub Actions)

1. Ensure your API repository has an OpenAPI specification (e.g., `openapi.yaml`).
2. Add the following GitHub Action workflow to your repository (`.github/workflows/api-lint-publish.yml`):

```yaml
name: "API Governance: Lint & Publish"
on:
  push:
    branches: [ "main" ]

jobs:
  lint-and-publish:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v3

      - name: Run Spectral Linter
        run: |
          npx @stoplight/spectral-cli lint openapi.yaml \
            -r https://raw.githubusercontent.com/scor/central-hub-gouv-poc/main/rulesets/enterprise-rules.spectral.yml \
            -f json -o spectral-results.json || true # We continue even if there are errors to publish the report

      - name: Push Report to Central Hub
        run: |
          git clone https://$API_HUB_TOKEN@github.com/scor/central-hub-gouv-poc.git hub-repo
          cp spectral-results.json hub-repo/incoming-reports/${{ github.event.repository.name }}.json
          cd hub-repo
          git config user.name "API Bot"
          git config user.email "bot@scor.com"
          git add incoming-reports/
          git commit -m "chore: Update API report for ${{ github.event.repository.name }}"
          git push
```

### What happens next?
Whenever you merge to `main`, your repository will push its JSON report to the `incoming-reports/` folder of this Central Hub. 
A workflow in this repository will detect the change, recalculate the global scores, and publish the updated **Enterprise Dashboard** on GitHub Pages.
