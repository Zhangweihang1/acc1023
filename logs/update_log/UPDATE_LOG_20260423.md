# Update Log - 20260423

## Change ID

20260423-01

## Module

Project initialization workflow documents

## Change Type

Project Control Initialization

## What Changed

- Created base project directories
- Created project mainline control markdown
- Created task execution checklist markdown
- Initialized update log for traceability

## Why

To keep the engineering workflow aligned, reviewable, and resistant to scope drift from the start of the project.

## Scope

- project structure
- workflow control
- execution traceability

## Validation

- confirmed workspace was initially empty
- confirmed required folders were created
- confirmed markdown control files were written into the project

## Output Files

- `C:\Users\38730\Desktop\ACC102\PROJECT_MAINLINE_20260423.md`
- `C:\Users\38730\Desktop\ACC102\TASK_EXECUTION_CHECKLIST_20260423.md`
- `C:\Users\38730\Desktop\ACC102\logs\update_log\UPDATE_LOG_20260423.md`

## Rollback Plan

- delete the newly created markdown files
- delete initialization folders if the project is restarted from scratch

## Risks

- mainline may still need refinement after data source locking
- decision gates are documented but not yet resolved

---

## Change ID

20260423-02

## Module

Data source locking documents

## Change Type

Source Planning Update

## What Changed

- Added data source matrix document
- Added Tushare user action guide
- Updated task checklist status for source-planning artifacts

## Why

To formalize the free-first data route and separate system work from user-account-only actions.

## Scope

- source planning
- user handoff
- workflow checkpointing

## Validation

- data source route is now documented in project files
- user-only setup steps are separated from codex-executable steps

## Output Files

- `C:\Users\38730\Desktop\ACC102\DATA_SOURCE_MATRIX_20260423.md`
- `C:\Users\38730\Desktop\ACC102\USER_ACTION_GUIDE_TUSHARE_20260423.md`
- `C:\Users\38730\Desktop\ACC102\TASK_EXECUTION_CHECKLIST_20260423.md`

## Rollback Plan

- remove the newly added planning markdown files
- revert checklist status lines to pending

## Risks

- final source route still depends on user eligibility and source preference

---

## Change ID

20260423-03

## Module

Lightweight B+B route scaffold

## Change Type

Workflow Route Update

## What Changed

- Switched active route documents to B+B lightweight mode
- Added lightweight route guidance document
- Added project config skeleton
- Added initiation, path, and logging utility scripts
- Added placeholder curated universe workflow script
- Added requirements file

## Why

To move from planning into the fastest fully free executable workflow while preserving a later upgrade path to A+A.

## Scope

- project routing
- scaffold utilities
- lightweight data workflow entry

## Validation

- active route now documented as B+B
- reusable utility modules now exist
- first workflow script exists and can be used as the next execution entry

## Output Files

- `C:\Users\38730\Desktop\ACC102\LIGHTWEIGHT_ROUTE_BB_20260423.md`
- `C:\Users\38730\Desktop\ACC102\config\project_config.yaml`
- `C:\Users\38730\Desktop\ACC102\src\initiation\init_env.py`
- `C:\Users\38730\Desktop\ACC102\src\utils\path_utils.py`
- `C:\Users\38730\Desktop\ACC102\src\utils\log_utils.py`
- `C:\Users\38730\Desktop\ACC102\src\workflows\build_curated_universe_int.py`
- `C:\Users\38730\Desktop\ACC102\requirements.txt`

## Rollback Plan

- revert route documents to previous A-oriented planning state
- delete scaffold files added for lightweight route

## Risks

- placeholder universe workflow still needs real AKShare integration
- current route is intentionally simplified and not yet feature-complete

---

## Change ID

20260423-04

## Module

Universe builder workflow

## Change Type

Data Pipeline Update

## What Changed

- Replaced placeholder universe builder with real AKShare-based universe selection
- Added liquidity ranking and stock filtering logic
- Added metadata JSON output for traceability
- Generated the first real curated universe artifact

## Why

To make the B+B route produce a real, explainable stock pool instead of a placeholder artifact.

## Scope

- universe construction
- raw data artifact generation
- source traceability

## Validation

- workflow executed successfully
- `universe_int_20260423.csv` was generated
- `universe_int_meta_20260423.json` was generated
- workflow log captured the run result

## Output Files

- `C:\Users\38730\Desktop\ACC102\data\raw\universe_int_20260423.csv`
- `C:\Users\38730\Desktop\ACC102\data\raw\universe_int_meta_20260423.json`
- `C:\Users\38730\Desktop\ACC102\src\workflows\build_curated_universe_int.py`

## Rollback Plan

- revert to the placeholder workflow version
- delete the current universe artifacts and rerun after code rollback

## Risks

- AKShare spot endpoint may still fluctuate across runs
- current liquidity rule is practical but not yet the final academic stock-pool definition

---

## Change ID

20260423-05

## Module

Price adjust mode decision

## Change Type

Configuration Update

## What Changed

- Locked the lightweight route price adjust mode to `qfq`
- Updated the task checklist decision gate status

## Why

To align price retrieval with return-based modeling and more intuitive app visualization.

## Scope

- price retrieval config
- workflow decision tracking

## Validation

- config now records `qfq`
- checklist now records the selected adjust mode

## Output Files

- `C:\Users\38730\Desktop\ACC102\config\project_config.yaml`
- `C:\Users\38730\Desktop\ACC102\TASK_EXECUTION_CHECKLIST_20260423.md`

## Rollback Plan

- switch `ADJUST_MODE` back to `hfq`
- update checklist decision record accordingly

## Risks

- none significant at current lightweight route stage

---

## Change ID

20260423-06

## Module

Daily price fetch workflow

## Change Type

Data Pipeline Update

## What Changed

- Added `fetch_price_daily_int.py`
- Implemented `qfq` daily price retrieval from AKShare
- Added per-stock raw file output and summary JSON output
- Completed a 5-stock validation run with zero failures

## Why

To establish the second core pipeline leg after universe construction and verify that historical daily prices can be fetched reliably in the lightweight route.

## Scope

- price data acquisition
- raw artifact generation
- fetch summary traceability

## Validation

- script executed successfully
- 5 per-stock price files were generated
- summary JSON was generated
- workflow log recorded each successful fetch

## Output Files

