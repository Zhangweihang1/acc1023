from __future__ import annotations

"""
initiation
- environment check
- import packages
- unified path management
- portable configuration
"""

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
import time

import akshare as ak
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.initiation.init_env import ensure_base_directories
from src.utils.log_utils import append_text_log
from src.utils.path_utils import RAW_ROOT, build_dated_file_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch daily price data for the curated universe."
    )
    parser.add_argument(
        "--mode",
        choices=("full", "sample"),
        default=None,
        help="Fetch mode. Default comes from config and is full.",
    )
    parser.add_argument(
        "--limit-count",
        type=int,
        default=None,
        help="Optional stock cap for sample mode.",
    )
    return parser


def load_project_config() -> dict:
    config_path = PROJECT_ROOT / "config" / "project_config.yaml"
    with config_path.open("r", encoding="utf-8") as file_handle:
        config_dict = yaml.safe_load(file_handle)
    return config_dict


def find_latest_universe_file() -> Path:
    candidate_list = sorted(RAW_ROOT.glob("universe_int_*.csv"))
    if not candidate_list:
        raise FileNotFoundError("No universe_int CSV file found in data/raw.")
    return candidate_list[-1]


def convert_ts_code_to_ak_symbol(ts_code: str) -> str:
    code_text, market_text = ts_code.split(".")
    if market_text.upper() == "SH":
        return f"sh{code_text}"
    if market_text.upper() == "SZ":
        return f"sz{code_text}"
    raise ValueError(f"Unsupported market in TS_CODE: {ts_code}")


def load_universe_df(universe_path: Path) -> pd.DataFrame:
    DF_UniverseInt = pd.read_csv(universe_path, encoding="utf-8-sig")
    DF_UniverseInt["TS_CODE"] = DF_UniverseInt["TS_CODE"].astype(str)
    return DF_UniverseInt


def fetch_one_price_df(
    ts_code: str,
    start_date: str,
    end_date: str,
    adjust_mode: str,
) -> pd.DataFrame:
    ak_symbol = convert_ts_code_to_ak_symbol(ts_code=ts_code)
    DF_PriceRaw = ak.stock_zh_a_daily(
        symbol=ak_symbol,
        start_date=start_date,
        end_date=end_date,
        adjust=adjust_mode,
    )
    if DF_PriceRaw.empty:
        return DF_PriceRaw
    DF_Price = DF_PriceRaw.copy()
    DF_Price["date"] = pd.to_datetime(DF_Price["date"])
    DF_Price["TS_CODE"] = ts_code
    DF_Price["AK_SYMBOL"] = ak_symbol
    DF_Price.columns = [
        "TRADE_DATE" if column_name == "date" else column_name.upper()
        for column_name in DF_Price.columns
    ]
    return DF_Price


def save_price_df(price_df: pd.DataFrame, output_path: Path) -> None:
    price_df.to_csv(output_path, index=False, encoding="utf-8-sig")


def resolve_run_mode(
    config_dict: dict,
    cli_mode: str | None,
) -> str:
    default_mode = str(
        config_dict.get("PRICE_FETCH", {}).get("DEFAULT_MODE", "full")
    ).lower()
    run_mode = str(cli_mode or default_mode).lower()
    if run_mode not in {"full", "sample"}:
        raise ValueError(f"Unsupported price fetch mode: {run_mode}")
    return run_mode


def resolve_limit_count(
    config_dict: dict,
    run_mode: str,
    cli_limit_count: int | None,
) -> int | None:
    price_fetch_config = config_dict.get("PRICE_FETCH", {})
    if run_mode == "full":
        return int(price_fetch_config.get("FULL_LIMIT", 150))
    if cli_limit_count is not None:
        return int(cli_limit_count)
    return int(price_fetch_config.get("SAMPLE_LIMIT", 5))


def main(
    run_mode: str | None = None,
    limit_count: int | None = None,
) -> dict:
    ensure_base_directories()
    config_dict = load_project_config()
    resolved_run_mode = resolve_run_mode(config_dict=config_dict, cli_mode=run_mode)
    resolved_limit_count = resolve_limit_count(
        config_dict=config_dict,
        run_mode=resolved_run_mode,
        cli_limit_count=limit_count,
    )
    universe_path = find_latest_universe_file()
    DF_UniverseInt = load_universe_df(universe_path=universe_path)
    if resolved_limit_count is not None:
        DF_UniverseInt = DF_UniverseInt.head(resolved_limit_count).copy()

    run_date = datetime.now().strftime("%Y%m%d")
    price_root = RAW_ROOT / "price_daily"
    price_root.mkdir(parents=True, exist_ok=True)

    start_date = config_dict["PRICE"]["START_DATE"]
    end_date = config_dict["PRICE"]["END_DATE"]
    adjust_mode = config_dict["PRICE"]["ADJUST_MODE"]
    sleep_seconds = float(
        config_dict.get("PRICE_FETCH", {}).get("PER_STOCK_SLEEP_SECONDS", 0.2)
    )

    success_count = 0
    failure_list: list[dict[str, str]] = []
    output_file_list: list[str] = []

    for row_item in DF_UniverseInt.itertuples(index=False):
        ts_code = str(row_item.TS_CODE)
        try:
            DF_PriceInt = fetch_one_price_df(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
                adjust_mode=adjust_mode,
            )
            if DF_PriceInt.empty:
                raise ValueError("Returned empty price dataframe.")

            output_path = price_root / f"price_daily_int_{ts_code}_{run_date}.csv"
            save_price_df(price_df=DF_PriceInt, output_path=output_path)
            output_file_list.append(str(output_path))
            success_count += 1
            append_text_log(
                log_path=PROJECT_ROOT / "logs" / "workflow.log",
                message_text=(
                    f"Price fetched ({resolved_run_mode}) for {ts_code} -> {output_path}"
                ),
            )
            time.sleep(sleep_seconds)
        except Exception as exc:
            failure_item = {"TS_CODE": ts_code, "ERROR": str(exc)}
            failure_list.append(failure_item)
            append_text_log(
                log_path=PROJECT_ROOT / "logs" / "workflow.log",
                message_text=f"Price fetch failed ({resolved_run_mode}) for {ts_code}: {exc}",
            )

    summary_dict = {
        "RUN_DATE": run_date,
        "RUN_MODE": resolved_run_mode.upper(),
        "UNIVERSE_FILE": str(universe_path),
        "ADJUST_MODE": adjust_mode,
        "START_DATE": start_date,
        "END_DATE": end_date,
        "LIMIT_COUNT": resolved_limit_count,
        "INPUT_STOCK_COUNT": int(len(DF_UniverseInt)),
        "SUCCESS_COUNT": success_count,
        "FAILURE_COUNT": len(failure_list),
        "OUTPUT_FILE_COUNT": len(output_file_list),
        "FAILURES": failure_list,
    }

    summary_path = build_dated_file_path(
        folder_path=RAW_ROOT,
        stem_name=f"price_daily_fetch_summary_int_{resolved_run_mode}",
        date_text=run_date,
        suffix=".json",
    )
    summary_path.write_text(
        json.dumps(summary_dict, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary_dict


if __name__ == "__main__":
    Parser = build_arg_parser()
    Args = Parser.parse_args()
    Summary = main(run_mode=Args.mode, limit_count=Args.limit_count)
    print(json.dumps(Summary, ensure_ascii=False, indent=2))
