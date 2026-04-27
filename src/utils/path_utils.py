from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT / "data"
RAW_ROOT = DATA_ROOT / "raw"
CLEAN_ROOT = DATA_ROOT / "clean"
FEATURE_ROOT = DATA_ROOT / "feature_store"
MODEL_ROOT = DATA_ROOT / "model_output"
PREDICTION_ROOT = DATA_ROOT / "predictions"
CONFIG_ROOT = PROJECT_ROOT / "config"
LOG_ROOT = PROJECT_ROOT / "logs"
BACKUP_ROOT = PROJECT_ROOT / "backup"


def ensure_project_paths() -> None:
    path_list = [
        DATA_ROOT,
        RAW_ROOT,
        CLEAN_ROOT,
        FEATURE_ROOT,
        MODEL_ROOT,
        PREDICTION_ROOT,
        CONFIG_ROOT,
        LOG_ROOT,
        BACKUP_ROOT,
    ]
    for path_item in path_list:
        path_item.mkdir(parents=True, exist_ok=True)


def build_dated_file_path(folder_path: Path, stem_name: str, date_text: str, suffix: str) -> Path:
    return folder_path / f"{stem_name}_{date_text}{suffix}"

