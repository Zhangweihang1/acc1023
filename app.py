from __future__ import annotations

from pathlib import Path
import json
import sys

import akshare as ak
import pandas as pd
import plotly.express as px
import streamlit as st
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.app_ui import page_renderers

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.workflows.build_features_price_int import build_price_features, load_and_merge_macro_rate
from src.workflows.build_targets_int import build_target_columns
from src.workflows.fetch_price_daily_int import fetch_one_price_df, load_project_config
from src.workflows.train_baseline_model_int import (
    TARGET_COLUMN,
    build_model_dataset,
    find_latest_feature_panel_file,
    load_feature_panel,
)


MODEL_ROOT = PROJECT_ROOT / "data" / "model_output"
PREDICTION_ROOT = PROJECT_ROOT / "data" / "predictions"
RAW_ROOT = PROJECT_ROOT / "data" / "raw"
BASKET_ROOT = RAW_ROOT / "basket_registry"
WEIGHTING_OPTION_LIST = ["Equal", "Turnover-Weighted"]
ANALYSIS_SCOPE_OPTION_LIST = ["Coverage Universe", "Current Basket"]
PAGE_OPTION_LIST = [
    "Step 1 | Coverage Universe",
    "Step 2 | Build Research Set",
    "Step 3 | Analyze Current Set",
    "Step 4 | Future Extension",
]
DATE_WINDOW_OPTION_LIST = [
    "Last 30 Days",
    "Last 90 Days",
    "Last 180 Days",
    "Last 252 Days",
    "All History",
    "Custom Range",
]


def find_latest_file(folder_path: Path, pattern_text: str) -> Path | None:
    candidate_list = sorted(folder_path.glob(pattern_text))
    if not candidate_list:
        return None
    return candidate_list[-1]


def get_basket_registry_latest_path() -> Path:
    BASKET_ROOT.mkdir(parents=True, exist_ok=True)
    return BASKET_ROOT / "basket_registry_int_latest.json"


def get_basket_registry_snapshot_path() -> Path:
    BASKET_ROOT.mkdir(parents=True, exist_ok=True)
    return BASKET_ROOT / f"basket_registry_int_{pd.Timestamp.now().strftime('%Y%m%d')}.json"


@st.cache_data
def load_prediction_df(file_path: Path) -> pd.DataFrame:
    DF_PredictionInt = pd.read_csv(file_path, encoding="utf-8-sig")
    DF_PredictionInt["TRADE_DATE"] = pd.to_datetime(DF_PredictionInt["TRADE_DATE"])
    return DF_PredictionInt


@st.cache_data
def load_json_dict(file_path: Path) -> dict:
    return json.loads(file_path.read_text(encoding="utf-8"))


@st.cache_data
def load_universe_df(file_path: Path) -> pd.DataFrame:
    return pd.read_csv(file_path, encoding="utf-8-sig")


@st.cache_data
def load_basket_registry_dict(file_path_text: str) -> dict:
    file_path = Path(file_path_text)
    if not file_path.exists():
        return {"BASKETS": {}, "UPDATED_AT": None}
    return json.loads(file_path.read_text(encoding="utf-8"))


def convert_raw_code_to_ts_code(raw_code: str) -> str:
    raw_code_text = str(raw_code).lower()
    if raw_code_text.startswith("sh"):
        return f"{raw_code_text[2:].upper()}.SH"
    if raw_code_text.startswith("sz"):
        return f"{raw_code_text[2:].upper()}.SZ"
    return raw_code_text.upper()


@st.cache_data(ttl=1800, show_spinner=False)
def load_market_snapshot_df() -> pd.DataFrame:
    DF_MarketRaw = ak.stock_zh_a_spot()
    DF_MarketInt = DF_MarketRaw.copy()
    DF_MarketInt["代码"] = DF_MarketInt["代码"].astype(str)
    DF_MarketInt["名称"] = DF_MarketInt["名称"].astype(str)
    DF_MarketInt["成交额"] = pd.to_numeric(DF_MarketInt["成交额"], errors="coerce")
    DF_MarketInt = DF_MarketInt.loc[
        DF_MarketInt["代码"].str.startswith(("sh", "sz"))
    ].copy()
    DF_MarketInt["TS_CODE"] = DF_MarketInt["代码"].map(convert_raw_code_to_ts_code)
    DF_MarketInt["SEC_NAME"] = DF_MarketInt["名称"]
    DF_MarketInt["TURNOVER_AMOUNT"] = DF_MarketInt["成交额"]
    return DF_MarketInt[
        ["TS_CODE", "SEC_NAME", "代码", "TURNOVER_AMOUNT"]
    ].rename(columns={"代码": "RAW_CODE"})


