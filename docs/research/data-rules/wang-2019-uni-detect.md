# Uni-Detect: a unified approach to automated error detection in tables

Pei Wang and Yeye He, 2019, SIGMOD. Algorithm paper with a system-style evaluation.

## In one paragraph

Existing error detectors (outlier scores, FD checks, uniqueness checks, spell checkers) each need an expert to tune thresholds per data set, and produce many false positives when run automatically on real tables. UniDetect fixes this with one idea used for all error types: remove a small suspect subset from a column, and ask whether the column becomes much more "normal" after removal, compared to a huge corpus of real web tables (over 100M). "Normal" is measured with a metric function (MAD score for outliers, minimum pairwise edit distance for spelling, uniqueness ratio for duplicates, FD-compliance ratio for functional dependencies), and "much more normal" is a likelihood ratio counting, in the corpus, how many columns look like the column before removal versus after. The same suspect value can look equally "outlying" by a raw score in two columns, but the likelihood ratio tells them apart because it checks how rare that whole before/after pattern is across real tables. Tested on Wikipedia, web and enterprise spreadsheet tables, UniDetect beats existing single-purpose methods on precision for all four error types: 0.92 to 1.0 for numeric outliers, over 0.8 for spelling (over 0.9 with a dictionary check).

## Core principles

1. **An error is a value whose removal makes the column look far more normal.** UniDetect removes a small suspect subset O and compares how "normal" the column is before and after (p. 5-6).
2. **"Normal" is decided against a huge corpus of real tables, not a fixed assumption.** Over 100M web tables (T) act as ground truth for what clean columns look like (p. 4, p. 11).
3. **The test is a likelihood-ratio (LR) test between two hypotheses.** H0: the column is normal. H1: it is normal only after removing O. Reject H0 when LR = P(D\|T) / P(D_after\|T) is below a significance level alpha (p. 5-6).
4. **A raw outlier score alone cannot separate true errors from false positives.** Two columns can share the identical worst MAD score, yet removing the worst value collapses the score a lot in one (rare, true error) and barely in the other (common, false positive) (p. 10, Example 5).
5. **Featurization (subsetting the corpus) matters more than raw corpus size.** Comparing a column only to corpus columns of similar type, row count and traits gives sharper estimates than the whole corpus (p. 7-8).
6. **Each error type is a different instantiation of the same framework.** Numeric outliers use max-MAD, spelling uses minimum pairwise edit distance, uniqueness uses the uniqueness ratio, FD uses an FD-compliance ratio; the LR machinery is identical (p. 8-12).
7. **Existing "almost holds" heuristics for uniqueness and FD are unreliable on real tables.** About half of real columns over 99% unique are not real violations, since duplicates happen by chance in large lists of common names or dates (p. 2).
8. **Smoothing point estimates into range estimates avoids noisy corpus statistics.** Instead of "exactly theta1 before, exactly theta2 after", the paper asks "max-MAD >= theta1 before, <= theta2 after" (p. 10).
9. **The smoothed ratio is monotonic: a bigger gap always gives a smaller, more surprising ratio** (p. 10-11, Theorem 1).
10. **Automation and precision matter more than recall for a non-expert software feature.** Framed as an "APR" trade-off like the CAP theorem: pick automation plus precision (p. 2).
11. **The method fits simple, learnable error structures, not expert-defined constraints.** The authors doubt it extends to conditional FDs or denial constraints (p. 4, p. 9).

## The numeric-outlier metric (worked example)

This is the part closest to what RESSLab-Hub needs.

**Step 1, dispersion.** For a numeric column C: `MAD(C) = median(|v - median(C)| for v in C)` (p. 9, Eq. 7). MAD is preferred over SD, since it is less thrown off by the outlier itself.

**Step 2, per-value score.** `score_MAD(v, C) = |v - median(C)| / MAD(C)` (p. 10, Eq. 9), the same idea as a z-score but built from median and MAD.

**Step 3, column metric.** `max-MAD(C) = max over v in C of score_MAD(v, C)`, the score of the single most outlying value (p. 10, Eq. 10). This is the metric function m.

