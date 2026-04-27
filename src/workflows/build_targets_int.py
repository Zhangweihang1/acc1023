from __future__ import annotations

"""
initiation
- environment check
- import packages
- unified path management
- portable configuration
"""

from datetime import datetime
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.initiation.init_env import ensure_base_directories
from src.utils.log_utils import append_text_log
from src.utils.path_utils import CLEAN_ROOT, FEATURE_ROOT, build_dated_file_path


def load_project_config() -> dict:
    config_path = PROJECT_ROOT / "config" / "project_config.yaml"
    with config_path.open("r", encoding="utf-8") as file_handle:
        return yaml.safe_load(file_handle)


def find_latest_price_panel_file() -> Path:
    candidate_list = sorted(CLEAN_ROOT.glob("price_panel_int_*.csv"))
    if not candidate_list:
        raise FileNotFoundError("No price_panel_int file found in data/clean.")
    return candidate_list[-1]


def load_price_panel(panel_path: Path) -> pd.DataFrame:
    DF_PricePanelInt = pd.read_csv(panel_path, encoding="utf-8-sig")
    DF_PricePanelInt["TRADE_DATE"] = pd.to_datetime(DF_PricePanelInt["TRADE_DATE"])
    return DF_PricePanelInt


def build_target_columns(
    DF_PricePanelInt: pd.DataFrame,
    vol_window: int,
    target_window: int,
) -> pd.DataFrame:
    DF_TargetInt = DF_PricePanelInt.copy()
    DF_TargetInt = DF_TargetInt.sort_values(
        by=["TS_CODE", "TRADE_DATE"]
    ).reset_index(drop=True)

    DF_TargetInt["RET"] = (
        DF_TargetInt.groupby("TS_CODE")["CLOSE"].pct_change()
    )
    DF_TargetInt["LOG_RET"] = np.log1p(DF_TargetInt["RET"])
    DF_TargetInt["RV_20"] = (
        DF_TargetInt.groupby("TS_CODE")["LOG_RET"]
        .transform(lambda series: np.sqrt((series.pow(2)).rolling(vol_window).mean()))
    )
    DF_TargetInt["FUTURE_RV_5"] = (
        DF_TargetInt.groupby("TS_CODE")["LOG_RET"]
        .transform(
            lambda series: np.sqrt(
                (series.shift(-1).pow(2))
                .rolling(target_window)
                .mean()
                .shift(-(target_window - 1))
            )
        )
    )
    return DF_TargetInt


def main() -> dict:
    ensure_base_directories()
    config_dict = load_project_config()
    run_date = datetime.now().strftime("%Y%m%d")
    panel_path = find_latest_price_panel_file()
    DF_PricePanelInt = load_price_panel(panel_path=panel_path)
    vol_window = int(config_dict["TARGET"]["VOL_WINDOW"])
    target_window = int(config_dict["TARGET"]["TARGET_WINDOW"])

    DF_TargetInt = build_target_columns(
        DF_PricePanelInt=DF_PricePanelInt,
        vol_window=vol_window,
        target_window=target_window,
    )
    output_path = build_dated_file_path(
        folder_path=FEATURE_ROOT,
        stem_name="target_panel_int",
        date_text=run_date,
        suffix=".csv",
    )
    DF_TargetInt.to_csv(output_path, index=False, encoding="utf-8-sig")

    valid_target_count = int(DF_TargetInt["FUTURE_RV_5"].notna().sum())
    summary_dict = {
        "RUN_DATE": run_date,
        "INPUT_FILE": str(panel_path),
        "ROW_COUNT": int(len(DF_TargetInt)),
        "STOCK_COUNT": int(DF_TargetInt["TS_CODE"].nunique()),
        "VALID_TARGET_COUNT": valid_target_count,
        "VOL_WINDOW": vol_window,
        "TARGET_WINDOW": target_window,
        "OUTPUT_FILE": str(output_path),
    }
    summary_path = build_dated_file_path(
        folder_path=FEATURE_ROOT,
        stem_name="target_panel_int_summary",
        date_text=run_date,
        suffix=".json",
    )
    summary_path.write_text(
        json.dumps(summary_dict, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    append_text_log(
        log_path=PROJECT_ROOT / "logs" / "workflow.log",
        message_text=f"Target panel built -> {output_path}",
    )
    return summary_dict


if __name__ == "__main__":
    Summary = main()
    print(json.dumps(Summary, ensure_ascii=False, indent=2))
