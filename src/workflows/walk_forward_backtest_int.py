from __future__ import annotations

"""
initiation
- environment check
- import packages
- unified path management
- portable configuration
"""

from datetime import datetime
import argparse
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.initiation.init_env import ensure_base_directories
from src.utils.log_utils import append_text_log
from src.utils.path_utils import FEATURE_ROOT, MODEL_ROOT, PREDICTION_ROOT, build_dated_file_path


FEATURE_COLUMN_LIST = [
    "RET_1",
    "RET_5",
    "RET_20",
    "VOLATILITY_5",
    "VOLATILITY_20",
    "AMOUNT_MA_5",
    "TURNOVER_MA_5",
    "RANGE_PCT",
    "GAP_PCT",
    "MAIN_NET_INFLOW",
    "MAIN_NET_INFLOW_RATIO",
    "XL_NET_INFLOW",
    "L_NET_INFLOW",
    "M_NET_INFLOW",
    "S_NET_INFLOW",
    "MAIN_NET_INFLOW_MA_5",
    "MAIN_NET_INFLOW_RATIO_MA_5",
    "CN_GOV_BOND_YIELD_10Y",
    "US_GOV_BOND_YIELD_10Y",
    "CN_US_10Y_SPREAD",
    "CN_GOV_BOND_YIELD_10Y_CHG_5",
    "US_GOV_BOND_YIELD_10Y_CHG_5",
    "CN_YIELD_CURVE_10Y_2Y_CHG_5",
]
TARGET_COLUMN = "FUTURE_RV_5"
MIN_FEATURE_COVERAGE_RATIO = 0.20


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a minimal walk-forward backtest on the latest feature panel."
    )
    parser.add_argument("--min-train-dates", type=int, default=60)
    parser.add_argument("--test-window", type=int, default=10)
    parser.add_argument("--step-size", type=int, default=10)
    return parser.parse_args()


def find_latest_feature_panel_file() -> Path:
    candidate_list = sorted(FEATURE_ROOT.glob("feature_panel_int_*.csv"))
    if not candidate_list:
        raise FileNotFoundError("No feature_panel_int file found in data/feature_store.")
    return candidate_list[-1]


def load_feature_panel(panel_path: Path) -> pd.DataFrame:
    DF_FeatureInt = pd.read_csv(panel_path, encoding="utf-8-sig")
    DF_FeatureInt["TRADE_DATE"] = pd.to_datetime(DF_FeatureInt["TRADE_DATE"])
    return DF_FeatureInt


def build_model_dataset(DF_FeatureInt: pd.DataFrame) -> pd.DataFrame:
    DF_ModelInt = DF_FeatureInt.copy()
    candidate_feature_list = [
        column_name for column_name in FEATURE_COLUMN_LIST if column_name in DF_ModelInt.columns
    ]
    available_feature_list = [
        column_name
        for column_name in candidate_feature_list
        if float(DF_ModelInt[column_name].notna().mean()) >= MIN_FEATURE_COVERAGE_RATIO
    ]
    if not available_feature_list:
        raise ValueError("No feature columns passed the minimum coverage threshold.")

    DF_ModelInt = DF_ModelInt.dropna(subset=available_feature_list + [TARGET_COLUMN]).copy()
    DF_ModelInt = DF_ModelInt.sort_values(by=["TRADE_DATE", "TS_CODE"]).reset_index(drop=True)
    DF_ModelInt.attrs["FEATURE_COLUMN_LIST"] = available_feature_list
    DF_ModelInt.attrs["DROPPED_FEATURE_COLUMN_LIST"] = [
        column_name
        for column_name in candidate_feature_list
        if column_name not in available_feature_list
    ]
    return DF_ModelInt


def build_fold_start_indices(
    unique_date_list: list[pd.Timestamp],
    min_train_dates: int,
    test_window: int,
    step_size: int,
) -> list[int]:
    start_index_list: list[int] = []
    fold_start_index = min_train_dates
    max_start_index = len(unique_date_list) - test_window
    while fold_start_index <= max_start_index:
        start_index_list.append(fold_start_index)
        fold_start_index += step_size
    if not start_index_list:
        raise ValueError(
            "Insufficient date coverage for walk-forward backtest. "
            "Try lowering --min-train-dates or --test-window."
        )
    return start_index_list


def compute_metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict[str, float]:
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": rmse,
        "R2": float(r2_score(y_true, y_pred)),
    }