- `C:\Users\38730\Desktop\ACC102\src\workflows\fetch_price_daily_int.py`
- `C:\Users\38730\Desktop\ACC102\data\raw\price_daily_fetch_summary_int_20260423.json`
- `C:\Users\\38730\\Desktop\\ACC102\\data\\raw\\price_daily\\price_daily_int_300308.SZ_20260423.csv`

## Rollback Plan

- remove the price workflow script
- delete generated per-stock files and summary JSON if rerunning from scratch

## Risks

- full 150-stock run may encounter intermittent upstream failures
- current workflow still saves per-stock raw files only; merged panel is not built yet

---

## Change ID

20260423-07

## Module

Downstream pipeline focus decision

## Change Type

Workflow Decision Update

## What Changed

- Chose to continue downstream pipeline development on the verified 5-stock sample instead of launching the full 150-stock price run

## Why

To prioritize end-to-end pipeline closure and catch schema or target-definition issues earlier with lower source-side risk.

## Scope

- workflow sequencing
- validation pacing

## Validation

- task checklist now records the selected focus path

## Output Files

- `C:\Users\38730\Desktop\ACC102\TASK_EXECUTION_CHECKLIST_20260423.md`

## Rollback Plan

- switch the focus decision back to full-run price fetch in the checklist

## Risks

- sample-first workflow may delay detection of some full-universe scaling issues

---

## Change ID

20260423-08

## Module

Price panel merge and target construction

## Change Type

Feature Pipeline Update

## What Changed

- Added `merge_price_panel_int.py` to combine per-stock price files into one panel
- Added `build_targets_int.py` to construct return and future volatility targets
- Generated a clean price panel for 5 stocks
- Generated a target panel with valid `FUTURE_RV_5` values

## Why

To move the lightweight route from raw acquisition into a model-ready intermediate dataset.

## Scope

- clean panel construction
- target definition
- feature-store preparation

## Validation

- merged panel built successfully with 8850 rows across 5 stocks
- target panel built successfully with 8825 valid target rows
- workflow log captured both stage completions

## Output Files

- `C:\Users\38730\Desktop\ACC102\src\workflows\merge_price_panel_int.py`
- `C:\Users\38730\Desktop\ACC102\src\workflows\build_targets_int.py`
- `C:\Users\38730\Desktop\ACC102\data\clean\price_panel_int_20260423.csv`
- `C:\Users\38730\Desktop\ACC102\data\feature_store\target_panel_int_20260423.csv`

## Rollback Plan

- remove the two workflow scripts
- delete the generated panel files and rerun after workflow rollback

## Risks

- current target definition is price-only and still lacks broader explanatory features

---

## Change ID

20260423-09

## Module

Price-only feature engineering and baseline model

## Change Type

Modeling Pipeline Update

## What Changed

- Added `build_features_price_int.py` for the first minimal feature set
- Added `train_baseline_model_int.py` for the first baseline regression model
- Generated feature panel output
- Generated baseline prediction output and model summary metrics

## Why

To complete the first end-to-end lightweight modeling loop from raw prices to predictions.

## Scope

- feature engineering
- baseline modeling
- prediction artifact generation

## Validation

- feature panel built successfully
- baseline model trained successfully
- test metrics were produced on held-out data
- prediction file was written successfully

## Output Files

- `C:\Users\38730\Desktop\ACC102\src\workflows\build_features_price_int.py`
- `C:\Users\38730\Desktop\ACC102\src\workflows\train_baseline_model_int.py`
- `C:\Users\38730\Desktop\ACC102\data\feature_store\feature_panel_int_20260423.csv`
- `C:\Users\38730\Desktop\ACC102\data\predictions\baseline_prediction_int_20260423.csv`

## Rollback Plan

- remove the two workflow scripts
- delete the generated feature and prediction artifacts and rerun after rollback

## Risks

- current model uses only price-derived features and is still a weak baseline
- current train/test split is simple time-based split and not yet a full walk-forward backtest

---

## Change ID

20260423-10

## Module

Boosted model and minimal Streamlit app

## Change Type

Model Comparison and App Update

## What Changed

- Added `train_boosted_model_int.py`
- Added `compare_model_results_int.py`
- Added minimal `app.py` that loads baseline and boosted prediction artifacts
- Trained the boosted model and generated comparison output

## Why

To extend the first modeling loop beyond the baseline and expose prediction artifacts through a minimal interactive interface.

## Scope

- boosted modeling
- model comparison
- app entry layer

## Validation

- boosted model summary was generated
- model comparison summary was generated
- `app.py` imported successfully and artifact loading paths resolved

## Output Files

- `C:\Users\38730\Desktop\ACC102\src\workflows\train_boosted_model_int.py`
- `C:\Users\38730\Desktop\ACC102\src\workflows\compare_model_results_int.py`
- `C:\Users\38730\Desktop\ACC102\app.py`
- `C:\Users\38730\Desktop\ACC102\data\model_output\boosted_model_summary_int_20260423.json`
- `C:\Users\38730\Desktop\ACC102\data\model_output\model_comparison_int_20260423.json`
- `C:\Users\38730\Desktop\ACC102\data\predictions\boosted_prediction_int_20260423.csv`

## Rollback Plan

- remove the boosted workflow, comparison workflow, and app entry
- delete boosted artifacts and keep baseline-only route

## Risks

- boosted model currently overfits on the 5-stock sample and underperforms baseline on the test set
- Streamlit server is a long-running process, so current validation is import-level rather than a full interactive smoke test

---

## Change ID

20260423-11

## Module

Mainline status sync and app page skeleton expansion

## Change Type

Control Doc and App Update

## What Changed

- Updated the mainline control documents with completed and remaining engineering status
- Expanded `app.py` from a single view into page skeletons:
  - Overview
  - Single Stock
  - Diagnostics
  - Method & Limitations
- Ran a formal local Streamlit smoke test using local HTTP request validation

## Why

To bring project documentation back in sync with actual implementation progress and move the app from a minimal entry into a clearer MVP structure.

## Scope

- project control documentation
- app structure
- app validation

## Validation

- app page skeletons render from persisted artifacts
- local smoke test returned HTTP 200
- smoke test result was written to `logs/app_smoke_test_20260423.txt`

## Output Files

