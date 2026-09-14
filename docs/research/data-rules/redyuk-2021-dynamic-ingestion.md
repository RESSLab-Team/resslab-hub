# Automating data quality validation for dynamic data ingestion

Sergey Redyuk, Zoi Kaoudi, Volker Markl, Sebastian Schelter. EDBT 2021. Algorithm and system paper, with an experimental evaluation.

## In one paragraph

The paper targets pipelines that regularly ingest large batches of external data into a data lake, where errors often corrupt a large fraction of one batch and no domain expert keeps hand-written rules up to date. The method: for every past batch, compute a small set of descriptive statistics per column (completeness, distinct count, most-frequent-value ratio, numeric mean/min/max/std, a typo score for text), concatenate them into one feature vector per batch, and train a one-class novelty detection model (k-nearest neighbors) on the history of "acceptable" batches. A new batch is flagged an outlier if its feature vector's average distance to its k nearest historical batches exceeds a learned percentile threshold. On five real datasets, this reaches the same detection quality (ROC AUC around 95%) as hand-tuned baselines (Deequ, TensorFlow Data Validation), beats their automated variants which over-flag, and runs about ten times faster (p. 1, p. 4, p. 8).

## Core principles

1. **Batch-level, not row-level.** The method judges a whole incoming batch, not single rows, targeting errors that corrupt a large fraction of a batch at once (p. 1).
2. **History as the only training signal.** Past batches are the sole "positive" examples; no labeled bad data and no manual rules are needed (p. 3).
3. **Descriptive statistics stand in for the raw data.** Per column: completeness, approximate distinct count, most-frequent-value ratio, and for numeric columns min/max/mean/standard deviation; for text a typo score. All are cheap, single-pass statistics (p. 2, p. 3).
4. **One feature vector per batch.** Per-column statistics of a batch are concatenated into one numeric vector, normalized to 0-1, with fixed length per dataset (p. 4).
5. **kNN wins the internal comparison.** Among seven one-class algorithms tried, average-distance kNN gave the best ROC AUC and zero false positives in the preliminary study (p. 4).
6. **The decision rule is a percentile threshold on distance.** A batch is an outlier if its mean distance to its k nearest historical batches exceeds the (1 - contamination)-th percentile of those distances in the training history (p. 4).
7. **Small, fixed hyperparameters.** k = 5, Euclidean distance, mean aggregation, contamination = 1%; none needed heavy tuning (p. 4).
8. **Automated beats automated, ties hand-tuned.** Against fully automated TFDV, Deequ and statistical tests the method wins; against hand-tuned versions it reaches comparable ROC AUC, without a domain expert (p. 7-8).
9. **Hand-tuned rules still win when someone can write them.** Hand-tuned Deequ reached 100% and 92% ROC AUC on the two ground-truth datasets, above the automated method's 95% (p. 8).
10. **Detection quality is error-type specific.** Missing values and numeric anomalies are detected reliably, often already at 10% corruption; typos are hardest in every dataset (p. 9).
11. **Needs a minimum history, then flattens out.** Experiments start once at least 8 prior partitions exist (too little history gives a broad, false-positive-prone boundary); ROC AUC then stays roughly flat as more history accumulates (p. 6, p. 10-11).

## The algorithm

Algorithm 1 (p. 4) is the core: given a new batch `t`, a neighbor count `k`, the matrix `X` of feature vectors of previously ingested batches, a `contamination` fraction, a distance and an aggregation function:

1. For every column of `t`, compute the statistics for its data type and append them into one vector `statistics`.
2. Build a Ball tree (a space-partitioning structure for fast nearest-neighbor search) over `X`.
3. For every historical vector `x` in `X`, get its distance to its own k nearest neighbors within `X`, aggregate with `agg` (mean), and collect into a `distances` array. Done once per retraining.
4. Set `threshold` as the `(1 - contamination)`-th percentile of `distances`.
5. Compute `t`'s aggregated distance to its k nearest neighbors in `X`. Below `threshold` means inlier, otherwise outlier.

Reimplementable in Python with `sklearn.neighbors.NearestNeighbors` and `numpy.percentile`. The model retrains every time a batch is accepted, self-adapting as data drifts (p. 3-4).

## Evaluation setup and error types

Five datasets: Flights and FBPosts have real ground truth (dirty and cleaned versions of each partition); the other three have none, so six error types are injected synthetically: explicit and implicit missing values (`'NONE'` or `99999`), numeric anomalies (Gaussian noise on the column mean, std scaled 2 to 5 times), swapped numeric and textual fields, and typos ("butterfinger" qwerty swaps) (p. 6-7). Training starts once at least 8 partitions exist; at every later timestamp the method and baselines get the clean partition and its corrupted counterpart and must label each (p. 6). Baselines: TensorFlow Data Validation (schema and constraint inference), Deequ (declarative data unit tests plus constraint suggestion), and statistical tests (Kolmogorov-Smirnov for numeric, chi-squared for categorical, p = 0.05, Bonferroni corrected), each fully automated and hand-tuned (p. 7).

## Rules of thumb

| Quantity | Value | Condition | Page |
|---|---|---|---|
| Minimum training partitions before evaluation starts | 8 | all experiments | p. 6 |
| Neighbors k | 5 | kNN novelty detector | p. 4 |
| Contamination hyperparameter | 1% | best on average in a preliminary sweep | p. 4-5 |
| Distance / aggregation | Euclidean, mean of k distances | beat max and median in their tests | p. 4-5 |
| Statistical test significance threshold | p = 0.05 | KS / chi-squared baseline, Bonferroni corrected | p. 7 |
| ROC AUC, average kNN vs. hand-tuned Deequ | ~95% vs. 100% / 92% | Flights and FBPosts | p. 8 |
| ROC AUC, hand-tuned TFDV | 50-82% | across settings | p. 8 |
| Execution time | ~1 order of magnitude faster | average kNN vs. all three baselines | p. 8 |
| Error magnitude where detection is often already reliable | 10% | error types with a "flat" ROC AUC curve | p. 9-10 |
| Combined vs. single error type ROC AUC | mean squared error 0.028 | close to the easier single-type score | p. 10 |
| Real-world dataset sizes used | 11k to 1.49M records, 31 to 3579 partitions, ~45-2350 records/partition | Table 2 | p. 5 |

