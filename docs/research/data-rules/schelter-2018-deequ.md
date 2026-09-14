# Automating large-scale data quality verification

Sebastian Schelter, Dustin Lange, Philipp Schmidt, Meltem Celikel, Felix Biessmann, Andreas Grafberger. PVLDB 2018. System paper: the Deequ data quality library built at Amazon.

## In one paragraph

Teams that ingest data at scale need to check its quality, but usually do this by hand with ad hoc scripts. The paper presents Deequ, a library on Apache Spark for declarative "unit tests" for data: named constraints (completeness, uniqueness, value range, and more) backed by metrics (numbers computed from the data). It computes metrics in few passes, updates them incrementally as new data arrives instead of rescanning history, can suggest constraints from single-column profiling plus a small classifier, and can flag anomalies in the time series of metrics across dataset versions. Experiments on up to 120 million records show metric computation scales linearly, incremental computation beats batch after a few deltas for grouped metrics, and suggestion heuristics produce mostly correct constraints on two real datasets.

## Core principles

1. **Declarative over imperative.** Users say what the data should look like; the system works out which metrics to compute and how (p. 1781-1782).
2. **A constraint is a predicate over a metric.** For example `Completeness(title) == 1.0`, letting computation be shared across constraints (p. 1784).
3. **Constraints combine with user code.** A constraint can take a user function as its comparison, not just fixed thresholds (p. 1782, p. 1784).
4. **Scan sharing.** Metrics not needing re-partitioning are computed together in one query, so passes do not grow with the number of checks (p. 1787, p. 1789).
5. **Incremental over batch on growing data.** Metrics rewrite as a state plus an update function, so a new snapshot's metric comes from the old state plus the new delta only (p. 1785).
6. **Incremental is not always a win.** Grouped metrics on a high-cardinality column keep a histogram as state; if almost every value is new, incremental can be slower than batch (p. 1789-1790).
7. **Constraint suggestion is cheap single-column profiling**, since tables can have billions of rows: three passes only (p. 1788).
8. **Suggestion is human-in-the-loop.** Suggestions are reviewed and picked by a person, not auto-applied, since a constraint holding on a sample may not hold on future data (p. 1788).
9. **Predictability as a quality signal.** If a naive bayes model predicts a column well from others, a drop across versions flags a problem, without knowing the rule in advance (p. 1786, p. 1791).
10. **Metric history enables cross-version checks.** Every computed metric is stored per dataset version for anomaly detection (p. 1784-1785, p. 1794).
11. **Anomaly detection is pluggable.** The default, `OnlineNormal`, keeps a running mean and standard deviation and flags values past a user-set number of deviations (p. 1794).
12. **Conservative suggestions build trust.** When unsure, the system prefers a missed true constraint over a wrong suggested one (p. 1790).

## The constraint API and metric catalogue

Table 1 (p. 1783) lists constraints; Table 2 (p. 1784) lists the metrics behind them.

- **Completeness**: `isComplete(column)` requires fraction non-missing = 1.0; `hasCompleteness` allows a custom threshold. Metric `Completeness` = non-null count / N.
- **Uniqueness/keys**: `isUnique(column)`, `hasUniqueness`, `hasDistinctness`. Metrics `Uniqueness` (values occurring exactly once, among distinct values) and `Distinctness` (distinct count / N).
- **Ranges, types, shape**: `isInRange`, `hasConsistentType`, `isNonNegative`, `isLessThan(colA, colB)`, `satisfies(predicate)`, `satisfiesIf(predA, predB)`. All reduce to metric `Compliance`: fraction of rows matching a predicate.
- **Predictability**: `hasPredictability(target, inputColumns)` checks a naive bayes model's held-out quality.
- **Row count and summary stats**: `hasSize`, `hasTypeConsistency`, `hasCountDistinct`, `hasApproxCountDistinct`, `hasMin`, `hasMax`, `hasMean`, `hasStandardDeviation`, `hasApproxQuantile`, `hasEntropy`, `hasHistogramValues`.
- **Column pairs**: `hasMutualInformation`, `hasCorrelation`.
- **Time**: `hasNoAnomalies(metric, detector)`, the only constraint looking across versions, not one snapshot.

A check groups constraints under one severity `Level`, can be scoped to the incoming delta (`on = "delta"`), and kept per group value (`groupBy = "..."`). A run returns, per constraint, `Success` or `Failure` with the compiled predicate and the failing value (p. 1785).