- `C:\Users\38730\Desktop\ACC102\PROJECT_MAINLINE_20260423.md`
- `C:\Users\38730\Desktop\ACC102\LIGHTWEIGHT_ROUTE_BB_20260423.md`
- `C:\Users\38730\Desktop\ACC102\TASK_EXECUTION_CHECKLIST_20260423.md`
- `C:\Users\38730\Desktop\ACC102\app.py`
- `C:\Users\38730\Desktop\ACC102\logs\app_smoke_test_20260423.txt`

## Rollback Plan

- revert control document additions
- revert `app.py` to the prior single-view version
- delete the smoke test log file if re-running from scratch

## Risks

- app page structure is still compact and lives in one file
- broader market and screener views are still not implemented

---

## Change ID

20260423-13

## Module

Non-price feature layer: individual fund flow

## Change Type

Feature Pipeline Update

## What Changed

- Added `fetch_fund_flow_individual_int.py`
- Extended `build_features_price_int.py` to merge individual fund flow features when available
- Updated baseline and boosted training workflows to consume the enriched feature set dynamically

## Why

To introduce the first non-price explanatory layer without depending on Tushare, while keeping the current lightweight route executable.

## Scope

- raw non-price data acquisition
- feature enrichment
- model input expansion

## Validation

- individual fund flow interface was verified locally
- fund flow date coverage overlaps the current held-out modeling period
- model workflows remain backward-compatible because they detect available feature columns dynamically

## Output Files

- `C:\Users\38730\Desktop\ACC102\src\workflows\fetch_fund_flow_individual_int.py`
- `C:\Users\38730\Desktop\ACC102\src\workflows\build_features_price_int.py`
- `C:\Users\38730\Desktop\ACC102\src\workflows\train_baseline_model_int.py`
- `C:\Users\38730\Desktop\ACC102\src\workflows\train_boosted_model_int.py`

## Rollback Plan

- remove the fund flow workflow
- revert feature and model workflows to the price-only version
- rebuild feature panel and model artifacts

## Risks

- fund flow coverage is recent-window only, not full-history
- enriched model dataset may shrink because rows now require overlapping fund flow observations

---

## Change ID

20260423-12

## Module

Daily price fetch full-run path upgrade

## Change Type

Workflow Parameterization and Traceability Update

## What Changed

- Upgraded `fetch_price_daily_int.py` from a hardcoded 5-stock validation run to a configurable fetch workflow
- Added explicit `full` and `sample` execution modes with CLI arguments
- Added `PRICE_FETCH` configuration for default mode, sample limit, full limit, and per-stock pacing
- Split fetch summaries by run mode so sample and full runs write distinct JSON artifacts
- Logged run mode in the workflow log for easier traceability

## Why

To make the daily price fetch path production-ready for the 150-stock curated universe while preserving a lightweight validation route for faster checks and safer debugging.

## Scope

- price fetching workflow
- project configuration
- execution traceability

## Validation

- `python -m py_compile src/workflows/fetch_price_daily_int.py` passed
- `python src/workflows/fetch_price_daily_int.py --mode sample --limit-count 1` completed successfully
- configuration logic resolved default mode to `full`, full limit to `150`, and sample limit to `5`
- sample summary JSON was written with `RUN_MODE=SAMPLE` and `LIMIT_COUNT=1`

## Output Files

- `C:\Users\38730\Desktop\ACC102\src\workflows\fetch_price_daily_int.py`
- `C:\Users\38730\Desktop\ACC102\config\project_config.yaml`
- `C:\Users\38730\Desktop\ACC102\data\raw\price_daily_fetch_summary_int_sample_20260423.json`
- `C:\Users\38730\Desktop\ACC102\data\raw\price_daily\price_daily_int_300394.SZ_20260423.csv`

## Rollback Plan

- restore `fetch_price_daily_int.py` to the previous hardcoded 5-stock entry
- remove the `PRICE_FETCH` block from `project_config.yaml`
- delete the new sample summary artifact if it is no longer needed

## Risks

- a full 150-stock fetch still depends on AKShare and upstream endpoint stability
- sample and full runs on the same day still reuse the same per-stock CSV naming, so reruns will overwrite per-stock files for the same symbols

---

## Change ID

20260423-14

## Module

Dual-track status sync after full fetch and first non-price layer

## Change Type

Control Doc and App Copy Update

## What Changed

- Synced the mainline control documents to reflect that the full 150-stock raw fetch has completed successfully
- Synced the lightweight route document to reflect the first integrated non-price feature layer and the remaining full-universe downstream gap
- Updated the task checklist with the new dual-track follow-up gate
- Updated the app method/limitation copy so it no longer describes the feature stack as price-only

## Why

To prevent the project control layer and app explanation layer from drifting behind the actual engineering state after the parallel full-fetch and non-price-feature work.

## Scope

- project control documentation
- app disclosure copy
- next-step decision tracking

## Validation

- confirmed the full-run summary shows 150 input stocks, 150 successes, and 0 failures
- confirmed the individual fund-flow summary shows 5 requested stocks and 5 successes
- confirmed the current comparison artifact still shows the enriched 5-stock model underperforming the earlier baseline path
- confirmed the latest app smoke test log still records HTTP 200

## Output Files

- `C:\Users\38730\Desktop\ACC102\PROJECT_MAINLINE_20260423.md`
- `C:\Users\38730\Desktop\ACC102\LIGHTWEIGHT_ROUTE_BB_20260423.md`
- `C:\Users\38730\Desktop\ACC102\TASK_EXECUTION_CHECKLIST_20260423.md`
- `C:\Users\38730\Desktop\ACC102\app.py`
- `C:\Users\38730\Desktop\ACC102\logs\update_log\UPDATE_LOG_20260423.md`

## Rollback Plan

- revert the documentation and app copy edits from this change block
- restore the previous checklist wording if a different follow-up gate is adopted

## Risks

- the documentation is now accurate for the current state, but it will drift again if we rerun the downstream stack on 150 stocks without another sync
- app copy still reflects a mixed state where raw data has scaled but model artifacts have not yet been recomputed on the full universe

---

## Change ID

20260423-15

## Module

Full-universe downstream closure and model coverage gating

## Change Type

Modeling Pipeline Update

## What Changed

- Reran the full 150-stock downstream chain from merged price panel to model comparison
- Added feature coverage gating in baseline and boosted training scripts so sparse optional features no longer collapse the model dataset
- Promoted the full-universe path from raw-only completion to data-to-model completion