def run_walk_forward(
    DF_ModelInt: pd.DataFrame,
    feature_column_list: list[str],
    min_train_dates: int,
    test_window: int,
    step_size: int,
) -> tuple[pd.DataFrame, list[dict], dict[str, float]]:
    unique_date_list = sorted(DF_ModelInt["TRADE_DATE"].unique())
    start_index_list = build_fold_start_indices(
        unique_date_list=unique_date_list,
        min_train_dates=min_train_dates,
        test_window=test_window,
        step_size=step_size,
    )

    prediction_frame_list: list[pd.DataFrame] = []
    fold_summary_list: list[dict] = []

    for fold_number, start_index in enumerate(start_index_list, start=1):
        train_end_date = unique_date_list[start_index - 1]
        test_date_list = unique_date_list[start_index : start_index + test_window]
        test_start_date = test_date_list[0]
        test_end_date = test_date_list[-1]

        DF_TrainInt = DF_ModelInt.loc[DF_ModelInt["TRADE_DATE"] <= train_end_date].copy()
        DF_TestInt = DF_ModelInt.loc[DF_ModelInt["TRADE_DATE"].isin(test_date_list)].copy()

        Model = LinearRegression()
        Model.fit(DF_TrainInt[feature_column_list], DF_TrainInt[TARGET_COLUMN])
        TestPred = Model.predict(DF_TestInt[feature_column_list])
        fold_metrics = compute_metrics(DF_TestInt[TARGET_COLUMN], TestPred)

        DF_FoldPredictionInt = DF_TestInt[["TRADE_DATE", "TS_CODE", TARGET_COLUMN]].copy()
        DF_FoldPredictionInt["PRED_FUTURE_RV_5"] = TestPred
        DF_FoldPredictionInt["FOLD_ID"] = fold_number
        prediction_frame_list.append(DF_FoldPredictionInt)

        fold_summary_list.append(
            {
                "FOLD_ID": fold_number,
                "TRAIN_END_DATE": str(pd.Timestamp(train_end_date).date()),
                "TEST_START_DATE": str(pd.Timestamp(test_start_date).date()),
                "TEST_END_DATE": str(pd.Timestamp(test_end_date).date()),
                "TRAIN_ROWS": int(len(DF_TrainInt)),
                "TEST_ROWS": int(len(DF_TestInt)),
                "TEST_METRICS": fold_metrics,
            }
        )

    DF_WalkForwardPredInt = pd.concat(prediction_frame_list, ignore_index=True)
    aggregate_metrics = compute_metrics(
        DF_WalkForwardPredInt[TARGET_COLUMN],
        DF_WalkForwardPredInt["PRED_FUTURE_RV_5"].to_numpy(),
    )
    return DF_WalkForwardPredInt, fold_summary_list, aggregate_metrics


def main() -> dict:
    ensure_base_directories()
    args = parse_args()
    run_date = datetime.now().strftime("%Y%m%d")
    input_path = find_latest_feature_panel_file()
    DF_FeatureInt = load_feature_panel(panel_path=input_path)
    DF_ModelInt = build_model_dataset(DF_FeatureInt=DF_FeatureInt)
    feature_column_list = DF_ModelInt.attrs["FEATURE_COLUMN_LIST"]
    dropped_feature_column_list = DF_ModelInt.attrs["DROPPED_FEATURE_COLUMN_LIST"]

    DF_WalkForwardPredInt, fold_summary_list, aggregate_metrics = run_walk_forward(
        DF_ModelInt=DF_ModelInt,
        feature_column_list=feature_column_list,
        min_train_dates=args.min_train_dates,
        test_window=args.test_window,
        step_size=args.step_size,
    )

    prediction_path = build_dated_file_path(
        folder_path=PREDICTION_ROOT,
        stem_name="walk_forward_prediction_int",
        date_text=run_date,
        suffix=".csv",
    )
    DF_WalkForwardPredInt.to_csv(prediction_path, index=False, encoding="utf-8-sig")

    summary_dict = {
        "RUN_DATE": run_date,
        "INPUT_FILE": str(input_path),
        "MODEL_NAME": "LINEAR_REGRESSION_WALK_FORWARD",
        "TOTAL_ROWS": int(len(DF_ModelInt)),
        "TOTAL_DATES": int(DF_ModelInt["TRADE_DATE"].nunique()),
        "TOTAL_STOCKS": int(DF_ModelInt["TS_CODE"].nunique()),
        "FEATURE_COLUMNS": feature_column_list,
        "DROPPED_FEATURE_COLUMNS": dropped_feature_column_list,
        "MIN_FEATURE_COVERAGE_RATIO": MIN_FEATURE_COVERAGE_RATIO,
        "MIN_TRAIN_DATES": int(args.min_train_dates),
        "TEST_WINDOW": int(args.test_window),
        "STEP_SIZE": int(args.step_size),
        "FOLD_COUNT": int(len(fold_summary_list)),
        "AGGREGATE_TEST_METRICS": aggregate_metrics,
        "FOLD_SUMMARY": fold_summary_list,
        "PREDICTION_FILE": str(prediction_path),
    }
    summary_path = build_dated_file_path(
        folder_path=MODEL_ROOT,
        stem_name="walk_forward_summary_int",
        date_text=run_date,
        suffix=".json",
    )
    summary_path.write_text(
        json.dumps(summary_dict, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    append_text_log(
        log_path=PROJECT_ROOT / "logs" / "workflow.log",
        message_text=f"Walk-forward backtest completed -> {summary_path}",
    )
    return summary_dict


if __name__ == "__main__":
    Summary = main()
    print(json.dumps(Summary, ensure_ascii=False, indent=2))
