from __future__ import annotations

from pathlib import Path
import platform
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
CONFIG_ROOT = PROJECT_ROOT / "config"
LOG_ROOT = PROJECT_ROOT / "logs"
BACKUP_ROOT = PROJECT_ROOT / "backup"


def get_environment_snapshot() -> dict[str, str]:
    return {
        "PROJECT_ROOT": str(PROJECT_ROOT),
        "PYTHON_VERSION": sys.version.split()[0],
        "PLATFORM": platform.platform(),
    }


def ensure_base_directories() -> None:
    required_paths = [
        PROJECT_ROOT / "data",
        PROJECT_ROOT / "data" / "raw",
        PROJECT_ROOT / "data" / "clean",
        PROJECT_ROOT / "data" / "feature_store",
        PROJECT_ROOT / "data" / "model_output",
        PROJECT_ROOT / "data" / "predictions",
        LOG_ROOT,
        BACKUP_ROOT,
    ]
    for path_item in required_paths:
        path_item.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    ensure_base_directories()
    for key, value in get_environment_snapshot().items():
        print(f"{key}: {value}")

