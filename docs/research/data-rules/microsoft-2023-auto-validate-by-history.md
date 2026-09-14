# Auto-Validate by-History: Auto-Program Data Quality Constraints to Validate Recurring Data Pipelines

Tu, He, Cui, Ge, Zhang, Shi, Zhang, Chaudhuri (Microsoft Research / UCLA), KDD 2023. System and algorithm paper, with a proven approximation guarantee.

## In one paragraph

Companies run thousands of recurring data pipelines. Quality bugs like schema drift, more nulls, a changed unit, or a changed row count creep in silently, and engineers today write validation rules by hand, column by column, in tools like TFDV or Deequ. This is slow and needs statistics know-how. The paper's system, Auto-Validate-by-History (AVH), looks at the history of past, presumed-good runs of a column, computes statistical metrics on that history (row count, mean, distinct count, distributional distances), and picks thresholds using Chebyshev-style probability bounds so each rule has a proven, low false-positive rate. It then picks a small set of rules that catch the most synthetic and real data problems while keeping the total false-positive rate under a target. Tested on 2000 real Microsoft pipelines, AVH beats over 20 commercial tools, anomaly-detection methods and statistical tests on precision and recall, and runs in about 1.6 seconds on 100K rows.

## Core principles

1. **History replaces hand-written rules.** AVH fits bounds from the mean and variance of a metric's past values, instead of a human picking a metric and threshold per column (p. 1, p. 4).
2. **Every rule has a proven false-positive-rate bound, not a guess.** Chebyshev's, Cantelli's inequality and the CLT each give a provable upper bound on how often a rule fires on clean data (p. 4-5).
3. **A rule is a range on one metric.** A "single-distribution" constraint bounds one metric of one column (row count, mean, unique ratio) (p. 3).
4. **A two-distribution rule compares two batches directly.** It bounds a distance metric (L1, L-infinity, Jensen-Shannon, Kolmogorov-Smirnov) between a new batch and a baseline batch (p. 3-4).
5. **Rules combine with AND only.** A "conjunctive DQ program" is a set of rules that must all hold, matching how Deequ and TFDV already work (p. 3).
6. **Precision and recall trade off through a budget.** Rule selection maximizes recall subject to the sum of the rules' FPR bounds staying under a target delta (p. 4, p. 6).
7. **Recall is estimated with synthetic error injection.** A catalogue of 10 common DQ issue types with 60 parameterized variants is injected into each column to count what a candidate rule would catch (p. 6).
8. **Rule selection is a coverage problem, solved greedily.** Add the rule with the best "new recall caught, divided by its FPR cost" ratio, until the budget is used up (p. 6-7).
9. **The greedy algorithm has a worst-case guarantee.** It reaches at least about 42% (1/2 minus 1/2e) of the best possible recall for a given budget, and never violates the budget in expectation (p. 8).
10. **Trending or cyclic history is differenced first.** A metric's history is tested with the ADF test and, if not stationary, differenced before fitting bounds (p. 5).
11. **Single-distribution metrics alone get most of the value.** Dropping the costlier two-distribution metrics gives comparable quality (p. 17).
12. **Few rules are enough.** A median of 2 to 3 clauses per column; capping at 1 or 2 hurts recall, 3 already gets most of the benefit (p. 17-18).

## The metric space and how a threshold is built

Table 1/2 list the candidate metrics. Numeric single-distribution: min, max, mean, median, sum, range, row_count, unique_ratio, complete_ratio. Numeric two-distribution: EMD, Jensen-Shannon/Kullback-Leibler divergence, Kolmogorov-Smirnov distance, Cohen's d. Categorical single-distribution: str_len, char_len, digit_len, punc_len, row_count, unique_ratio, complete_ratio, distinct value count. Categorical two-distribution: L1, L-infinity, cosine distance, chi-squared, JS/KL divergence. A "pattern" variant turns each string value into a wildcard shape (digits to `\d`, letters to `\l`, punctuation kept), useful for timestamps or currency where raw-value overlap is small (p. 15).

