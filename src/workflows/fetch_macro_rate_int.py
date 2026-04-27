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

import akshare as ak
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.initiation.init_env import ensure_base_directories
from src.utils.log_utils import append_text_log
from src.utils.path_utils import RAW_ROOT, build_dated_file_path


MACRO_COLUMN_MAP = {
    "日期": "TRADE_DATE",
    "中国国债收益率2年": "CN_GOV_BOND_YIELD_2Y",
    "中国国债收益率5年": "CN_GOV_BOND_YIELD_5Y",
    "中国国债收益率10年": "CN_GOV_BOND_YIELD_10Y",
    "中国国债收益率30年": "CN_GOV_BOND_YIELD_30Y",
    "中国国债收益率10年-2年": "CN_YIELD_CURVE_10Y_2Y",
    "美国国债收益率2年": "US_GOV_BOND_YIELD_2Y",
    "美国国债收益率5年": "US_GOV_BOND_YIELD_5Y",
    "美国国债收益率10年": "US_GOV_BOND_YIELD_10Y",
    "美国国债收益率30年": "US_GOV_BOND_YIELD_30Y",
    "美国国债收益率10年-2年": "US_YIELD_CURVE_10Y_2Y",
}


def fetch_macro_rate_df() -> pd.DataFrame:
    DF_MacroRaw = ak.bond_zh_us_rate()
    available_column_map = {
        raw_name: standard_name
        for raw_name, standard_name in MACRO_COLUMN_MAP.items()
        if raw_name in DF_MacroRaw.columns
    }
    if "日期" not in available_column_map:
        raise KeyError("AKShare bond_zh_us_rate output is missing 日期 column.")

    DF_MacroInt = DF_MacroRaw.rename(columns=available_column_map).copy()
    selected_column_list = list(available_column_map.values())
    DF_MacroInt = DF_MacroInt[selected_column_list]
    DF_MacroInt["TRADE_DATE"] = pd.to_datetime(DF_MacroInt["TRADE_DATE"])

    numeric_column_list = [
        column_name for column_name in DF_MacroInt.columns if column_name != "TRADE_DATE"
    ]
    for column_name in numeric_column_list:
        DF_MacroInt[column_name] = pd.to_numeric(DF_MacroInt[column_name], errors="coerce")

    DF_MacroInt = DF_MacroInt.dropna(
        subset=[
            "CN_GOV_BOND_YIELD_2Y",
            "CN_GOV_BOND_YIELD_10Y",
            "US_GOV_BOND_YIELD_2Y",
            "US_GOV_BOND_YIELD_10Y",
        ],
        how="all",
    ).sort_values("TRADE_DATE").reset_index(drop=True)
    return DF_MacroInt


def main() -> dict:
    ensure_base_directories()
    run_date = datetime.now().strftime("%Y%m%d")

    DF_MacroInt = fetch_macro_rate_df()
    output_path = build_dated_file_path(
        folder_path=RAW_ROOT,
        stem_name="macro_rate_int",
        date_text=run_date,
        suffix=".csv",
    )
    DF_MacroInt.to_csv(output_path, index=False, encoding="utf-8-sig")

    summary_dict = {
        "RUN_DATE": run_date,
        "ROW_COUNT": int(len(DF_MacroInt)),
        "START_DATE": DF_MacroInt["TRADE_DATE"].min().strftime("%Y-%m-%d"),
        "END_DATE": DF_MacroInt["TRADE_DATE"].max().strftime("%Y-%m-%d"),
        "COLUMN_LIST": DF_MacroInt.columns.tolist(),
        "OUTPUT_FILE": str(output_path),
    }
    summary_path = build_dated_file_path(
        folder_path=RAW_ROOT,
        stem_name="macro_rate_fetch_summary_int",
        date_text=run_date,
        suffix=".json",
    )
    summary_path.write_text(
        json.dumps(summary_dict, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    append_text_log(
        log_path=PROJECT_ROOT / "logs" / "workflow.log",
        message_text=f"Macro rate fetched -> {output_path}",
    )
    return summary_dict


if __name__ == "__main__":
    Summary = main()
    print(json.dumps(Summary, ensure_ascii=False, indent=2))
