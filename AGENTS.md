# Project rules for coding assistants

1. Read README.md, docs/02_learning_plan_12_weeks.md, docs/03_architecture.md, docs/05_methods.md and TESTING.md before editing.
2. Official files live in data/raw, downloaded by `python run.py download` (Asset1 v2 file 67453365, Asset2 file 62130498; provider MD5 verified, see data/raw/manifest.json). data/demo is an independently generated fixture for offline tests/CI, NOT PRIME-CVD. Never fabricate provenance or results. Never silently fall back from official to demo.
3. data/raw is immutable. Preserve provider file IDs, source metadata and hashes. Keep transformed output separate (data/processed, outputs/).
4. Patient-level splits only. Identifiers, source indices, follow-up and outcomes cannot be predictors. Fit preprocessing within each training fold.
5. Hyperparameters are chosen within training only. Keep test locked (the shipped outputs have NOT opened it; that is left to the learner in week 12). Do not erase the fact that a test set was examined.
6. Asset2 is the same cohort representation, NOT external validation. Do not reconstruct continuous censoring times from a shared censoring month (w10a does this only as a deliberately quantified counter-example). BMI may be derived from measured height and weight in the same EMR table and must be labelled in BMI_source; never back-fill it from Asset1.
7. Unknown units/labels and duplicate measurements must be audited, not silently dropped. Disease absence=0 and "High glucose → diabetes" are specific to the known synthetic construction, not general EMR advice.
8. The package (engineering track, pipeline) fits Cox via statsmodels partial likelihood. The tutorial notebooks (w**a) use lifelines with `fit_options={"step_size": 0.5}`; the default step silently diverges (HR≈0) for strong effects. Results were checked against R survival::coxph. Do not claim support for competing risks or formal PH diagnostics that are not implemented.
9. Write tests for every fix. Run `python -m pytest -q` and `python scripts/execute_notebooks.py`. Report actual outcomes including skips.
10. Figures use primecvd/pubplot.py (print sizes, Okabe-Ito semantic colours: exposed/event = vermillion, reference = blue; KM with number-at-risk table; forest plots with log axis). See docs/10_visualization_guide.md.
11. Notebooks are named by week: w**a = tutorial (concepts, full cohort), w**b or single = engineering practice (splits, package functions). Keep cross-references ("第 N 周 a/b") consistent when renaming.
12. Do not run arbitrary downloaded code, upload data, store credentials, overwrite the user's reports, or commit virtual environments/font files.
