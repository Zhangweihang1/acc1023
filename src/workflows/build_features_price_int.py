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

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.initiation.init_env import ensure_base_directories
from src.utils.log_utils import append_text_log
from src.utils.path_utils import FEATURE_ROOT, RAW_ROOT, build_dated_file_path


def find_latest_target_panel_file() -> Path:
    candidate_list = sorted(FEATURE_ROOT.glob("target_panel_int_*.csv"))
    if not candidate_list:
        raise FileNotFoundError("No target_panel_int file found in data/feature_store.")
    return candidate_list[-1]


def load_target_panel(panel_path: Path) -> pd.DataFrame:
    DF_TargetInt = pd.read_csv(panel_path, encoding="utf-8-sig")
    DF_TargetInt["TRADE_DATE"] = pd.to_datetime(DF_TargetInt["TRADE_DATE"])
    return DF_TargetInt


def list_fund_flow_files() -> list[Path]:
    flow_root = RAW_ROOT / "fund_flow_individual"
    return sorted(flow_root.glob("fund_flow_individual_int_*.csv"))


def find_latest_macro_rate_file() -> Path | None:
    candidate_list = sorted(RAW_ROOT.glob("macro_rate_int_*.csv"))
    if not candidate_list:
        return None
    return candidate_list[-1]


