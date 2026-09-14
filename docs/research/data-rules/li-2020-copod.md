# COPOD: copula-based outlier detection

Li, Zhao, Botta, Ionescu, Hu, 2020, arXiv preprint. Algorithm paper, with a benchmark study across 30 public datasets.

## In one paragraph

COPOD detects outliers with no parameters to tune. It builds an ECDF per column, then combines these into an empirical copula, describing the joint shape of the data from per-column ranks alone. For each row, it estimates the probability of something at least as extreme from the left tail, the right tail, and a skewness-corrected mix, turns each into a negative log score, and takes the max as the row's outlier score. Because the score is built column by column, COPOD can also show which columns drove it (the Dimensional Outlier Graph). On 30 benchmark datasets, the skewness-corrected variant beats 9 other detectors on ROC-AUC and precision, and scales to 10,000 columns and 1,000,000 rows (p. 1, p. 5).

## Core principles

1. **A copula separates marginals from dependency.** A copula is the CDF of a vector whose marginals are all Uniform(0,1). Any joint distribution can be written as a copula applied to the marginal CDFs, so each column can be modeled alone (p. 1-2).
2. **The empirical copula needs no distribution assumption, and the right tail ECDF must be flipped.** COPOD estimates each column's ECDF rank-based, no fitted family; a plain ECDF gives a zero right tail probability at the largest value, so COPOD fits a second ECDF on the negated column (p. 2-3).
3. **An outlier is a tail event, and summing logs avoids underflow.** A point is a candidate outlier if the probability of something at least as extreme is small; multiplying per-column probabilities collapses toward zero as columns pile up, so COPOD sums negative logs, picking left or right tail per column by its skewness sign (p. 2-3).
4. **The final score is the max of three variants, and doubles as an explanation.** Left-tail, right-tail, skewness-corrected; the max works without knowing which tail holds outliers, and the per-column negative logs explain a flagged row (p. 4).
5. **The score is relative, parameter-free, and wins the benchmark.** Scores lie in (0, infinity), meaningful only compared across rows of the same table; no training or hyperparameter, best average ROC-AUC (0.8247) and precision (0.5649) of 10 detectors on 30 sets (p. 1, p. 4-6).

## The algorithm, step by step

Input: table X, n rows, d columns. Output: one outlier score per row.

Per column j: left tail ECDF F_j(x), fraction of rows at or below x (p. 2, eq. 5); right tail ECDF, same but on the negated column -X_j so the largest value does not zero out (p. 3); skewness, the usual third-moment estimator (p. 4).

Per row i, column j: U = F_j(x), V = right tail ECDF value, W = U if skewness negative else V. Sum negative logs across columns: pl = -sum(log U), pr = -sum(log V), ps = -sum(log W). Row score O(x_i) = max(pl, pr, ps).

Per-column explanation: Od(x_i) = max(log U_d, log V_d, log W_d) (no minus sign here in the source, unlike pl/pr/ps, p. 4). Threshold these (paper suggests -log(0.01) = 4.61, or top alpha percent) to say which columns explain a flagged row; plotted with percentile lines, this is the "Dimensional Outlier Graph" (p. 4). Reimplement in plain Python: rank-based ECDF, `scipy.stats.skew` (ddof=1), then log-sum-max. Ships as `pyod.models.copod`.

## Rules of thumb

| Quantity | Value | Condition | Page |
|---|---|---|---|
| Average ROC-AUC / AP, skewness corrected | 0.8247 / 0.5649 | best of 10 detectors, +1.5 / +2.7 pts over 2nd best | p. 5, p. 1 |
| Average runtime | 0.227 s | 3rd fastest of 10, behind HBOS 0.046s, LODA 0.062s | p. 5-6 |
| Runtime, d=10,000, n=1,000,000 | 5376.59 s | synthetic data, laptop CPU | p. 6 |
| ROC-AUC / AP, ablation | 0.51-0.78 / 0.25-0.48 | worst to best non-skewness variant | p. 5 |
| Suggested per-column threshold | -log(0.01) = 4.61 | or top alpha percent | p. 4 |
| Benchmark setup | 30 datasets, 9 competitors, 60/40 split | 10 trials averaged | p. 5 |

## Vocabulary

- **Copula**: function in [0,1] that is the CDF of a vector with Uniform(0,1) marginals; describes dependency apart from each variable's own distribution.
- **Empirical copula**: copula built from per-column empirical CDFs, not a fitted one.
- **Left/right tail probability**: P(X<=x) or P(X>=x); small means unusually low or high.
- **Skewness correction**: per-column choice of left or right tail ECDF, by sign of skewness.
- **Dimensional Outlier Graph**: plot of the per-column score for a row, with percentile lines.

## Examples worth remembering

- **Synthetic 2D toy set (Figure 1)**: outliers built on the low end of both dimensions. Left-tail-only COPOD catches them; right-tail-only wrongly flags the largest normal points; skewness-corrected gets it right since both dimensions are negatively skewed. Flipping which end the outliers sit on reverses which single tail works, but skewness correction adapts (p. 3-4).
- **BreastW, row 70**: 369 samples, 9 features scored 1-10. Dimensions 2, 5 and 9 (cell size uniformity, epithelial cell size, mitoses) cross the 99th percentile line while the rest stay below it, the worked example of per-column explanation (p. 4-5).
- **High-dimension scaling**: d=10,000, n=1,000,000 runs in about 5,377 seconds on a laptop (p. 6).

## Quotes

- "COPOD is deterministic without hyperparameters." (p. 1)
- "We say that an outlier has a small tail probability if either of the two quantities are small." (p. 2)
- "In order to avoid diminishing tail probabilities ... we instead work with the sum of the negative log probabilities." (p. 3)
- "The bigger O(Xi) is, the more likely Xi is an outlier." (p. 4)

## Applying it to RESSLab-Hub

- Iteration one excludes ML-based multivariate detection, but COPOD's per-column ECDF-plus-tail-probability works standalone. Transfer: compute F_j(x) per numeric column (f_y, f_u, slenderness) as a "fraction of the database at or below this value", sharper than today's min/max warning (p. 2-3). Skewness-corrected tail choice (principle 3) fits per-peer-group ranges: picking a tail per peer group (steel family, section family) tells a warning which side to quote a percentile against.
- The per-column score (principle 4) maps onto "issues get code, severity, suggestion, why": per-column negative-log tail probability ranks which columns pushed a row over the line, no ML needed. Do not adopt the combined row-level max score yet, it needs a contamination-rate threshold excluded now (p. 4).
- "No hyperparameters, no training" (principle 5) is a design rule to keep, in the spirit of simpleeval. PyOD is a candidate only for a later, full multivariate iteration; plain numpy/scipy covers what we need now (p. 5). The paper's scale (up to 1,000,000 rows, p. 6) dwarfs RESSLab's; percentile messages should state sample size, since a 100-row peer group gives a coarse ECDF.

## Limits and caveats

- No guidance on setting a threshold beyond one example number (p. 4); no small-sample discussion. Benchmark datasets (p. 5-6) are generic, not structural.
- Od may be missing a minus sign in the source; quoted as printed. Numeric columns only; RESSLab's categorical ones (steel grade, section, boundary condition, loading protocol) are out of scope.