For metric M and column C, apply M to each of K historical batches, getting mean mu and variance sigma^2. For a margin beta, build the rule "mu - beta <= M(C) <= mu + beta" (two-sided) or "M(C) <= mu + beta" (one-sided, distance-like metrics). Three bounds on the resulting FPR, using only sigma and beta:

- Any metric (Chebyshev): FPR <= (sigma/beta)^2.
- Distance-like metrics (EMD, JS/KL-div, KS-distance, Cohen's d, L1, L-infinity, cosine, chi-squared; Cantelli, one-sided): FPR <= sigma^2/(beta^2+sigma^2).
- Sum-like metrics (count, mean, str_len, char_len, digit_len, punc_len, complete_ratio; CLT, two-sided): FPR is the normal tail past beta/sigma standard deviations.

Sweeping beta from sigma to n*sigma builds a family of candidate rules per metric, each with a known FPR bound (p. 15). Each metric's history is first checked for stationarity (ADF test); if not stationary, differencing (optionally with a log transform) is applied until stationary or the metric is dropped (p. 5, p. 16).

## Choosing the rule set: greedy budgeted coverage

AVH runs a greedy loop (p. 7): start with empty S, FPR used = 0; repeat, pick the unused rule with the best ratio of (new synthetic errors caught, not already covered by S) over (its own FPR bound); if adding it keeps the total under delta, add it; stop when nothing fits. Finally compare S against the single best individual rule, keep the higher-recall one. This is budgeted maximum coverage, proven NP-hard; the greedy algorithm reaches at least (1/2 - 1/2e), about 42%, of optimal recall for the same budget; a better (1 - 1/e) approximation exists but costs O(|Q|^3), too slow since |Q| is in the hundreds (p. 8, p. 17-18). Reimplementable in Python: compute each metric per historical version, fit mu/sigma, sweep beta with the formulas above, score each rule's recall against synthetic "bad" versions, run the greedy loop.

## Rules of thumb

| Quantity | Value | Condition | Page |
|---|---|---|---|
| Target FPR delta | 0.01% to 0.1% | example default | p. 1, p. 4 |
| FPR bound, any metric | (sigma/beta)^2 | Chebyshev | p. 4 |
| FPR bound, distance-like metrics | sigma^2/(beta^2+sigma^2) | Cantelli, one-sided | p. 5 |
| FPR bound, sum-like metrics | normal tail past beta/sigma std devs | CLT | p. 5, p. 16 |
| Greedy approximation ratio | ~0.42 (1/2 - 1/2e) of optimal recall | Proposition 4 | p. 8 |
| Unused better ratio | (1 - 1/e), costs O(\|Q\|^3) | not used | p. 17-18 |
| History in main experiments | 60 runs, 30-run sliding windows | Real/Synthetic benchmarks | p. 7 |
| Best history length | 28 days best; 14, 7 days competitive | sensitivity study | p. 17 |
| Synthetic error catalogue | 10 issue types, 60 procedures | recall estimation | p. 6 |
| Median/mean clauses per column | numeric 3/2.62; categorical 2/2.15 | Real benchmark | p. 17 |
| Latency | ~1.6 s average | 100K rows | p. 9 |
| Evaluation scale | 2000 pipelines, 1000+1000 columns, 60K+40K tests | Real benchmark | p. 7 |

## Vocabulary

- **Single-distribution DQ constraint**: a rule bounding one metric of one column.
- **Two-distribution DQ constraint**: a rule bounding a distance metric between a new batch and a baseline.
- **Conjunctive DQ program**: a set of constraints that all must hold (AND).
- **FPR**: chance a rule fires on data with no real issue.
- **Recall**: fraction of problems a rule/program catches.
- **Stationary process**: one whose mean and variance do not change over time.
- **Time-series differencing**: subtracting values a fixed steps apart to remove a trend or cycle.
- **ADF test**: statistical test for whether a series is stationary.
- **Chebyshev's / Cantelli's inequality**: distribution-free bounds on deviation from the mean, the second one-sided.
- **Budgeted maximum coverage**: choosing sets to maximize covered elements under a cost budget.
- **Pattern string**: a value with digits/letters/punctuation replaced by wildcards.

## Examples worth remembering

- **The 50-states row count.** A pipeline always outputting 50 rows has row_count = 50 as an invariant; a rule pinning it exactly catches most injected errors (p. 3, p. 7).
- **complete_ratio with two betas.** mu = 0.9, sigma^2 = 0.0001. beta = 0.05 gives [0.85, 0.95], FPR <= 0.04; beta = 0.1 gives [0.8, 1], FPR <= 0.01: wider tolerance is safer but less sensitive (p. 5).
- **Growing row counts need differencing.** Daily row_count grows from 100K to over 150K; differencing turns it into a roughly stable series before fitting (p. 5-6).
- **The age-in-days-to-hours bug.** A real Google incident where a field's unit silently changed from days to hours, multiplying values 24-30x (p. 1).
- **The unique_ratio Deequ example.** "review_id must be unique" is exactly unique_ratio bounded in [1, 1] (p. 3).
- **Ablation on clause count.** Restricting to 1 or 2 clauses hurts recall; 3 clauses already captures nearly the full benefit (p. 17-18).

## Quotes

- "we aim for very low False-Positive-Rate or FPR (e.g., 0.01%), which is also configurable if users so choose." (p. 1)
- "it is critical to ensure high precision, in AVH we explicitly aim for a very low level of FPR, which we denote by delta, e.g., delta = 0.1%." (p. 4)
- "These K previous batches of data are assumed to be free of DQ issues... engineers usually manually check the first few pipeline runs." (p. 4)
- "A DQ with a larger beta allows a larger range of M(C) values, which is less sensitive/effective... but is also 'safer' with lower expected FPR." (p. 5)
- "the real FPR is consistently lower than the target-FPR, likely due to the conservative nature of the statistical guarantees we leverage." (p. 17)

## Applying it to RESSLab-Hub

- Our per-column stats cache should store mean and variance (or a median-based equivalent), and reuse the Chebyshev formula FPR <= (sigma/beta)^2 to pick a warning band beta instead of guessing a percentile. Paper's formula (p. 4), transferred: our "history" is the current accepted rows, or a peer group (steel family, section family), not past pipeline runs.
- row_count, complete_ratio and unique_ratio checks (p. 3) are cheap to add to the existing min/max warning.
- Clearest transfer: give every threshold a provable, not guessed, FPR. Derive beta from a target delta with the Chebyshev or CLT formula, and show that bound in the warning, wwPDB-report style (p. 4-5, our transfer).
- Two-distribution metrics (L1, KS-distance) do not fit us: they compare batches, but our contributions add a few rows to a stable table. Skip that half (our judgment).
- The greedy budgeted-coverage selection (p. 7-8) is overkill for a few hundred rows and a handful of metrics per column: a curator can pick 2-3 checks per column by hand in `<table>_rules.yaml`, matching the paper's own finding that 2-3 clauses get most of the benefit (p. 17). Borrow the FPR formulas, skip the optimization.
- Synthetic error injection (10 issue types, 60 variants, p. 6) is worth borrowing for the rule-discovery spike: inject nulls, unit-scale changes (our unit-factor detector, 25.4/6.895/1000, is this paper's "change of units" type, p. 1) and swapped values, then check which rules catch them.
- The stationarity/differencing machinery (p. 5) does not apply: our columns are static measurements, not time series. Skip it.
- Do not copy the paper's exact delta (0.01%-0.1%): that fits thousands of pipelines where a tiny FPR means many daily alarms. We have one small database, so a looser delta, reported with each warning, fits better (our judgment).

## Limits and caveats

The paper targets thousands of recurring pipelines with many historical runs and hundreds of columns; RESSLab-Hub has a handful of tables, 30-80 columns each, no batch recurrence. Its optimization step, two-distribution metrics, and stationarity handling do not apply here. I did not read Appendix B (DQ-issue parameters) or Appendix L (manual inspection) beyond the main-text summary, and skipped the reference list. The source is a text-only PDF conversion with garbled subscripts and Greek letters; every formula above is described in words to avoid guessing a symbol. Figures 2, 3, 5-10 are described only qualitatively, since the conversion has no readable chart data.
