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
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

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
RIDGE_ALPHA_GRID = [0.01, 0.1, 1.0, 10.0, 100.0]


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


def split_train_test(DF_ModelInt: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    unique_date_list = sorted(DF_ModelInt["TRADE_DATE"].unique())
    split_index = int(len(unique_date_list) * 0.8)
    split_date = unique_date_list[split_index]
    DF_TrainInt = DF_ModelInt.loc[DF_ModelInt["TRADE_DATE"] < split_date].copy()
    DF_TestInt = DF_ModelInt.loc[DF_ModelInt["TRADE_DATE"] >= split_date].copy()
    return DF_TrainInt, DF_TestInt


def split_train_validation(DF_TrainInt: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    unique_date_list = sorted(DF_TrainInt["TRADE_DATE"].unique())
    split_index = int(len(unique_date_list) * 0.8)
    split_date = unique_date_list[split_index]
    DF_SubTrainInt = DF_TrainInt.loc[DF_TrainInt["TRADE_DATE"] < split_date].copy()
    DF_ValidationInt = DF_TrainInt.loc[DF_TrainInt["TRADE_DATE"] >= split_date].copy()
    return DF_SubTrainInt, DF_ValidationInt


def compute_metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict[str, float]:
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": rmse,
        "R2": float(r2_score(y_true, y_pred)),
    }


def build_ridge_pipeline(alpha_value: float) -> Pipeline:
    return Pipeline(
        steps=[
            ("SCALER", StandardScaler()),
            ("RIDGE", Ridge(alpha=alpha_value)),
        ]
    )


def select_best_alpha(
    DF_SubTrainInt: pd.DataFrame,
    DF_ValidationInt: pd.DataFrame,
    feature_column_list: list[str],
) -> tuple[float, list[dict[str, float]]]:
    candidate_result_list: list[dict[str, float]] = []
    best_alpha = RIDGE_ALPHA_GRID[0]
    best_rmse = float("inf")

    for alpha_value in RIDGE_ALPHA_GRID:
        Model = build_ridge_pipeline(alpha_value=alpha_value)
        Model.fit(DF_SubTrainInt[feature_column_list], DF_SubTrainInt[TARGET_COLUMN])
        ValidationPred = Model.predict(DF_ValidationInt[feature_column_list])
        validation_metrics = compute_metrics(DF_ValidationInt[TARGET_COLUMN], ValidationPred)
        candidate_result = {
            "ALPHA": float(alpha_value),
            "VALIDATION_MAE": validation_metrics["MAE"],
            "VALIDATION_RMSE": validation_metrics["RMSE"],
            "VALIDATION_R2": validation_metrics["R2"],
        }
        candidate_result_list.append(candidate_result)
        if validation_metrics["RMSE"] < best_rmse:
            best_rmse = validation_metrics["RMSE"]
            best_alpha = alpha_value

    return float(best_alpha), candidate_result_list


def main() -> dict:
    ensure_base_directories()
    run_date = datetime.now().strftime("%Y%m%d")
    input_path = find_latest_feature_panel_file()
    DF_FeatureInt = load_feature_panel(panel_path=input_path)
    DF_ModelInt = build_model_dataset(DF_FeatureInt=DF_FeatureInt)
    feature_column_list = DF_ModelInt.attrs["FEATURE_COLUMN_LIST"]
    dropped_feature_column_list = DF_ModelInt.attrs["DROPPED_FEATURE_COLUMN_LIST"]
    DF_TrainInt, DF_TestInt = split_train_test(DF_ModelInt=DF_ModelInt)
    DF_SubTrainInt, DF_ValidationInt = split_train_validation(DF_TrainInt=DF_TrainInt)

    best_alpha, validation_result_list = select_best_alpha(
        DF_SubTrainInt=DF_SubTrainInt,
        DF_ValidationInt=DF_ValidationInt,
        feature_column_list=feature_column_list,
    )

    Model = build_ridge_pipeline(alpha_value=best_alpha)
    Model.fit(DF_TrainInt[feature_column_list], DF_TrainInt[TARGET_COLUMN])
    TrainPred = Model.predict(DF_TrainInt[feature_column_list])
    TestPred = Model.predict(DF_TestInt[feature_column_list])

    train_metrics = compute_metrics(DF_TrainInt[TARGET_COLUMN], TrainPred)
    test_metrics = compute_metrics(DF_TestInt[TARGET_COLUMN], TestPred)

    DF_PredictionInt = DF_TestInt[["TRADE_DATE", "TS_CODE", TARGET_COLUMN]].copy()
    DF_PredictionInt["PRED_FUTURE_RV_5"] = TestPred

    prediction_path = build_dated_file_path(
        folder_path=PREDICTION_ROOT,
        stem_name="regularized_prediction_int",
        date_text=run_date,
        suffix=".csv",
    )
    DF_PredictionInt.to_csv(prediction_path, index=False, encoding="utf-8-sig")

    summary_dict = {
        "RUN_DATE": run_date,
        "MODEL_NAME": "RIDGE_REGRESSION",
        "INPUT_FILE": str(input_path),
        "TRAIN_ROWS": int(len(DF_TrainInt)),
        "TEST_ROWS": int(len(DF_TestInt)),
        "SUBTRAIN_ROWS": int(len(DF_SubTrainInt)),
        "VALIDATION_ROWS": int(len(DF_ValidationInt)),
        "FEATURE_COLUMNS": feature_column_list,
        "DROPPED_FEATURE_COLUMNS": dropped_feature_column_list,
        "MIN_FEATURE_COVERAGE_RATIO": MIN_FEATURE_COVERAGE_RATIO,
        "RIDGE_ALPHA_GRID": RIDGE_ALPHA_GRID,
        "BEST_ALPHA": float(best_alpha),
        "VALIDATION_RESULTS": validation_result_list,
        "TRAIN_METRICS": train_metrics,
        "TEST_METRICS": test_metrics,
        "PREDICTION_FILE": str(prediction_path),
    }
    summary_path = build_dated_file_path(
        folder_path=MODEL_ROOT,
        stem_name="regularized_model_summary_int",
        date_text=run_date,
        suffix=".json",
    )
    summary_path.write_text(
        json.dumps(summary_dict, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    append_text_log(
        log_path=PROJECT_ROOT / "logs" / "workflow.log",
        message_text=f"Regularized model trained -> {summary_path}",
    )
    return summary_dict


if __name__ == "__main__":
    Summary = main()
    print(json.dumps(Summary, ensure_ascii=False, indent=2))