## Incremental computation and suggestion, in words

**Incremental metrics.** For D(t+1) = D(t) plus delta ∆D, the system keeps a small state S and an update rule instead of rescanning: `Size` adds row counts; `Compliance`/`Completeness` keep a matching count and N, adding the delta's; `Uniqueness`/`Distinctness` and `Entropy` share a per-value count histogram, merged with the delta's by summing counts per value; `MutualInformation` keeps per-column and co-occurrence histograms and merges them; `Predictability` keeps naive bayes per-feature, per-class counts and adds the delta's. `ApproxQuantile` and `ApproxCountDistinct` use sketches that merge natively (p. 1785-1787). Physically, a grouped metric's state is `delta.groupBy(columns).count()`; updating is a full outer join with the old histogram plus a sum (Figure 3, p. 1788).

**Constraint suggestion.** Three passes over an untyped table: (1) size, type detection, completeness, approximate distinct count (hyperloglog); (2) min/max/mean/standard deviation/approximate quartiles for numeric columns; (3) full frequency table for low-cardinality columns. Heuristics read off constraints (p. 1788): complete in sample -> `isComplete`; incomplete -> `hasCompleteness` with a lower bound from a Bernoulli confidence interval; type not string -> `hasConsistentType`; row count / approx. distinct count within the sketch's error bound -> `isUnique`; bounded numeric range (for example min 0) -> a `Compliance` range constraint; distinct count below a threshold -> categorical, suggest `isInRange` over the observed set. A logistic regression classifier (2,453 (table, column, type, is_unique) tuples from open source schemas, hashed name n-grams, AUC 0.859) only confirms or vetoes the `isUnique` heuristic, above 50% probability (p. 1789-1790).

## Rules of thumb

| Quantity | Value | Condition | Page |
|---|---|---|---|
| Growing dataset | ~120M records, ~50GB, 10 deltas of ~12M | scalability experiments | p. 1789 |
| Runtime vs size | linear | all four metric workloads | p. 1789 |
| Incremental vs batch crossover | wins after 3-4 deltas | grouped metrics, low-cardinality columns | p. 1790 |
| Incremental on near-unique column | no benefit, same growth as batch | product_id | p. 1790 |
| Predictability, brand from name | F1 over 97%, up to 99.5% with more columns | 100k-600k and full of 845k sample | p. 1790 |
| Unique-classifier AUC | 0.859, threshold: suggest only if probability > 50% | logistic regression, L1, reg. 0.001 | p. 1790 |
| location completeness (twitter) | 0.28076, suggests `hasCompleteness >= 0.28`, holds held-out | sample-suggested constraint | p. 1791 |
| statuses_count uniqueness, held-out | 64% (heuristic wrongly suggested `isUnique`) | classifier assigns it 2% vs 81% for id | p. 1791-1792 |
| Example anomaly bounds | warn at 3 std devs, error at 4 | `OnlineNormal(stdDevs=...)` example | p. 1783 |

## Vocabulary

- **Check**: a named group of constraints at one severity, optionally scoped to a delta or a group.
- **Constraint**: a user-facing rule compiled to a metric plus a predicate.
- **Metric**: a number computed from the data that a constraint's predicate checks.
- **Analyzer / AnalysisRunner**: the operator computing one metric; the runner schedules and shares work across analyzers.
- **Delta / state**: records added since the last snapshot; the sufficient statistics kept between snapshots for updates.
- **Predictability**: a metric equal to a naive bayes model's held-out prediction quality for one column from others.
- **Hyperloglog sketch**: a probabilistic structure behind `ApproxCountDistinct`.
- **Scan sharing**: running aggregations with the same grouping in one pass.

## Examples worth remembering

