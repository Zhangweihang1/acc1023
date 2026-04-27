# Streamlit Deployment Handoff 20260427

## Goal

Publish `ACC102` to GitHub and deploy `app.py` on Streamlit Community Cloud.

## Current State

- Streamlit entrypoint: `app.py`
- Python runtime: `python-3.11`
- Dependency file: `requirements.txt`
- Lightweight data folder size: 8.87 MiB
- Data reduction audit: `data/data_reduction_audit_int_20260427.json`

## GitHub Upload Scope

Include:

- `app.py`
- `src/`
- `config/`
- `data/`
- `requirements.txt`
- `runtime.txt`
- `.streamlit/config.toml`
- project documentation and update logs

Exclude:

- `.venv/`
- `.idea/`
- `__pycache__/`
- `backup/`
- local logs and screenshots
- `.streamlit/secrets.toml`

## Streamlit Cloud Settings

- Repository: the GitHub repository created from this folder
- Branch: `main`
- Main file path: `app.py`
- Python version: resolved from `runtime.txt`

## Validation

- `python -m compileall app.py src\app_ui\page_renderers.py`
- `data/` size verified below 25 MiB

## Update Log

- Reason: prepare the lightweight ACC102 app for GitHub and Streamlit deployment.
- Impact: deployment metadata added; runtime and ignored-file behavior clarified.
- Rollback: remove `.gitignore`, `runtime.txt`, `.streamlit/config.toml`, and this handoff file.