def build_stock_lookup_df(
    DF_UniverseInt: pd.DataFrame,
    DF_MarketSnapshotInt: pd.DataFrame,
    covered_code_set: set[str],
) -> pd.DataFrame:
    DF_LookupInt = DF_MarketSnapshotInt.merge(
        DF_UniverseInt[["TS_CODE", "LIQUIDITY_RANK", "UNIVERSE_DATE"]],
        on="TS_CODE",
        how="left",
    )
    DF_LookupInt["IS_MODEL_COVERED"] = DF_LookupInt["TS_CODE"].isin(covered_code_set)
    DF_LookupInt["COVERAGE_STATUS"] = DF_LookupInt["IS_MODEL_COVERED"].map(
        {True: "Covered", False: "Live Fetch"}
    )
    DF_LookupInt["STOCK_LABEL"] = (
        DF_LookupInt["TS_CODE"]
        + " | "
        + DF_LookupInt["SEC_NAME"]
        + " | "
        + DF_LookupInt["COVERAGE_STATUS"]
    )
    DF_LookupInt = DF_LookupInt.sort_values(
        by=["IS_MODEL_COVERED", "TURNOVER_AMOUNT", "TS_CODE"],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    return DF_LookupInt


def get_stock_label_map(DF_StockLookupInt: pd.DataFrame) -> dict[str, str]:
    return dict(zip(DF_StockLookupInt["TS_CODE"], DF_StockLookupInt["STOCK_LABEL"]))


def sanitize_basket_code_list(
    basket_code_list: list[str],
    valid_code_list: list[str],
) -> list[str]:
    valid_code_set = set(valid_code_list)
    clean_code_list: list[str] = []
    for ts_code in basket_code_list:
        if ts_code in valid_code_set and ts_code not in clean_code_list:
            clean_code_list.append(ts_code)
    return clean_code_list


def sanitize_basket_name(basket_name: str) -> str:
    safe_text = "".join(
        character
        for character in str(basket_name).strip()
        if character.isalnum() or character in {" ", "-", "_"}
    ).strip()
    return safe_text[:60]


def get_basket_name_option_list(basket_registry_dict: dict) -> list[str]:
    basket_dict = basket_registry_dict.get("BASKETS", {})
    return sorted(basket_dict.keys())


def write_basket_registry_dict(basket_registry_dict: dict) -> None:
    latest_path = get_basket_registry_latest_path()
    snapshot_path = get_basket_registry_snapshot_path()
    payload_text = json.dumps(basket_registry_dict, ensure_ascii=False, indent=2)
    latest_path.write_text(payload_text, encoding="utf-8")
    snapshot_path.write_text(payload_text, encoding="utf-8")
    load_basket_registry_dict.clear()


def save_named_basket(basket_name: str, basket_code_list: list[str]) -> None:
    clean_name = sanitize_basket_name(basket_name)
    if not clean_name:
        raise ValueError("Basket name cannot be empty.")
    registry_path = get_basket_registry_latest_path()
    basket_registry_dict = load_basket_registry_dict(str(registry_path))
    basket_registry_dict.setdefault("BASKETS", {})
    basket_registry_dict["BASKETS"][clean_name] = {
        "TS_CODE_LIST": basket_code_list,
        "UPDATED_AT": pd.Timestamp.now().isoformat(),
    }
    basket_registry_dict["UPDATED_AT"] = pd.Timestamp.now().isoformat()
    write_basket_registry_dict(basket_registry_dict=basket_registry_dict)


def load_named_basket_codes(basket_name: str) -> list[str]:
    registry_path = get_basket_registry_latest_path()
    basket_registry_dict = load_basket_registry_dict(str(registry_path))
    return list(
        basket_registry_dict.get("BASKETS", {})
        .get(basket_name, {})
        .get("TS_CODE_LIST", [])
    )


def delete_named_basket(basket_name: str) -> None:
    registry_path = get_basket_registry_latest_path()
    basket_registry_dict = load_basket_registry_dict(str(registry_path))
    basket_dict = basket_registry_dict.get("BASKETS", {})
    if basket_name in basket_dict:
        del basket_dict[basket_name]
    basket_registry_dict["BASKETS"] = basket_dict
    basket_registry_dict["UPDATED_AT"] = pd.Timestamp.now().isoformat()
    write_basket_registry_dict(basket_registry_dict=basket_registry_dict)


def rename_named_basket(old_basket_name: str, new_basket_name: str) -> str:
    clean_new_name = sanitize_basket_name(new_basket_name)
    if not clean_new_name:
        raise ValueError("New basket name cannot be empty.")
    registry_path = get_basket_registry_latest_path()
    basket_registry_dict = load_basket_registry_dict(str(registry_path))
    basket_dict = basket_registry_dict.get("BASKETS", {})
    if old_basket_name not in basket_dict:
        raise ValueError("Source basket does not exist.")
    if clean_new_name != old_basket_name and clean_new_name in basket_dict:
        raise ValueError("Target basket name already exists.")
    basket_dict[clean_new_name] = {
        "TS_CODE_LIST": basket_dict[old_basket_name]["TS_CODE_LIST"],
        "UPDATED_AT": pd.Timestamp.now().isoformat(),
    }
    if clean_new_name != old_basket_name:
        del basket_dict[old_basket_name]
    basket_registry_dict["BASKETS"] = basket_dict
    basket_registry_dict["UPDATED_AT"] = pd.Timestamp.now().isoformat()
    write_basket_registry_dict(basket_registry_dict=basket_registry_dict)
    return clean_new_name


def duplicate_named_basket(source_basket_name: str, target_basket_name: str) -> str:
    clean_target_name = sanitize_basket_name(target_basket_name)
    if not clean_target_name:
        raise ValueError("Duplicate basket name cannot be empty.")
    registry_path = get_basket_registry_latest_path()
    basket_registry_dict = load_basket_registry_dict(str(registry_path))
    basket_dict = basket_registry_dict.get("BASKETS", {})
    if source_basket_name not in basket_dict:
        raise ValueError("Source basket does not exist.")
    if clean_target_name in basket_dict:
        raise ValueError("Duplicate basket name already exists.")
    basket_dict[clean_target_name] = {
        "TS_CODE_LIST": list(basket_dict[source_basket_name]["TS_CODE_LIST"]),
        "UPDATED_AT": pd.Timestamp.now().isoformat(),
    }
    basket_registry_dict["BASKETS"] = basket_dict
    basket_registry_dict["UPDATED_AT"] = pd.Timestamp.now().isoformat()
    write_basket_registry_dict(basket_registry_dict=basket_registry_dict)
    return clean_target_name


def initialize_session_state(default_stock_code: str) -> None:
    st.session_state.setdefault("page_state", "Step 1 | Coverage Universe")
    st.session_state.setdefault("selected_code_state", default_stock_code)
    st.session_state.setdefault("task_state", "NONE")
    st.session_state.setdefault("display_model_state", "Regularized")
    st.session_state.setdefault("date_window_state", "Last 90 Days")
    st.session_state.setdefault("coverage_filter_state", "All Supported A-Shares")
    st.session_state.setdefault("basket_codes_state", [default_stock_code])
    st.session_state.setdefault("basket_name_input_state", "")
    st.session_state.setdefault("saved_basket_state", "")
    st.session_state.setdefault("weighting_mode_state", "Equal")
    st.session_state.setdefault("analysis_scope_state", "Coverage Universe")
    st.session_state.setdefault("page_widget_sync_pending", False)
    st.session_state.setdefault("stock_widget_sync_pending", False)
    st.session_state.setdefault("basket_widget_sync_pending", False)
    st.session_state.setdefault("basket_name_input_widget_sync_pending", False)
    st.session_state.setdefault("saved_basket_widget_sync_pending", False)
    st.session_state.setdefault("weighting_mode_widget_sync_pending", False)
    st.session_state.setdefault("analysis_scope_widget_sync_pending", False)


def sync_widget_state(stock_code_option_list: list[str]) -> None:
    if st.session_state["page_state"] not in PAGE_OPTION_LIST:
        st.session_state["page_state"] = PAGE_OPTION_LIST[0]
    if st.session_state["selected_code_state"] not in stock_code_option_list:
        st.session_state["selected_code_state"] = stock_code_option_list[0]
    st.session_state["basket_codes_state"] = sanitize_basket_code_list(
        basket_code_list=st.session_state.get("basket_codes_state", []),
        valid_code_list=stock_code_option_list,
    )

    if "page_widget" not in st.session_state:
        st.session_state["page_widget"] = st.session_state["page_state"]
    elif st.session_state.get("page_widget_sync_pending"):
        st.session_state["page_widget"] = st.session_state["page_state"]
        st.session_state["page_widget_sync_pending"] = False
    if "stock_widget" not in st.session_state:
        st.session_state["stock_widget"] = st.session_state["selected_code_state"]
    elif st.session_state.get("stock_widget_sync_pending"):
        st.session_state["stock_widget"] = st.session_state["selected_code_state"]
        st.session_state["stock_widget_sync_pending"] = False
    if "display_model_widget" not in st.session_state:
        st.session_state["display_model_widget"] = st.session_state["display_model_state"]
    if "date_window_widget" not in st.session_state:
        st.session_state["date_window_widget"] = st.session_state["date_window_state"]
    if "coverage_filter_widget" not in st.session_state:
        st.session_state["coverage_filter_widget"] = st.session_state["coverage_filter_state"]
    if "basket_widget" not in st.session_state:
        st.session_state["basket_widget"] = st.session_state["basket_codes_state"]
    elif st.session_state.get("basket_widget_sync_pending"):
        st.session_state["basket_widget"] = st.session_state["basket_codes_state"]
        st.session_state["basket_widget_sync_pending"] = False
    if "basket_name_input_widget" not in st.session_state:
        st.session_state["basket_name_input_widget"] = st.session_state["basket_name_input_state"]
    elif st.session_state.get("basket_name_input_widget_sync_pending"):
        st.session_state["basket_name_input_widget"] = st.session_state["basket_name_input_state"]
        st.session_state["basket_name_input_widget_sync_pending"] = False
    if "saved_basket_widget" not in st.session_state:
        st.session_state["saved_basket_widget"] = st.session_state["saved_basket_state"]
    elif st.session_state.get("saved_basket_widget_sync_pending"):
        st.session_state["saved_basket_widget"] = st.session_state["saved_basket_state"]
        st.session_state["saved_basket_widget_sync_pending"] = False
    if "weighting_mode_widget" not in st.session_state:
        st.session_state["weighting_mode_widget"] = st.session_state["weighting_mode_state"]
    elif st.session_state.get("weighting_mode_widget_sync_pending"):
        st.session_state["weighting_mode_widget"] = st.session_state["weighting_mode_state"]
        st.session_state["weighting_mode_widget_sync_pending"] = False
    if "analysis_scope_widget" not in st.session_state:
        st.session_state["analysis_scope_widget"] = st.session_state["analysis_scope_state"]
    elif st.session_state.get("analysis_scope_widget_sync_pending"):
        st.session_state["analysis_scope_widget"] = st.session_state["analysis_scope_state"]
        st.session_state["analysis_scope_widget_sync_pending"] = False
    if st.session_state.get("stock_widget") not in stock_code_option_list:
        st.session_state["stock_widget"] = st.session_state["selected_code_state"]
    st.session_state["basket_widget"] = sanitize_basket_code_list(
        basket_code_list=st.session_state.get("basket_widget", []),
        valid_code_list=stock_code_option_list,
    )


def navigate_to_page(page_name: str, task_name: str = "NONE") -> None:
    st.session_state["page_state"] = page_name
    st.session_state["task_state"] = task_name
    st.session_state["page_widget_sync_pending"] = True
    st.rerun()


def navigate_to_stock(ts_code: str) -> None:
    st.session_state["selected_code_state"] = ts_code
    st.session_state["page_state"] = "Step 3 | Analyze Current Set"
    st.session_state["task_state"] = "NONE"
    st.session_state["stock_widget_sync_pending"] = True
    st.session_state["page_widget_sync_pending"] = True
    st.rerun()


def add_current_stock_to_basket(ts_code: str) -> None:
    basket_code_list = sanitize_basket_code_list(
        basket_code_list=st.session_state.get("basket_codes_state", []),
        valid_code_list=st.session_state.get("all_stock_code_option_list", []),
    )
    if ts_code not in basket_code_list:
        basket_code_list.append(ts_code)
    st.session_state["basket_codes_state"] = basket_code_list
    st.session_state["analysis_scope_state"] = "Current Basket"
    st.session_state["basket_widget_sync_pending"] = True
    st.session_state["analysis_scope_widget_sync_pending"] = True
    st.rerun()


def clear_basket() -> None:
    st.session_state["basket_codes_state"] = []
    st.session_state["analysis_scope_state"] = "Coverage Universe"
    st.session_state["basket_widget_sync_pending"] = True
    st.session_state["analysis_scope_widget_sync_pending"] = True
    st.rerun()


def load_named_basket_into_state(
    basket_name: str,
    valid_code_list: list[str],
) -> None:
    basket_code_list = sanitize_basket_code_list(
        basket_code_list=load_named_basket_codes(basket_name=basket_name),
        valid_code_list=valid_code_list,
    )
    st.session_state["basket_codes_state"] = basket_code_list
    st.session_state["saved_basket_state"] = basket_name
    st.session_state["analysis_scope_state"] = "Current Basket"
    st.session_state["basket_widget_sync_pending"] = True
    st.session_state["saved_basket_widget_sync_pending"] = True
    st.session_state["analysis_scope_widget_sync_pending"] = True
    st.rerun()


def replace_basket_from_code_list(basket_code_list: list[str]) -> None:
    clean_code_list = sanitize_basket_code_list(
        basket_code_list=basket_code_list,
        valid_code_list=st.session_state.get("all_stock_code_option_list", []),
    )
    st.session_state["basket_codes_state"] = clean_code_list
    st.session_state["analysis_scope_state"] = (
        "Current Basket" if clean_code_list else "Coverage Universe"
    )
    st.session_state["basket_widget_sync_pending"] = True
    st.session_state["analysis_scope_widget_sync_pending"] = True
    st.rerun()


def append_basket_from_code_list(basket_code_list: list[str]) -> None:
    existing_code_list = sanitize_basket_code_list(
        basket_code_list=st.session_state.get("basket_codes_state", []),
        valid_code_list=st.session_state.get("all_stock_code_option_list", []),
    )
    append_code_list = sanitize_basket_code_list(
        basket_code_list=basket_code_list,
        valid_code_list=st.session_state.get("all_stock_code_option_list", []),
    )
    for ts_code in append_code_list:
        if ts_code not in existing_code_list:
            existing_code_list.append(ts_code)
    st.session_state["basket_codes_state"] = existing_code_list
    st.session_state["analysis_scope_state"] = (
        "Current Basket" if existing_code_list else "Coverage Universe"
    )
    st.session_state["basket_widget_sync_pending"] = True
    st.session_state["analysis_scope_widget_sync_pending"] = True
    st.rerun()


def get_active_prediction_column(model_view: str) -> str:
    return "REGULARIZED_PRED"


def get_display_series_list(model_view: str) -> list[str]:
    return ["FUTURE_RV_5", "REGULARIZED_PRED"]


def build_merged_prediction_df(
    DF_RegularizedPredictionInt: pd.DataFrame,
    DF_BoostedPredictionInt: pd.DataFrame,
) -> pd.DataFrame:
    DF_MergedInt = DF_RegularizedPredictionInt.rename(
        columns={"PRED_FUTURE_RV_5": "REGULARIZED_PRED"}
    ).merge(
        DF_BoostedPredictionInt.rename(columns={"PRED_FUTURE_RV_5": "BOOSTED_PRED"}),
        on=["TRADE_DATE", "TS_CODE", "FUTURE_RV_5"],
        how="inner",
    )
    return DF_MergedInt.sort_values(["TRADE_DATE", "TS_CODE"]).reset_index(drop=True)


def resolve_date_filter(
    DF_MergedInt: pd.DataFrame,
    window_mode: str,
    custom_date_tuple: tuple[pd.Timestamp, pd.Timestamp] | tuple,
) -> tuple[pd.Timestamp, pd.Timestamp]:
    unique_date_list = sorted(pd.to_datetime(DF_MergedInt["TRADE_DATE"]).unique())
    end_date = pd.Timestamp(unique_date_list[-1])
    if window_mode == "Custom Range" and len(custom_date_tuple) == 2:
        return pd.Timestamp(custom_date_tuple[0]), pd.Timestamp(custom_date_tuple[1])

    window_map = {
        "All History": len(unique_date_list),
        "Last 30 Days": 30,
        "Last 90 Days": 90,
        "Last 180 Days": 180,
        "Last 252 Days": 252,
    }
    window_size = min(window_map[window_mode], len(unique_date_list))
    start_date = pd.Timestamp(unique_date_list[-window_size])
    return start_date, end_date


def build_filtered_prediction_df(
    DF_MergedInt: pd.DataFrame,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> pd.DataFrame:
    return DF_MergedInt.loc[
        (DF_MergedInt["TRADE_DATE"] >= start_date)
        & (DF_MergedInt["TRADE_DATE"] <= end_date)
    ].copy()


def render_metric_cards(summary_title: str, summary_dict: dict) -> None:
    st.subheader(summary_title)
    col_1, col_2, col_3 = st.columns(3)
    col_1.metric("Test MAE", f"{summary_dict['TEST_METRICS']['MAE']:.6f}")
    col_2.metric("Test RMSE", f"{summary_dict['TEST_METRICS']['RMSE']:.6f}")
    col_3.metric("Test R2", f"{summary_dict['TEST_METRICS']['R2']:.6f}")


def render_model_control() -> str:
    return "Regularized"


def format_metric_value(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value):.6f}"


def build_explanation_text(
    DF_SelectedInt: pd.DataFrame,
    DF_LatestMarketInt: pd.DataFrame,
    model_view: str,
    is_model_covered: bool,
) -> str:
    active_prediction_column = get_active_prediction_column(model_view=model_view)
    latest_row = DF_SelectedInt.iloc[-1]
    market_median = float(DF_LatestMarketInt[active_prediction_column].median())
    relative_text = "above" if latest_row[active_prediction_column] >= market_median else "below"
    recent_window = min(20, len(DF_SelectedInt))

    if DF_SelectedInt["FUTURE_RV_5"].notna().sum() >= 2:
        actual_series = DF_SelectedInt["FUTURE_RV_5"].dropna()
        trend_change = float(actual_series.iloc[-1] - actual_series.iloc[max(0, len(actual_series) - recent_window)])
        trend_text = "rising" if trend_change >= 0 else "cooling"
        source_text = "observed future volatility"
    else:
        prediction_series = DF_SelectedInt[active_prediction_column].dropna()
        trend_change = float(
            prediction_series.iloc[-1] - prediction_series.iloc[max(0, len(prediction_series) - recent_window)]
        )
        trend_text = "rising" if trend_change >= 0 else "cooling"
        source_text = "predicted volatility"

    stock_scope_text = "model coverage history" if is_model_covered else "live on-demand history"
    return (
        f"This stock is currently {relative_text} the market median in {active_prediction_column}. "
        f"The latest signal comes from {stock_scope_text}, and the last {recent_window} observations show {source_text} {trend_text}."
    )


@st.cache_resource(show_spinner=False)
def build_live_model_bundle() -> dict:
    feature_panel_path = find_latest_feature_panel_file()
    DF_FeatureInt = load_feature_panel(feature_panel_path)
    DF_ModelInt = build_model_dataset(DF_FeatureInt=DF_FeatureInt)
    feature_column_list = DF_ModelInt.attrs["FEATURE_COLUMN_LIST"]

    regularized_model = Pipeline(
        steps=[
            ("SCALER", StandardScaler()),
            ("RIDGE", Ridge(alpha=100.0)),
        ]
    )
    regularized_model.fit(DF_ModelInt[feature_column_list], DF_ModelInt[TARGET_COLUMN])

    boosted_model = HistGradientBoostingRegressor(
        learning_rate=0.03,
        max_depth=3,
        max_iter=250,
        min_samples_leaf=80,
        l2_regularization=1.0,
        random_state=42,
    )
    boosted_model.fit(DF_ModelInt[feature_column_list], DF_ModelInt[TARGET_COLUMN])

    return {
        "FEATURE_COLUMNS": feature_column_list,
        "REGULARIZED_MODEL": regularized_model,
        "BOOSTED_MODEL": boosted_model,
    }


@st.cache_data(show_spinner=False)
def build_live_prediction_df(ts_code: str) -> pd.DataFrame:
    config_dict = load_project_config()
    DF_PriceInt = fetch_one_price_df(
        ts_code=ts_code,
        start_date=config_dict["PRICE"]["START_DATE"],
        end_date=config_dict["PRICE"]["END_DATE"],
        adjust_mode=config_dict["PRICE"]["ADJUST_MODE"],
    )
    if DF_PriceInt.empty:
        raise ValueError(f"No price history returned for {ts_code}.")

    DF_TargetInt = build_target_columns(
        DF_PricePanelInt=DF_PriceInt,
        vol_window=int(config_dict["TARGET"]["VOL_WINDOW"]),
        target_window=int(config_dict["TARGET"]["TARGET_WINDOW"]),
    )
    DF_FeatureInt = build_price_features(DF_TargetInt=DF_TargetInt)
    DF_FeatureInt, _ = load_and_merge_macro_rate(DF_FeatureInt=DF_FeatureInt)

    model_bundle = build_live_model_bundle()
    feature_column_list = model_bundle["FEATURE_COLUMNS"]
    for column_name in feature_column_list:
        if column_name not in DF_FeatureInt.columns:
            DF_FeatureInt[column_name] = pd.NA

    DF_PredictableInt = DF_FeatureInt.dropna(subset=feature_column_list).copy()
    if DF_PredictableInt.empty:
        raise ValueError(f"No predictable rows were available for {ts_code}.")

    DF_PredictableInt["REGULARIZED_PRED"] = model_bundle["REGULARIZED_MODEL"].predict(
        DF_PredictableInt[feature_column_list]
    )
    DF_PredictableInt["BOOSTED_PRED"] = model_bundle["BOOSTED_MODEL"].predict(
        DF_PredictableInt[feature_column_list]
    )
    return DF_PredictableInt[
        ["TRADE_DATE", "TS_CODE", "FUTURE_RV_5", "REGULARIZED_PRED", "BOOSTED_PRED"]
    ].sort_values("TRADE_DATE").reset_index(drop=True)


def build_basket_panel_df(
    basket_code_list: list[str],
    DF_MergedFilteredInt: pd.DataFrame,
    covered_code_set: set[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame_list: list[pd.DataFrame] = []
    status_item_list: list[dict[str, str]] = []

    date_min = (
        pd.Timestamp(DF_MergedFilteredInt["TRADE_DATE"].min())
        if not DF_MergedFilteredInt.empty
        else None
    )
    date_max = (
        pd.Timestamp(DF_MergedFilteredInt["TRADE_DATE"].max())
        if not DF_MergedFilteredInt.empty
        else None
    )

    for ts_code in basket_code_list:
        if ts_code in covered_code_set:
            DF_OneInt = DF_MergedFilteredInt.loc[
                DF_MergedFilteredInt["TS_CODE"] == ts_code
            ].copy()
            if not DF_OneInt.empty:
                frame_list.append(DF_OneInt)
                status_item_list.append(
                    {"TS_CODE": ts_code, "SOURCE_MODE": "Covered", "STATUS": "Ready", "DETAIL": "Persisted prediction rows loaded."}
                )
            else:
                status_item_list.append(
                    {"TS_CODE": ts_code, "SOURCE_MODE": "Covered", "STATUS": "Empty Window", "DETAIL": "No persisted rows were available under the current date window."}
                )
            continue

        try:
            DF_OneInt = build_live_prediction_df(ts_code=ts_code)
            if date_min is not None and date_max is not None:
                DF_OneInt = DF_OneInt.loc[
                    (DF_OneInt["TRADE_DATE"] >= date_min)
                    & (DF_OneInt["TRADE_DATE"] <= date_max)
                ].copy()
            if DF_OneInt.empty:
                status_item_list.append(
                    {"TS_CODE": ts_code, "SOURCE_MODE": "Live Fetch", "STATUS": "Empty Window", "DETAIL": "Live prediction rows were outside the current date window."}
                )
            else:
                frame_list.append(DF_OneInt)
                status_item_list.append(
                    {"TS_CODE": ts_code, "SOURCE_MODE": "Live Fetch", "STATUS": "Ready", "DETAIL": "AKShare history fetched and scored on demand."}
                )
        except Exception as exc:
            status_item_list.append(
                {"TS_CODE": ts_code, "SOURCE_MODE": "Live Fetch", "STATUS": "Unavailable", "DETAIL": str(exc)}
            )

    if frame_list:
        DF_BasketPanelInt = pd.concat(frame_list, ignore_index=True).sort_values(
            ["TRADE_DATE", "TS_CODE"]
        ).reset_index(drop=True)
    else:
        DF_BasketPanelInt = pd.DataFrame(
            columns=["TRADE_DATE", "TS_CODE", "FUTURE_RV_5", "REGULARIZED_PRED", "BOOSTED_PRED"]
        )
    DF_BasketStatusInt = pd.DataFrame(status_item_list)
    return DF_BasketPanelInt, DF_BasketStatusInt


def build_basket_aggregate_df(DF_BasketPanelInt: pd.DataFrame) -> pd.DataFrame:
    if DF_BasketPanelInt.empty:
        return pd.DataFrame(
            columns=[
                "TRADE_DATE",
                "FUTURE_RV_5_MEAN",
                "REGULARIZED_PRED_MEAN",
                "BOOSTED_PRED_MEAN",
                "STOCK_COUNT",
            ]
        )
    DF_AggInt = (
        DF_BasketPanelInt.groupby("TRADE_DATE", as_index=False)
        .agg(
            FUTURE_RV_5_MEAN=("FUTURE_RV_5", "mean"),
            REGULARIZED_PRED_MEAN=("REGULARIZED_PRED", "mean"),
            BOOSTED_PRED_MEAN=("BOOSTED_PRED", "mean"),
            STOCK_COUNT=("TS_CODE", "nunique"),
        )
        .sort_values("TRADE_DATE")
        .reset_index(drop=True)
    )
    return DF_AggInt


def build_weighted_basket_aggregate_df(
    DF_BasketPanelInt: pd.DataFrame,
    DF_StockLookupInt: pd.DataFrame,
    weighting_mode: str,
) -> pd.DataFrame:
    if DF_BasketPanelInt.empty:
        return pd.DataFrame(
            columns=[
                "TRADE_DATE",
                "FUTURE_RV_5_MEAN",
                "REGULARIZED_PRED_MEAN",
                "BOOSTED_PRED_MEAN",
                "STOCK_COUNT",
            ]
        )

    if weighting_mode == "Equal":
        return build_basket_aggregate_df(DF_BasketPanelInt=DF_BasketPanelInt)

    DF_WeightedInt = DF_BasketPanelInt.merge(
        DF_StockLookupInt[["TS_CODE", "TURNOVER_AMOUNT"]],
        on="TS_CODE",
        how="left",
    )
    DF_WeightedInt["WEIGHT_VALUE"] = pd.to_numeric(
        DF_WeightedInt["TURNOVER_AMOUNT"], errors="coerce"
    ).fillna(0.0)

    aggregate_item_list: list[dict[str, float | int | pd.Timestamp]] = []
    for trade_date, DF_GroupInt in DF_WeightedInt.groupby("TRADE_DATE"):
        weight_series = DF_GroupInt["WEIGHT_VALUE"].copy()
        if float(weight_series.sum()) <= 0:
            weight_series = pd.Series(1.0, index=DF_GroupInt.index)

        aggregate_item_list.append(
            {
                "TRADE_DATE": trade_date,
                "FUTURE_RV_5_MEAN": float(
                    (DF_GroupInt["FUTURE_RV_5"].fillna(0.0) * weight_series).sum()
                    / weight_series.loc[DF_GroupInt["FUTURE_RV_5"].notna()].sum()
                )
                if DF_GroupInt["FUTURE_RV_5"].notna().any()
                else float("nan"),
                "REGULARIZED_PRED_MEAN": float(
                    (DF_GroupInt["REGULARIZED_PRED"] * weight_series).sum() / weight_series.sum()
                ),
                "BOOSTED_PRED_MEAN": float(
                    (DF_GroupInt["BOOSTED_PRED"] * weight_series).sum() / weight_series.sum()
                ),
                "STOCK_COUNT": int(DF_GroupInt["TS_CODE"].nunique()),
            }
        )

    return pd.DataFrame(aggregate_item_list).sort_values("TRADE_DATE").reset_index(drop=True)


def resolve_active_scope_label(
    analysis_scope: str,
    basket_code_list: list[str],
) -> str:
    if analysis_scope == "Current Basket" and basket_code_list:
        return "Current Basket"
    return "Coverage Universe"


def build_active_panel_df(
    analysis_scope: str,
    DF_MergedFilteredInt: pd.DataFrame,
    DF_BasketPanelInt: pd.DataFrame,
) -> pd.DataFrame:
    if analysis_scope == "Current Basket" and not DF_BasketPanelInt.empty:
        return DF_BasketPanelInt.copy()
    if analysis_scope == "Current Basket" and DF_BasketPanelInt.empty:
        return pd.DataFrame(columns=DF_MergedFilteredInt.columns)
    return DF_MergedFilteredInt.copy()


def build_active_lookup_df(
    analysis_scope: str,
    DF_StockLookupInt: pd.DataFrame,
    basket_code_list: list[str],
) -> pd.DataFrame:
    if analysis_scope == "Current Basket":
        return DF_StockLookupInt.loc[
            DF_StockLookupInt["TS_CODE"].isin(basket_code_list)
        ].copy()
    return DF_StockLookupInt.copy()


def render_overview_page(
    regularized_summary: dict,
    boosted_summary: dict,
    comparison_summary: dict,
    regularized_walk_forward_summary: dict | None,
    boosted_walk_forward_summary: dict | None,
    DF_ActivePanelInt: pd.DataFrame,
    DF_BasketAggregateInt: pd.DataFrame,
    DF_BasketStatusInt: pd.DataFrame,
    weighting_mode: str,
    analysis_scope_label: str,
) -> None:
    st.header("Overview")
    model_view = render_model_control()
    st.session_state["display_model_state"] = model_view
    if DF_ActivePanelInt.empty:
        st.warning("No rows are available for the selected date window.")
        return
    st.caption(f"Current analysis scope: {analysis_scope_label}")

    if model_view in ["Regularized", "Both"]:
        render_metric_cards("Regularized Model", regularized_summary)
    if model_view in ["Boosted", "Both"]:
        render_metric_cards("Boosted Model", boosted_summary)

    st.subheader("Model Delta")
    delta_col_1, delta_col_2, delta_col_3 = st.columns(3)
    delta_col_1.metric(
        "Boosted - Regularized MAE",
        f"{comparison_summary.get('DELTA_MAE_BOOSTED_VS_REGULARIZED', comparison_summary['DELTA_MAE']):.6f}",
    )
    delta_col_2.metric(
        "Boosted - Regularized RMSE",
        f"{comparison_summary.get('DELTA_RMSE_BOOSTED_VS_REGULARIZED', comparison_summary['DELTA_RMSE']):.6f}",
    )
    delta_col_3.metric("Best Model", comparison_summary.get("BEST_MODEL_BY_RMSE", "N/A"))

    if regularized_walk_forward_summary is not None:
        st.subheader("Walk-Forward Stability")
        walk_regularized_metrics = regularized_walk_forward_summary["AGGREGATE_TEST_METRICS"]
        walk_col_1, walk_col_2, walk_col_3 = st.columns(3)
        walk_col_1.metric("Regularized WF RMSE", f"{walk_regularized_metrics['RMSE']:.6f}")
        walk_col_2.metric("Regularized WF R2", f"{walk_regularized_metrics['R2']:.6f}")
        if boosted_walk_forward_summary is not None:
            walk_boosted_metrics = boosted_walk_forward_summary["AGGREGATE_TEST_METRICS"]
            walk_col_3.metric(
                "Boosted - Regularized WF RMSE",
                f"{walk_boosted_metrics['RMSE'] - walk_regularized_metrics['RMSE']:.6f}",
            )
        else:
            walk_col_3.metric("Boosted - Regularized WF RMSE", "N/A")

    latest_date = DF_ActivePanelInt["TRADE_DATE"].max()
    DF_LatestInt = DF_ActivePanelInt.loc[
        DF_ActivePanelInt["TRADE_DATE"] == latest_date
    ].copy()
    DF_LatestInt["REGULARIZED_ABS_ERROR"] = (
        DF_LatestInt["REGULARIZED_PRED"] - DF_LatestInt["FUTURE_RV_5"]
    ).abs()
    DF_LatestInt["BOOSTED_ABS_ERROR"] = (
        DF_LatestInt["BOOSTED_PRED"] - DF_LatestInt["FUTURE_RV_5"]
    ).abs()

    display_column_list = ["TS_CODE", "FUTURE_RV_5"]
    if model_view in ["Regularized", "Both"]:
        display_column_list += ["REGULARIZED_PRED", "REGULARIZED_ABS_ERROR"]
    if model_view in ["Boosted", "Both"]:
        display_column_list += ["BOOSTED_PRED", "BOOSTED_ABS_ERROR"]

    st.subheader("Latest Snapshot")
    st.caption(f"Latest prediction date: {latest_date.date()}")
    st.dataframe(
        DF_LatestInt[display_column_list].sort_values("TS_CODE"),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Quick Tasks")
    task_col_1, task_col_2, task_col_3 = st.columns(3)
    if task_col_1.button("Top Risk Picks Today", use_container_width=True):
        navigate_to_page(page_name="Market", task_name="TOP_RISK")
    if task_col_2.button("Low-Liquidity High-Vol Names", use_container_width=True):
        navigate_to_page(page_name="Screener", task_name="LOW_LIQ_HIGH_VOL")
    if task_col_3.button("Model Failure Cases", use_container_width=True):
        navigate_to_page(page_name="Diagnostics", task_name="MODEL_FAILURE")

    st.subheader("Research Basket Snapshot")
    if DF_BasketStatusInt.empty:
        st.caption("No research basket has been selected yet.")
        return
    ready_count = int((DF_BasketStatusInt["STATUS"] == "Ready").sum())
    unavailable_count = int((DF_BasketStatusInt["STATUS"] == "Unavailable").sum())
    basket_col_1, basket_col_2, basket_col_3 = st.columns(3)
    basket_col_1.metric("Basket Names", str(len(DF_BasketStatusInt)))
    basket_col_2.metric("Ready Names", str(ready_count))
    basket_col_3.metric("Unavailable Names", str(unavailable_count))
    st.caption(f"Current basket weighting: {weighting_mode}")
    if DF_BasketAggregateInt.empty:
        st.warning("The current basket has no usable rows under the selected date window.")
    else:
        latest_basket_row = DF_BasketAggregateInt.sort_values("TRADE_DATE").iloc[-1]
        st.caption(
            f"Latest basket date: {pd.Timestamp(latest_basket_row['TRADE_DATE']).date()} | Basket members on date: {int(latest_basket_row['STOCK_COUNT'])}"
        )
        st.dataframe(DF_BasketStatusInt, use_container_width=True, hide_index=True)


def render_market_page(
    DF_ActivePanelInt: pd.DataFrame,
    DF_ActiveLookupInt: pd.DataFrame,
    analysis_scope_label: str,
) -> None:
    st.header("Market")
    model_view = render_model_control()
    st.session_state["display_model_state"] = model_view
    if DF_ActivePanelInt.empty:
        st.warning("No rows are available for the selected date window.")
        return
    st.caption(f"Current analysis scope: {analysis_scope_label}")

    active_prediction_column = get_active_prediction_column(model_view=model_view)
    latest_date = DF_ActivePanelInt["TRADE_DATE"].max()
    DF_LatestInt = DF_ActivePanelInt.loc[
        DF_ActivePanelInt["TRADE_DATE"] == latest_date
    ].copy()
    DF_LatestInt = DF_LatestInt.merge(
        DF_ActiveLookupInt[["TS_CODE", "SEC_NAME", "TURNOVER_AMOUNT", "LIQUIDITY_RANK"]],
        on="TS_CODE",
        how="left",
    )
    DF_LatestInt["LIQUIDITY_RANK"] = pd.to_numeric(
        DF_LatestInt["LIQUIDITY_RANK"], errors="coerce"
    ).fillna(999999)

    metric_col_1, metric_col_2, metric_col_3 = st.columns(3)
    metric_col_1.metric("Latest Date", str(latest_date.date()))
    metric_col_2.metric("Active Universe", str(DF_LatestInt["TS_CODE"].nunique()))
    metric_col_3.metric(
        f"Average {active_prediction_column}",
        f"{DF_LatestInt[active_prediction_column].mean():.6f}",
    )

    if st.session_state["task_state"] == "TOP_RISK":
        st.info("Quick task active: Top Risk Picks Today")

    st.caption("This page summarizes the currently active analysis universe.")
    st.subheader("Highest Predicted Volatility")
    DF_DisplayInt = DF_LatestInt[
        [
            "TS_CODE",
            "SEC_NAME",
            "FUTURE_RV_5",
            "REGULARIZED_PRED",
            "BOOSTED_PRED",
            "TURNOVER_AMOUNT",
            "LIQUIDITY_RANK",
        ]
    ].sort_values(active_prediction_column, ascending=False).head(20)
    selection_event = st.dataframe(
        DF_DisplayInt,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )
    if selection_event.selection.rows:
        selected_row = selection_event.selection.rows[0]
        navigate_to_stock(ts_code=DF_DisplayInt.iloc[selected_row]["TS_CODE"])

    st.subheader("Prediction Distribution")
    chart_column_list = (
        ["REGULARIZED_PRED", "BOOSTED_PRED"]
        if model_view == "Both"
        else [active_prediction_column]
    )
    chart_df = DF_LatestInt.melt(
        id_vars=["TS_CODE"],
        value_vars=chart_column_list,
        var_name="MODEL_NAME",
        value_name="PRED_VALUE",
    )
    fig = px.histogram(
        chart_df,
        x="PRED_VALUE",
        color="MODEL_NAME" if model_view == "Both" else None,
        nbins=24,
        title="Latest Prediction Distribution",
        barmode="overlay",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_basket_page(
    DF_BasketPanelInt: pd.DataFrame,
    DF_BasketAggregateInt: pd.DataFrame,
    DF_BasketStatusInt: pd.DataFrame,
    DF_StockLookupInt: pd.DataFrame,
    weighting_mode: str,
) -> None:
    st.header("Basket")
    model_view = render_model_control()
    st.session_state["display_model_state"] = model_view

    if DF_BasketStatusInt.empty:
        st.info("Build a research basket from the basket builder to start studying custom stock groups.")
        return

    ready_count = int((DF_BasketStatusInt["STATUS"] == "Ready").sum())
    covered_count = int((DF_BasketStatusInt["SOURCE_MODE"] == "Covered").sum())
    live_count = int((DF_BasketStatusInt["SOURCE_MODE"] == "Live Fetch").sum())
    basket_col_1, basket_col_2, basket_col_3 = st.columns(3)
    basket_col_1.metric("Basket Names", str(len(DF_BasketStatusInt)))
    basket_col_2.metric("Covered / Live", f"{covered_count} / {live_count}")
    basket_col_3.metric("Ready Names", str(ready_count))
    st.caption(f"Current weighting mode: {weighting_mode}")

    st.subheader("Basket Availability")
    st.dataframe(DF_BasketStatusInt, use_container_width=True, hide_index=True)

    if DF_BasketAggregateInt.empty:
        st.warning("No basket rows are available under the current date window.")
        return

    active_prediction_column = get_active_prediction_column(model_view=model_view)
    latest_row = DF_BasketAggregateInt.sort_values("TRADE_DATE").iloc[-1]
    latest_col_1, latest_col_2, latest_col_3 = st.columns(3)
    latest_col_1.metric("Latest Basket Actual Mean", format_metric_value(latest_row["FUTURE_RV_5_MEAN"]))
    latest_col_2.metric(
        f"Latest Basket {active_prediction_column} Mean",
        format_metric_value(latest_row[f"{active_prediction_column}_MEAN"]),
    )
    latest_col_3.metric("Latest Basket Size On Date", str(int(latest_row["STOCK_COUNT"])))

    series_column_list = ["FUTURE_RV_5_MEAN"]
    if model_view in ["Regularized", "Both"]:
        series_column_list.append("REGULARIZED_PRED_MEAN")
    if model_view in ["Boosted", "Both"]:
        series_column_list.append("BOOSTED_PRED_MEAN")
    DF_BasketChartInt = DF_BasketAggregateInt.melt(
        id_vars=["TRADE_DATE"],
        value_vars=series_column_list,
        var_name="SERIES_NAME",
        value_name="VALUE",
    )
    fig = px.line(
        DF_BasketChartInt,
        x="TRADE_DATE",
        y="VALUE",
        color="SERIES_NAME",
        title="Basket Aggregate Performance",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Latest Basket Constituents")
    latest_date = DF_BasketPanelInt["TRADE_DATE"].max()
    DF_LatestPanelInt = DF_BasketPanelInt.loc[DF_BasketPanelInt["TRADE_DATE"] == latest_date].copy()
    DF_LatestPanelInt = DF_LatestPanelInt.merge(
        DF_StockLookupInt[["TS_CODE", "SEC_NAME", "COVERAGE_STATUS"]],
        on="TS_CODE",
        how="left",
    )
    st.dataframe(
        DF_LatestPanelInt[
            ["TS_CODE", "SEC_NAME", "COVERAGE_STATUS", "FUTURE_RV_5", "REGULARIZED_PRED", "BOOSTED_PRED"]
        ].sort_values(active_prediction_column, ascending=False),
        use_container_width=True,
        hide_index=True,
    )


def render_screener_page(
    DF_ActivePanelInt: pd.DataFrame,
    DF_ActiveLookupInt: pd.DataFrame,
    analysis_scope_label: str,
) -> None:
    st.header("Screener")
    model_view = render_model_control()
    st.session_state["display_model_state"] = model_view
    if DF_ActivePanelInt.empty:
        st.warning("No rows are available for the selected date window.")
        return
    st.caption(f"Current analysis scope: {analysis_scope_label}")

    active_prediction_column = get_active_prediction_column(model_view=model_view)
    latest_date = DF_ActivePanelInt["TRADE_DATE"].max()
    DF_LatestInt = DF_ActivePanelInt.loc[
        DF_ActivePanelInt["TRADE_DATE"] == latest_date
    ].copy()
    DF_LatestInt = DF_LatestInt.merge(
        DF_ActiveLookupInt[["TS_CODE", "SEC_NAME", "TURNOVER_AMOUNT", "LIQUIDITY_RANK"]],
        on="TS_CODE",
        how="left",
    )
    DF_LatestInt["LIQUIDITY_RANK"] = pd.to_numeric(
        DF_LatestInt["LIQUIDITY_RANK"], errors="coerce"
    ).fillna(999999)

    if st.session_state["task_state"] == "LOW_LIQ_HIGH_VOL":
        st.info("Quick task active: Low-Liquidity High-Vol Names")
        turnover_default = float(DF_LatestInt["TURNOVER_AMOUNT"].quantile(0.30))
        rank_default = int(DF_LatestInt["LIQUIDITY_RANK"].quantile(0.70))
    else:
        turnover_default = float(DF_LatestInt["TURNOVER_AMOUNT"].min())
        rank_default = int(DF_LatestInt["LIQUIDITY_RANK"].max())

    turnover_threshold = st.slider(
        "Minimum Turnover Amount",
        min_value=float(DF_LatestInt["TURNOVER_AMOUNT"].min()),
        max_value=float(DF_LatestInt["TURNOVER_AMOUNT"].max()),
        value=turnover_default,
    )
    rank_limit = st.slider(
        "Maximum Liquidity Rank",
        min_value=1,
        max_value=int(DF_LatestInt["LIQUIDITY_RANK"].max()),
        value=rank_default,
    )
    sort_field = st.selectbox(
        "Sort By",
        [active_prediction_column, "FUTURE_RV_5", "TURNOVER_AMOUNT", "LIQUIDITY_RANK"],
    )

    DF_FilteredInt = DF_LatestInt.loc[
        (DF_LatestInt["TURNOVER_AMOUNT"] >= turnover_threshold)
        & (DF_LatestInt["LIQUIDITY_RANK"] <= rank_limit)
    ].copy()
    DF_FilteredInt = DF_FilteredInt.sort_values(sort_field, ascending=False)

    st.caption(f"Filtered rows: {len(DF_FilteredInt)}")
    screen_col_1, screen_col_2 = st.columns(2)
    if screen_col_1.button("Replace Basket With Screen Result", use_container_width=True):
        replace_basket_from_code_list(DF_FilteredInt["TS_CODE"].tolist())
    if screen_col_2.button("Add Screen Result To Basket", use_container_width=True):
        append_basket_from_code_list(DF_FilteredInt["TS_CODE"].tolist())
    selection_event = st.dataframe(
        DF_FilteredInt[
            [
                "TS_CODE",
                "SEC_NAME",
                "FUTURE_RV_5",
                "REGULARIZED_PRED",
                "BOOSTED_PRED",
                "TURNOVER_AMOUNT",
                "LIQUIDITY_RANK",
            ]
        ],
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )
    if selection_event.selection.rows:
        selected_row = selection_event.selection.rows[0]
        navigate_to_stock(ts_code=DF_FilteredInt.iloc[selected_row]["TS_CODE"])


def render_single_stock_page(
    DF_MergedFilteredInt: pd.DataFrame,
    DF_StockLookupInt: pd.DataFrame,
) -> None:
    st.header("Single Stock")
    model_view = render_model_control()
    st.session_state["display_model_state"] = model_view

    selected_code = st.session_state["selected_code_state"]
    is_model_covered = bool(
        DF_StockLookupInt.loc[
            DF_StockLookupInt["TS_CODE"] == selected_code, "IS_MODEL_COVERED"
        ].iloc[0]
    )

    if is_model_covered:
        DF_SelectedInt = DF_MergedFilteredInt.loc[
            DF_MergedFilteredInt["TS_CODE"] == selected_code
        ].copy()
        stock_mode_text = "Model Coverage"
    else:
        try:
            with st.spinner(f"Fetching live history and scoring {selected_code}..."):
                DF_SelectedInt = build_live_prediction_df(ts_code=selected_code)
        except Exception as exc:
            st.warning(
                "Live on-demand prediction is currently unavailable for this stock. "
                "The most common reason is insufficient history for the rolling feature windows."
            )
            st.caption(f"Technical detail: {exc}")
            return
        if not DF_MergedFilteredInt.empty:
            start_date = DF_MergedFilteredInt["TRADE_DATE"].min()
            end_date = DF_MergedFilteredInt["TRADE_DATE"].max()
            DF_SelectedInt = DF_SelectedInt.loc[
                (DF_SelectedInt["TRADE_DATE"] >= start_date)
                & (DF_SelectedInt["TRADE_DATE"] <= end_date)
            ].copy()
        stock_mode_text = "Live On-Demand"

    if DF_SelectedInt.empty:
        st.warning("No rows are available for the selected stock under the current date window.")
        return

    active_prediction_column = get_active_prediction_column(model_view=model_view)
    latest_row = DF_SelectedInt.sort_values("TRADE_DATE").iloc[-1]
    latest_market_date = DF_MergedFilteredInt["TRADE_DATE"].max() if not DF_MergedFilteredInt.empty else latest_row["TRADE_DATE"]
    DF_LatestMarketInt = DF_MergedFilteredInt.loc[
        DF_MergedFilteredInt["TRADE_DATE"] == latest_market_date
    ].copy()
    if DF_LatestMarketInt.empty:
        DF_LatestMarketInt = DF_SelectedInt.tail(1).copy()

    stock_name_series = DF_StockLookupInt.loc[
        DF_StockLookupInt["TS_CODE"] == selected_code, "SEC_NAME"
    ]
    stock_name = stock_name_series.iloc[0] if not stock_name_series.empty else selected_code

    st.caption(f"{selected_code} | {stock_name} | {stock_mode_text}")
    if not is_model_covered:
        st.info(
            "This stock is outside the persisted model coverage pool. The app fetched price history from AKShare and generated live predictions with the latest feature contract."
        )

    explanation_text = build_explanation_text(
        DF_SelectedInt=DF_SelectedInt.sort_values("TRADE_DATE"),
        DF_LatestMarketInt=DF_LatestMarketInt,
        model_view=model_view,
        is_model_covered=is_model_covered,
    )
    st.info(explanation_text)

    top_col_1, top_col_2, top_col_3 = st.columns(3)
    top_col_1.metric("Latest Actual Future RV 5", format_metric_value(latest_row["FUTURE_RV_5"]))
    top_col_2.metric(
        f"Latest {active_prediction_column}",
        format_metric_value(latest_row[active_prediction_column]),
    )
    if model_view == "Both":
        top_col_3.metric(
            "Latest Prediction Spread",
            format_metric_value(latest_row["BOOSTED_PRED"] - latest_row["REGULARIZED_PRED"]),
        )
    else:
        prediction_error = (
            abs(latest_row[active_prediction_column] - latest_row["FUTURE_RV_5"])
            if pd.notna(latest_row["FUTURE_RV_5"])
            else None
        )
        top_col_3.metric("Latest Prediction Error", format_metric_value(prediction_error))

    chart_df = DF_SelectedInt.melt(
        id_vars=["TRADE_DATE"],
        value_vars=get_display_series_list(model_view=model_view),
        var_name="SERIES_NAME",
        value_name="VALUE",
    )
    fig = px.line(
        chart_df,
        x="TRADE_DATE",
        y="VALUE",
        color="SERIES_NAME",
        title=f"{selected_code} - Actual vs Predicted Future RV 5",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Latest Rows")
    display_column_list = ["TRADE_DATE", "TS_CODE", "FUTURE_RV_5", active_prediction_column]
    if model_view == "Both":
        display_column_list = ["TRADE_DATE", "TS_CODE", "FUTURE_RV_5", "REGULARIZED_PRED", "BOOSTED_PRED"]
    st.dataframe(
        DF_SelectedInt.sort_values("TRADE_DATE")[display_column_list].tail(20),
        use_container_width=True,
        hide_index=True,
    )


def render_diagnostics_page(
    comparison_summary: dict,
    regularized_walk_forward_summary: dict | None,
    boosted_walk_forward_summary: dict | None,
    DF_ActivePanelInt: pd.DataFrame,
    analysis_scope_label: str,
) -> None:
    st.header("Diagnostics")
    model_view = render_model_control()
    st.session_state["display_model_state"] = model_view
    if DF_ActivePanelInt.empty:
        st.warning("No rows are available for the selected date window.")
        return
    st.caption(f"Current analysis scope: {analysis_scope_label}")

    st.write("The current held-out comparison is based on a simple time split over the lightweight rerun and is filtered by the current analysis scope.")
    DF_DiagnosticInt = DF_ActivePanelInt.copy()
    DF_DiagnosticInt["REGULARIZED_ABS_ERROR"] = (
        DF_DiagnosticInt["REGULARIZED_PRED"] - DF_DiagnosticInt["FUTURE_RV_5"]
    ).abs()
    DF_DiagnosticInt["BOOSTED_ABS_ERROR"] = (
        DF_DiagnosticInt["BOOSTED_PRED"] - DF_DiagnosticInt["FUTURE_RV_5"]
    ).abs()
    DF_GroupedInt = DF_DiagnosticInt.groupby("TS_CODE", as_index=False)[
        ["REGULARIZED_ABS_ERROR", "BOOSTED_ABS_ERROR"]
    ].mean()

    if st.session_state["task_state"] == "MODEL_FAILURE":
        st.info("Quick task active: Model Failure Cases")
        active_error_column = (
            "BOOSTED_ABS_ERROR" if model_view == "Boosted" else "REGULARIZED_ABS_ERROR"
        )
        st.dataframe(
            DF_GroupedInt.sort_values(active_error_column, ascending=False).head(20),
            use_container_width=True,
            hide_index=True,
        )

    value_column_list = (
        ["REGULARIZED_ABS_ERROR", "BOOSTED_ABS_ERROR"]
        if model_view == "Both"
        else ["BOOSTED_ABS_ERROR" if model_view == "Boosted" else "REGULARIZED_ABS_ERROR"]
    )
    fig = px.bar(
        DF_GroupedInt.melt(
            id_vars=["TS_CODE"],
            value_vars=value_column_list,
            var_name="MODEL_NAME",
            value_name="MEAN_ABS_ERROR",
        ),
        x="TS_CODE",
        y="MEAN_ABS_ERROR",
        color="MODEL_NAME",
        barmode="group",
        title="Average Absolute Error by Stock",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Current Reading")
    st.write(
        "The current regularized model remains the safest default for the app because it wins on the main held-out benchmark and is easier to explain, while the tuned boosted branch is kept as a higher-variance comparison model."
    )
    st.json(comparison_summary)
    if regularized_walk_forward_summary is not None:
        st.subheader("Walk-Forward Summary")
        walk_forward_payload = {
            "REGULARIZED_WALK_FORWARD": regularized_walk_forward_summary["AGGREGATE_TEST_METRICS"],
        }
        if boosted_walk_forward_summary is not None:
            walk_forward_payload["BOOSTED_WALK_FORWARD"] = boosted_walk_forward_summary[
                "AGGREGATE_TEST_METRICS"
            ]
        st.json(walk_forward_payload)


def render_method_page(
    regularized_summary: dict,
    boosted_summary: dict,
    comparison_summary: dict,
    regularized_walk_forward_summary: dict | None,
    boosted_walk_forward_summary: dict | None,
) -> None:
    st.header("Method & Limitations")
    st.subheader("Current Method")
    st.markdown(
        """
        - Route: `B + B` lightweight route
        - Coverage pool: lightweight liquid A-share sample ranked by turnover snapshot
        - Price source: AKShare
        - Adjust mode: `qfq`
        - Target: `FUTURE_RV_5`
        - Features: rolling return, rolling volatility, turnover, amount, intraday range, opening gap, and macro-rate features
        - Models: `Ridge` regularized model as the stable default and `HistGradientBoostingRegressor` as the higher-variance comparison model
        - App behavior: all supported SH/SZ A-shares are selectable; out-of-coverage names are fetched and scored live on demand
        - Basket behavior: users can define, save, load, and delete custom research baskets and inspect aggregate basket behavior on the Basket page
        - Basket weighting: equal-weight and turnover-weighted aggregation are both supported
        - Analysis scope: Overview, Market, Screener, and Diagnostics can follow the current basket instead of the full coverage universe
        - Screen workflow: screener results can replace the basket or be appended into it directly
        """
    )
    st.subheader("Current Metrics")
    metric_col_1, metric_col_2, metric_col_3 = st.columns(3)
    metric_col_1.metric("Regularized Holdout RMSE", f"{regularized_summary['TEST_METRICS']['RMSE']:.6f}")
    metric_col_2.metric("Boosted Holdout RMSE", f"{boosted_summary['TEST_METRICS']['RMSE']:.6f}")
    metric_col_3.metric("Best Holdout Model", comparison_summary.get("BEST_MODEL_BY_RMSE", "N/A"))
    if regularized_walk_forward_summary is not None:
        st.caption(
            "Walk-forward aggregate: "
            f"regularized RMSE={regularized_walk_forward_summary['AGGREGATE_TEST_METRICS']['RMSE']:.6f}"
            + (
                f", boosted RMSE={boosted_walk_forward_summary['AGGREGATE_TEST_METRICS']['RMSE']:.6f}"
                if boosted_walk_forward_summary is not None
                else ""
            )
        )
    st.subheader("Current Limitations")
    st.markdown(
        """
        - Market and Screener pages still summarize the persisted model coverage universe rather than every supported stock.
        - Live on-demand inference currently uses the latest feature contract and retrained cached models inside the app, not a separately versioned serving artifact.
        - Sparse fund-flow fields are still excluded by coverage gating in the default model path.
        - The current holdout split and the current walk-forward aggregate do not fully agree on the ranking between regularized and boosted, so the tree branch is still not stable enough to become the default app narrative.
        - The current evaluation snapshot is still a lightweight route rather than a full production deployment pipeline.
        """
    )
    st.subheader("Upgrade Path")
    st.markdown(
        """
        - Persist trained serving artifacts rather than refitting models inside the app
        - Add richer non-price and event features with stronger coverage discipline
        - Expand Market and Screener views beyond the current model coverage slice
        - Upgrade from `B + B` to `A + A` when stronger data coverage is needed
        """
    )


def main() -> None:
    st.set_page_config(page_title="ACC102 Volatility Research App", layout="wide")
    st.title("ACC102 Volatility Research App")

    regularized_prediction_path = find_latest_file(PREDICTION_ROOT, "regularized_prediction_int_*.csv")
    boosted_prediction_path = find_latest_file(PREDICTION_ROOT, "boosted_prediction_int_*.csv")
    regularized_summary_path = find_latest_file(MODEL_ROOT, "regularized_model_summary_int_*.json")
    boosted_summary_path = find_latest_file(MODEL_ROOT, "boosted_model_summary_int_*.json")
    comparison_path = find_latest_file(MODEL_ROOT, "model_comparison_int_*.json")
    regularized_walk_forward_path = find_latest_file(
        MODEL_ROOT,
        "walk_forward_regularized_summary_int_*.json",
    )
    boosted_walk_forward_path = find_latest_file(
        MODEL_ROOT,
        "walk_forward_boosted_summary_int_*.json",
    )
    universe_path = find_latest_file(RAW_ROOT, "universe_int_*.csv")

    if not all(
        [
            regularized_prediction_path,
            boosted_prediction_path,
            regularized_summary_path,
            boosted_summary_path,
            comparison_path,
            universe_path,
        ]
    ):
        st.warning("Required model artifacts are missing. Run the workflow scripts first.")
        return

    DF_RegularizedPredictionInt = load_prediction_df(regularized_prediction_path)
    DF_BoostedPredictionInt = load_prediction_df(boosted_prediction_path)
    DF_UniverseInt = load_universe_df(universe_path)
    DF_MarketSnapshotInt = load_market_snapshot_df()
    regularized_summary = load_json_dict(regularized_summary_path)
    boosted_summary = load_json_dict(boosted_summary_path)
    comparison_summary = load_json_dict(comparison_path)
    regularized_walk_forward_summary = (
        load_json_dict(regularized_walk_forward_path)
        if regularized_walk_forward_path is not None
        else None
    )
    boosted_walk_forward_summary = (
        load_json_dict(boosted_walk_forward_path)
        if boosted_walk_forward_path is not None
        else None
    )

    DF_MergedInt = build_merged_prediction_df(
        DF_RegularizedPredictionInt=DF_RegularizedPredictionInt,
        DF_BoostedPredictionInt=DF_BoostedPredictionInt,
    )
    covered_code_set = set(DF_MergedInt["TS_CODE"].unique().tolist())
    coverage_universe_size = len(covered_code_set)
    st.caption(
        f"A simplified regularized-model workflow: start from the {coverage_universe_size}-stock lightweight liquid universe, build a research set, analyze it, and keep boosted ideas as future extension only."
    )
    DF_StockLookupInt = build_stock_lookup_df(
        DF_UniverseInt=DF_UniverseInt,
        DF_MarketSnapshotInt=DF_MarketSnapshotInt,
        covered_code_set=covered_code_set,
    )
    stock_code_option_list = DF_StockLookupInt["TS_CODE"].tolist()
    stock_label_map = get_stock_label_map(DF_StockLookupInt)
    st.session_state["all_stock_code_option_list"] = stock_code_option_list

    initialize_session_state(default_stock_code=stock_code_option_list[0])
    sync_widget_state(stock_code_option_list=stock_code_option_list)

    previous_page_name = st.session_state["page_state"]
    st.radio("Page", PAGE_OPTION_LIST, horizontal=True, key="page_widget", label_visibility="collapsed")
    if st.session_state["page_widget"] != previous_page_name:
        st.session_state["task_state"] = "NONE"
    st.session_state["page_state"] = st.session_state["page_widget"]

    top_col_1, top_col_2 = st.columns([2.6, 1.4])
    selector_df = DF_StockLookupInt.copy()
    selector_code_list = selector_df["TS_CODE"].tolist()
    if st.session_state["selected_code_state"] not in selector_code_list:
        st.session_state["selected_code_state"] = selector_code_list[0]
        st.session_state["stock_widget_sync_pending"] = True

    selected_code = top_col_1.selectbox(
        "Stock Lookup",
        selector_code_list,
        format_func=lambda code_text: stock_label_map.get(code_text, code_text),
        key="stock_widget",
    )
    st.session_state["selected_code_state"] = selected_code

    window_mode = top_col_2.selectbox(
        "Date Window",
        DATE_WINDOW_OPTION_LIST,
        key="date_window_widget",
    )
    st.session_state["date_window_state"] = window_mode

    date_min = pd.Timestamp(DF_MergedInt["TRADE_DATE"].min())
    date_max = pd.Timestamp(DF_MergedInt["TRADE_DATE"].max())
    custom_date_tuple: tuple = (
        date_min.to_pydatetime(),
        date_max.to_pydatetime(),
    )
    if window_mode == "Custom Range":
        custom_date_tuple = st.date_input(
            "Custom Date Range",
            value=(date_min.to_pydatetime(), date_max.to_pydatetime()),
            min_value=date_min.to_pydatetime(),
            max_value=date_max.to_pydatetime(),
        )

    start_date, end_date = resolve_date_filter(
        DF_MergedInt=DF_MergedInt,
        window_mode=window_mode,
        custom_date_tuple=custom_date_tuple,
    )
    DF_MergedFilteredInt = build_filtered_prediction_df(
        DF_MergedInt=DF_MergedInt,
        start_date=start_date,
        end_date=end_date,
    )

    if st.session_state["page_state"] == "Step 2 | Build Research Set":
        st.subheader("Path Selection")
        path_col_1, path_col_2 = st.columns(2)
        if path_col_1.button(
            f"Use Default {coverage_universe_size}-Stock Coverage Universe",
            use_container_width=True,
        ):
            st.session_state["analysis_scope_state"] = "Coverage Universe"
            st.session_state["analysis_scope_widget_sync_pending"] = True
            st.rerun()
        if path_col_2.button("Use Custom Research Basket", use_container_width=True):
            st.session_state["analysis_scope_state"] = "Current Basket"
            st.session_state["analysis_scope_widget_sync_pending"] = True
            st.rerun()

        with st.expander("Research Basket Builder", expanded=True):
            st.caption(
                f"Path 1 keeps the current lightweight {coverage_universe_size}-stock liquid universe. Path 2 lets you define your own research basket from all supported SH/SZ A-shares, including names that will be scored live on demand when needed."
            )
            analysis_scope = st.radio(
                "Current Analysis Path",
                ["Coverage Universe", "Current Basket"],
                horizontal=True,
                key="analysis_scope_widget",
            )
            st.session_state["analysis_scope_state"] = analysis_scope
            weighting_mode = st.radio(
                "Basket Weighting",
                WEIGHTING_OPTION_LIST,
                horizontal=True,
                key="weighting_mode_widget",
            )
            st.session_state["weighting_mode_state"] = weighting_mode
            basket_code_list = st.multiselect(
                "Research Basket",
                stock_code_option_list,
                format_func=lambda code_text: stock_label_map.get(code_text, code_text),
                key="basket_widget",
            )
            st.session_state["basket_codes_state"] = sanitize_basket_code_list(
                basket_code_list=basket_code_list,
                valid_code_list=stock_code_option_list,
            )
            basket_registry_dict = load_basket_registry_dict(str(get_basket_registry_latest_path()))
            saved_basket_option_list = get_basket_name_option_list(basket_registry_dict=basket_registry_dict)
            if st.session_state.get("saved_basket_state", "") not in saved_basket_option_list:
                st.session_state["saved_basket_state"] = ""
                st.session_state["saved_basket_widget_sync_pending"] = True
            saved_basket_name = st.selectbox(
                "Saved Basket",
                [""] + saved_basket_option_list,
                key="saved_basket_widget",
            )
            st.session_state["saved_basket_state"] = saved_basket_name
            basket_name_input = st.text_input(
                "Basket Name",
                key="basket_name_input_widget",
                placeholder="e.g. AI Chain or Bank Basket",
            )
            st.session_state["basket_name_input_state"] = basket_name_input
            basket_button_col_1, basket_button_col_2, basket_button_col_3 = st.columns(3)
            if basket_button_col_1.button("Add Selected Stock To Basket", use_container_width=True):
                add_current_stock_to_basket(ts_code=st.session_state["selected_code_state"])
            if basket_button_col_2.button("Clear Basket", use_container_width=True):
                clear_basket()
            if basket_button_col_3.button("Use Current Scope Top 10", use_container_width=True):
                top_scope_code_list = selector_df["TS_CODE"].head(10).tolist()
                st.session_state["basket_codes_state"] = top_scope_code_list
                st.session_state["analysis_scope_state"] = "Current Basket"
                st.session_state["basket_widget_sync_pending"] = True
                st.session_state["analysis_scope_widget_sync_pending"] = True
                st.rerun()
            action_col_1, action_col_2, action_col_3 = st.columns(3)
            if action_col_1.button("Save Basket", use_container_width=True):
                try:
                    save_named_basket(
                        basket_name=st.session_state["basket_name_input_state"],
                        basket_code_list=st.session_state["basket_codes_state"],
                    )
                    st.session_state["saved_basket_state"] = sanitize_basket_name(
                        st.session_state["basket_name_input_state"]
                    )
                    st.session_state["analysis_scope_state"] = "Current Basket"
                    st.session_state["saved_basket_widget_sync_pending"] = True
                    st.session_state["analysis_scope_widget_sync_pending"] = True
                    st.success("Basket saved.")
                except Exception as exc:
                    st.warning(f"Basket save failed: {exc}")
            if action_col_2.button("Load Basket", use_container_width=True):
                if st.session_state["saved_basket_state"]:
                    load_named_basket_into_state(
                        basket_name=st.session_state["saved_basket_state"],
                        valid_code_list=stock_code_option_list,
                    )
                else:
                    st.warning("Select a saved basket first.")
            if action_col_3.button("Delete Basket", use_container_width=True):
                if st.session_state["saved_basket_state"]:
                    delete_named_basket(basket_name=st.session_state["saved_basket_state"])
                    st.session_state["saved_basket_state"] = ""
                    st.session_state["saved_basket_widget_sync_pending"] = True
                    st.success("Basket deleted.")
                    st.rerun()
                else:
                    st.warning("Select a saved basket first.")
            manage_col_1, manage_col_2 = st.columns(2)
            if manage_col_1.button("Rename Basket", use_container_width=True):
                if st.session_state["saved_basket_state"]:
                    try:
                        renamed_basket_name = rename_named_basket(
                            old_basket_name=st.session_state["saved_basket_state"],
                            new_basket_name=st.session_state["basket_name_input_state"],
                        )
                        st.session_state["saved_basket_state"] = renamed_basket_name
                        st.session_state["basket_name_input_state"] = renamed_basket_name
                        st.session_state["saved_basket_widget_sync_pending"] = True
                        st.session_state["basket_name_input_widget_sync_pending"] = True
                        st.success("Basket renamed.")
                        st.rerun()
                    except Exception as exc:
                        st.warning(f"Basket rename failed: {exc}")
                else:
                    st.warning("Select a saved basket first.")
            if manage_col_2.button("Duplicate Basket", use_container_width=True):
                if st.session_state["saved_basket_state"]:
                    try:
                        duplicated_basket_name = duplicate_named_basket(
                            source_basket_name=st.session_state["saved_basket_state"],
                            target_basket_name=st.session_state["basket_name_input_state"],
                        )
                        st.session_state["saved_basket_state"] = duplicated_basket_name
                        st.session_state["basket_name_input_state"] = duplicated_basket_name
                        st.session_state["saved_basket_widget_sync_pending"] = True
                        st.session_state["basket_name_input_widget_sync_pending"] = True
                        st.success("Basket duplicated.")
                        st.rerun()
                    except Exception as exc:
                        st.warning(f"Basket duplicate failed: {exc}")
                else:
                    st.warning("Select a saved basket first.")
            if st.button("Open Analysis Step", use_container_width=True):
                navigate_to_page(page_name="Step 3 | Analyze Current Set", task_name="NONE")

    DF_BasketPanelInt, DF_BasketStatusInt = build_basket_panel_df(
        basket_code_list=st.session_state["basket_codes_state"],
        DF_MergedFilteredInt=DF_MergedFilteredInt,
        covered_code_set=covered_code_set,
    )
    analysis_scope_label = resolve_active_scope_label(
        analysis_scope=st.session_state["analysis_scope_state"],
        basket_code_list=st.session_state["basket_codes_state"],
    )
    DF_ActivePanelInt = build_active_panel_df(
        analysis_scope=analysis_scope_label,
        DF_MergedFilteredInt=DF_MergedFilteredInt,
        DF_BasketPanelInt=DF_BasketPanelInt,
    )
    DF_ActiveLookupInt = build_active_lookup_df(
        analysis_scope=analysis_scope_label,
        DF_StockLookupInt=DF_StockLookupInt,
        basket_code_list=st.session_state["basket_codes_state"],
    )
    DF_BasketAggregateInt = build_weighted_basket_aggregate_df(
        DF_BasketPanelInt=DF_BasketPanelInt,
        DF_StockLookupInt=DF_StockLookupInt,
        weighting_mode=st.session_state["weighting_mode_state"],
    )

    selected_stock_row = DF_StockLookupInt.loc[
        DF_StockLookupInt["TS_CODE"] == st.session_state["selected_code_state"]
    ].iloc[0]
    status_col_1, status_col_2, status_col_3 = st.columns(3)
    status_col_1.metric("Selected Stock", st.session_state["selected_code_state"])
    status_col_2.metric("Coverage Status", selected_stock_row["COVERAGE_STATUS"])
    status_col_3.metric("Analysis Scope", analysis_scope_label)

    if st.session_state["page_state"] == "Step 1 | Coverage Universe":
        page_renderers.render_overview_page(
            regularized_summary=regularized_summary,
            boosted_summary=boosted_summary,
            comparison_summary=comparison_summary,
            regularized_walk_forward_summary=regularized_walk_forward_summary,
            boosted_walk_forward_summary=boosted_walk_forward_summary,
            DF_ActivePanelInt=DF_ActivePanelInt,
            DF_BasketAggregateInt=DF_BasketAggregateInt,
            DF_BasketStatusInt=DF_BasketStatusInt,
            weighting_mode=st.session_state["weighting_mode_state"],
            analysis_scope_label=analysis_scope_label,
            render_model_control_fn=render_model_control,
            render_metric_cards_fn=render_metric_cards,
            navigate_to_page_fn=navigate_to_page,
        )
    elif st.session_state["page_state"] == "Step 2 | Build Research Set":
        page_renderers.render_basket_page(
            DF_BasketPanelInt=DF_BasketPanelInt,
            DF_BasketAggregateInt=DF_BasketAggregateInt,
            DF_BasketStatusInt=DF_BasketStatusInt,
            DF_StockLookupInt=DF_StockLookupInt,
            weighting_mode=st.session_state["weighting_mode_state"],
        )
    elif st.session_state["page_state"] == "Step 3 | Analyze Current Set":
        page_renderers.render_analysis_page(
            DF_ActivePanelInt=DF_ActivePanelInt,
            DF_ActiveLookupInt=DF_ActiveLookupInt,
            analysis_scope_label=analysis_scope_label,
            DF_MergedFilteredInt=DF_MergedFilteredInt,
            DF_StockLookupInt=DF_StockLookupInt,
            DF_BasketPanelInt=DF_BasketPanelInt,
            DF_BasketAggregateInt=DF_BasketAggregateInt,
            DF_BasketStatusInt=DF_BasketStatusInt,
            format_metric_value_fn=format_metric_value,
            build_explanation_text_fn=build_explanation_text,
            add_current_stock_to_basket_fn=add_current_stock_to_basket,
            build_live_prediction_df_fn=build_live_prediction_df,
            comparison_summary=comparison_summary,
            regularized_walk_forward_summary=regularized_walk_forward_summary,
            boosted_walk_forward_summary=boosted_walk_forward_summary,
            replace_basket_from_code_list_fn=replace_basket_from_code_list,
            append_basket_from_code_list_fn=append_basket_from_code_list,
            navigate_to_stock_fn=navigate_to_stock,
        )
    else:
        page_renderers.render_future_page(
            regularized_summary=regularized_summary,
            boosted_summary=boosted_summary,
            comparison_summary=comparison_summary,
            regularized_walk_forward_summary=regularized_walk_forward_summary,
            boosted_walk_forward_summary=boosted_walk_forward_summary,
        )


if __name__ == "__main__":
    main()
