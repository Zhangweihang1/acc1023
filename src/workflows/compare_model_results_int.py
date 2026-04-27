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


def read_json_file(file_path: Path) -> dict:
    return json.loads(file_path.read_text(encoding="utf-8"))


def find_latest_summary(pattern_text: str) -> Path:
    candidate_list = sorted(MODEL_ROOT.glob(pattern_text))
    if not candidate_list:
        raise FileNotFoundError(f"No file found for pattern: {pattern_text}")
    return candidate_list[-1]


def main() -> dict:
    ensure_base_directories()
    run_date = datetime.now().strftime("%Y%m%d")
    baseline_path = find_latest_summary("baseline_model_summary_int_*.json")
    boosted_path = find_latest_summary("boosted_model_summary_int_*.json")
    baseline_summary = read_json_file(baseline_path)
    boosted_summary = read_json_file(boosted_path)
    regularized_candidate_list = sorted(MODEL_ROOT.glob("regularized_model_summary_int_*.json"))
    regularized_summary = None
    regularized_path = None
    if regularized_candidate_list:
        regularized_path = regularized_candidate_list[-1]
        regularized_summary = read_json_file(regularized_path)
    walk_forward_candidate_list = sorted(MODEL_ROOT.glob("walk_forward_summary_int_*.json"))
    regularized_walk_forward_candidate_list = sorted(
        MODEL_ROOT.glob("walk_forward_regularized_summary_int_*.json")
    )
    boosted_walk_forward_candidate_list = sorted(
        MODEL_ROOT.glob("walk_forward_boosted_summary_int_*.json")
    )

    comparison_dict = {
        "RUN_DATE": run_date,
        "BASELINE_FILE": str(baseline_path),
        "BOOSTED_FILE": str(boosted_path),
        "BASELINE_TEST_METRICS": baseline_summary["TEST_METRICS"],
        "BOOSTED_TEST_METRICS": boosted_summary["TEST_METRICS"],
        "DELTA_RMSE": (
            boosted_summary["TEST_METRICS"]["RMSE"]
            - baseline_summary["TEST_METRICS"]["RMSE"]
        ),
        "DELTA_MAE": (
            boosted_summary["TEST_METRICS"]["MAE"]
            - baseline_summary["TEST_METRICS"]["MAE"]
        ),
        "DELTA_R2": (
            boosted_summary["TEST_METRICS"]["R2"]
            - baseline_summary["TEST_METRICS"]["R2"]
        ),
    }
    if regularized_summary is not None and regularized_path is not None:
        comparison_dict["REGULARIZED_FILE"] = str(regularized_path)
        comparison_dict["REGULARIZED_TEST_METRICS"] = regularized_summary["TEST_METRICS"]
        comparison_dict["DELTA_RMSE_REGULARIZED_VS_BASELINE"] = (
            regularized_summary["TEST_METRICS"]["RMSE"]
            - baseline_summary["TEST_METRICS"]["RMSE"]
        )
        comparison_dict["DELTA_MAE_REGULARIZED_VS_BASELINE"] = (
            regularized_summary["TEST_METRICS"]["MAE"]
            - baseline_summary["TEST_METRICS"]["MAE"]
        )
        comparison_dict["DELTA_R2_REGULARIZED_VS_BASELINE"] = (
            regularized_summary["TEST_METRICS"]["R2"]
            - baseline_summary["TEST_METRICS"]["R2"]
        )
        comparison_dict["DELTA_RMSE_BOOSTED_VS_REGULARIZED"] = (
            boosted_summary["TEST_METRICS"]["RMSE"]
            - regularized_summary["TEST_METRICS"]["RMSE"]
        )
        comparison_dict["DELTA_MAE_BOOSTED_VS_REGULARIZED"] = (
            boosted_summary["TEST_METRICS"]["MAE"]
            - regularized_summary["TEST_METRICS"]["MAE"]
        )
        comparison_dict["DELTA_R2_BOOSTED_VS_REGULARIZED"] = (
            boosted_summary["TEST_METRICS"]["R2"]
            - regularized_summary["TEST_METRICS"]["R2"]
        )

        candidate_metrics_dict = {
            "BASELINE": baseline_summary["TEST_METRICS"],
            "BOOSTED": boosted_summary["TEST_METRICS"],
            "REGULARIZED": regularized_summary["TEST_METRICS"],
        }
        best_model_name = min(
            candidate_metrics_dict.keys(),
            key=lambda model_name: candidate_metrics_dict[model_name]["RMSE"],
        )
        comparison_dict["BEST_MODEL_BY_RMSE"] = best_model_name
        comparison_dict["BEST_MODEL_TEST_METRICS"] = candidate_metrics_dict[best_model_name]

    if walk_forward_candidate_list:
        walk_forward_path = walk_forward_candidate_list[-1]
        walk_forward_summary = read_json_file(walk_forward_path)
        comparison_dict["BASELINE_WALK_FORWARD_FILE"] = str(walk_forward_path)
        comparison_dict["BASELINE_WALK_FORWARD_METRICS"] = walk_forward_summary[
            "AGGREGATE_TEST_METRICS"
        ]
    if regularized_walk_forward_candidate_list:
        regularized_walk_forward_path = regularized_walk_forward_candidate_list[-1]
        regularized_walk_forward_summary = read_json_file(regularized_walk_forward_path)
        comparison_dict["REGULARIZED_WALK_FORWARD_FILE"] = str(regularized_walk_forward_path)
        comparison_dict["REGULARIZED_WALK_FORWARD_METRICS"] = regularized_walk_forward_summary[
            "AGGREGATE_TEST_METRICS"
        ]
    if boosted_walk_forward_candidate_list:
        boosted_walk_forward_path = boosted_walk_forward_candidate_list[-1]
        boosted_walk_forward_summary = read_json_file(boosted_walk_forward_path)
        comparison_dict["BOOSTED_WALK_FORWARD_FILE"] = str(boosted_walk_forward_path)
        comparison_dict["BOOSTED_WALK_FORWARD_METRICS"] = boosted_walk_forward_summary[
            "AGGREGATE_TEST_METRICS"
        ]
    if (
        "REGULARIZED_WALK_FORWARD_METRICS" in comparison_dict
        and "BOOSTED_WALK_FORWARD_METRICS" in comparison_dict
    ):
        comparison_dict["DELTA_RMSE_BOOSTED_VS_REGULARIZED_WALK_FORWARD"] = (
            comparison_dict["BOOSTED_WALK_FORWARD_METRICS"]["RMSE"]
            - comparison_dict["REGULARIZED_WALK_FORWARD_METRICS"]["RMSE"]
        )
        comparison_dict["DELTA_MAE_BOOSTED_VS_REGULARIZED_WALK_FORWARD"] = (
            comparison_dict["BOOSTED_WALK_FORWARD_METRICS"]["MAE"]
            - comparison_dict["REGULARIZED_WALK_FORWARD_METRICS"]["MAE"]
        )
        comparison_dict["DELTA_R2_BOOSTED_VS_REGULARIZED_WALK_FORWARD"] = (
            comparison_dict["BOOSTED_WALK_FORWARD_METRICS"]["R2"]
            - comparison_dict["REGULARIZED_WALK_FORWARD_METRICS"]["R2"]
        )

    output_path = build_dated_file_path(
        folder_path=MODEL_ROOT,
        stem_name="model_comparison_int",
        date_text=run_date,
        suffix=".json",
    )
    output_path.write_text(
        json.dumps(comparison_dict, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    append_text_log(
        log_path=PROJECT_ROOT / "logs" / "workflow.log",
        message_text=f"Model comparison built -> {output_path}",
    )
    return comparison_dict


if __name__ == "__main__":
    Summary = main()
    print(json.dumps(Summary, ensure_ascii=False, indent=2))