**Step 4, perturbation.** The suspect O is the one value with the highest score_MAD; D_after is the column with that value removed (p. 10).

**Step 5, featurization.** Restrict the corpus first to similar columns: data type, row-count bucket (see table below), and whether a log transform fits better (p. 10).

**Step 6, the ratio.** Let theta1 = max-MAD(C) before removal, theta2 = max-MAD(C_after) after. In the matching corpus subset: numerator = corpus columns with max-MAD >= theta1 before their own worst-value removal AND <= theta2 after; denominator = corpus columns with max-MAD after removal >= theta2. Numerator/denominator is LR (p. 10, Eq. 12, the smoothed range version of Eq. 11). A small LR means it is rare, in real tables, for a worst-value score to start at theta1 or higher and collapse to theta2 or lower: evidence for a genuine outlier.

**Why this beats raw MAD score.** Two columns in the paper's comparison had identical max-MAD of 8.1 for their worst value, so "flag if MAD-score > k" cannot tell them apart. One dropped only to 7.4 after removal (false positive), the other to 3.5 (a mistyped "8.716", true error). The corpus ratio rewards the bigger, rarer drop with a smaller LR (p. 10-11, Example 5).

## Rules of thumb

| Quantity | Value | Condition | Page |
|---|---|---|---|
| Spreadsheet error rate | 24% of professionally produced spreadsheets have errors | study cited | p. 1 |
| Cell-level error rate | 1% to 5% of data cells | across studies cited | p. 1 |
| Uniqueness heuristic false-positive rate | about half of >99%-unique real columns are not true violations | "almost unique" heuristic | p. 2 |
| Perturbation size epsilon | 1 row, or 1% of rows | parameter, set per use case | p. 6 |
| Row-count buckets (featurization) | (0-20], (20-50], (50-100], (100-500], (500-1000], (1000-infinity) | outliers, spelling, uniqueness, FD | p. 10-12 |
| UniDetect precision, numeric outliers | 0.92 (WEB), 0.95 (Wikipedia), 1.0 (Enterprise) | Precision@K, top-100 judged | p. 13-14 |
| UniDetect precision, spelling | over 0.8, over 0.9 with dictionary filter | Precision@K | p. 13-14 |
| UniDetect precision, FD | better than baselines but "not very high" | Precision@K | p. 15 |

## Vocabulary

- **UniDetect**: the proposed framework, one likelihood-ratio test reused for every error type.
- **Corpus T**: the background set of real tables (over 100M) used as reference for "normal" data.
- **Epsilon-perturbation**: removing a small subset O of up to epsilon rows from D to get D_after.
- **Likelihood-ratio (LR) test**: compares P(H0\|evidence) to P(H1\|evidence); reject H0 below significance level alpha.
- **Metric function m**: turns a column into one number for comparison to corpus columns (max-MAD, MPD, UR, FR).
- **Featurization F**: restricting the corpus to columns "like" the tested one before computing statistics.
- **MAD**: median absolute deviation from the column's median; a spread measure that outliers barely move.
- **max-MAD(C)**: highest per-value MAD-score in C; metric for numeric-outlier detection.
- **MPD**: minimum pairwise edit distance in a column; metric for spelling-error detection.
- **UR**: distinct values divided by total values; metric for uniqueness-violation detection.
- **FR**: for a candidate FD, the fraction of value pairs consistent with it; metric for FD-violation detection.
- **Precision@K**: fraction of the top K ranked predictions that are true errors.
- **APR**: automation, precision, recall; pick automation plus precision over recall.

## Examples worth remembering

