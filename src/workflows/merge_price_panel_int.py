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

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.initiation.init_env import ensure_base_directories
from src.utils.log_utils import append_text_log
from src.utils.path_utils import CLEAN_ROOT, RAW_ROOT, build_dated_file_path


def list_price_files() -> list[Path]:
    price_root = RAW_ROOT / "price_daily"
    return sorted(price_root.glob("price_daily_int_*.csv"))


def load_one_price_file(file_path: Path) -> pd.DataFrame:
    DF_PriceInt = pd.read_csv(file_path, encoding="utf-8-sig")
    DF_PriceInt["TRADE_DATE"] = pd.to_datetime(DF_PriceInt["TRADE_DATE"])
    return DF_PriceInt


def build_price_panel(PriceFileList: list[Path]) -> pd.DataFrame:
    frame_list: list[pd.DataFrame] = []
    for file_path in PriceFileList:
        frame_list.append(load_one_price_file(file_path=file_path))
    DF_PricePanelInt = pd.concat(frame_list, ignore_index=True)
    DF_PricePanelInt = DF_PricePanelInt.sort_values(
        by=["TS_CODE", "TRADE_DATE"]
    ).reset_index(drop=True)
    return DF_PricePanelInt


def main() -> dict:
    ensure_base_directories()
    run_date = datetime.now().strftime("%Y%m%d")
    price_file_list = list_price_files()
    if not price_file_list:
        raise FileNotFoundError("No price files found in data/raw/price_daily.")

    DF_PricePanelInt = build_price_panel(PriceFileList=price_file_list)
    output_path = build_dated_file_path(
        folder_path=CLEAN_ROOT,
        stem_name="price_panel_int",
        date_text=run_date,
        suffix=".csv",
    )
    DF_PricePanelInt.to_csv(output_path, index=False, encoding="utf-8-sig")

    summary_dict = {
        "RUN_DATE": run_date,
        "INPUT_FILE_COUNT": len(price_file_list),
        "ROW_COUNT": int(len(DF_PricePanelInt)),
        "STOCK_COUNT": int(DF_PricePanelInt["TS_CODE"].nunique()),
        "START_DATE": str(DF_PricePanelInt["TRADE_DATE"].min().date()),
        "END_DATE": str(DF_PricePanelInt["TRADE_DATE"].max().date()),
        "OUTPUT_FILE": str(output_path),
    }
    summary_path = build_dated_file_path(
        folder_path=CLEAN_ROOT,
        stem_name="price_panel_int_summary",
        date_text=run_date,
        suffix=".json",
    )
    summary_path.write_text(
        json.dumps(summary_dict, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    append_text_log(
        log_path=PROJECT_ROOT / "logs" / "workflow.log",
        message_text=f"Price panel built -> {output_path}",
    )
    return summary_dict


if __name__ == "__main__":
    Summary = main()
    print(json.dumps(Summary, ensure_ascii=False, indent=2))
