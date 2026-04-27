# Reflection

## Project Framing
This project started with a deliberate trade-off: choose a lightweight route that can be executed quickly and verified early, then retain the option to upgrade later.

Instead of beginning with the most formal `A + A` path, we started from:

- curated liquid stock universe
- AKShare-first data workflow
- sample-first modeling loop

This decision reduced startup friction and let the engineering skeleton form early. In practice, that was useful because it gave us a real pipeline, a real app shell, and real artifacts before the project became too large to reason about.

## What Worked Well
The strongest part of the project so far is engineering structure rather than model performance.

What worked well:

- the project was organized into modular workflow scripts instead of notebook-only logic
- intermediate outputs were persisted with dated filenames
- the app reads saved outputs instead of retraining online
- baseline, regularized, boosted, and comparison outputs were separated cleanly
- the route choice was documented rather than hidden

This made the project easier to debug, easier to explain, and easier to resume after interruptions.

## What Did Not Work As Well
The main weakness is no longer raw-vs-model scale mismatch, but model stability under richer features and longer history.

The raw daily price layer and the downstream model loop have both now been pushed to the lightweight full-universe path. That closed an important engineering gap, but it also revealed a new one: the system is now coherent enough to expose model instability more clearly.

Another issue is that the first non-price feature layer introduced a practical trade-off. Adding individual fund flow features made the feature set richer, but because those features have more limited temporal coverage, the usable modeling sample became much smaller. We eventually responded by adding a coverage gate at model entry, which protects the full-universe path but also means those sparse features are currently excluded from the default model path.

This is a good reminder that more features do not automatically mean a better model. Coverage, consistency, and time alignment matter just as much.

## Model Reflection
The current results still suggest that the regularized ridge model is the safer default for the app and submission narrative. After the full-universe rerun with macro features, the boosted model can still fit the training sample much more aggressively, and after retuning it even becomes slightly stronger on aggregate walk-forward RMSE. However, its main held-out split remains much worse than the regularized branch. This likely reflects some combination of:

- imperfect boosting hyperparameters for the current feature stack
- sensitivity to the expanded date/stock panel
- heterogeneous regimes across the longer full-universe sample
- limited feature engineering depth
- weak model-selection discipline earlier in the project, before the regularized benchmark was added

That is not a dead end. It simply means the current project stage is still closer to engineering validation than to a high-confidence forecasting result.

## What I Would Improve Next
If I continue this project, the first priority is not to add many more models. The better next step is to make the data-to-model path more coherent.

Priority improvements:

1. decide whether boosted deserves any further work after its mixed retuned comparison against regularized
2. inspect feature coverage before merging additional non-price layers
3. use walk-forward evaluation as a default gate before promoting any model narrative
4. only then decide whether to stay on `B + B` or upgrade toward `A + A`

This order matters because otherwise I would be adding complexity faster than I can validate it.

## Lessons Learned
The most important lesson is that a project can look complete on the surface before it is actually aligned underneath. A working app, model outputs, and many scripts do not automatically mean the system is fully coherent. The internal state of the pipeline matters: which layers are sample-only, which are full-scale, and which assumptions are still provisional.

Another lesson is that traceability helps not only with grading but also with thinking. When outputs, routes, and limitations are explicitly written down, it becomes much easier to notice where the project is genuinely strong and where it is still unfinished.

## Final Reflection
At this stage, I would describe the project as a credible engineering prototype with a clear path to becoming a stronger submission. It already demonstrates workflow design, reproducibility discipline, modular implementation, a full-universe downstream rerun, and a stronger regularized benchmark than the original plain baseline. The next milestone is to decide whether the project should keep pushing feature breadth or lock the regularized branch as the final submitted model narrative.
