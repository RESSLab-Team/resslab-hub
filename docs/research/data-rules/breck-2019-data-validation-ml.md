# Data validation for machine learning

Breck, Polyzotis, Roy, Whang, Zinkevich, 2019, SysML (2nd conference). System paper: describes a production data-validation system (part of TFX at Google) and reports deployment results.

## In one paragraph

Data errors that reach a training pipeline can silently hurt model quality, and the bad data often feeds back into more training data before anyone notices. The paper presents a system that checks data before training: a schema, like a database schema but extended for ML, encodes what a batch of data should look like (types, presence, value counts, domains). A Data Analyzer computes per-batch statistics, a Data Validator compares them to the schema and flags anomalies, and a Model Unit Tester fuzzes the training code with schema-generated synthetic data to catch code assumptions the schema misses. The schema starts as an auto-inferred draft, then is owned and edited by humans, versioned like code. Beyond single-batch checks, the system compares batches to each other and to serving data to catch skew and drift, using a distance metric instead of classic statistical tests, which proved too sensitive at Google's scale. Deployed across more than 700 pipelines, it caught real production bugs, cut debugging time from months to days in one case, and most fired anomalies were fixed, not ignored.

## Core principles

1. **Data is a production asset**, monitored and validated with the same rigor as algorithm and infrastructure code (p. 1).
2. **The schema is the contract, but data comes first.** Unlike a database schema written before data exists, here it is reverse-engineered from data and co-evolves with it (p. 2, 5).
3. **Schema inference gives a starting point, not a final answer, and is versioned like code.** A basic schema is synthesized from available batches, avoiding overfitting, then reviewed and stored in version control (p. 5).
4. **Single-batch validation** checks one batch against the schema: missing feature, wrong type, out-of-domain value, wrong presence rate. **Inter-batch validation** checks batches against each other or serving data for skew and drift (p. 3-4, 6).
5. **Classic statistical tests are too sensitive at scale, so use a bounded distance metric with a named "culprit" value instead.** A harmless 0.01% noise injection made a chi-squared test reject 7 times out of 10; the alternative gives an interpretable threshold plus the value that changed most (p. 6-7).
6. **Alerts must be high-precision and narrow, or on-calls learn to ignore them**, letting real errors go unnoticed (p. 1, 5).
7. **Schema-driven fuzz testing catches assumptions the schema does not state**, such as code silently assuming a feature is always positive (p. 7-8).
8. **Most fired anomalies get fixed**, but some are left because regenerating data is impossible, or a human missed the alert (p. 8-9).
9. **Validate data directly, not just aggregate model quality**, since a per-slice error can hide in overall metrics (p. 1-2).

## The schema formalism and its distance metric