## Why

To close the gap between full raw data acquisition and sample-only modeling, and to prevent sparse fund-flow columns from shrinking the usable dataset to a small subset of stocks.

## Scope

- full-universe panel / target / feature / model workflow
- model input selection logic
- held-out model comparison

## Validation

- full merged price panel rebuilt with 150 stocks and 248762 rows
- target panel rebuilt with 150 stocks and 248014 valid targets
- baseline and boosted summaries now reflect the full-universe rerun rather than the earlier 5-stock sample
- comparison summary was regenerated from the updated model outputs

## Output Files

- `C:\Users\38730\Desktop\ACC102\data\clean\price_panel_int_20260423.csv`
- `C:\Users\38730\Desktop\ACC102\data\feature_store\target_panel_int_20260423.csv`
- `C:\Users\38730\Desktop\ACC102\src\workflows\train_baseline_model_int.py`
- `C:\Users\38730\Desktop\ACC102\src\workflows\train_boosted_model_int.py`
- `C:\Users\38730\Desktop\ACC102\data\model_output\baseline_model_summary_int_20260423.json`
- `C:\Users\38730\Desktop\ACC102\data\model_output\boosted_model_summary_int_20260423.json`
- `C:\Users\38730\Desktop\ACC102\data\model_output\model_comparison_int_20260423.json`

## Rollback Plan

- revert the coverage-threshold edits in the model scripts
- rebuild the feature and model artifacts from the previous logic if a sample-only path is intentionally restored

## Risks

- feature coverage gating is a practical engineering rule, not yet a tuned research design choice
- the current boosted hyperparameters are unstable on the full-universe rerun and need separate tuning

---

## Change ID

20260423-16

## Module

Macro feature layer, walk-forward evaluator, and submission draft sync

## Change Type

Feature, Evaluation, and Documentation Update

## What Changed

- Added AKShare macro-rate fetch workflow and merged macro features into the feature panel
- Added a walk-forward evaluation workflow
- Drafted README, reflection, and AI disclosure documents
- Updated app copy and mainline documents to reflect the new full-universe state

## Why

To add a broader-coverage non-price layer, strengthen time-based evaluation, and bring the project narrative back in sync with the newly completed downstream rerun.

## Scope

- non-price feature expansion
- evaluation workflow
- app narrative
- submission materials

## Validation

- macro-rate fetch completed successfully and generated dated raw outputs
- macro-enriched feature panel was rebuilt successfully
- walk-forward summary was generated on the updated feature panel
- README / reflection / AI disclosure were revised to match the current full-universe engineering state

## Output Files

- `C:\Users\38730\Desktop\ACC102\src\workflows\fetch_macro_rate_int.py`
- `C:\Users\38730\Desktop\ACC102\src\workflows\build_features_price_int.py`
- `C:\Users\38730\Desktop\ACC102\src\workflows\walk_forward_backtest_int.py`
- `C:\Users\38730\Desktop\ACC102\README_20260423.md`
- `C:\Users\38730\Desktop\ACC102\REFLECTION_20260423.md`
- `C:\Users\38730\Desktop\ACC102\AI_DISCLOSURE_20260423.md`
- `C:\Users\38730\Desktop\ACC102\PROJECT_MAINLINE_20260423.md`
- `C:\Users\38730\Desktop\ACC102\LIGHTWEIGHT_ROUTE_BB_20260423.md`
- `C:\Users\38730\Desktop\ACC102\TASK_EXECUTION_CHECKLIST_20260423.md`
- `C:\Users\38730\Desktop\ACC102\app.py`
- `C:\Users\38730\Desktop\ACC102\logs\update_log\UPDATE_LOG_20260423.md`

## Rollback Plan

- remove the macro-rate and walk-forward workflows
- revert feature-panel, app, and documentation text to the previous state

## Risks

- macro features broaden coverage but also shorten the earliest usable history after lagged transformations
- app and docs will need another sync if we later retune boosted or switch to A + A

---

## Change ID

20260423-17

## Module

App interaction enhancement

## Change Type

App UX Update

## What Changed

- Added page-to-stock navigation so Market and Screener can jump directly into Single Stock
- Added global time-window controls and filtered the app views by the selected date range
- Added explicit model-view controls for Baseline / Boosted / Both
- Added an auto-generated explanation card on the Single Stock page
- Added quick task entry buttons for top-risk, low-liquidity high-vol, and model-failure exploration

## Why

To make the app feel less like a static dashboard and more like an interactive product that responds to user intent and exploration paths.

## Scope

- Streamlit app interaction flow
- page routing and selection state
- app narrative and discovery flow

## Validation

- `app.py` passed syntax validation through `python -m py_compile`
- app data schema was checked against the latest persisted prediction and universe files
- navigation logic, model switch logic, and time filter logic were implemented against the current artifact contract
- single-stock explanation card was switched to a clean UTF-8 helper to avoid mojibake in the UI text

## Output Files

- `C:\Users\38730\Desktop\ACC102\app.py`
- `C:\Users\38730\Desktop\ACC102\logs\update_log\UPDATE_LOG_20260423.md`

## Rollback Plan

- revert `app.py` to the previous non-interactive page version
- remove this change block from the update log if the interaction redesign is abandoned

## Risks

- the Market and Screener row-click flow depends on Streamlit dataframe selection behavior in the current version
- global date filtering can produce thin slices for some pages if the chosen window is too short

---

20260423-18

## Module

App interaction and live inference redesign

## Change Type

App UX Update

## What Changed

- rewrote `app.py` into an English-only UI layer
- moved model-view control out of the old sidebar pattern and rendered it inside model-driven pages
- replaced widget-bound page navigation with separate state management to remove quick-task warnings
- added full stock lookup over supported SH/SZ A-shares with explicit `Covered` vs `Live Fetch` tagging
- added live on-demand prediction for out-of-coverage stocks by fetching AKShare history, rebuilding the feature contract, and scoring with cached models
- added graceful fallback messaging for stocks that do not yet have enough history for rolling-window prediction

## Why

To make the app feel more coherent, reduce confusing controls, fix navigation warnings, and support the product goal of exploring any supported stock instead of only the persisted 150-stock coverage pool.

## Scope

- Streamlit app layout and control placement
- session-state and navigation flow
- stock lookup scope
- live inference behavior for uncovered stocks

