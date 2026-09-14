# Conformalized quantile regression

Romano, Patterson, Candès, 2019, NeurIPS (preprint, "Work in progress", p. 1). Kind of paper: algorithm, with a coverage proof and experiments.

## In one paragraph

The paper wants prediction intervals that are valid (contain the true value often enough, in finite samples, no distribution assumed) and short (adapted to how uncertain each point is). Split conformal prediction gives validity, but a fixed width for every point, wasteful where data is easy, too narrow where hard. Quantile regression gives adaptive width but no finite-sample guarantee. Conformalized quantile regression (CQR) combines both: fit a lower and an upper quantile regressor on part of the data, then use a held-out calibration set to compute one correction number, and shift the fitted interval by it. It keeps the exact coverage guarantee of conformal prediction, whatever the quantile regressor is, while being shorter than plain conformal prediction and its locally adaptive variant, across 11 benchmark datasets (p. 1, p. 9).

## Core principles

1. **Coverage is a promise about all future draws, not one model.** Target: P{Y in C(X)} ≥ 1 − α, a marginal probability over a fresh exchangeable draw, for any distribution, any sample size (p. 2, eq. 1).
2. **Exchangeability is the only assumption.** The proof needs the calibration points plus the new point to be exchangeable; i.i.d. draws satisfy this, but no normality or linearity is required (p. 2, p. 5).
3. **Split the data once, each part does one job.** A proper training set fits the model; a separate calibration set only measures error and computes the correction (p. 2-3).
4. **Quantile regression alone is adaptive but not valid.** Fitting the alpha/2 and 1 − alpha/2 quantiles directly reacts to local variability but has no finite-sample guarantee; neural-net quantile intervals were found to substantially undercover (p. 3).
5. **Plain conformal prediction is valid but not adaptive.** Its interval width is one fixed number everywhere in the input space (p. 4).
6. **The conformity score is signed, not just absolute.** It is the larger of "how far below the lower quantile" and "how far above the upper quantile"; a point inside the interval gets a negative score, so the correction can also tighten intervals (p. 4-5).
7. **One correction number fixes the whole interval, and no regressor needs to be good.** An inflated empirical quantile of the calibration scores is added to the upper quantile prediction and subtracted from the lower one; the guarantee holds "regardless of the choice or accuracy of the quantile regression estimator" (p. 2, p. 5).
8. **The upper coverage bound needs distinct scores.** Coverage is at least 1 − alpha always, at most 1 − alpha + 1/(calibration size + 1) when scores are distinct; ties break this near-tightness (p. 5).
9. **CQR beat plain and locally adaptive conformal prediction.** Across 11 datasets and 2,200 runs, CQR gave the shortest intervals at about target coverage (p. 9-10).
10. **Calibration set size sets the resolution, and a symmetric split of error is not the only option.** The correction is close to the (1 − alpha)-th smallest calibration score, so a small calibration set makes it coarse and the 1/(n+1) slack stops being negligible (p. 5); a two-sided version (Theorem 2) instead controls each tail separately, for a wider interval (p. 6, p. 10).

## The algorithm

Algorithm 1 in the paper (p. 6). Inputs: n rows of (X, Y), a miscoverage level alpha (0.1 for 90%), any quantile-fitting algorithm.

