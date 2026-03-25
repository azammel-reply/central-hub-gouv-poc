"""
dashboard/config.py
-------------------
Central configuration for the API Governance scoring engine.
Single source of truth for OWASP mappings, severity weights, grades, and colors.
"""

# ---------------------------------------------------------------------------
# OWASP API Security Top 10 2023 — Rule → Category mapping
# ---------------------------------------------------------------------------
OWASP_CATEGORY_MAP = {
    "owasp:api1:2023-no-numeric-ids":                   "API1 - Broken Object Level Auth",
    "owasp:api2:2023-no-http-basic":                    "API2 - Broken Authentication",
    "owasp:api2:2023-no-api-keys-in-url":               "API2 - Broken Authentication",
    "owasp:api2:2023-no-credentials-in-url":            "API2 - Broken Authentication",
    "owasp:api2:2023-auth-insecure-schemes":            "API2 - Broken Authentication",
    "owasp:api2:2023-jwt-best-practices":               "API2 - Broken Authentication",
    "owasp:api2:2023-short-lived-access-tokens":        "API2 - Broken Authentication",
    "owasp:api2:2023-write-restricted":                 "API2 - Broken Authentication",
    "owasp:api2:2023-read-restricted":                  "API2 - Broken Authentication",
    "owasp:api3:2023-no-additionalProperties":          "API3 - Broken Object Property Auth",
    "owasp:api3:2023-constrained-additionalProperties": "API3 - Broken Object Property Auth",
    "owasp:api3:2023-no-unevaluatedProperties":         "API3 - Broken Object Property Auth",
    "owasp:api3:2023-constrained-unevaluatedProperties":"API3 - Broken Object Property Auth",
    "owasp:api4:2023-rate-limit":                       "API4 - Unrestricted Resource Consumption",
    "owasp:api4:2023-rate-limit-retry-after":           "API4 - Unrestricted Resource Consumption",
    "owasp:api4:2023-rate-limit-responses-429":         "API4 - Unrestricted Resource Consumption",
    "owasp:api4:2023-array-limit":                      "API4 - Unrestricted Resource Consumption",
    "owasp:api4:2023-string-limit":                     "API4 - Unrestricted Resource Consumption",
    "owasp:api4:2023-string-restricted":                "API4 - Unrestricted Resource Consumption",
    "owasp:api4:2023-integer-limit":                    "API4 - Unrestricted Resource Consumption",
    "owasp:api4:2023-integer-limit-legacy":             "API4 - Unrestricted Resource Consumption",
    "owasp:api4:2023-integer-format":                   "API4 - Unrestricted Resource Consumption",
    "owasp:api5:2023-admin-security-unique":            "API5 - Broken Function Level Auth",
    "owasp:api7:2023-concerning-url-parameter":         "API7 - Server Side Request Forgery",
    "owasp:api8:2023-define-cors-origin":               "API8 - Security Misconfiguration",
    "owasp:api8:2023-no-scheme-http":                   "API8 - Security Misconfiguration",
    "owasp:api8:2023-no-server-http":                   "API8 - Security Misconfiguration",
    "owasp:api8:2023-define-error-validation":          "API8 - Security Misconfiguration",
    "owasp:api8:2023-define-error-responses-401":       "API8 - Security Misconfiguration",
    "owasp:api8:2023-define-error-responses-500":       "API8 - Security Misconfiguration",
    "owasp:api9:2023-inventory-access":                 "API9 - Improper Inventory Management",
    "owasp:api9:2023-inventory-environment":            "API9 - Improper Inventory Management",
}

# ---------------------------------------------------------------------------
# Scoring: Severity weights (penalty per distinct violated rule)
# ---------------------------------------------------------------------------
SEVERITY_WEIGHTS = {
    0: 20,   # error   → -20 pts
    1: 10,   # warning → -10 pts
    2: 2,    # info    → -2  pts
    3: 1,    # hint    → -1  pt
}

SEVERITY_LABELS = {0: "error", 1: "warning", 2: "info", 3: "hint"}

# ---------------------------------------------------------------------------
# Grade scale (score >= threshold → grade)
# ---------------------------------------------------------------------------
GRADE_SCALE = [
    (85, "A"),
    (70, "B"),
    (50, "C"),
    (30, "D"),
    (0,  "E"),
]

# ---------------------------------------------------------------------------
# Grade colors (used in both scoring output and HTML dashboard)
# ---------------------------------------------------------------------------
GRADE_COLORS = {
    "A": "#22c55e",
    "B": "#84cc16",
    "C": "#eab308",
    "D": "#f97316",
    "E": "#ef4444",
}
