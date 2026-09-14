# ECOD: Unsupervised outlier detection using empirical cumulative distribution functions

Li, Zhao, Hu, Botta, Ionescu, Chen, 2022, IEEE TKDE. Algorithm paper with a benchmark study.

## In one paragraph

ECOD finds outliers by treating them as rare events in the tails of a distribution. For each column of the data, it builds an empirical cumulative distribution function (ECDF) from the sample itself, no fitted parametric model. For each row and each column, it reads off the left-tail and right-tail probability from that column's ECDF, and picks which tail to use based on the sign of that column's skewness. It turns the chosen tail probability into a negative log probability, sums these across all columns (assuming columns are independent), and that sum is the outlier score: a high score means the point sits in a rare, extreme part of the data. The paper tests this on 30 benchmark datasets against 11 other detectors and finds ECOD wins on average accuracy while being one of the fastest methods and needing no hyperparameters.

## Core principles

1. **Outliers are rare events in the tails.** An outlier is a point whose value is unusually extreme compared to the rest of the sample, on at least one dimension (p. 1).
2. **Use the empirical CDF, not a fitted distribution.** ECOD estimates each column's CDF from the sample counts, no parameters to tune, unlike GMM or kernel density estimation (p. 2-3).
3. **Estimate each dimension on its own, then combine.** A joint ECDF over many columns converges slowly as columns grow, so ECOD computes one ECDF per column and assumes independence when combining (p. 3).
4. **Skewness picks the tail per dimension.** Negative skew uses the left tail as the sign of outlyingness, positive skew uses the right tail (p. 5).
5. **Scores are summed negative log probabilities.** A very small tail probability becomes a large score; the final score is the max of the left-only, right-only, and skewness-chosen sums (p. 5).
6. **The method is parameter-free.** No threshold, bandwidth, or neighbor count to tune (p. 2).
7. **The score is interpretable per dimension.** Since the total is a sum over columns, each column's own contribution shows which columns made a point look like an outlier (p. 6).
8. **Complexity is linear in rows times columns.** O(n·d) time and space, far better than distance- or density-based methods (p. 6).
9. **Independence across dimensions is a strong, explicit simplification**, made so the method stays parameter-free and fast (p. 2).
10. **Performance degrades when no single column is extreme.** If an outlier is unremarkable on every column alone, ECOD's per-column view cannot catch it (p. 9-10).
11. **The method does not handle multimodal columns.** It is not built for a column whose normal values form two clumps with an outlier value between them (p. 12).

## The algorithm, step by step

For a table of n rows and d columns:

1. For each column j, compute two empirical CDFs from the n values: left-tail ECDF at value z is the fraction of rows with value ≤ z; right-tail ECDF at z is the fraction of rows with value ≥ z.
2. For each column j, compute the sample skewness coefficient (mean cubed deviation from the mean, divided by the standard deviation cubed).
3. For each row and column, look up the left-tail and right-tail probability of that row's value in that column, from the ECDFs in step 1.
4. For each row, sum negative logs of tail probabilities across columns three ways: left-only, right-only, and auto (per column, left if skewness is negative, else right).
5. The row's final score is the max of the three sums; higher means more extreme.
6. To flag outliers, sort by score, or compare against a fixed cutoff such as -log(0.01) ≈ 4.61, or the top-alpha-percent of scores seen.

Directly implementable on a small table in plain Python or numpy: `scipy.stats.rankdata` gives each column's ECDF, `scipy.stats.skew` gives step 2. The paper's own implementation lives in PyOD as `pyod.models.ecod`.

## The dimensional outlier graph

Because the total score is a sum of one term per column, ECOD can show, for one flagged row, a bar per column of that column's own negative log tail probability, plus a reference line at a fixed percentile (the paper uses the 99th percentile of that column's scores) (p. 6). Columns whose bar crosses the line are the ones driving that row's outlier status. The worked example is Breast Cancer Wisconsin, 369 rows, 9 columns scored 1 to 10; for one malignant row, 3 of 9 columns cross the 99th-percentile line, which the authors read as the explanation for the flag (p. 6).

## Complexity and scalability

Building all d ECDFs from n rows costs O(n·d) time and space; computing and summing tail probabilities for all rows is also O(n·d) (p. 6). Each column is estimated independently, so work splits across worker threads or processes, one column (or group of columns) per worker, with no synchronization needed until the final sum (p. 6). Measured runtimes on one laptop: d=10, n=1,000 took 0.068 s and n=1,000,000 took 11.460 s; d=10,000, n=1,000 took 11.403 s and n=1,000,000 took 5376.593 s, under 1.5 hours (p. 10, Table 6).

## Rules of thumb

| Quantity | Value | Condition | Page |
|---|---|---|---|
| Time and space complexity | O(n·d) | n rows, d columns | p. 6 |
| Avg. ROC across 30 datasets | 0.825 | ECOD, best of 12 methods | p. 9 |
| Avg. average precision (AP) across 30 datasets | 0.565 | ECOD, best of 12 methods | p. 10 |
| ROC improvement over 2nd best (iForest) | +2% | average across 30 datasets | p. 9 |
| AP improvement over 2nd best (iForest) | +5% | average across 30 datasets | p. 9 |
| Rank 1st in ROC | 13 of 30 datasets | | p. 9 |
| Rank 1st in AP | 12 of 30 datasets | | p. 9 |
| Avg. runtime rank | 3rd fastest of 12, 0.228 s/dataset avg | HBOS and LODA faster | p. 10 |
| Suggested fixed cutoff for a column's own score | -log(0.01) ≈ 4.61 | one possible threshold | p. 6 |
| Percentile reference line in the example graph | 99th percentile | of that column's scores | p. 6 |
| ECOD variant ranking (auto best) | avg ROC 0.824 / 0.781 / 0.714 / 0.560 | auto, avg-of-tails, right-only, left-only | p. 8 |
| Skewness rule | negative skew → left tail; positive skew → right tail | tie broken arbitrarily | p. 5 |