1. **Split.** Randomly split the n rows into a proper training set I1 and a calibration set I2 (equal sizes in the paper's experiments, p. 8).
2. **Fit two quantile regressors on I1 only.** q_lo targets the alpha/2 conditional quantile of Y, q_hi targets the 1 − alpha/2 quantile. Any quantile-capable method works: quantile regression forests, quantile neural nets, linear quantile regression (p. 6-7). This is a first-pass interval, adaptive but not yet guaranteed.
3. **Score the calibration set.** For each row i in I2: E_i = max(q_lo(X_i) − Y_i, Y_i − q_hi(X_i)). Below the lower prediction, E_i is how far below (a miss). Above the upper prediction, how far above (a miss). Inside, E_i is negative, the slack before it would have escaped (p. 4-5).
4. **Take one inflated quantile of the scores.** Sort the |I2| scores, take the ceil((1 − alpha) * (|I2| + 1))-th smallest; call it Q. Close to, not exactly, the plain (1 − alpha) empirical quantile; the "+1" is what makes the proof exact in finite samples (p. 4, appendix A).
5. **Build the corrected interval for a new point x.** C(x) = [q_lo(x) − Q, q_hi(x) + Q]. If calibration points mostly fell inside, Q can be negative and shrink the interval; if the regressors over- or undershot systematically, Q corrects for that (p. 5).

The proof (Theorem 1, p. 5) gives P{Y in C(X)} ≥ 1 − alpha for exchangeable data, whatever q_lo and q_hi are. An asymmetric variant (Theorem 2, p. 6) uses two separate calibration quantiles, one per tail, at the cost of a wider interval.

## Rules of thumb

| Quantity | Value | Condition | Page |
|---|---|---|---|
| Nominal miscoverage alpha | 0.1 (90% interval) | fixed, all experiments | p. 8 |
| Train / test, then proper-training / calibration split | 80% / 20%, then 50% / 50% | 20 random splits per dataset | p. 8 |
| Coverage upper bound slack | 1/(\|I2\|+1) added to 1 − alpha | only if scores are almost surely distinct | p. 5 |
| Avg. length: split / local / CQR (random forest) | 2.94 / 2.24 / 1.41 | 11 datasets, 20 splits | p. 10 |
| Avg. length: split / local / CQR (neural net) | 2.16 / 1.81 / 1.40 | same setting | p. 10 |
| Avg. coverage, all conformal methods | about 89.9% to 90.3% | target 90% | p. 10 |
| Coverage, quantile forest / neural net (no guarantee) | 92.62% / 88.51% | no calibration step | p. 10 |
| Asymmetric (two-tailed) correction | CQR neural net 1.40 to 1.58; CQR forest 1.41 to 1.57 | Theorem 2 variant | p. 10 |
| Experiments summarized in Table 1 | 2,200 | 11 datasets x 20 splits x 10 methods | p. 9-10 |

## Vocabulary

- **Exchangeability**: joint distribution unchanged under reordering; weaker than i.i.d. but satisfied by it (p. 2).
- **Conformal prediction**: methods that build intervals with finite-sample, distribution-free coverage by checking conformity against a calibration set (p. 2).
- **Split (inductive) conformal prediction**: splits data once, proper training set plus calibration set, rather than refitting many times (p. 3-4).
- **Pinball loss (check function)**: asymmetric loss used to fit a quantile regressor (p. 3).
- **Conditional quantile function q_alpha(x)**: value below which Y falls with probability alpha given X = x (p. 2).
- **Conformity score**: number on each calibration point measuring miss or slack; CQR's version is signed (p. 4-5).
- **Quantile crossing**: a fitted lower quantile ends up above the fitted upper quantile (p. 10).

## Examples worth remembering

- **Synthetic heteroscedastic example (Figure 2, p. 4-5; Appendix B, p. 19).** X uniform on [1, 5], Y a Poisson variable with mean depending on sin^2(X), plus small noise, plus a rare large outlier on 1% of points. Split conformal gives a fixed band (length 2.91) despite visibly changing spread; locally adaptive does slightly better (2.86); CQR tracks the true spread, average length 1.99, all near 90% coverage.
- **Facebook datasets overcoverage (p. 11).** CQR random forests came out overly conservative on two Facebook datasets, because ties among conformity scores break the tight upper coverage bound: the paper's own admission that tightness can fail in a real dataset.
- **Non-conformalized quantile regression looks shorter but is not trustworthy (p. 10).** Plain quantile random forests' reported interval is longer than CQR's, yet coverage drifts to 92.62% (too wide) or, for the neural net variant, 88.51% (too narrow), since neither has a guarantee.
- **Asymmetric two-tailed variant (Theorem 2, p. 6, p. 10).** A separate correction for "too low" and "too high" predictions, each with its own guarantee, widens CQR neural net length from 1.40 to 1.58.

## Quotes

- "Conformal prediction is a technique for constructing prediction intervals that attain valid coverage in finite samples, without making distributional assumptions." (p. 1)
- "A key strength of CQR is its rigorous control of the miscoverage rate, independent of the underlying regression algorithm." (p. 2)
- "The conformity score thus accounts for both undercoverage and overcoverage." (p. 5)
- "The length of C(Xn+1) is fixed ... independent of Xn+1." (p. 4)
- "The CQR random forests are overly conservative on the two Facebook datasets ... there are ties among the conformity scores and so the upper bound in Theorem 1 does not apply." (p. 11)

## Applying it to RESSLab-Hub

- **What it could give us**: a plausibility interval for one numeric column predicted from the others (predict f_u from geometry and steel grade), message-style: "measured X, plausible range at 90%: [lo, hi]", instead of a global min/max flag. Our transfer; principle 5 and the length numbers (p. 10) show CQR replaces a fixed band with something shorter and still valid.
- **Layer of the proposal**: an addition to layer (2), group ranges per peer group, not a replacement. CQR needs a train/calibration split and a fitted regressor, heavier than percentile ranges; worth it only if that layer proves too coarse.
- **Python package**: the paper uses `sklearn` for random forests (p. 9) and its own code at github.com/yromano/cqr; a quantile-capable forest fits our tabular data better than a neural net (our choice).
- **Be honest about calibration set size**: our tables run about 100 to a few thousand rows. With the paper's 80/20 then 50/50 splits, a 200-row peer group leaves about 80 calibration rows; the slack term (principle 8) is then about 1.2 points, tolerable. At 20-30 rows the slack grows to 3-5 points, and the correction is coarse (roughly the 2nd or 3rd worst residual standing in for the 90th percentile, principle 10). Below roughly 30-50 rows, say "wide interval, few comparable specimens" instead of a percentage (our transfer).
- **Keep the model small**: fit on few predictor columns (section family, one or two geometric ratios), not the full dictionary, to avoid overfitting a small I1 (inferred from the paper's preference for simple models, p. 9).
- **Keep the message honest**: the guarantee is marginal (principle 1), an average over calibration-like rows, not a promise for one specimen. Say "about 9 in 10 comparable specimens fall in this range", and flag a thin or one-lab peer group, which weakens exchangeability (principle 2).
- **LLM stays advisory**: it may draft the message, never compute the interval; bounds come from the algorithm run in Python.
- **Not for the first iteration**: the issue rules out ML-based multivariate detection at first; CQR should wait for the simpler layers to ship.

## Limits and caveats

- The paper's smallest calibration sets are still in the thousands of rows; it never tests the tens-to-low-hundreds our peer groups would produce. Every claim above about our scale is a transfer.
- The paper tunes hyperparameters by cross-validation on folds large enough to do so reliably; it does not discuss too little data to tune at all, our likely case for a small peer group.
- Sections 5-6 per-dataset figures (3-6, p. 14-17) were read for the comparison numbers, not figure by figure. The formal proofs (Appendix A, p. 18) were read but not reproduced step by step, only what they establish.
- Some inline formulas in the conversion run subscripts and indices together; affected steps are described in words, not garbled symbols.
- The paper is a 2019 preprint ("Work in progress", p. 1); a covariate-shift conformal method is referenced only as a 2019 arXiv entry [50], not read here, that may matter for a growing, unevenly sampled database like ours.
