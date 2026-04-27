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

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.initiation.init_env import ensure_base_directories
from src.utils.log_utils import append_text_log
from src.utils.path_utils import MODEL_ROOT, build_dated_file_path


def find_latest_file(pattern_text: str) -> Path:
    candidate_list = sorted(MODEL_ROOT.glob(pattern_text))
    if not candidate_list:
        raise FileNotFoundError(f"No file found for pattern: {pattern_text}")
    return candidate_list[-1]


def read_json_file(file_path: Path) -> dict:
    return json.loads(file_path.read_text(encoding="utf-8"))


def build_recommendation_text(comparison_dict: dict) -> tuple[str, list[str]]:
    holdout_best_model = comparison_dict.get("BEST_MODEL_BY_RMSE", "UNKNOWN")
    walk_forward_delta = comparison_dict.get("DELTA_RMSE_BOOSTED_VS_REGULARIZED_WALK_FORWARD")
    reason_list: list[str] = []
    if holdout_best_model == "REGULARIZED":
        reason_list.append("regularized wins the main held-out benchmark")
    if walk_forward_delta is not None and walk_forward_delta < 0:
        reason_list.append("boosted is slightly better on aggregate walk-forward RMSE")
    reason_list.append("regularized remains easier to explain and safer to present as the default app model")
    if holdout_best_model == "REGULARIZED":
        recommendation_text = "LOCK_REGULARIZED_AS_DEFAULT"
    else:
        recommendation_text = "KEEP_COMPARISON_OPEN"
    return recommendation_text, reason_list


