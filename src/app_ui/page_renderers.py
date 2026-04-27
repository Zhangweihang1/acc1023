from __future__ import annotations

from collections.abc import Callable

import pandas as pd
import plotly.express as px
import streamlit as st


def build_walk_forward_fold_df(
    regularized_walk_forward_summary: dict | None,
    boosted_walk_forward_summary: dict | None,
) -> pd.DataFrame:
    frame_list: list[pd.DataFrame] = []
    if regularized_walk_forward_summary is not None:
        DF_RegularizedFoldInt = pd.DataFrame(
            regularized_walk_forward_summary.get("FOLD_SUMMARY", [])
        )
        if not DF_RegularizedFoldInt.empty:
            DF_RegularizedFoldInt["MODEL_NAME"] = "REGULARIZED"
            DF_RegularizedFoldInt["RMSE"] = DF_RegularizedFoldInt["TEST_METRICS"].map(
                lambda metric_dict: metric_dict.get("RMSE")
            )
            DF_RegularizedFoldInt["R2"] = DF_RegularizedFoldInt["TEST_METRICS"].map(
                lambda metric_dict: metric_dict.get("R2")
            )
            frame_list.append(
                DF_RegularizedFoldInt[
                    ["FOLD_ID", "TRAIN_END_DATE", "TEST_START_DATE", "TEST_END_DATE", "RMSE", "R2", "MODEL_NAME"]
                ].copy()
            )
    if boosted_walk_forward_summary is not None:
        DF_BoostedFoldInt = pd.DataFrame(boosted_walk_forward_summary.get("FOLD_SUMMARY", []))
        if not DF_BoostedFoldInt.empty:
            DF_BoostedFoldInt["MODEL_NAME"] = "BOOSTED"
            DF_BoostedFoldInt["RMSE"] = DF_BoostedFoldInt["TEST_METRICS"].map(
                lambda metric_dict: metric_dict.get("RMSE")
            )
            DF_BoostedFoldInt["R2"] = DF_BoostedFoldInt["TEST_METRICS"].map(
                lambda metric_dict: metric_dict.get("R2")
            )
            frame_list.append(
                DF_BoostedFoldInt[
                    ["FOLD_ID", "TRAIN_END_DATE", "TEST_START_DATE", "TEST_END_DATE", "RMSE", "R2", "MODEL_NAME"]
                ].copy()
            )
    if not frame_list:
        return pd.DataFrame()
    DF_WalkForwardFoldInt = pd.concat(frame_list, ignore_index=True)
    DF_WalkForwardFoldInt["TEST_START_DATE"] = pd.to_datetime(DF_WalkForwardFoldInt["TEST_START_DATE"])
    DF_WalkForwardFoldInt["TEST_END_DATE"] = pd.to_datetime(DF_WalkForwardFoldInt["TEST_END_DATE"])
    return DF_WalkForwardFoldInt.sort_values(by=["FOLD_ID", "MODEL_NAME"]).reset_index(drop=True)


def build_prediction_bucket_df(DF_InputInt: pd.DataFrame) -> pd.DataFrame:
    DF_BucketInt = DF_InputInt[["FUTURE_RV_5", "REGULARIZED_PRED"]].dropna().copy()
    if DF_BucketInt.empty:
        return pd.DataFrame()
    bucket_count = min(5, DF_BucketInt["REGULARIZED_PRED"].nunique())
    if bucket_count < 2:
        return pd.DataFrame()
    DF_BucketInt["PRED_BUCKET"] = pd.qcut(
        DF_BucketInt["REGULARIZED_PRED"],
        q=bucket_count,
        labels=[f"Q{i}" for i in range(1, bucket_count + 1)],
        duplicates="drop",
    )
    return (
        DF_BucketInt.groupby("PRED_BUCKET", as_index=False)
        .agg(
            ACTUAL_MEAN=("FUTURE_RV_5", "mean"),
            PREDICTED_MEAN=("REGULARIZED_PRED", "mean"),
            ROW_COUNT=("REGULARIZED_PRED", "size"),
        )
        .sort_values("PRED_BUCKET")
        .reset_index(drop=True)
    )