## Vocabulary

- **ECDF**: fraction of sample values at or below (or above) a given value, a stand-in for the true, unknown distribution.
- **Tail probability**: the ECDF value itself, read as "how much of the sample is at least this extreme."
- **Skewness**: a measure of distribution asymmetry; negative means a longer left tail, positive a longer right tail.
- **Outlier score**: the paper's Oi, a nonnegative number, higher meaning more likely an outlier; not a probability, only meant to compare points.
- **Dimensional outlier score**: one column's own contribution (its negative log tail probability) to a row's total score.
- **Dimensional outlier graph**: a plot, per row, of the dimensional outlier score for every column plus a percentile reference line, used to explain a flag.
- **Curse of dimensionality**: density- and distance-based methods get slower and less accurate as columns grow.
- **Contamination rate**: the assumed fraction of outliers in a dataset, used to pick a cutoff on scores.

## Examples worth remembering

- **Breast Cancer Wisconsin walk-through**: 369 rows, 9 columns scored 1-10. For one malignant row, 3 of 9 columns cross the 99th-percentile line, giving a plain explanation for the flag (p. 6).
- **Synthetic 2-D illustration of tail choice**: inliers near one corner of a unit square, outliers spread uniformly over it. Left-tail-only catches them well (matches how data was built); right-tail-only catches almost none; averaging catches about half; skewness-corrected catches them cleanly (p. 4-5).
- **Datasets where ECOD wins**: Breastw and Shuttle, where outliers sit at the tail of at least one dimension (p. 8-9).
- **Datasets where ECOD loses**: Ionosphere and Speech, where outliers mix among normal points rather than sitting in any tail (p. 9-10).
- **HBOS comparison**: HBOS also fits one model per column (a histogram, not an ECDF), but scores lower on average (0.795 vs 0.825 ROC), attributed to lost within-bin information and needing a bin count choice (p. 9).

## Quotes

- "Outliers... are often the 'rare events' that appear in the tails of a distribution." (p. 1)
- "the skewness of the dataset plays a major role in whether left tail probabilities or right tail probabilities should be used." (p. 5)
- "ECOD has O(nd) time and space complexity." (p. 6)
- "it is unlikely that an outlier resembles normal points in all dimensions, and this explains why ECOD could consistently work for most of the datasets." (p. 9-10)
- "our approach is not designed to handle multimodal distributions for which an outlier could be in neither left nor right tails." (p. 12)

## Applying it to RESSLab-Hub

- **Layer 2 percentile messages match this paper's core idea.** "Percentile messages in the style of wwPDB" is, in plain terms, ECOD's per-column tail probability: how far into the tail a value sits, per peer group, per column. Our own transfer, the paper does not mention wwPDB or peer groups.
- **Do not adopt the full ECOD summed score.** Our tables fit ECOD's speed range (p. 3, p. 10), but the proposal rules out multivariate ML-style detection first, and a summed cross-column score is exactly that, harder to read than one flag with one reason. Keep the per-column percentile message, skip the sum.
- **Borrow the skewness-aware tail choice for the per-column warning.** When flagging an extreme value (layer 2, group ranges), check the sign of the column's skewness within its peer group and report the matching tail's percentile, instead of always a two-sided distance from the median. Follows principle 4 (p. 5); fits our skewed columns (loads, rotations, section dimensions rarely symmetric).
- **Reuse the ECDF idea directly, no library needed.** An empirical CDF per column (or peer group) is a one-line `numpy`/`pandas` rank operation. `pyod.models.ecod` exists (p. 2) for a heavier implementation, but the "no ML-based multivariate detection" rule argues against pulling in PyOD's full detector now.
- **Use the dimensional outlier graph idea for the curation UI, not the algorithm.** The explanation device (one bar per column plus a percentile line, p. 6) is a good template for curation.md: one line per column with its own percentile, not one opaque score. An interpretability transfer, not a statistical one.
- **Do not use independence to justify skipping cross-column rules.** ECOD ignores relationships between columns, a known weakness (p. 2, p. 12). Layer 1's rules (like f_u > f_y) are exactly what ECOD cannot see; keep layer 1 and layer 2 separate.
- **The paper's scale settles nothing here.** Benchmarks run 80 to 11,183 rows, up to 400 columns (p. 7); scalability tests reach a million rows. Our tables sit comfortably inside that range.

## Limits and caveats

Stated limits: ECOD assumes independence between columns (p. 2, p. 12); it is not built for columns with two-clump (multimodal) normal ranges (p. 12); accuracy drops when an outlier is not extreme on any single column but only in combination (p. 9-10). The paper leaves modeling column relationships (copulas, graphical models) to future work, expecting that to need tuning, unlike the base method (p. 12). I did not read the full per-dataset runtime table (Table 7, p. 10-11) in detail, baseline numbers not needed here, and skipped the author biography (p. 12-13). Nothing read was unreadable; equations were garbled by the conversion but the surrounding prose stated each formula in words closely enough to describe here without guessing.
