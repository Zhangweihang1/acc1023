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
import time

import akshare as ak
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.initiation.init_env import ensure_base_directories
from src.utils.log_utils import append_text_log
from src.utils.path_utils import FEATURE_ROOT, RAW_ROOT, build_dated_file_path


FLOW_COLUMN_MAP = {
    "日期": "TRADE_DATE",
    "收盘价": "FLOW_CLOSE",
    "涨跌幅": "FLOW_PCT_CHG",
    "主力净流入-净额": "MAIN_NET_INFLOW",
    "主力净流入-净占比": "MAIN_NET_INFLOW_RATIO",
    "超大单净流入-净额": "XL_NET_INFLOW",
    "超大单净流入-净占比": "XL_NET_INFLOW_RATIO",
    "大单净流入-净额": "L_NET_INFLOW",
    "大单净流入-净占比": "L_NET_INFLOW_RATIO",
    "中单净流入-净额": "M_NET_INFLOW",
    "中单净流入-净占比": "M_NET_INFLOW_RATIO",
    "小单净流入-净额": "S_NET_INFLOW",
    "小单净流入-净占比": "S_NET_INFLOW_RATIO",
}


def find_latest_target_panel_file() -> Path:
    candidate_list = sorted(FEATURE_ROOT.glob("target_panel_int_*.csv"))
    if not candidate_list:
        raise FileNotFoundError("No target_panel_int file found in data/feature_store.")
    return candidate_list[-1]


def load_sample_stock_list(panel_path: Path) -> list[str]:
    DF_TargetInt = pd.read_csv(panel_path, encoding="utf-8-sig")
    return sorted(DF_TargetInt["TS_CODE"].dropna().astype(str).unique().tolist())


def convert_ts_code_to_market_stock(ts_code: str) -> tuple[str, str]:
    code_text, market_text = ts_code.split(".")
    return market_text.lower(), code_text


def fetch_one_flow_df(ts_code: str) -> pd.DataFrame:
    market_text, stock_text = convert_ts_code_to_market_stock(ts_code=ts_code)
    DF_FlowRaw = ak.stock_individual_fund_flow(stock=stock_text, market=market_text)
    DF_FlowInt = DF_FlowRaw.rename(columns=FLOW_COLUMN_MAP).copy()
    DF_FlowInt["TRADE_DATE"] = pd.to_datetime(DF_FlowInt["TRADE_DATE"])
    numeric_column_list = [
        column_name for column_name in DF_FlowInt.columns if column_name != "TRADE_DATE"
    ]
    for column_name in numeric_column_list:
        DF_FlowInt[column_name] = pd.to_numeric(DF_FlowInt[column_name], errors="coerce")
    DF_FlowInt["TS_CODE"] = ts_code
    return DF_FlowInt


def main(limit_count: int | None = None) -> dict:
    ensure_base_directories()
    run_date = datetime.now().strftime("%Y%m%d")
    target_panel_path = find_latest_target_panel_file()
    ts_code_list = load_sample_stock_list(panel_path=target_panel_path)
    if limit_count is not None:
        ts_code_list = ts_code_list[:limit_count]

    flow_root = RAW_ROOT / "fund_flow_individual"
    flow_root.mkdir(parents=True, exist_ok=True)

    success_count = 0
    failure_list: list[dict[str, str]] = []
    output_file_list: list[str] = []

    for ts_code in ts_code_list:
        try:
            DF_FlowInt = fetch_one_flow_df(ts_code=ts_code)
            output_path = flow_root / f"fund_flow_individual_int_{ts_code}_{run_date}.csv"
            DF_FlowInt.to_csv(output_path, index=False, encoding="utf-8-sig")
            output_file_list.append(str(output_path))
            success_count += 1
            append_text_log(
                log_path=PROJECT_ROOT / "logs" / "workflow.log",
                message_text=f"Fund flow fetched for {ts_code} -> {output_path}",
            )
            time.sleep(0.2)
        except Exception as exc:
            failure_list.append({"TS_CODE": ts_code, "ERROR": str(exc)})
            append_text_log(
                log_path=PROJECT_ROOT / "logs" / "workflow.log",
                message_text=f"Fund flow fetch failed for {ts_code}: {exc}",
            )

    summary_dict = {
        "RUN_DATE": run_date,
        "INPUT_FILE": str(target_panel_path),
        "REQUESTED_STOCK_COUNT": len(ts_code_list),
        "SUCCESS_COUNT": success_count,
        "FAILURE_COUNT": len(failure_list),
        "OUTPUT_FILE_COUNT": len(output_file_list),
        "FAILURES": failure_list,
    }
    summary_path = build_dated_file_path(
        folder_path=RAW_ROOT,
        stem_name="fund_flow_fetch_summary_int",
        date_text=run_date,
        suffix=".json",
    )
    summary_path.write_text(
        json.dumps(summary_dict, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary_dict


if __name__ == "__main__":
    Summary = main()
    print(json.dumps(Summary, ensure_ascii=False, indent=2))