def add_quantile_group_column(
    DF_InputInt: pd.DataFrame,
    source_column: str,
    group_column: str,
    label_prefix: str,
) -> pd.DataFrame:
    DF_OutputInt = DF_InputInt.copy()
    DF_OutputInt[source_column] = pd.to_numeric(DF_OutputInt[source_column], errors="coerce")
    non_null_count = int(DF_OutputInt[source_column].notna().sum())
    unique_count = int(DF_OutputInt[source_column].nunique(dropna=True))
    if non_null_count < 3 or unique_count < 3:
        DF_OutputInt[group_column] = "Not Enough Variation"
        return DF_OutputInt
    bucket_count = min(3, unique_count)
    DF_OutputInt[group_column] = pd.qcut(
        DF_OutputInt[source_column],
        q=bucket_count,
        labels=[f"{label_prefix} {i}" for i in range(1, bucket_count + 1)],
        duplicates="drop",
    )
    DF_OutputInt[group_column] = DF_OutputInt[group_column].astype(str)
    return DF_OutputInt


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
    render_model_control_fn: Callable[[], str],
    render_metric_cards_fn: Callable[[str, dict], None],
    navigate_to_page_fn: Callable[[str, str], None],
) -> None:
    st.header("Step 1 | Coverage Universe")
    if DF_ActivePanelInt.empty:
        st.warning("No rows are available for the selected date window.")
        return
    coverage_universe_size = int(DF_ActivePanelInt["TS_CODE"].nunique())
    st.markdown(
        f"""
        This project starts from a fixed **{coverage_universe_size}-stock lightweight liquid A-share universe**.
        The universe is not random. It is built from the AKShare market snapshot with three simple rules:

        1. keep Shanghai and Shenzhen A-shares only
        2. remove `ST` and delisting-risk names
        3. rank by turnover and keep the current lightweight coverage sample
        """
    )
    st.caption(f"Current analysis scope: {analysis_scope_label}")

    render_metric_cards_fn("Regularized Model", regularized_summary)
    summary_col_1, summary_col_2, summary_col_3 = st.columns(3)
    summary_col_1.metric("Default Model", "Regularized")
    summary_col_2.metric("Best Holdout Model", comparison_summary.get("BEST_MODEL_BY_RMSE", "N/A"))
    summary_col_3.metric("Coverage Universe Size", str(DF_ActivePanelInt["TS_CODE"].nunique()))

    if regularized_walk_forward_summary is not None:
        st.subheader("Regularized Stability")
        walk_regularized_metrics = regularized_walk_forward_summary["AGGREGATE_TEST_METRICS"]
        walk_col_1, walk_col_2, walk_col_3 = st.columns(3)
        walk_col_1.metric("Regularized WF RMSE", f"{walk_regularized_metrics['RMSE']:.6f}")
        walk_col_2.metric("Regularized WF R2", f"{walk_regularized_metrics['R2']:.6f}")
        walk_col_3.metric("Holdout RMSE", f"{regularized_summary['TEST_METRICS']['RMSE']:.6f}")

    latest_date = DF_ActivePanelInt["TRADE_DATE"].max()
    DF_LatestInt = DF_ActivePanelInt.loc[DF_ActivePanelInt["TRADE_DATE"] == latest_date].copy()
    DF_LatestInt["REGULARIZED_ABS_ERROR"] = (
        DF_LatestInt["REGULARIZED_PRED"] - DF_LatestInt["FUTURE_RV_5"]
    ).abs()
    DF_FitInt = DF_ActivePanelInt[["FUTURE_RV_5", "REGULARIZED_PRED"]].dropna().copy()

    st.subheader(f"Latest {coverage_universe_size}-Stock Snapshot")
    st.caption(f"Latest prediction date: {latest_date.date()}")
    st.dataframe(
        DF_LatestInt[["TS_CODE", "FUTURE_RV_5", "REGULARIZED_PRED", "REGULARIZED_ABS_ERROR"]].sort_values(
            "REGULARIZED_PRED",
            ascending=False,
        ),
        use_container_width=True,
        hide_index=True,
    )

    if not DF_FitInt.empty:
        st.subheader("Regularized Fit View")
        fit_fig = px.scatter(
            DF_FitInt.sample(min(2000, len(DF_FitInt)), random_state=42),
            x="FUTURE_RV_5",
            y="REGULARIZED_PRED",
            trendline="ols",
            title="Actual vs Regularized Prediction",
        )
        st.plotly_chart(fit_fig, use_container_width=True)

    st.subheader("Next Step")
    st.write(
        f"If this default {coverage_universe_size}-stock universe already matches your research need, go straight to Step 3. "
        "If not, go to Step 2 and build your own research basket from any supported stock."
    )
    if st.button("Go To Step 2 | Build Research Set", use_container_width=True):
        navigate_to_page_fn("Step 2 | Build Research Set", "NONE")

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
    render_model_control_fn: Callable[[], str],
    navigate_to_stock_fn: Callable[[str], None],
) -> None:
    st.header("Market")
    model_view = render_model_control_fn()
    st.session_state["display_model_state"] = model_view
    if DF_ActivePanelInt.empty:
        st.warning("No rows are available for the selected date window.")
        return
    st.caption(f"Current analysis scope: {analysis_scope_label}")

    latest_date = DF_ActivePanelInt["TRADE_DATE"].max()
    DF_LatestInt = DF_ActivePanelInt.loc[DF_ActivePanelInt["TRADE_DATE"] == latest_date].copy()
    DF_LatestInt = DF_LatestInt.merge(
        DF_ActiveLookupInt[["TS_CODE", "SEC_NAME", "TURNOVER_AMOUNT", "LIQUIDITY_RANK"]],
        on="TS_CODE",
        how="left",
    )
    active_prediction_column = "BOOSTED_PRED" if model_view == "Boosted" else "REGULARIZED_PRED"

    if st.session_state["task_state"] == "TOP_RISK":
        st.info("Quick task active: Top Risk Picks Today")
        DF_LatestInt = DF_LatestInt.sort_values(active_prediction_column, ascending=False).head(20)

    st.dataframe(
        DF_LatestInt[
            ["TS_CODE", "SEC_NAME", "TURNOVER_AMOUNT", "LIQUIDITY_RANK", "FUTURE_RV_5", "REGULARIZED_PRED", "BOOSTED_PRED"]
        ].sort_values(active_prediction_column, ascending=False),
        use_container_width=True,
        hide_index=True,
    )

    selected_market_code = st.selectbox(
        "Open Stock From Current Market View",
        DF_LatestInt["TS_CODE"].tolist(),
        format_func=lambda code_text: f"{code_text} | {DF_LatestInt.loc[DF_LatestInt['TS_CODE'] == code_text, 'SEC_NAME'].iloc[0]}",
    )
    if st.button("Open Selected Stock", use_container_width=True):
        navigate_to_stock_fn(selected_market_code)

    fig = px.histogram(
        DF_LatestInt,
        x=active_prediction_column,
        nbins=30,
        title=f"Distribution of {active_prediction_column}",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_basket_page(
    DF_BasketPanelInt: pd.DataFrame,
    DF_BasketAggregateInt: pd.DataFrame,
    DF_BasketStatusInt: pd.DataFrame,
    DF_StockLookupInt: pd.DataFrame,
    weighting_mode: str,
) -> None:
    st.header("Step 2 | Build Research Set")
    coverage_universe_size = int(
        (DF_StockLookupInt["COVERAGE_STATUS"] == "Covered").sum()
    )
    st.write(
        f"You now have two research paths: keep the current {coverage_universe_size}-stock lightweight liquid universe, or build a custom research basket from supported A-shares. "
        "The current basket summary below shows what will be used when the analysis path is set to `Current Basket`."
    )
    if DF_BasketStatusInt.empty:
        st.info(
            f"No custom basket is selected yet. You can still continue with the default {coverage_universe_size}-stock universe."
        )
        return

    basket_ready_count = int((DF_BasketStatusInt["STATUS"] == "Ready").sum())
    basket_live_count = int((DF_BasketStatusInt["SOURCE_MODE"] == "Live Fetch").sum())
    basket_metric_col_1, basket_metric_col_2, basket_metric_col_3 = st.columns(3)
    basket_metric_col_1.metric("Basket Members", str(len(DF_BasketStatusInt)))
    basket_metric_col_2.metric("Ready Members", str(basket_ready_count))
    basket_metric_col_3.metric("Live Members", str(basket_live_count))
    st.caption(f"Basket weighting mode: {weighting_mode}")
    st.dataframe(DF_BasketStatusInt, use_container_width=True, hide_index=True)

    if DF_BasketAggregateInt.empty:
        st.warning("No usable basket rows are available for the current date window.")
        return

    fig = px.line(
        DF_BasketAggregateInt,
        x="TRADE_DATE",
        y=["FUTURE_RV_5_MEAN", "REGULARIZED_PRED_MEAN"],
        title="Current Basket: Actual vs Regularized Prediction",
    )
    st.plotly_chart(fig, use_container_width=True)

    latest_date = DF_BasketAggregateInt["TRADE_DATE"].max()
    DF_LatestBasketInt = DF_BasketPanelInt.loc[DF_BasketPanelInt["TRADE_DATE"] == latest_date].copy()
    DF_LatestBasketInt = DF_LatestBasketInt.merge(
        DF_StockLookupInt[["TS_CODE", "SEC_NAME", "COVERAGE_STATUS"]],
        on="TS_CODE",
        how="left",
    )
    st.subheader("Latest Basket Constituents")
    st.caption(f"Latest basket date: {latest_date.date()}")
    st.dataframe(
        DF_LatestBasketInt[
            ["TS_CODE", "SEC_NAME", "COVERAGE_STATUS", "FUTURE_RV_5", "REGULARIZED_PRED"]
        ].sort_values("TS_CODE"),
        use_container_width=True,
        hide_index=True,
    )


def render_analysis_page(
    DF_ActivePanelInt: pd.DataFrame,
    DF_ActiveLookupInt: pd.DataFrame,
    analysis_scope_label: str,
    DF_MergedFilteredInt: pd.DataFrame,
    DF_StockLookupInt: pd.DataFrame,
    DF_BasketPanelInt: pd.DataFrame,
    DF_BasketAggregateInt: pd.DataFrame,
    DF_BasketStatusInt: pd.DataFrame,
    format_metric_value_fn: Callable[[float | int | None], str],
    build_explanation_text_fn: Callable[[pd.DataFrame, pd.DataFrame, str, bool], str],
    add_current_stock_to_basket_fn: Callable[[str], None],
    build_live_prediction_df_fn: Callable[[str], pd.DataFrame],
    comparison_summary: dict,
    regularized_walk_forward_summary: dict | None,
    boosted_walk_forward_summary: dict | None,
    replace_basket_from_code_list_fn: Callable[[list[str]], None],
    append_basket_from_code_list_fn: Callable[[list[str]], None],
    navigate_to_stock_fn: Callable[[str], None],
) -> None:
    st.header("Step 3 | Analyze Current Set")
    if DF_ActivePanelInt.empty:
        st.warning("No rows are available for the selected date window.")
        return
    st.caption(f"Current analysis scope: {analysis_scope_label}")

    latest_date = DF_ActivePanelInt["TRADE_DATE"].max()
    DF_LatestInt = DF_ActivePanelInt.loc[DF_ActivePanelInt["TRADE_DATE"] == latest_date].copy()
    DF_LatestInt = DF_LatestInt.merge(
        DF_ActiveLookupInt[["TS_CODE", "SEC_NAME", "TURNOVER_AMOUNT", "LIQUIDITY_RANK"]],
        on="TS_CODE",
        how="left",
    )
    DF_LatestInt["REGULARIZED_ABS_ERROR"] = (
        DF_LatestInt["REGULARIZED_PRED"] - DF_LatestInt["FUTURE_RV_5"]
    ).abs()
    DF_AnalysisInt = DF_ActivePanelInt[["TRADE_DATE", "TS_CODE", "FUTURE_RV_5", "REGULARIZED_PRED"]].dropna().copy()
    DF_AnalysisInt = DF_AnalysisInt.merge(
        DF_ActiveLookupInt[["TS_CODE", "SEC_NAME", "TURNOVER_AMOUNT", "LIQUIDITY_RANK"]].drop_duplicates("TS_CODE"),
        on="TS_CODE",
        how="left",
    )
    DF_AnalysisInt["RESIDUAL"] = DF_AnalysisInt["REGULARIZED_PRED"] - DF_AnalysisInt["FUTURE_RV_5"]
    DF_AnalysisInt["ABS_ERROR"] = DF_AnalysisInt["RESIDUAL"].abs()
    DF_AnalysisInt = add_quantile_group_column(
        DF_InputInt=DF_AnalysisInt,
        source_column="LIQUIDITY_RANK",
        group_column="LIQUIDITY_GROUP",
        label_prefix="Liquidity Tier",
    )
    DF_AnalysisInt = add_quantile_group_column(
        DF_InputInt=DF_AnalysisInt,
        source_column="TURNOVER_AMOUNT",
        group_column="TURNOVER_GROUP",
        label_prefix="Turnover Tier",
    )

    overall_mae = float(DF_AnalysisInt["ABS_ERROR"].mean()) if not DF_AnalysisInt.empty else float("nan")
    overall_bias = float(DF_AnalysisInt["RESIDUAL"].mean()) if not DF_AnalysisInt.empty else float("nan")
    overall_corr = float(DF_AnalysisInt["FUTURE_RV_5"].corr(DF_AnalysisInt["REGULARIZED_PRED"])) if len(DF_AnalysisInt) >= 2 else float("nan")

    top_col_1, top_col_2, top_col_3 = st.columns(3)
    top_col_1.metric("Current Set Size", str(DF_ActivePanelInt["TS_CODE"].nunique()))
    top_col_2.metric("Latest Date", str(latest_date.date()))
    top_col_3.metric("Regularized Holdout RMSE", f"{comparison_summary['REGULARIZED_TEST_METRICS']['RMSE']:.6f}")
    summary_col_1, summary_col_2, summary_col_3 = st.columns(3)
    summary_col_1.metric("Current Window MAE", format_metric_value_fn(overall_mae))
    summary_col_2.metric("Current Window Bias", format_metric_value_fn(overall_bias))
    summary_col_3.metric("Actual vs Pred Corr", format_metric_value_fn(overall_corr))

    st.subheader("Set-Level View")
    set_fig = px.histogram(
        DF_LatestInt,
        x="REGULARIZED_PRED",
        nbins=30,
        title="Distribution of Regularized Predicted Volatility",
    )
    st.plotly_chart(set_fig, use_container_width=True)
    st.dataframe(
        DF_LatestInt[
            ["TS_CODE", "SEC_NAME", "FUTURE_RV_5", "REGULARIZED_PRED", "REGULARIZED_ABS_ERROR", "TURNOVER_AMOUNT", "LIQUIDITY_RANK"]
        ].sort_values("REGULARIZED_PRED", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Model Fit Checks")
    check_col_1, check_col_2 = st.columns(2)
    if not DF_AnalysisInt.empty:
        DF_ScatterInt = DF_AnalysisInt.sample(min(3000, len(DF_AnalysisInt)), random_state=42)
        fit_fig = px.scatter(
            DF_ScatterInt,
            x="FUTURE_RV_5",
            y="REGULARIZED_PRED",
            trendline="ols",
            opacity=0.45,
            title="Actual vs Regularized Prediction",
        )
        check_col_1.plotly_chart(fit_fig, use_container_width=True)

        residual_fig = px.histogram(
            DF_AnalysisInt,
            x="RESIDUAL",
            nbins=40,
            title="Residual Distribution",
        )
        check_col_2.plotly_chart(residual_fig, use_container_width=True)

        DF_TimeInt = (
            DF_AnalysisInt.groupby("TRADE_DATE", as_index=False)
            .agg(
                ACTUAL_MEAN=("FUTURE_RV_5", "mean"),
                PREDICTED_MEAN=("REGULARIZED_PRED", "mean"),
                MAE_MEAN=("ABS_ERROR", "mean"),
            )
            .sort_values("TRADE_DATE")
            .reset_index(drop=True)
        )
        time_fig = px.line(
            DF_TimeInt,
            x="TRADE_DATE",
            y=["ACTUAL_MEAN", "PREDICTED_MEAN"],
            title="Average Actual vs Predicted Volatility Through Time",
        )
        st.plotly_chart(time_fig, use_container_width=True)

        error_time_fig = px.line(
            DF_TimeInt,
            x="TRADE_DATE",
            y="MAE_MEAN",
            title="Average Absolute Error Through Time",
        )
        st.plotly_chart(error_time_fig, use_container_width=True)

        DF_BucketSummaryInt = build_prediction_bucket_df(DF_AnalysisInt)
        if not DF_BucketSummaryInt.empty:
            bucket_fig = px.bar(
                DF_BucketSummaryInt.melt(
                    id_vars=["PRED_BUCKET", "ROW_COUNT"],
                    value_vars=["ACTUAL_MEAN", "PREDICTED_MEAN"],
                    var_name="SERIES_NAME",
                    value_name="VALUE",
                ),
                x="PRED_BUCKET",
                y="VALUE",
                color="SERIES_NAME",
                barmode="group",
                title="Prediction Bucket Check",
            )
            st.plotly_chart(bucket_fig, use_container_width=True)
            st.dataframe(DF_BucketSummaryInt, use_container_width=True, hide_index=True)

    st.subheader("Prediction Direction Checks")
    over_under_col_1, over_under_col_2 = st.columns(2)
    DF_ResidualRankInt = DF_AnalysisInt.sort_values("RESIDUAL", ascending=False).copy()
    over_under_col_1.dataframe(
        DF_ResidualRankInt[
            ["TS_CODE", "SEC_NAME", "TRADE_DATE", "FUTURE_RV_5", "REGULARIZED_PRED", "RESIDUAL", "ABS_ERROR"]
        ].head(20),
        use_container_width=True,
        hide_index=True,
    )
    over_under_col_1.caption("Top Over-Predicted: predicted volatility is much higher than actual volatility.")
    over_under_col_2.dataframe(
        DF_ResidualRankInt[
            ["TS_CODE", "SEC_NAME", "TRADE_DATE", "FUTURE_RV_5", "REGULARIZED_PRED", "RESIDUAL", "ABS_ERROR"]
        ].tail(20).sort_values("RESIDUAL", ascending=True),
        use_container_width=True,
        hide_index=True,
    )
    over_under_col_2.caption("Top Under-Predicted: predicted volatility is much lower than actual volatility.")

    st.subheader("Grouped Stability View")
    DF_LiquidityGroupInt = (
        DF_AnalysisInt.groupby("LIQUIDITY_GROUP", as_index=False)
        .agg(
            ACTUAL_MEAN=("FUTURE_RV_5", "mean"),
            PREDICTED_MEAN=("REGULARIZED_PRED", "mean"),
            MAE_MEAN=("ABS_ERROR", "mean"),
            BIAS_MEAN=("RESIDUAL", "mean"),
            ROW_COUNT=("TS_CODE", "size"),
        )
        .sort_values("LIQUIDITY_GROUP")
        .reset_index(drop=True)
    )
    DF_TurnoverGroupInt = (
        DF_AnalysisInt.groupby("TURNOVER_GROUP", as_index=False)
        .agg(
            ACTUAL_MEAN=("FUTURE_RV_5", "mean"),
            PREDICTED_MEAN=("REGULARIZED_PRED", "mean"),
            MAE_MEAN=("ABS_ERROR", "mean"),
            BIAS_MEAN=("RESIDUAL", "mean"),
            ROW_COUNT=("TS_CODE", "size"),
        )
        .sort_values("TURNOVER_GROUP")
        .reset_index(drop=True)
    )
    group_col_1, group_col_2 = st.columns(2)
    if not DF_LiquidityGroupInt.empty:
        liquidity_fig = px.bar(
            DF_LiquidityGroupInt.melt(
                id_vars=["LIQUIDITY_GROUP", "ROW_COUNT"],
                value_vars=["ACTUAL_MEAN", "PREDICTED_MEAN", "MAE_MEAN"],
                var_name="SERIES_NAME",
                value_name="VALUE",
            ),
            x="LIQUIDITY_GROUP",
            y="VALUE",
            color="SERIES_NAME",
            barmode="group",
            title="Performance by Liquidity Tier",
        )
        group_col_1.plotly_chart(liquidity_fig, use_container_width=True)
        group_col_1.dataframe(DF_LiquidityGroupInt, use_container_width=True, hide_index=True)
    if not DF_TurnoverGroupInt.empty:
        turnover_fig = px.bar(
            DF_TurnoverGroupInt.melt(
                id_vars=["TURNOVER_GROUP", "ROW_COUNT"],
                value_vars=["ACTUAL_MEAN", "PREDICTED_MEAN", "MAE_MEAN"],
                var_name="SERIES_NAME",
                value_name="VALUE",
            ),
            x="TURNOVER_GROUP",
            y="VALUE",
            color="SERIES_NAME",
            barmode="group",
            title="Performance by Turnover Tier",
        )
        group_col_2.plotly_chart(turnover_fig, use_container_width=True)
        group_col_2.dataframe(DF_TurnoverGroupInt, use_container_width=True, hide_index=True)

    st.subheader("Optional Screen-To-Basket Workflow")
    filter_col_1, filter_col_2 = st.columns(2)
    turnover_threshold = filter_col_1.slider(
        "Minimum Turnover Amount",
        min_value=float(DF_LatestInt["TURNOVER_AMOUNT"].fillna(0).min()),
        max_value=float(DF_LatestInt["TURNOVER_AMOUNT"].fillna(0).max()),
        value=float(DF_LatestInt["TURNOVER_AMOUNT"].fillna(0).quantile(0.3)),
    )
    liquidity_threshold = filter_col_2.slider(
        "Maximum Liquidity Rank",
        min_value=int(DF_LatestInt["LIQUIDITY_RANK"].fillna(999999).min()),
        max_value=int(DF_LatestInt["LIQUIDITY_RANK"].fillna(999999).max()),
        value=int(DF_LatestInt["LIQUIDITY_RANK"].fillna(999999).quantile(0.7)),
    )
    DF_FilteredInt = DF_LatestInt.loc[
        (DF_LatestInt["TURNOVER_AMOUNT"].fillna(0) >= turnover_threshold)
        & (DF_LatestInt["LIQUIDITY_RANK"].fillna(999999) <= liquidity_threshold)
    ].copy().sort_values("REGULARIZED_PRED", ascending=False)
    st.caption(f"Filtered stock count: {len(DF_FilteredInt)}")
    st.dataframe(
        DF_FilteredInt[["TS_CODE", "SEC_NAME", "REGULARIZED_PRED", "TURNOVER_AMOUNT", "LIQUIDITY_RANK"]],
        use_container_width=True,
        hide_index=True,
    )
    screen_col_1, screen_col_2 = st.columns(2)
    if screen_col_1.button("Replace Basket With Screen Result", use_container_width=True):
        replace_basket_from_code_list_fn(DF_FilteredInt["TS_CODE"].tolist())
    if screen_col_2.button("Add Screen Result To Basket", use_container_width=True):
        append_basket_from_code_list_fn(DF_FilteredInt["TS_CODE"].tolist())

    st.subheader("Selected Stock Detail")
    selected_code = st.session_state["selected_code_state"]
    is_model_covered = bool(
        DF_StockLookupInt.loc[DF_StockLookupInt["TS_CODE"] == selected_code, "IS_MODEL_COVERED"].iloc[0]
    )
    if is_model_covered:
        DF_SelectedInt = DF_MergedFilteredInt.loc[DF_MergedFilteredInt["TS_CODE"] == selected_code].copy()
    else:
        try:
            with st.spinner(f"Fetching live history and scoring {selected_code}..."):
                DF_SelectedInt = build_live_prediction_df_fn(ts_code=selected_code)
        except Exception as exc:
            st.warning(
                "Live on-demand prediction is currently unavailable for this stock. "
                "The most common reason is insufficient history for the rolling feature windows."
            )
            st.caption(f"Technical detail: {exc}")
            DF_SelectedInt = pd.DataFrame()
    if not DF_SelectedInt.empty:
        stock_name_series = DF_StockLookupInt.loc[DF_StockLookupInt["TS_CODE"] == selected_code, "SEC_NAME"]
        stock_name = stock_name_series.iloc[0] if not stock_name_series.empty else selected_code
        latest_market_date = DF_MergedFilteredInt["TRADE_DATE"].max() if not DF_MergedFilteredInt.empty else DF_SelectedInt["TRADE_DATE"].max()
        DF_LatestMarketInt = DF_MergedFilteredInt.loc[DF_MergedFilteredInt["TRADE_DATE"] == latest_market_date].copy()
        if DF_LatestMarketInt.empty:
            DF_LatestMarketInt = DF_SelectedInt.tail(1).copy()
        latest_row = DF_SelectedInt.sort_values("TRADE_DATE").iloc[-1]
        metric_col_1, metric_col_2, metric_col_3 = st.columns(3)
        metric_col_1.metric("Selected Stock", f"{selected_code} | {stock_name}")
        metric_col_2.metric("Latest Actual Future RV 5", format_metric_value_fn(latest_row["FUTURE_RV_5"]))
        metric_col_3.metric("Latest Regularized Prediction", format_metric_value_fn(latest_row["REGULARIZED_PRED"]))
        st.info(
            build_explanation_text_fn(
                DF_SelectedInt=DF_SelectedInt.sort_values("TRADE_DATE"),
                DF_LatestMarketInt=DF_LatestMarketInt,
                model_view="Regularized",
                is_model_covered=is_model_covered,
            )
        )
        stock_fig = px.line(
            DF_SelectedInt,
            x="TRADE_DATE",
            y=["FUTURE_RV_5", "REGULARIZED_PRED"],
            title=f"{selected_code} - Actual vs Regularized Prediction",
        )
        st.plotly_chart(stock_fig, use_container_width=True)
        if st.button("Add Selected Stock To Basket", use_container_width=True):
            add_current_stock_to_basket_fn(ts_code=selected_code)
    else:
        st.info("Choose another stock if you want a single-name chart under the current date window.")

    st.subheader("Diagnostics")
    DF_DiagnosticInt = DF_ActivePanelInt.copy()
    DF_DiagnosticInt["REGULARIZED_ABS_ERROR"] = (
        DF_DiagnosticInt["REGULARIZED_PRED"] - DF_DiagnosticInt["FUTURE_RV_5"]
    ).abs()
    DF_GroupedInt = DF_DiagnosticInt.groupby("TS_CODE", as_index=False)["REGULARIZED_ABS_ERROR"].mean()
    diag_fig = px.bar(
        DF_GroupedInt.sort_values("REGULARIZED_ABS_ERROR", ascending=False).head(20),
        x="TS_CODE",
        y="REGULARIZED_ABS_ERROR",
        title="Top 20 Average Absolute Error by Stock",
    )
    st.plotly_chart(diag_fig, use_container_width=True)
    if regularized_walk_forward_summary is not None:
        st.caption(
            f"Walk-forward aggregate RMSE={regularized_walk_forward_summary['AGGREGATE_TEST_METRICS']['RMSE']:.6f}, "
            f"R2={regularized_walk_forward_summary['AGGREGATE_TEST_METRICS']['R2']:.6f}."
        )
    if not DF_BasketAggregateInt.empty and not DF_BasketStatusInt.empty:
        st.subheader("Current Basket Aggregation")
        basket_fig = px.line(
            DF_BasketAggregateInt,
            x="TRADE_DATE",
            y=["FUTURE_RV_5_MEAN", "REGULARIZED_PRED_MEAN"],
            title="Current Basket: Actual vs Regularized Prediction",
        )
        st.plotly_chart(basket_fig, use_container_width=True)
        st.dataframe(DF_BasketStatusInt, use_container_width=True, hide_index=True)


def render_screener_page(
    DF_ActivePanelInt: pd.DataFrame,
    DF_ActiveLookupInt: pd.DataFrame,
    analysis_scope_label: str,
    render_model_control_fn: Callable[[], str],
    replace_basket_from_code_list_fn: Callable[[list[str]], None],
    append_basket_from_code_list_fn: Callable[[list[str]], None],
    navigate_to_stock_fn: Callable[[str], None],
) -> None:
    st.header("Screener")
    model_view = render_model_control_fn()
    st.session_state["display_model_state"] = model_view
    if DF_ActivePanelInt.empty:
        st.warning("No rows are available for the selected date window.")
        return
    st.caption(f"Current analysis scope: {analysis_scope_label}")

    latest_date = DF_ActivePanelInt["TRADE_DATE"].max()
    DF_LatestInt = DF_ActivePanelInt.loc[DF_ActivePanelInt["TRADE_DATE"] == latest_date].copy()
    DF_LatestInt = DF_LatestInt.merge(
        DF_ActiveLookupInt[["TS_CODE", "SEC_NAME", "TURNOVER_AMOUNT", "LIQUIDITY_RANK"]],
        on="TS_CODE",
        how="left",
    )
    selected_prediction_column = "BOOSTED_PRED" if model_view == "Boosted" else "REGULARIZED_PRED"
    min_turnover = float(DF_LatestInt["TURNOVER_AMOUNT"].fillna(0).min())
    max_turnover = float(DF_LatestInt["TURNOVER_AMOUNT"].fillna(0).max())
    min_liquidity = int(DF_LatestInt["LIQUIDITY_RANK"].fillna(999999).min())
    max_liquidity = int(DF_LatestInt["LIQUIDITY_RANK"].fillna(999999).max())
    screener_col_1, screener_col_2, screener_col_3 = st.columns(3)
    turnover_threshold = screener_col_1.slider(
        "Minimum Turnover Amount",
        min_value=float(min_turnover),
        max_value=float(max_turnover),
        value=float(min_turnover),
    )
    liquidity_threshold = screener_col_2.slider(
        "Maximum Liquidity Rank",
        min_value=int(min_liquidity),
        max_value=int(max_liquidity),
        value=int(max_liquidity),
    )
    sort_column = screener_col_3.selectbox(
        "Sort Field",
        ["REGULARIZED_PRED", "BOOSTED_PRED", "TURNOVER_AMOUNT", "LIQUIDITY_RANK"],
    )
    DF_FilteredInt = DF_LatestInt.loc[
        (DF_LatestInt["TURNOVER_AMOUNT"].fillna(0) >= turnover_threshold)
        & (DF_LatestInt["LIQUIDITY_RANK"].fillna(999999) <= liquidity_threshold)
    ].copy()

    if st.session_state["task_state"] == "LOW_LIQ_HIGH_VOL":
        st.info("Quick task active: Low-Liquidity High-Vol Names")
        DF_FilteredInt = DF_FilteredInt.sort_values(
            by=["LIQUIDITY_RANK", selected_prediction_column],
            ascending=[True, False],
        ).head(20)
    else:
        DF_FilteredInt = DF_FilteredInt.sort_values(sort_column, ascending=False)

    st.caption(f"Filtered stock count: {len(DF_FilteredInt)}")
    st.dataframe(
        DF_FilteredInt[
            ["TS_CODE", "SEC_NAME", "TURNOVER_AMOUNT", "LIQUIDITY_RANK", "FUTURE_RV_5", "REGULARIZED_PRED", "BOOSTED_PRED"]
        ],
        use_container_width=True,
        hide_index=True,
    )
    if not DF_FilteredInt.empty:
        screen_action_col_1, screen_action_col_2 = st.columns(2)
        if screen_action_col_1.button("Replace Basket With Screen Result", use_container_width=True):
            replace_basket_from_code_list_fn(DF_FilteredInt["TS_CODE"].tolist())
        if screen_action_col_2.button("Add Screen Result To Basket", use_container_width=True):
            append_basket_from_code_list_fn(DF_FilteredInt["TS_CODE"].tolist())

        selected_screen_code = st.selectbox(
            "Open Stock From Screener",
            DF_FilteredInt["TS_CODE"].tolist(),
            format_func=lambda code_text: f"{code_text} | {DF_FilteredInt.loc[DF_FilteredInt['TS_CODE'] == code_text, 'SEC_NAME'].iloc[0]}",
        )
        if st.button("Open Screener Stock", use_container_width=True):
            navigate_to_stock_fn(selected_screen_code)


def render_single_stock_page(
    DF_MergedFilteredInt: pd.DataFrame,
    DF_StockLookupInt: pd.DataFrame,
    render_model_control_fn: Callable[[], str],
    get_active_prediction_column_fn: Callable[[str], str],
    get_display_series_list_fn: Callable[[str], list[str]],
    format_metric_value_fn: Callable[[float | int | None], str],
    build_explanation_text_fn: Callable[[pd.DataFrame, str], str],
    add_current_stock_to_basket_fn: Callable[[str], None],
    build_live_prediction_df_fn: Callable[[str], pd.DataFrame],
) -> None:
    selected_code = st.session_state["selected_code_state"]
    st.header("Single Stock")
    model_view = render_model_control_fn()
    st.session_state["display_model_state"] = model_view
    active_prediction_column = get_active_prediction_column_fn(model_view=model_view)
    DF_SelectedInt = DF_MergedFilteredInt.loc[DF_MergedFilteredInt["TS_CODE"] == selected_code].copy()

    selected_stock_row = DF_StockLookupInt.loc[DF_StockLookupInt["TS_CODE"] == selected_code].iloc[0]
    coverage_status = selected_stock_row["COVERAGE_STATUS"]
    stock_mode_text = "Persisted Coverage" if coverage_status == "Covered" else "Live Fetch"
    st.caption(f"Selected stock mode: {stock_mode_text}")

    if DF_SelectedInt.empty and coverage_status != "Covered":
        with st.spinner(f"Fetching live prediction for {selected_code}..."):
            try:
                DF_SelectedInt = build_live_prediction_df_fn(ts_code=selected_code)
            except Exception as exc:
                st.error(f"Live fetch failed: {exc}")
                return
    if DF_SelectedInt.empty:
        st.warning("No rows are available for the selected stock under the chosen date window.")
        return

    top_metric_col_1, top_metric_col_2, top_metric_col_3 = st.columns(3)
    latest_row = DF_SelectedInt.sort_values("TRADE_DATE").iloc[-1]
    top_metric_col_1.metric("Selected Stock", selected_code)
    top_metric_col_2.metric(
        active_prediction_column,
        format_metric_value_fn(latest_row[active_prediction_column]),
    )
    top_metric_col_3.metric(
        "Boosted - Regularized",
        format_metric_value_fn(latest_row["BOOSTED_PRED"] - latest_row["REGULARIZED_PRED"]),
    )
    if st.button("Add Selected Stock To Basket", use_container_width=True):
        add_current_stock_to_basket_fn(ts_code=selected_code)

    st.info(build_explanation_text_fn(DF_SelectedInt=DF_SelectedInt, active_prediction_column=active_prediction_column))

    series_column_list = get_display_series_list_fn(model_view=model_view)
    fig = px.line(
        DF_SelectedInt,
        x="TRADE_DATE",
        y=series_column_list,
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
    render_model_control_fn: Callable[[], str],
) -> None:
    st.header("Diagnostics")
    model_view = render_model_control_fn()
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
        active_error_column = "BOOSTED_ABS_ERROR" if model_view == "Boosted" else "REGULARIZED_ABS_ERROR"
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

    DF_WalkForwardFoldInt = build_walk_forward_fold_df(
        regularized_walk_forward_summary=regularized_walk_forward_summary,
        boosted_walk_forward_summary=boosted_walk_forward_summary,
    )
    if not DF_WalkForwardFoldInt.empty:
        st.subheader("Fold-Level Walk-Forward Diagnostics")
        metric_name = st.selectbox("Fold Metric", ["RMSE", "R2"], key="fold_metric_widget")
        DF_FoldMetricInt = DF_WalkForwardFoldInt.copy()
        if model_view == "Regularized":
            DF_FoldMetricInt = DF_FoldMetricInt.loc[DF_FoldMetricInt["MODEL_NAME"] == "REGULARIZED"].copy()
        elif model_view == "Boosted":
            DF_FoldMetricInt = DF_FoldMetricInt.loc[DF_FoldMetricInt["MODEL_NAME"] == "BOOSTED"].copy()
        fig_fold = px.line(
            DF_FoldMetricInt,
            x="FOLD_ID",
            y=metric_name,
            color="MODEL_NAME",
            hover_data=["TEST_START_DATE", "TEST_END_DATE"],
            title=f"Walk-Forward {metric_name} by Fold",
            markers=True,
        )
        st.plotly_chart(fig_fold, use_container_width=True)
        st.dataframe(
            DF_FoldMetricInt[["FOLD_ID", "TEST_START_DATE", "TEST_END_DATE", "MODEL_NAME", "RMSE", "R2"]],
            use_container_width=True,
            hide_index=True,
        )

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
            walk_forward_payload["BOOSTED_WALK_FORWARD"] = boosted_walk_forward_summary["AGGREGATE_TEST_METRICS"]
        st.json(walk_forward_payload)


def render_future_page(
    regularized_summary: dict,
    boosted_summary: dict,
    comparison_summary: dict,
    regularized_walk_forward_summary: dict | None,
    boosted_walk_forward_summary: dict | None,
) -> None:
    st.header("Step 4 | Future Extension")
    st.subheader("Why Boosted Is Not In The Main Interface")
    st.markdown(
        """
        - The app now uses the **regularized model** as the only mainline display model.
        - This keeps the interface simpler and keeps the narrative aligned with the final submission decision.
        - The boosted branch is still valuable as a research extension, but not stable enough to deserve equal surface area in the current UI.
        """
    )
    st.subheader("Current Evidence")
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
    st.subheader("Where Boosted Still Looks Interesting")
    st.markdown(
        """
        - Boosted is not completely discarded. In rolling evaluation it can look slightly better in some time slices.
        - That suggests the tree model may benefit more than ridge from richer non-price features or stronger event-level signals.
        - In other words, boosted is now a **future improvement direction**, not the current production-facing story.
        """
    )
    st.subheader("How We Would Improve Boosted Later")
    st.markdown(
        """
        - Add higher-coverage non-price and event features
        - Move from lightweight `B + B` sources toward stronger `A + A` data coverage
        - Persist trained serving artifacts instead of refitting inside the app
        - Re-test boosted under the same decision artifact before promoting it
        """
    )