def main() -> dict:
    ensure_base_directories()
    run_date = datetime.now().strftime("%Y%m%d")
    comparison_path = find_latest_file("model_comparison_int_*.json")
    regularized_path = find_latest_file("regularized_model_summary_int_*.json")
    boosted_path = find_latest_file("boosted_model_summary_int_*.json")
    regularized_walk_forward_path = find_latest_file("walk_forward_regularized_summary_int_*.json")
    boosted_walk_forward_path = find_latest_file("walk_forward_boosted_summary_int_*.json")

    comparison_dict = read_json_file(comparison_path)
    regularized_dict = read_json_file(regularized_path)
    boosted_dict = read_json_file(boosted_path)
    regularized_walk_forward_dict = read_json_file(regularized_walk_forward_path)
    boosted_walk_forward_dict = read_json_file(boosted_walk_forward_path)

    recommendation_text, reason_list = build_recommendation_text(comparison_dict=comparison_dict)
    artifact_dict = {
        "RUN_DATE": run_date,
        "DECISION_TOPIC": "MODEL_SELECTION_REGULARIZED_VS_BOOSTED",
        "DEFAULT_MODEL_FOR_APP": "REGULARIZED",
        "RECOMMENDATION": recommendation_text,
        "HOLDOUT_VIEW": {
            "REGULARIZED_RMSE": regularized_dict["TEST_METRICS"]["RMSE"],
            "BOOSTED_RMSE": boosted_dict["TEST_METRICS"]["RMSE"],
            "BEST_MODEL": comparison_dict.get("BEST_MODEL_BY_RMSE", "UNKNOWN"),
            "DELTA_RMSE_BOOSTED_VS_REGULARIZED": comparison_dict.get("DELTA_RMSE_BOOSTED_VS_REGULARIZED"),
        },
        "WALK_FORWARD_VIEW": {
            "REGULARIZED_RMSE": regularized_walk_forward_dict["AGGREGATE_TEST_METRICS"]["RMSE"],
            "BOOSTED_RMSE": boosted_walk_forward_dict["AGGREGATE_TEST_METRICS"]["RMSE"],
            "DELTA_RMSE_BOOSTED_VS_REGULARIZED": comparison_dict.get(
                "DELTA_RMSE_BOOSTED_VS_REGULARIZED_WALK_FORWARD"
            ),
        },
        "WHY_RANKING_DIFFERS": [
            "holdout uses one late time split and amplifies recent-regime sensitivity",
            "walk-forward averages many rolling windows and can reward a model that adapts better across regimes",
            "boosted may capture nonlinearity that appears in rolling windows but still overreacts on the final holdout block",
        ],
        "DECISION_RULE": [
            "prefer the simpler and more explainable model when the held-out gap is large",
            "do not promote boosted to default unless it improves both holdout and walk-forward in a consistent direction",
            "use further feature expansion rather than more blind tree tuning if the evaluation picture remains mixed",
        ],
        "CURRENT_REASONS": reason_list,
        "NEXT_ACTION_OPTIONS": [
            "lock regularized as the final submission model and keep boosted as a comparison branch",
            "add one high-coverage non-price feature layer and rerun the same comparison before changing the default model",
        ],
        "SOURCE_FILES": {
            "COMPARISON": str(comparison_path),
            "REGULARIZED_SUMMARY": str(regularized_path),
            "BOOSTED_SUMMARY": str(boosted_path),
            "REGULARIZED_WALK_FORWARD": str(regularized_walk_forward_path),
            "BOOSTED_WALK_FORWARD": str(boosted_walk_forward_path),
        },
    }

    json_path = build_dated_file_path(
        folder_path=MODEL_ROOT,
        stem_name="model_decision_artifact_int",
        date_text=run_date,
        suffix=".json",
    )
    json_path.write_text(json.dumps(artifact_dict, ensure_ascii=False, indent=2), encoding="utf-8")

    markdown_path = PROJECT_ROOT / f"MODEL_DECISION_ARTIFACT_{run_date}.md"
    markdown_text = f"""# Model Decision Artifact - {run_date}

## Decision

- Default app / submission model: `REGULARIZED`
- Comparison model: `BOOSTED`
- Recommendation code: `{artifact_dict['RECOMMENDATION']}`

## Holdout View

- Regularized RMSE: `{artifact_dict['HOLDOUT_VIEW']['REGULARIZED_RMSE']:.6f}`
- Boosted RMSE: `{artifact_dict['HOLDOUT_VIEW']['BOOSTED_RMSE']:.6f}`
- Best holdout model: `{artifact_dict['HOLDOUT_VIEW']['BEST_MODEL']}`
- Boosted minus regularized holdout RMSE: `{artifact_dict['HOLDOUT_VIEW']['DELTA_RMSE_BOOSTED_VS_REGULARIZED']:.6f}`

## Walk-Forward View

- Regularized walk-forward RMSE: `{artifact_dict['WALK_FORWARD_VIEW']['REGULARIZED_RMSE']:.6f}`
- Boosted walk-forward RMSE: `{artifact_dict['WALK_FORWARD_VIEW']['BOOSTED_RMSE']:.6f}`
- Boosted minus regularized walk-forward RMSE: `{artifact_dict['WALK_FORWARD_VIEW']['DELTA_RMSE_BOOSTED_VS_REGULARIZED']:.6f}`

## Why The Ranking Differs

""" + "\n".join(f"- {one_reason}" for one_reason in artifact_dict["WHY_RANKING_DIFFERS"]) + """

## Decision Rule

""" + "\n".join(f"- {one_rule}" for one_rule in artifact_dict["DECISION_RULE"]) + """

## Current Reasons

""" + "\n".join(f"- {one_reason}" for one_reason in artifact_dict["CURRENT_REASONS"]) + """

## Next Actions

""" + "\n".join(f"- {one_action}" for one_action in artifact_dict["NEXT_ACTION_OPTIONS"]) + "\n"
    markdown_path.write_text(markdown_text, encoding="utf-8")

    append_text_log(
        log_path=PROJECT_ROOT / "logs" / "workflow.log",
        message_text=f"Model decision artifact completed -> {json_path}",
    )
    return {
        "RUN_DATE": run_date,
        "JSON_FILE": str(json_path),
        "MARKDOWN_FILE": str(markdown_path),
        "RECOMMENDATION": recommendation_text,
    }


if __name__ == "__main__":
    Summary = main()
    print(json.dumps(Summary, ensure_ascii=False, indent=2))
