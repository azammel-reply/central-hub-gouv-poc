"""
scripts/generate_excel.py
--------------------------
Reads scores.csv and violations_flat.csv and generates a single structured
Excel workbook (results/powerbi_data.xlsx) with proper tables and types.
This makes importing into Power BI Service (Web) significantly easier and cleaner.
"""

import argparse
import os
import pandas as pd

def main():
    parser = argparse.ArgumentParser(description="Convert CSVs to Excel for Power BI")
    parser.add_argument("--scores-file", default="results/scores.csv")
    parser.add_argument("--violations-file", default="results/violations_flat.csv")
    parser.add_argument("--output", default="results/powerbi_data.xlsx")
    args = parser.parse_args()

    if not os.path.exists(args.scores_file) or not os.path.exists(args.violations_file):
        print("[ERROR] CSV files not found. Run scoring first.")
        return

    # Read CSVs
    df_scores = pd.read_csv(args.scores_file)
    df_violations = pd.read_csv(args.violations_file)

    # Convert numeric columns explicitly (just in case)
    if "numerical_score" in df_scores.columns:
        df_scores["numerical_score"] = pd.to_numeric(df_scores["numerical_score"], errors="coerce")
    if "total_issues" in df_scores.columns:
        df_scores["total_issues"] = pd.to_numeric(df_scores["total_issues"], errors="coerce")
    if "operations_count" in df_scores.columns:
        df_scores["operations_count"] = pd.to_numeric(df_scores["operations_count"], errors="coerce")
    if "rank" in df_scores.columns:
        df_scores["rank"] = pd.to_numeric(df_scores["rank"], errors="coerce")
    
    if "occurrences" in df_violations.columns:
        df_violations["occurrences"] = pd.to_numeric(df_violations["occurrences"], errors="coerce")
    if "penalty" in df_violations.columns:
        df_violations["penalty"] = pd.to_numeric(df_violations["penalty"], errors="coerce")

    # Write to Excel with two distinct sheets
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    
    with pd.ExcelWriter(args.output, engine="openpyxl") as writer:
        df_scores.to_excel(writer, sheet_name="Scores", index=False)
        df_violations.to_excel(writer, sheet_name="Violations", index=False)
        
    print(f"[OK] Excel generation complete → {args.output}")

if __name__ == "__main__":
    main()