def load_and_merge_fund_flow(DF_FeatureInt: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    flow_file_list = list_fund_flow_files()
    if not flow_file_list:
        return DF_FeatureInt, []

    frame_list: list[pd.DataFrame] = []
    for file_path in flow_file_list:
        DF_FlowInt = pd.read_csv(file_path, encoding="utf-8-sig")
        DF_FlowInt["TRADE_DATE"] = pd.to_datetime(DF_FlowInt["TRADE_DATE"])
        frame_list.append(DF_FlowInt)
    DF_FlowPanelInt = pd.concat(frame_list, ignore_index=True)
    DF_FlowPanelInt = DF_FlowPanelInt.sort_values(["TS_CODE", "TRADE_DATE"]).reset_index(drop=True)

    merge_column_list = [
        "TRADE_DATE",
        "TS_CODE",
        "MAIN_NET_INFLOW",
        "MAIN_NET_INFLOW_RATIO",
        "XL_NET_INFLOW",
        "L_NET_INFLOW",
        "M_NET_INFLOW",
        "S_NET_INFLOW",
    ]
    DF_MergedInt = DF_FeatureInt.merge(
        DF_FlowPanelInt[merge_column_list],
        on=["TRADE_DATE", "TS_CODE"],
        how="left",
    )
    GroupObject = DF_MergedInt.groupby("TS_CODE")
    DF_MergedInt["MAIN_NET_INFLOW_MA_5"] = GroupObject["MAIN_NET_INFLOW"].transform(
        lambda series: series.rolling(5).mean()
    )
    DF_MergedInt["MAIN_NET_INFLOW_RATIO_MA_5"] = GroupObject["MAIN_NET_INFLOW_RATIO"].transform(
        lambda series: series.rolling(5).mean()
    )
    merged_feature_list = [
        "MAIN_NET_INFLOW",
        "MAIN_NET_INFLOW_RATIO",
        "XL_NET_INFLOW",
        "L_NET_INFLOW",
        "M_NET_INFLOW",
        "S_NET_INFLOW",
        "MAIN_NET_INFLOW_MA_5",
        "MAIN_NET_INFLOW_RATIO_MA_5",
    ]
    return DF_MergedInt, merged_feature_list


def load_and_merge_macro_rate(DF_FeatureInt: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    macro_path = find_latest_macro_rate_file()
    if macro_path is None:
        return DF_FeatureInt, []

    DF_MacroInt = pd.read_csv(macro_path, encoding="utf-8-sig")
    DF_MacroInt["TRADE_DATE"] = pd.to_datetime(DF_MacroInt["TRADE_DATE"])
    DF_MacroInt = DF_MacroInt.sort_values("TRADE_DATE").drop_duplicates(
        subset=["TRADE_DATE"], keep="last"
    ).reset_index(drop=True)

    DF_MacroInt["CN_US_10Y_SPREAD"] = (
        DF_MacroInt["CN_GOV_BOND_YIELD_10Y"] - DF_MacroInt["US_GOV_BOND_YIELD_10Y"]
    )
    DF_MacroInt["CN_US_2Y_SPREAD"] = (
        DF_MacroInt["CN_GOV_BOND_YIELD_2Y"] - DF_MacroInt["US_GOV_BOND_YIELD_2Y"]
    )
    DF_MacroInt["CN_GOV_BOND_YIELD_10Y_CHG_5"] = (
        DF_MacroInt["CN_GOV_BOND_YIELD_10Y"] - DF_MacroInt["CN_GOV_BOND_YIELD_10Y"].shift(5)
    )
    DF_MacroInt["US_GOV_BOND_YIELD_10Y_CHG_5"] = (
        DF_MacroInt["US_GOV_BOND_YIELD_10Y"] - DF_MacroInt["US_GOV_BOND_YIELD_10Y"].shift(5)
    )
    DF_MacroInt["CN_YIELD_CURVE_10Y_2Y_CHG_5"] = (
        DF_MacroInt["CN_YIELD_CURVE_10Y_2Y"] - DF_MacroInt["CN_YIELD_CURVE_10Y_2Y"].shift(5)
    )
    DF_MacroInt["US_YIELD_CURVE_10Y_2Y_CHG_5"] = (
        DF_MacroInt["US_YIELD_CURVE_10Y_2Y"] - DF_MacroInt["US_YIELD_CURVE_10Y_2Y"].shift(5)
    )

    DF_MergedInt = pd.merge_asof(
        DF_FeatureInt.sort_values("TRADE_DATE"),
        DF_MacroInt.sort_values("TRADE_DATE"),
        on="TRADE_DATE",
        direction="backward",
        allow_exact_matches=True,
    )
    merged_feature_list = [
        "CN_GOV_BOND_YIELD_2Y",
        "CN_GOV_BOND_YIELD_5Y",
        "CN_GOV_BOND_YIELD_10Y",
        "CN_GOV_BOND_YIELD_30Y",
        "CN_YIELD_CURVE_10Y_2Y",
        "US_GOV_BOND_YIELD_2Y",
        "US_GOV_BOND_YIELD_5Y",
        "US_GOV_BOND_YIELD_10Y",
        "US_GOV_BOND_YIELD_30Y",
        "US_YIELD_CURVE_10Y_2Y",
        "CN_US_10Y_SPREAD",
        "CN_US_2Y_SPREAD",
        "CN_GOV_BOND_YIELD_10Y_CHG_5",
        "US_GOV_BOND_YIELD_10Y_CHG_5",
        "CN_YIELD_CURVE_10Y_2Y_CHG_5",
        "US_YIELD_CURVE_10Y_2Y_CHG_5",
    ]
    return DF_MergedInt, merged_feature_list


def build_price_features(DF_TargetInt: pd.DataFrame) -> pd.DataFrame:
    DF_FeatureInt = DF_TargetInt.copy()
    GroupObject = DF_FeatureInt.groupby("TS_CODE")

    DF_FeatureInt["RET_1"] = GroupObject["RET"].shift(1)
    DF_FeatureInt["RET_5"] = (
        GroupObject["CLOSE"].pct_change(periods=5)
    )
    DF_FeatureInt["RET_20"] = (
        GroupObject["CLOSE"].pct_change(periods=20)
    )
    DF_FeatureInt["VOLATILITY_5"] = GroupObject["LOG_RET"].transform(
        lambda series: np.sqrt((series.pow(2)).rolling(5).mean())
    )
    DF_FeatureInt["VOLATILITY_20"] = GroupObject["LOG_RET"].transform(
        lambda series: np.sqrt((series.pow(2)).rolling(20).mean())
    )
    DF_FeatureInt["AMOUNT_MA_5"] = GroupObject["AMOUNT"].transform(
        lambda series: series.rolling(5).mean()
    )
    DF_FeatureInt["TURNOVER_MA_5"] = GroupObject["TURNOVER"].transform(
        lambda series: series.rolling(5).mean()
    )
    DF_FeatureInt["RANGE_PCT"] = (
        (DF_FeatureInt["HIGH"] - DF_FeatureInt["LOW"]) / DF_FeatureInt["CLOSE"]
    )
    DF_FeatureInt["GAP_PCT"] = (
        (DF_FeatureInt["OPEN"] - GroupObject["CLOSE"].shift(1))
        / GroupObject["CLOSE"].shift(1)
    )
    return DF_FeatureInt


def main() -> dict:
    ensure_base_directories()
    run_date = datetime.now().strftime("%Y%m%d")
    input_path = find_latest_target_panel_file()
    DF_TargetInt = load_target_panel(panel_path=input_path)
    DF_FeatureInt = build_price_features(DF_TargetInt=DF_TargetInt)
    DF_FeatureInt, fund_flow_feature_list = load_and_merge_fund_flow(DF_FeatureInt=DF_FeatureInt)
    DF_FeatureInt, macro_feature_list = load_and_merge_macro_rate(DF_FeatureInt=DF_FeatureInt)
    merged_feature_list = fund_flow_feature_list + macro_feature_list

    output_path = build_dated_file_path(
        folder_path=FEATURE_ROOT,
        stem_name="feature_panel_int",
        date_text=run_date,
        suffix=".csv",
    )
    DF_FeatureInt.to_csv(output_path, index=False, encoding="utf-8-sig")

    summary_dict = {
        "RUN_DATE": run_date,
        "INPUT_FILE": str(input_path),
        "ROW_COUNT": int(len(DF_FeatureInt)),
        "STOCK_COUNT": int(DF_FeatureInt["TS_CODE"].nunique()),
        "FEATURE_COLUMNS": [
            "RET_1",
            "RET_5",
            "RET_20",
            "VOLATILITY_5",
            "VOLATILITY_20",
            "AMOUNT_MA_5",
            "TURNOVER_MA_5",
            "RANGE_PCT",
            "GAP_PCT",
        ] + merged_feature_list,
        "OUTPUT_FILE": str(output_path),
    }
    summary_path = build_dated_file_path(
        folder_path=FEATURE_ROOT,
        stem_name="feature_panel_int_summary",
        date_text=run_date,
        suffix=".json",
    )
    summary_path.write_text(
        json.dumps(summary_dict, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    append_text_log(
        log_path=PROJECT_ROOT / "logs" / "workflow.log",
        message_text=f"Feature panel built -> {output_path}",
    )
    return summary_dict


if __name__ == "__main__":
    Summary = main()
    print(json.dumps(Summary, ensure_ascii=False, indent=2))