- **The "8.716" outlier (p. 4, p. 10-11).** A column of counts like "8,011", "9,954" has one value "8.716" where a comma was mistyped as a period. Its raw MAD-score (8.1) matches a false-positive case (a legitimate large vote count). Removing "8.716" collapses max-MAD to 3.5 (rare, true error); removing the vote count only drops it to 7.4 (common, false positive).
- **Two false-positive uniqueness cases (p. 2-3).** A Titanic-passenger table is 99%+ unique with two people sharing a name by chance; a book table has two books sharing a publication date. Both trigger the "almost unique" heuristic but are not errors.
- **"Kevin Doeling" vs "Kevin Dowling" (p. 6-7).** A true spelling error, MPD = 1. Removing one of the pair jumps MPD to 9, a rare jump, unlike columns of chemical formulas or ordinal names where many pairs sit at distance 1 already.
- **Spellers fail on table data (p. 3, p. 13).** A commercial spell-checker "corrects" the real company "GAIL" to "GMAIL" and the town "Tulia" to "Trulia", trained on search logs, not table values.

## Quotes

- "We propose UniDetect, a unified framework to automatically detect diverse types of errors." (p. 1)
- "It is estimated that between 1% to 5% of data cells have errors." (p. 1)
- "[A]round half of real tables from Wikipedia and Web that are over 99% unique are in fact not violations of uniqueness constraints." (p. 2)
- "[N]ote that both the max-MAD(C+) and max-MAD(C-) have the same score of 8.1, which make them indistinguishable for MAD-based methods." (p. 10)
- "UniDetect achieves precision at 0.92, 0.95 and 1, for WEBT, WIKIT and EnterpriseT, respectively, outperforming alternative methods specifically designed for numeric-outliers." (p. 14)

## Applying it to RESSLab-Hub

- **Do not replicate the corpus-based likelihood-ratio test as-is (our transfer).** It needs 100M+ tables to estimate P(D\|T); RESSLab-Hub has one small domain database, no comparable outside corpus exists. Scale mismatch: transfer the idea, not the mechanics.
- **Borrow the perturbation-test idea for the group-range layer, proposal item 2 (our transfer).** Per peer group (steel family, section family), compute MAD on the group's own values, remove the most extreme value, and check how much the spread shrinks; a value whose removal collapses dispersion a lot is a stronger warning than one whose removal barely changes it (reuses Example 5, p. 10-11, peer group instead of a corpus). `numpy`/`scipy.stats` cover median and MAD.
- **Use max-MAD's per-value formula directly as the numeric-outlier warning metric (paper's formula, our reuse).** `score_MAD(v, C) = |v - median(C)| / MAD(C)` (p. 10, Eq. 9) fits a `<table>_rules.yaml` warning entry evaluated with simpleeval, computed per peer group.
- **Do not adopt the FD or spelling detectors (our judgment, backed by the paper).** RESSLab-Hub's cross-column relationships are known physics identities (h_over_t_cw = h_c / t_cw, p_yn = a_cn * f_yn, f_u > f_y, E = 200 GPa always), not discovered approximate FDs. The paper's own FD results are its weakest (p. 15); hand-written check expressions (proposal item 1) fit better, matching its own limit that complex constraints need human semantics (p. 4, p. 9).
- **Reuse the range-instead-of-point-estimate pattern for percentile messages (our transfer of p. 10, Eq. 11-12).** Phrase wwPDB-style messages as "value falls outside the range seen for X% to Y% of this peer group", not a single point comparison.
- **The APR framing backs the severity design (paper's claim, p. 2).** First-iteration warnings should stay high-precision, low-recall, matching an LLM that drafts but never decides.
- **Nothing here covers unit-factor detection** (value/median near 25.4, 6.895, 1000).

## Limits and caveats

- The paper needs a large corpus; it gives no guidance for a small, single-domain setting, so the corpus-comparison machinery (Sections 2.2-2.2.3) does not transfer, only the perturbation-and-compare idea does.
- Formulas in the converted text are garbled (subscripts collapsed, equation numbers duplicated); every formula above was cross-checked against the surrounding prose.
- Appendices A, B, C and E (related work, commercial-tool survey, PMI-to-LR proof, monotonicity proof) were read but not summarized here, since they do not bear on rule design for RESSLab-Hub.
- Appendix D gives no exact FD precision number, only "not very high".
- The paper is from 2019 and targets spreadsheet/web-table error detection; it says nothing about engineering unit checks or domain-specific tolerances, RESSLab-Hub's actual needs.