## Validation

- `python -m py_compile C:\Users\38730\Desktop\ACC102\app.py`
- verified one uncovered stock with insufficient history returns a handled warning path
- verified one uncovered stock (`603220.SH`) completes live on-demand prediction with non-empty output

## Output Files

- `C:\Users\38730\Desktop\ACC102\app.py`
- `C:\Users\38730\Desktop\ACC102\logs\update_log\UPDATE_LOG_20260423.md`

## Rollback Plan

- revert `app.py` to the prior persisted-artifact-only interface
- remove this log block if the redesign is abandoned

## Risks

- live on-demand prediction currently refits cached serving models inside the app rather than loading a separately versioned serving artifact
- newly listed or short-history stocks may still be selectable but not immediately predictable because rolling feature windows are not yet available

---

20260423-19

## Module

App state synchronization fix

## Change Type

Bug Fix

## What Changed

- fixed the widget-state sync logic so page, stock, model-view, and date controls are no longer overwritten on every rerun
- kept only first-run initialization behavior and added a guarded stock-selector reset when the current stock falls outside a newly filtered selector scope

## Why

The previous implementation eagerly copied persistent state back into widget keys on every rerun, which prevented manual page switching and made the UI appear unresponsive.

## Scope

- Streamlit session-state synchronization
- page switching
- top control interaction stability

## Validation

- `python -m py_compile C:\Users\38730\Desktop\ACC102\app.py`
- code-path inspection confirmed that widget keys are now initialized once instead of force-reset on every rerun

## Output Files

- `C:\Users\38730\Desktop\ACC102\app.py`
- `C:\Users\38730\Desktop\ACC102\logs\update_log\UPDATE_LOG_20260423.md`

## Rollback Plan

- revert the `sync_widget_state` helper to the prior version if a different state-management pattern is adopted

## Risks

- if later we add more widget keys, they need the same “initialize once, do not overwrite every rerun” rule to avoid similar UI lockups

---

20260423-20

## Module

App interaction audit and basket study flow

## Change Type

App UX Update

## What Changed

- audited the `Page / Scope / Stock / Date Window / Model View` control linkage and aligned programmatic navigation with manual widget navigation
- fixed quick-task navigation so button-triggered page changes now update both persistent state and widget state
- added a dedicated `Basket` page for custom stock-set research
- added a `Research Basket Builder` with multiselect selection, add-current-stock, clear, use-current-scope-top-10, and direct-open-basket-page actions
- added basket aggregation that combines persisted covered names with live-fetch on-demand names and maps them into basket-level time-series behavior

## Why

The app needed a full interaction stability pass and a more flexible research workflow so users can study custom stock groups instead of only the original liquidity-screened sample set.

## Scope

- page navigation stability
- control linkage across top-level widgets
- custom basket selection and aggregate study
- overview and basket-page presentation

## Validation

- `python -m py_compile C:\Users\38730\Desktop\ACC102\app.py`
- verified a mixed basket with one covered stock and one live-fetch stock returns non-empty basket panel and aggregate output
- confirmed the app still loads through headless smoke test with `STATUS_CODE=200`

## Output Files

- `C:\Users\38730\Desktop\ACC102\app.py`
- `C:\Users\38730\Desktop\ACC102\logs\update_log\UPDATE_LOG_20260423.md`
- `C:\Users\38730\Desktop\ACC102\logs\app_smoke_test_20260423_interactive_v4.txt`

## Rollback Plan

- revert the basket helpers and page additions in `app.py`
- remove this change block if the custom basket workflow is abandoned

## Risks

- large baskets with many uncovered stocks can still feel slow because live-fetch inference is cached per stock but still computed on first use
- basket aggregates currently average member series equally; they do not yet support custom weighting schemes such as turnover-weighted or equal-risk-weighted baskets

---

20260423-21

## Module

Basket registry and weighting controls

## Change Type

App UX Update

## What Changed

- added persistent basket registry storage with latest-file and dated-snapshot writes
- added save / load / delete controls for named baskets inside the basket builder
- added `Equal` and `Turnover-Weighted` basket aggregation modes
- wired basket weighting into overview snapshot and basket page reporting
- updated method documentation to reflect named-basket management and weighting support

## Why

The basket workflow needed to evolve from temporary selection into a reusable research object, and the aggregate view needed an explicit choice between simple member-average behavior and turnover-led market representation.

## Scope

- local basket persistence
- basket builder controls
- basket aggregation logic
- overview and basket-page summaries

## Validation

- `python -m py_compile C:\Users\38730\Desktop\ACC102\app.py`
- verified save -> load -> delete on a test basket name
- verified equal-weight and turnover-weighted aggregates diverge on a mixed basket for dates with more than one active constituent
- confirmed the app still loads through headless smoke test with `STATUS_CODE=200`

## Output Files

- `C:\Users\38730\Desktop\ACC102\app.py`
- `C:\Users\38730\Desktop\ACC102\data\raw\basket_registry\basket_registry_int_latest.json`
- `C:\Users\38730\Desktop\ACC102\data\raw\basket_registry\basket_registry_int_20260423.json`
- `C:\Users\38730\Desktop\ACC102\logs\update_log\UPDATE_LOG_20260423.md`
- `C:\Users\38730\Desktop\ACC102\logs\app_smoke_test_20260423_interactive_v5.txt`

## Rollback Plan

- remove the basket registry helpers and builder actions from `app.py`
- delete the basket registry files if this persistence layer is abandoned
- revert basket aggregation to equal-weight only

## Risks

- basket registry is currently local JSON storage, so it is easy to back up but not yet multi-user or merge-safe
- turnover weighting currently uses the latest snapshot turnover field from the stock lookup layer rather than a time-varying daily turnover series

---

20260423-22

## Module

Basket management completion and scope propagation

## Change Type

App UX Update

## What Changed

- completed basket management by adding rename and duplicate actions to the basket builder
- added `Analysis Dataset` scope control so downstream pages can follow either the coverage universe or the current basket
- wired Overview, Market, Screener, and Diagnostics to use the active analysis scope instead of always reading the full coverage universe
- added `screen-to-basket` actions in Screener so filtered results can replace or append into the current basket
- expanded the method page text to document basket-driven downstream analysis and screen-to-basket workflow

## Why