- **Video log check (Listing 1, p. 1783).** One check declares `isComplete` on six columns, `isUnique` on a four-column combination, a `hasCountDistinct` bound from a REST call, and a `hasHistogramValues` bound on the phone-device ratio: constraints mixed with external data and custom code.
- **Matching output (Listing 2, p. 1785).** `isComplete(title)` succeeds; `isUnique(...)` fails at 99.67% instead of 100%; `isInRange(priority, ...)` fails at 83.3% compliance: constraint, compiled predicate, failing value.
- **Entropy incremental update (Figure 3, p. 1788).** Delta grouped and counted, full-outer-joined with the previous histogram, counts summed, entropy recomputed without touching raw prior data.
- **Twitter `lang` failure (p. 1791).** The suggested value-set constraint fails on held-out data: rare languages (turkish, hungarian) are missing, and the same language appears under different capitalizations ("en-gb" vs "en-GB"), a real normalization bug the failure points at.
- **Twitter `statuses_count` false suggestion (p. 1791-1792).** Heuristic suggests `isUnique`, but held-out uniqueness is only 64%; the classifier assigns only 2% (versus 81% for the real id column), avoiding the bad suggestion.
- **Reddit trolling anomaly (p. 1794).** Tracking `Mean(controversiality)` per subreddit per day, most boards stay low variance, but spikes in cringepics and chicagobulls get flagged and tie to days with many deleted users.

## Quotes

- "We want them to focus on the definition of their checks and their validation code, but not on the computation of the metrics required for the constraints." (p. 1782)
- "We ... rely on the end user to select from and validate our suggestions which might not necessarily hold for future data." (p. 1788)
- "If a column is complete in the sample at hand, we suggest an isComplete (not null) constraint." (p. 1788)
- "We prefer conservative and robust suggestions (e.g., rather having false negatives than false positives), which build trust in our users." (p. 1790)
- "Data producers can leverage our system to halt their data publishing pipelines when they encounter cases of data anomalies." (p. 1792)

## Applying it to RESSLab-Hub

- Our `<table>_rules.yaml` (check expression, severity, message, fix, why) matches the paper's Check + Constraint model: one YAML rule = one constraint, severity = `Level` (Table 1, p. 1783).
- Map our rule kinds to the catalogue (our transfer, no steel example in the paper, Table 1-2, p. 1783-1784): not-null column -> `isComplete`; a min/max or peer-group range -> `isInRange`/`Compliance`; a derived-column identity (`h_over_t_cw = h_c / t_cw`) -> `satisfies` (a row predicate, not a history metric); an ordering (`f_u > f_y`) -> `isLessThan`/`satisfies`; a fixed constant (E = 200 GPa) -> `isInRange` with a near-zero width.
- Our "one span outside global min/max" warning is a `hasMin`/`hasMax` check; per-peer-group ranges are the same metric per group. The paper's `groupBy` only groups constraint history, not the range, so this is our extension (p. 1783).
- Skip the paper's architecture (Spark, DynamoDB, S3, incremental state): it solves a billions-of-rows problem we do not have. Pandas or plain Python plus simpleeval, recomputing on every upload, is enough at our size (p. 1785-1787, our judgment).
- Reuse the suggestion heuristics for the proposed rule-discovery spike (step 0): profile each CSV and turn each heuristic into a draft YAML rule for curator review, not auto-applied (p. 1788, transfer).
- Skip `hasPredictability` and the name-based `isUnique` classifier: both need far more rows and similar tables than we have; matches our decision to skip ML-based multivariate detection in v1 (p. 1788-1790).
- Our unit-factor detector (value / median near 25.4, 6.895, 1000) has no equivalent in the paper; it is our own addition for mm/inch, MPa/psi, N/kN mistakes.
- `hasNoAnomalies` and per-version metric history fit our submission-as-PR model: each merged contribution is a new table version, so flagging a jump with `OnlineNormal` is a cheap later addition, not v1 (p. 1791-1792, transfer).
- Keep our issue shape close to the paper's output (constraint name, compiled expression, failing value) alongside code/severity/suggestion/why, for predictable LLM explanations.

## Limits and caveats

- The paper targets scale (Spark, billions of rows, DynamoDB, S3) and never discusses small tables; only the constraint vocabulary and suggestion heuristics transfer here.
- I did not read the cited related work [1]-[50], only the paper's own summary in Section 7.
- A few page numbers are approximate where the two-column layout and figures interleaved in the conversion (around p. 1789-1792); I used the printed page numbers in the body text over the `<!-- page N -->` markers.
- Formulas for entropy, mutual information, and the smoothed naive bayes estimate were garbled by the conversion; described in words instead of reconstructing symbols.
- The heuristics and predictability metric are tested only on two datasets and one product catalog, none like small engineering tables, so the reuse above is an extrapolation.
- Section 4's Scala interfaces are Spark-specific; summarized, not transcribed.
