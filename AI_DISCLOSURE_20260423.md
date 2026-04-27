# AI Disclosure

## Purpose
This document discloses how AI assistance was used during the development of this project.

## Scope Of AI Use
AI was used as an engineering copilot, not as a replacement for project ownership.

AI-assisted tasks included:

- structuring workflow scripts
- drafting engineering documentation
- helping maintain project traceability
- proposing and refining feature-engineering and evaluation steps
- generating a minimal walk-forward evaluation script
- helping summarize current limitations and next-step options

## What AI Did Not Replace
AI did not replace responsibility for:

- choosing the project route
- deciding whether the lightweight route was sufficient
- interpreting whether current model performance is acceptable
- validating whether outputs match the actual project state
- deciding when to pause for design choices

Those decisions remained under human control.

## Verification Practice
AI-generated code and text were not accepted blindly.

They were checked against:

- current file structure
- persisted artifacts already present in the project
- current route and dataset scope
- actual model outputs rather than imagined results

Where the system was incomplete, documentation was written to reflect that incompleteness instead of hiding it.

## Current Honest Status
The current project is not represented as more complete than it really is.

Specifically:

- `150`-stock raw daily price fetch is complete
- full-universe downstream model loop is complete on the current lightweight route
- the current boosted model does not outperform the regularized default model on the main held-out benchmark, even though it looks somewhat better on the latest aggregate walk-forward check
- sparse fund-flow features are present in the data layer but excluded by coverage gating
- macro-rate features are now part of the active model path

This disclosure is included to support transparency and academic honesty.

## Author Responsibility
Final responsibility for the submitted project, its claims, its design choices, and its interpretation remains with the human author.