The app needed a complete basket-management workflow and a clear guarantee that, once a basket is chosen, downstream pages actually reflect that chosen dataset rather than silently falling back to the original coverage universe.

## Scope

- basket registry lifecycle
- downstream analysis scope selection
- screener to basket workflow
- overview / market / screener / diagnostics data source alignment

## Validation

- `python -m py_compile C:\Users\38730\Desktop\ACC102\app.py`
- verified save -> rename -> duplicate -> delete on named baskets
- verified current-basket scope resolves to the basket stock set while coverage scope still resolves to the full coverage universe
- verified helper behavior for screen-result append and replace basket flows
- confirmed the app still loads through headless smoke test with `STATUS_CODE=200`

## Output Files

- `C:\Users\38730\Desktop\ACC102\app.py`
- `C:\Users\38730\Desktop\ACC102\data\raw\basket_registry\basket_registry_int_latest.json`
- `C:\Users\38730\Desktop\ACC102\data\raw\basket_registry\basket_registry_int_20260423.json`
- `C:\Users\38730\Desktop\ACC102\logs\update_log\UPDATE_LOG_20260423.md`
- `C:\Users\38730\Desktop\ACC102\logs\app_smoke_test_20260423_interactive_v6.txt`

## Rollback Plan

- remove analysis-scope switching and basket-management actions from `app.py`
- revert to the previous save/load/delete-only basket flow
- delete the basket registry files if this persistence layer is abandoned

## Risks

- downstream pages now correctly follow the current basket when selected, but the single-stock page still focuses on the currently chosen stock rather than the basket aggregate by design
- screen-to-basket actions can generate large baskets quickly, which may increase the first-run latency for uncovered names

---

20260423-23

## Module

Regularized model branch and time-series validation

## Change Type

Model Engineering Update

## What Changed

- added `train_regularized_model_int.py` to introduce a `StandardScaler + Ridge` branch with time-ordered train / validation / test selection
- added `walk_forward_regularized_int.py` to validate the ridge branch under the same rolling backtest structure used by the plain baseline
- expanded `compare_model_results_int.py` so it can include the regularized summary and identify the current best model by RMSE
- updated `PROJECT_MAINLINE_20260423.md` so the mainline file reflects that the regularized branch is now the strongest validated model line

## Why

The old baseline was stable but under-regularized, while the boosted branch was materially overfitting. The next safest model-engineering improvement was to add a regularized linear benchmark before attempting more aggressive tree tuning or sparse feature expansion.

## Scope

- holdout model selection logic
- walk-forward evaluator extension
- model comparison artifact
- mainline control narrative

## Validation

- `python -m py_compile C:\Users\38730\Desktop\ACC102\src\workflows\train_regularized_model_int.py`
- `python -m py_compile C:\Users\38730\Desktop\ACC102\src\workflows\walk_forward_regularized_int.py`
- `python -m py_compile C:\Users\38730\Desktop\ACC102\src\workflows\compare_model_results_int.py`
- `python C:\Users\38730\Desktop\ACC102\src\workflows\train_regularized_model_int.py`
- `python C:\Users\38730\Desktop\ACC102\src\workflows\walk_forward_regularized_int.py --alpha 100`
- `python C:\Users\38730\Desktop\ACC102\src\workflows\compare_model_results_int.py`

## Output Files

- `C:\Users\38730\Desktop\ACC102\src\workflows\train_regularized_model_int.py`
- `C:\Users\38730\Desktop\ACC102\src\workflows\walk_forward_regularized_int.py`
- `C:\Users\38730\Desktop\ACC102\src\workflows\compare_model_results_int.py`
- `C:\Users\38730\Desktop\ACC102\data\model_output\regularized_model_summary_int_20260423.json`
- `C:\Users\38730\Desktop\ACC102\data\predictions\regularized_prediction_int_20260423.csv`
- `C:\Users\38730\Desktop\ACC102\data\model_output\walk_forward_regularized_summary_int_20260423.json`
- `C:\Users\38730\Desktop\ACC102\data\predictions\walk_forward_regularized_prediction_int_20260423.csv`
- `C:\Users\38730\Desktop\ACC102\data\model_output\model_comparison_int_20260423.json`
- `C:\Users\38730\Desktop\ACC102\PROJECT_MAINLINE_20260423.md`

## Rollback Plan

- remove the regularized workflow scripts and restore `compare_model_results_int.py` if the branch should be abandoned
- continue using the existing baseline / boosted artifacts, which remain untouched by this change

## Risks

- the app layer still presents the plain baseline / boosted pair, so the user-facing narrative is temporarily behind the newest validated model result
- the ridge branch is now the strongest linear benchmark, but the boosted branch has not yet been retuned against this stronger standard

---

20260424-01

## Module

Regularized-first narrative sync and boosted walk-forward extension

## Change Type

Model Engineering Update

## What Changed

- switched the app narrative and method page to treat the `regularized` ridge branch as the default stable model instead of the old plain baseline wording
- expanded the app to load and display walk-forward evidence for regularized and boosted when available
- retuned boosted remained in place for holdout comparison, and a new `walk_forward_boosted_int.py` workflow was added to evaluate the tuned boosted branch under the same rolling time split used elsewhere
- extended `compare_model_results_int.py` so the latest comparison artifact now includes both holdout metrics and walk-forward aggregate metrics for baseline, regularized, and boosted
- synchronized `PROJECT_MAINLINE_20260423.md`, `README_20260423.md`, `REFLECTION_20260423.md`, and `AI_DISCLOSURE_20260423.md` with the updated model evidence

## Why

The project had already validated regularized as the strongest held-out model, but the user-facing narrative was lagging behind. At the same time, boosted had only been retuned on a single holdout lens, so it was still unclear whether it should be abandoned or kept as a comparison branch. Adding boosted walk-forward closes that gap and exposes a more honest mixed-evidence picture.

## Scope

- app model narrative and method explanation
- boosted walk-forward workflow
- unified comparison artifact
- mainline control document
- README / reflection / disclosure sync

## Validation

- `python -m py_compile C:\Users\38730\Desktop\ACC102\app.py`
- `python -m py_compile C:\Users\38730\Desktop\ACC102\src\workflows\walk_forward_boosted_int.py`
- `python -m py_compile C:\Users\38730\Desktop\ACC102\src\workflows\compare_model_results_int.py`
- `python C:\Users\38730\Desktop\ACC102\src\workflows\walk_forward_boosted_int.py`
- `python C:\Users\38730\Desktop\ACC102\src\workflows\compare_model_results_int.py`
- `python -m streamlit run C:\Users\38730\Desktop\ACC102\app.py --server.port 8509 --server.headless true` with `HTTP 200`