The schema is a flat list of per-feature constraints (a protocol buffer message). Each feature carries: **type** (INT, FLOAT, BYTES; a type change can crash the trainer, p. 4, 13); **presence** (minimum fraction of examples where the feature must appear, `min_fraction: 1` means always present, p. 4, 13); **value_count** (min/max values per example, scalars have min = max = 1, p. 4, 13); **domain** (a shared or inline int/float/string/bool domain, which can also encode a semantic type beyond the raw type, e.g. a bytes feature really holding booleans, p. 4-5, 13); **lifecycle_stage** (PLANNED through DEBUG_ONLY, sets anomaly severity, p. 13); and **skew_comparator**/**drift_comparator** (drift bounds versus serving data or the previous batch, p. 13).

Reimplementable core idea: for each column, store an inferred min-presence fraction, type, domain, and value-count bounds; compare a new batch's statistics against these, and any violation becomes an anomaly with a templated message (column, expected constraint, observed value).

For drift, classic tests get more sensitive as sample size grows, so at Google's scale almost any two real batches "fail" even with harmless natural variation (p. 6-7). The chosen metric, d∞(p, q), is the largest absolute difference in probability for any single value between distributions p and q: it has a plain meaning, so teams can set a threshold like "alert if any value's share changes by more than 1%", and the value achieving the max is the culprit to debug from, e.g. a code default of -1 becoming common after a backend outage (p. 7). A second metric, d1(p, q), sums the per-value differences and is used only to visualize drift, since it does not blow up the way KL divergence can when a tiny probability becomes a slightly less tiny one (p. 14). An appendix argues, via a Dirichlet-prior model, that empirical drift stands in for true drift once each batch has about a billion observations; not claimed at smaller sizes (p. 13-14).

## Rules of thumb

| Quantity | Value | Condition | Page |
|---|---|---|---|
| Chi-squared test false alerts | 7 of 10 trials | 10K of 100M points swapped N(0,1) to N(0,2), 0.01% noise | p. 7 |
| Skew/drift metric | d∞(p,q) = max_i \|p_i − q_i\| | main alerting metric | p. 7 |
| Visualization metric | d1(p,q) = sum_i \|p_i − q_i\| | drift visualization, appendix | p. 14 |
| Pipelines with model unit tests | over 70% | of pipelines on the platform | p. 9 |
| Unit test executions / failure rate | 80K+ runs, 6% failed | over one month | p. 9 |
| Fuzz-test examples needed | "in the 100s" | to trigger common training-code errors | p. 8 |
| Pipelines analyzed | over 700 | schema-evolution study | p. 8 |
| Schema edits per pipeline | most: up to 5, tapering off | histogram over the >700 pipelines | p. 8 |
| App install rate gain | 2% | A/B test, missing-feature skew fixed | p. 9 |

Table 1 (p. 9, read from the page image), share of pipelines over 30 days:

| Anomaly | Used | Fired | Fixed given fired |
|---|---|---|---|
| New column (in data, not schema) | 100% | 10% | 65% |
| Out-of-domain categorical value | 45% | 6% | 66% |
| Missing column | 97% | 6% | 53% |
| Feature present in too few examples | 97% | 3% | 82% |
| Data completely missing | 100% | 3% | 65% |
| Wrong data type | 98% | <1% | 100% |
| Out-of-domain numeric value | 67% | 1% | 77% |

Rare checks (type) almost never fire, but every firing got fixed.

## Vocabulary

- **Schema**: codified expectations for a batch of data, owned by humans, stored in version control.
- **Single-batch / inter-batch validation**: checking one batch against the schema alone, versus checking batches against each other or against serving data.
- **Training-serving skew**: data differs between training and serving; feature skew (same example, different value), distribution skew (overall distribution differs), scoring skew (only shown examples get labels).
- **Data Analyzer / Data Validator / Model Unit Tester**: the three components (compute statistics; compare to schema; fuzz-test training code).
- **d∞ / d1**: largest, resp. summed, per-value probability gap between two distributions; d∞ alerts, d1 visualizes.
- **Lifecycle stage**: a tag on a feature that sets how seriously its anomalies are treated.

## Examples worth remembering

- **The -1 example (Section 1).** A serving-stack refactor makes an RPC fail for a slice of data, silently mapped to -1, a value the schema allows. The model degrades on that slice, and the bad value propagates into tomorrow's training data since serving data feeds back into training (p. 1-2).
- **The "event" feature schema (Figures 3-4).** A one-feature schema requires "event" present in every example, one value, drawn from {CLICK, CONVERSION}. A new value "IMPRESSIONS" appears; the validator flags it and suggests the fix: add IMPRESSIONS to the domain (p. 4-5).
- **The chi-squared sensitivity experiment (Figure 5).** From 100 million N(0,1) points, replacing 10 thousand (0.01%) with N(0,2) samples, 10 trials gave 7 false alerts at the 1% level, though the two distributions look "the same" to a person (p. 6-7).
- **The logarithm transform assumption.** Training code takes the log of a feature, silently assuming it is positive. Nothing looks wrong until a non-positive serving value crashes it; fuzz-testing with schema-generated examples catches this beforehand (p. 7-8).

## Quotes

- "errors in the input data can nullify any benefits on speed and accuracy for training and inference." (p. 1)
- "on-calls tend to ignore alerts that are either spammy or not actionable, which can cause important errors to go unnoticed." (p. 2)
- "in our setup the data comes first. This necessitates new workflows where the schema can be inferred from and co-evolve with the data." (p. 3)
- "an overfitted schema is more likely to cause spurious alerts ... may even lead them to switch off data validation altogether." (p. 5)
- "the variance of test statistics typically has an inverse square relationship to the total number of examples, which makes these tests sensitive to even minute differences." (p. 6-7)
- "an alert comes with a 'culprit' value that can be the starting point of an investigation." (p. 7)

## Applying it to RESSLab-Hub

- **Adopt "schema as contract, data comes first, humans own it" directly** (p. 2-5): `<table>_rules.yaml` should come from a discovery spike, then be reviewed and edited by a curator like code, matching issue #366. An LLM may draft rules and "why" text, but a human should approve each before it counts as `error` severity, to avoid the overfitting the paper warns about (p. 5).
- **Build single-batch checks first, skip full inter-batch machinery.** This matches the proposal's split between YAML rules and peer-group ranges (p. 3-4). The paper's skew/drift system targets daily, billion-row batches; RESSLab-Hub gets contributions of a handful to a few hundred rows against tables of a few hundred to a few thousand rows, so only the idea (comparing a contribution to the table with a bounded, explainable statistic) transfers.
- **Do not use chi-squared or KL-style tests** (p. 6-7): too sensitive even at huge scale, worse on tables this small. Use a percentile position plus a named comparison value instead (the wwPDB style), in the spirit of the paper's max-distance metric, not a p-value (p. 7).
- **Reuse the "culprit value" idea for messages**: name the offending value and broken constraint (p. 3-4, Figure 4), matching the proposed issue shape (row, column, value, message, suggestion, why).
- **Map presence/domain constraints to the data dictionary**: `min_fraction` maps to `nullable`; domains map to categorical columns like steel grade or section name. Flag new categorical values as `info`/`warning`, not `error`, matching the paper's treatment of them as common and benign (p. 4, 9, 13).
- **Borrow fuzz-testing only as a loose idea, not a system to build**: a synthetic row from schema bounds, checked against derived-column identities (`h_over_t_cw = h_c / t_cw`, `p_yn = a_cn * f_yn`, `f_u > f_y`, `th_80 <= th_50 <= th_20`), could sanity-test new rules before merge (p. 7-8). Our transfer.
- **Keep alert-fatigue avoidance central when picking severities** (p. 1-2, 5, 9): `error` for narrow, high-confidence checks (exact identities, hard orderings, type/nullability, constants like E = 200 GPa with a `why` citing the standard); `warning`/`info` for peer-group percentile checks, so contributors are not blocked by a statistical judgment call.

## Limits and caveats

- The paper targets petabytes/day, thousands of features, streaming batches, training/serving feedback loops. RESSLab-Hub tables are far smaller and update by pull request, so the inter-batch skew/drift system transfers only as an idea.
- The Appendix B soundness argument for empirical drift needs "at least a billion" observations per batch (p. 14); it says nothing about RESSLab-Hub's row counts and should not justify the hub's own thresholds.
- The schema formalism (Appendix A) targets tf.train.Example; fields like `value_count` for list-valued features have no clear CSV counterpart and are omitted above.
- Figure 5 and the Dirichlet-prior derivation in Appendix B contain formulas the PDF conversion may have partly garbled; described here in words, not exact notation.
- The paper does not detail the "reasonable heuristics" for initial schema inference (p. 5). Table 1 was garbled in the text conversion and was read from a page render instead. Three rows (list length too small or too large, non-boolean value) are left out.
- Related work (Section 7) was read but not summarized beyond noting the main comparison, Amazon's Deequ.