## Vocabulary

- **Novelty detection**: one-class learning from only "acceptable" examples, flagging new points that deviate; unlike anomaly detection it assumes no outliers in training data (p. 2).
- **Data partition (batch)**: one chronological slice of a growing dataset, e.g. one day's ingested records (p. 3).
- **Completeness**: ratio of non-null values in a column (p. 2).
- **Index of peculiarity**: a score from bi- and trigram letter frequencies in a text column, used to flag typos (p. 3).
- **Contamination**: assumed fraction of the training set secretly mislabeled "inlier"; sets the percentile for the decision threshold (p. 4).
- **Ball tree**: a binary tree partitioning points into nested hyperspheres, for fast nearest-neighbor search (p. 4).
- **ROC AUC**: area under the receiver operating characteristic curve, the metric for true/false positive trade-offs (p. 6).
- **Data lint**: a rule flagging a deviation from accepted data-analysis practice, like a code lint (p. 11).

## Examples worth remembering

- **Figure 1 walkthrough**: a toy table with columns A (text) and B (numeric). A missing value in A and a numeric outlier in B both shift the feature vector (lower completeness, shifted mean/std), and the batch is flagged as an outlier (p. 3).
- **Flights dataset**: 95% of timestamps have an inconsistent date-time format; 63% of gate fields mix missing values, inconsistent null encodings, and incomplete values. The method still reaches high ROC AUC despite never being told these patterns (p. 8).
- **TFDV false alarm on unseen categories**: TFDV flags "Source" and "Flight" as schema violations only because the new batch has previously unseen category values, though those columns have no real errors, illustrating over-flagging by conservative schema tools (p. 8-9).
- **Typos and word uniqueness**: the peculiarity score catches a typo when the corrupted word repeats elsewhere in the batch, but misses it when the word is already near-unique (p. 9-10).

## Quotes

- "we focus on scenarios where systems regularly ingest batches of external data, and data errors corrupt a large fraction of the batch" (p. 1).
- "our approach does not require domain experts to define rules and constraints or provide labeled examples, and self-adapts to temporal changes in the data characteristics" (p. 1).
- "a data point is considered an outlier if its aggregated distance to k nearest neighbors exceeds the learned threshold" (p. 4).
- "our approach outperforms other automated baseline solutions and reaches the predictive performance of hand-tuned baselines" (p. 8).
- "The automated variants of the baselines tend to be conservative and produce false alarms in the majority of cases" (figure 2 caption, p. 7).
- "hand-tuning of existing solutions with the domain expertise is highly dataset-specific and tedious" (p. 9).

## Applying it to RESSLab-Hub

- The paper's core claim (batch-level novelty detection matching hand-tuned rules) was shown on batches of roughly 45 to 2350 rows, with 8 or more historical batches (p. 5-6). This is my own transfer, not the paper's claim: our submissions are one to a few dozen rows, arriving occasionally, so per-batch mean/std/completeness would be noisy and 8 comparable batches will take a while to accumulate. Batch-level kNN novelty detection does not fit our scale; do not build it as the ingestion-time gate.
- What transfers is the row-level version of the same mechanism: percentile-based statistics of the whole database per column and peer group (steel family, section family), flagging a row's value outside the learned percentile band, as in the proposal's item 2. This reuses the paper's percentile threshold at row level instead of batch level; the scaling is my adaptation.
- The completeness metric (p. 2) is reusable per row against the data dictionary's nullability, not as a batch-wide ratio; the paper's framing is a good "why" for a check we already do.
- The index of peculiarity (p. 3) is worth adapting narrowly for categorical strings (steel grade, section name) to catch typos against values already in the database, as a warning, applied to one value against history, not as a batch statistic.
- The paper's finding that hand-tuned rules (Deequ) beat the automated detector when a domain expert can write them (p. 8) supports the proposal's direction: a `<table>_rules.yaml` of explicit checks (proposal item 1) fits us better than an unsupervised model, since curators are the domain experts and columns already have known exact identities and orderings (h_over_t_cw, f_u > f_y).
- The paper's "conservative baseline over-flags" finding (p. 8-9, TFDV flagging unseen categories) cautions our range checks: a rule firing on any new categorical value (a new steel grade) will cause false alarms and should stay "info" or "warning", not "error", unless the value truly breaks type or nullability.
- Do not adopt the paper's ML novelty detector for RESSLab-Hub: at our scale, hand-written rules plus percentile-based ranges match what the paper's own hand-tuned baselines do, and those beat the automated ML method in its results (p. 8).

## Limits and caveats

The paper tests six error types and does not claim to catch semantic or cross-column errors (a derived value inconsistent with the columns it comes from); it leaves "errors that are a deterministic function of the inputs, like accidentally changing the encoding" for future work (p. 12). It assumes every historical batch was acceptable, with no held-out true negatives, and has no formal control of the false alarm rate (future work, p. 12). All real datasets are far larger per batch than a RESSLab-Hub submission, so detection at very small batch sizes is untested. The feature vector in Figure 1 and the index-of-peculiarity formula (Equation 1, p. 3) came through the PDF conversion garbled; I described the method in words instead of transcribing the equation. I read the full paper, including related work and references, but did not follow up cited work.