## Output Files

- `C:\Users\38730\Desktop\ACC102\app.py`
- `C:\Users\38730\Desktop\ACC102\src\workflows\walk_forward_boosted_int.py`
- `C:\Users\38730\Desktop\ACC102\src\workflows\compare_model_results_int.py`
- `C:\Users\38730\Desktop\ACC102\PROJECT_MAINLINE_20260423.md`
- `C:\Users\38730\Desktop\ACC102\README_20260423.md`
- `C:\Users\38730\Desktop\ACC102\REFLECTION_20260423.md`
- `C:\Users\38730\Desktop\ACC102\AI_DISCLOSURE_20260423.md`
- `C:\Users\38730\Desktop\ACC102\data\model_output\walk_forward_boosted_summary_int_20260424.json`
- `C:\Users\38730\Desktop\ACC102\data\predictions\walk_forward_boosted_prediction_int_20260424.csv`
- `C:\Users\38730\Desktop\ACC102\data\model_output\model_comparison_int_20260424.json`
- `C:\Users\38730\Desktop\ACC102\logs\app_smoke_test_20260424_regularized_v3.txt`

## Rollback Plan

- remove `walk_forward_boosted_int.py` and revert `compare_model_results_int.py` if the boosted walk-forward branch is deemed unnecessary
- restore the previous app wording if the project intentionally goes back to a baseline-first narrative
- keep using the existing regularized and boosted holdout artifacts, which remain versioned and untouched

## Risks

- model selection is now more nuanced rather than simpler: regularized wins the main held-out split, while boosted is slightly stronger on aggregate walk-forward RMSE
- the app still uses regularized as the default stable model, so future narration must explain why simplicity and held-out reliability still outweigh the mixed boosted signal
- richer fold-level diagnostic visualization is still not exposed as a first-class app view

---

20260424-02

## Module

Decision artifact, app package split, and demo close-out

## Change Type

App / Submission / Evaluation Update

## What Changed

- added `build_model_decision_artifact_int.py` to generate a formal JSON + Markdown model-selection artifact that explains the mixed holdout vs walk-forward ranking
- added `MODEL_DECISION_ARTIFACT_20260424.md` and `model_decision_artifact_int_20260424.json` as stable references for submission and demo narration
- split app page rendering into `src/app_ui/page_renderers.py`, so the Streamlit layer is no longer purely a single-file MVP
- upgraded the diagnostics experience by adding fold-level walk-forward charts and tables in the diagnostics page
- drafted `DEMO_SCRIPT_20260424.md` and updated README / mainline / checklist to reflect the new artifact and multi-file app structure

## Why

The remaining work was no longer about training another model. The main gap was governance and communication: explain the model decision clearly, make the app architecture easier to maintain, and close the submission layer with a usable demo script.

## Scope

- model decision governance
- app page-package structure
- diagnostics depth
- demo and submission support

## Validation

- `python -m py_compile C:\Users\38730\Desktop\ACC102\app.py`
- `python -m py_compile C:\Users\38730\Desktop\ACC102\src\app_ui\page_renderers.py`
- `python -m py_compile C:\Users\38730\Desktop\ACC102\src\workflows\build_model_decision_artifact_int.py`
- `python C:\Users\38730\Desktop\ACC102\src\workflows\build_model_decision_artifact_int.py`
- `python -m streamlit run C:\Users\38730\Desktop\ACC102\app.py --server.port 8511 --server.headless true` with `HTTP 200`

## Output Files

- `C:\Users\38730\Desktop\ACC102\app.py`
- `C:\Users\38730\Desktop\ACC102\src\app_ui\__init__.py`
- `C:\Users\38730\Desktop\ACC102\src\app_ui\page_renderers.py`
- `C:\Users\38730\Desktop\ACC102\src\workflows\build_model_decision_artifact_int.py`
- `C:\Users\38730\Desktop\ACC102\MODEL_DECISION_ARTIFACT_20260424.md`
- `C:\Users\38730\Desktop\ACC102\data\model_output\model_decision_artifact_int_20260424.json`
- `C:\Users\38730\Desktop\ACC102\DEMO_SCRIPT_20260424.md`
- `C:\Users\38730\Desktop\ACC102\README_20260423.md`
- `C:\Users\38730\Desktop\ACC102\PROJECT_MAINLINE_20260423.md`
- `C:\Users\38730\Desktop\ACC102\TASK_EXECUTION_CHECKLIST_20260423.md`
- `C:\Users\38730\Desktop\ACC102\logs\app_smoke_test_20260424_package.txt`

## Rollback Plan

- remove `src/app_ui/` and route the page calls back to the local `app.py` functions if the split proves unnecessary
- delete the decision artifact files if the team decides to keep model choice only inside README and mainline docs
- keep the current trained model artifacts unchanged, since this update does not retrain any model

## Risks

- app page logic is now modularized, but some legacy helper code still remains in `app.py`, so a later cleanup pass may still be worthwhile
- the decision artifact resolves explanation quality, not the underlying model tension itself
- deployment handoff is still the remaining submission-side gap

---

20260424-03

## Module

Final regularized submission lock and deployment handoff

## Change Type

Submission Decision Update

## What Changed

- formally locked `REGULARIZED` as the final submission model and `BOOSTED` as comparison only
- drafted `DEPLOYMENT_HANDOFF_20260424.md` to cover final local verification, GitHub upload, and Streamlit Community Cloud deployment steps
- updated `PROJECT_MAINLINE_20260423.md`, `README_20260423.md`, and `TASK_EXECUTION_CHECKLIST_20260423.md` so the project no longer presents model choice as an unresolved blocker

## Why

The user selected the regularized-first submission path. At this point the remaining work is deployment and delivery, not more ambiguity around default model choice.

## Scope

- final submission model lock
- deployment handoff
- control / README / checklist sync

## Validation

- reviewed current decision artifact and comparison outputs to confirm `REGULARIZED` remains the safest submission choice
- confirmed deployment handoff matches the current local app run command and artifact layout

## Output Files

