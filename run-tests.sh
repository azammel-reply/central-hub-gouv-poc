#!/bin/bash

# Define colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}Spectral POC SCOR${NC}\n"
mkdir -p results

echo -e "--------------------------------------------------------"
echo -e "${BLUE}Linting all API Specifications in specs/${NC}"
echo -e "--------------------------------------------------------"

for spec in specs/*.yaml; do
    name=$(basename "$spec" .yaml)
    echo -e "\n${BLUE}➤ Linting: $name${NC}"
    
    # 1. Generate JSON for scoring (saves to results/)
    ./node_modules/.bin/spectral lint "$spec" \
      --ruleset owasp23-ruleset.spectral.yml \
      --format json \
      --output "results/${name}_spectral.json" || true
      
    # 2. Console Output for the developer
    ./node_modules/.bin/spectral lint "$spec" --ruleset owasp23-ruleset.spectral.yml || true
done
echo -e "--------------------------------------------------------"
echo -e "${BLUE}Scoring pipeline — generating Power BI records${NC}"
echo -e "--------------------------------------------------------"

if command -v python3 &> /dev/null; then
    python3 scripts/score_local.py \
      --results-dir results \
      --specs-dir specs \
      --output-dir results
    echo -e "${GREEN}Done — results/scores.csv ready for Power BI${NC}"

    echo -e "\n"
    echo -e "--------------------------------------------------------"
    echo -e "${BLUE}Generating Excel file for Power BI Web (.xlsx)${NC}"
    echo -e "--------------------------------------------------------"
    python3 scripts/generate_excel.py \
      --scores-file results/scores.csv \
      --violations-file results/violations_flat.csv \
      --output results/powerbi_data.xlsx

    echo -e "\n"
    echo -e "--------------------------------------------------------"
    echo -e "${BLUE}Generating HTML dashboard${NC}"
    echo -e "--------------------------------------------------------"
    python3 scripts/generate_dashboard.py \
      --scores-file results/scores.csv \
      --violations-file results/violations_flat.csv \
      --output results/dashboard.html
    echo -e "${GREEN}Done — open results/dashboard.html in your browser${NC}"
else
    echo -e "${RED}python3 not found — skipping score step${NC}"
fi