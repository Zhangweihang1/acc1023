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

# Make direct script execution work in PyCharm and terminal.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.initiation.init_env import ensure_base_directories
from src.utils.log_utils import append_text_log
from src.utils.path_utils import RAW_ROOT, build_dated_file_path


UNIVERSE_SIZE = 150
UNIVERSE_LIQUIDITY_FIELD = "成交额"


def convert_to_ts_code(raw_code: str) -> str:
    lower_code = str(raw_code).lower()
    if lower_code.startswith("sh"):
        return f"{lower_code[2:].upper()}.SH"
    if lower_code.startswith("sz"):
        return f"{lower_code[2:].upper()}.SZ"
    return lower_code.upper()


def fetch_spot_snapshot() -> pd.DataFrame:
    DF_SpotRaw = ak.stock_zh_a_spot()
    return DF_SpotRaw


def filter_curated_universe(DF_SpotRaw: pd.DataFrame) -> pd.DataFrame:
    DF_Spot = DF_SpotRaw.copy()
    DF_Spot["代码"] = DF_Spot["代码"].astype(str)
    DF_Spot["名称"] = DF_Spot["名称"].astype(str)
    DF_Spot[UNIVERSE_LIQUIDITY_FIELD] = pd.to_numeric(
        DF_Spot[UNIVERSE_LIQUIDITY_FIELD], errors="coerce"
    )

    MarketMask = DF_Spot["代码"].str.startswith(("sh", "sz"))
    NameMask = ~DF_Spot["名称"].str.contains("ST|退", regex=True, na=False)
    LiquidityMask = DF_Spot[UNIVERSE_LIQUIDITY_FIELD].notna()

    DF_Filtered = DF_Spot.loc[MarketMask & NameMask & LiquidityMask].copy()
    DF_Filtered = DF_Filtered.sort_values(
        by=UNIVERSE_LIQUIDITY_FIELD, ascending=False
    ).head(UNIVERSE_SIZE)
    DF_Filtered["TS_CODE"] = DF_Filtered["代码"].map(convert_to_ts_code)
    DF_Filtered["SEC_NAME"] = DF_Filtered["名称"]
    DF_Filtered["LIQUIDITY_RANK"] = range(1, len(DF_Filtered) + 1)
    DF_Filtered["UNIVERSE_DATE"] = datetime.now().strftime("%Y%m%d")
    DF_UniverseInt = DF_Filtered[
        [
            "TS_CODE",
            "SEC_NAME",
            "代码",
            "名称",
            UNIVERSE_LIQUIDITY_FIELD,
            "LIQUIDITY_RANK",
            "UNIVERSE_DATE",
        ]
    ].rename(
        columns={
            "代码": "RAW_CODE",
            "名称": "RAW_NAME",
            UNIVERSE_LIQUIDITY_FIELD: "TURNOVER_AMOUNT",
        }
    )
    return DF_UniverseInt


def save_universe_metadata(meta_path: Path, DF_UniverseInt: pd.DataFrame) -> None:
    metadata = {
        "RUN_DATE": datetime.now().strftime("%Y%m%d"),
        "ROUTE_MODE": "B_B_LIGHTWEIGHT",
        "UNIVERSE_SIZE": int(len(DF_UniverseInt)),
        "UNIVERSE_LIQUIDITY_FIELD": UNIVERSE_LIQUIDITY_FIELD,
        "FILTER_RULES": [
            "MARKET in sh/sz",
            "exclude names containing ST or 退",
            "rank by 成交额 descending",
            f"keep top {UNIVERSE_SIZE}",
        ],
    }
    meta_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> Path:
    ensure_base_directories()
    RunDate = datetime.now().strftime("%Y%m%d")
    OutputPath = build_dated_file_path(
        folder_path=RAW_ROOT,
        stem_name="universe_int",
        date_text=RunDate,
        suffix=".csv",
    )
    MetadataPath = build_dated_file_path(
        folder_path=RAW_ROOT,
        stem_name="universe_int_meta",
        date_text=RunDate,
        suffix=".json",
    )
    DF_SpotRaw = fetch_spot_snapshot()
    DF_UniverseInt = filter_curated_universe(DF_SpotRaw=DF_SpotRaw)
    DF_UniverseInt.to_csv(OutputPath, index=False, encoding="utf-8-sig")
    save_universe_metadata(meta_path=MetadataPath, DF_UniverseInt=DF_UniverseInt)
    append_text_log(
        log_path=Path("logs") / "workflow.log",
        message_text=f"Universe built with {len(DF_UniverseInt)} rows at {OutputPath}",
    )
    return OutputPath


if __name__ == "__main__":
    SavedPath = main()
    print(f"Saved: {SavedPath}")