- `C:\Users\38730\Desktop\ACC102\DEPLOYMENT_HANDOFF_20260424.md`
- `C:\Users\38730\Desktop\ACC102\PROJECT_MAINLINE_20260423.md`
- `C:\Users\38730\Desktop\ACC102\README_20260423.md`
- `C:\Users\38730\Desktop\ACC102\TASK_EXECUTION_CHECKLIST_20260423.md`

## Rollback Plan

- revert the final-model wording if a later feature rerun truly changes the submission recommendation
- keep the deployment handoff as a generic template even if the model choice changes

## Risks

- the deployment itself still requires your GitHub account and Streamlit Cloud account actions
- if you later choose to do another feature-expansion cycle, the final model lock may need to be revisited

---

20260424-04

## Module

Simplified regularized-first app flow

## Change Type

UI Simplification / Interaction Restructure

## What Changed

- simplified the main app navigation into four steps:
  - `Step 1 | Coverage Universe`
  - `Step 2 | Build Research Set`
  - `Step 3 | Analyze Current Set`
  - `Step 4 | Future Extension`
- removed user-facing model switching from the mainline UI and fixed the main narrative to `REGULARIZED`
- rewired stock navigation so row-level exploration opens the unified Step 3 analysis view
- moved the custom basket workflow into Step 2 and framed it as the second user path after the default 150-stock universe
- reworked the page renderers so:
  - Step 1 explains the original 150-stock liquid-universe rules and emphasizes regularized fit quality
  - Step 2 focuses on custom basket creation and saved basket management
  - Step 3 consolidates set-level analysis, screen-to-basket, selected-stock detail, diagnostics, and basket aggregation
  - Step 4 keeps boosted only as a future extension direction rather than a co-equal display model

## Why

The previous interface exposed too many parallel controls and made the main story harder to understand. The new layout follows the user's preferred progression: fixed universe first, then user-defined research set, then analysis, then future extension.

## Scope

- top-level app flow
- page hierarchy
- regularized-first presentation
- basket workflow placement

## Validation

- `python -m py_compile C:\Users\38730\Desktop\ACC102\app.py`
- `python -m py_compile C:\Users\38730\Desktop\ACC102\src\app_ui\page_renderers.py`
- launched Streamlit on port `8512` and verified `STATUS_CODE=200`

## Output Files

- `C:\Users\38730\Desktop\ACC102\app.py`
- `C:\Users\38730\Desktop\ACC102\src\app_ui\page_renderers.py`
- `C:\Users\38730\Desktop\ACC102\logs\app_smoke_test_20260424_simplified_ui.txt`

## Rollback Plan

- revert `app.py` and `src\app_ui\page_renderers.py` to the previous multi-model / multi-page interface
- keep the simplified flow only if it improves readability in real use

## Risks

- some legacy helper functions still remain in `app.py`, even though the user-facing flow is simpler
- boosted is still computed in the background for comparison artifacts, but no longer visible in the mainline UI

---

20260424-05

## Module

Analysis page validation and visualization enhancement

## Change Type

Analytics / Visualization Upgrade

## What Changed

- expanded `Step 3 | Analyze Current Set` with additional regularized-model checks:
  - current-window `MAE`, bias, and actual-vs-prediction correlation cards
  - actual-vs-predicted scatter with trendline
  - residual distribution histogram
  - time-series chart of average actual vs predicted volatility
  - time-series chart of average absolute error
  - prediction-bucket validation table and grouped bar chart
- kept the page regularized-first and avoided reintroducing boosted as a co-equal display model

## Why

The analysis page needed more evaluation directions and more intuitive visual evidence so users can better judge model fit, error behavior, stability over time, and ranking consistency by predicted-volatility bucket.

## Scope

- `Step 3 | Analyze Current Set`
- regularized diagnostics and visualization depth

## Validation

- `python -m py_compile C:\Users\38730\Desktop\ACC102\src\app_ui\page_renderers.py`
- `python -m py_compile C:\Users\38730\Desktop\ACC102\app.py`
- launched Streamlit on port `8513` and verified `STATUS_CODE=200`

## Output Files

- `C:\Users\38730\Desktop\ACC102\src\app_ui\page_renderers.py`
- `C:\Users\38730\Desktop\ACC102\logs\app_smoke_test_20260424_analysis_plus.txt`

## Rollback Plan

- remove the new fit-check and bucket-analysis sections from `render_analysis_page`
- keep only the earlier set-level, stock-level, and basket-level blocks if the page becomes too heavy

## Risks

- more charts may slightly increase page render time on larger windows
- prediction-bucket summaries depend on enough variation in the regularized predictions to form stable quantile buckets

---

20260424-06

## Module

Over/under-prediction checks and grouped stability view

## Change Type

Diagnostics / Grouped Analysis Upgrade

## What Changed

- added two direction-check tables to `Step 3 | Analyze Current Set`:
  - `Top Over-Predicted`
  - `Top Under-Predicted`
- added grouped stability views based on currently available stable grouping fields:
  - `Liquidity Tier`
  - `Turnover Tier`
- computed group-level `ACTUAL_MEAN`, `PREDICTED_MEAN`, `MAE_MEAN`, `BIAS_MEAN`, and `ROW_COUNT`
- intentionally did **not** add an industry breakdown because the current stable universe / market lookup data does not include an industry field

## Why

The user wanted clearer visibility into where the regularized model is overestimating or underestimating volatility, and wanted grouped performance views to see which stock subsets are modeled more reliably.

## Scope

- residual ranking tables
- group-level performance analysis inside the analysis page

## Validation

- `python -m py_compile C:\Users\38730\Desktop\ACC102\src\app_ui\page_renderers.py`
- `python -m py_compile C:\Users\38730\Desktop\ACC102\app.py`
- launched Streamlit on port `8514` and verified `STATUS_CODE=200`

## Output Files

- `C:\Users\38730\Desktop\ACC102\src\app_ui\page_renderers.py`
- `C:\Users\38730\Desktop\ACC102\logs\app_smoke_test_20260424_grouped_checks.txt`

## Rollback Plan

- remove the over/under-predicted tables and grouped-tier blocks from `render_analysis_page`
- restore the previous analysis page if the added diagnostics prove too heavy or confusing

## Risks

- liquidity / turnover tiers are proxy groupings, not industry classifications
- if a future data source adds industry fields, grouped analysis should be upgraded to use true sector labels
