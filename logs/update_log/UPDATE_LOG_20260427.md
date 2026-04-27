# Update Log 20260427

## Data Footprint Reduction

- Objective: reduce `data/` memory and repository footprint with minimum structural change.
- Constraints: keep project structure, workflow code, model logic, and existing loaded artifact filenames stable where possible; only reduce rows/files and update UI wording to match the smaller dataset.
- Inputs:
  - `data/raw/universe_int_20260423.csv`
  - `data/feature_store/feature_panel_int_20260423.csv`
  - `data/feature_store/target_panel_int_20260423.csv`
  - `data/predictions/*prediction_int_*.csv`
  - `data/raw/price_daily/*.csv`
- Outputs:
  - `data/data_reduction_audit_int_20260427.json`
  - reduced lightweight CSV artifacts under `data/`
  - updated UI copy in `app.py` and `src/app_ui/page_renderers.py`

## Change Summary

- Reduced coverage universe to the top 50 liquidity-ranked names from `universe_int_20260423.csv`.
- Reduced panel and prediction rows to the recent 180-date window while preserving existing columns.
- Deleted UI-unused prediction detail files:
  - `data/predictions/walk_forward_prediction_int_20260423.csv`
  - `data/predictions/walk_forward_regularized_prediction_int_20260423.csv`
  - `data/predictions/walk_forward_boosted_prediction_int_20260424.csv`
  - `data/predictions/baseline_prediction_int_20260423.csv`
  - `data/predictions/boosted_prediction_int_20260423.csv`
- Deleted raw daily price files outside the lightweight coverage universe.
- Updated UI text from fixed `150-stock` wording to dynamic lightweight coverage wording.

## Validation

- `python -m compileall app.py src\app_ui\page_renderers.py`
- Prediction merge check:
  - regularized rows: 8,768
  - boosted rows: 8,768
  - merged rows: 8,768
  - covered codes in merged predictions: 49
  - universe rows: 50
  - merged date range: 2025-06-11 to 2026-04-16
- Current `data/` size after reductions: 33.66 MiB.

## Constraint Gap

- Resolved in follow-up: `data/clean/price_panel_int_20260423.csv` file handle was released and the file was reduced in place.
- `data/clean/price_panel_int_20260423.csv` changed from 25.72 MiB / 248,762 rows to 0.93 MiB / 8,771 rows.
- Columns were preserved: 11 columns remain unchanged.
- Final `data/` size: 8.87 MiB.
- Rollback path: restore original data artifacts from the source workflow outputs or rerun the documented data workflow scripts for the full universe.

## Follow-Up Price Panel Reduction

- Reason: finish the urgent data footprint requirement after the previously locked price panel became writable.
- Scope: only `data/clean/price_panel_int_20260423.csv`.
- Method: filtered to the current lightweight 50-code universe and recent 180-date window; preserved original filename and columns.
- Impact: downstream code that expects the same CSV path and columns can keep reading the artifact; historical depth is intentionally reduced.
- Validation:
  - price panel rows: 8,771
  - price panel columns: 11
  - price panel codes: 50
  - price panel date range: 2025-07-25 to 2026-04-23
  - `python -m compileall app.py src\app_ui\page_renderers.py`

## GitHub And Streamlit Deployment Preparation

- Reason: prepare the lightweight project folder for GitHub upload and Streamlit Cloud connection.
- Scope:
  - added `.gitignore`
  - added `runtime.txt`
  - added `.streamlit/config.toml`
  - added `STREAMLIT_DEPLOYMENT_20260427.md`
- Impact:
  - local virtual environment, IDE files, Python caches, backups, screenshots, and local logs are excluded from git upload
  - Streamlit has explicit runtime and app config metadata
  - deployment settings are documented for handoff
- Rollback:
  - remove `.gitignore`, `runtime.txt`, `.streamlit/config.toml`, and `STREAMLIT_DEPLOYMENT_20260427.md`
