# Conformance constraint discovery: measuring trust in data-driven systems

Anna Fariha, Ashish Tiwari, Arjun Radhakrishna, Sumit Gulwani, Alexandra Meliou. Technical report (arXiv), January 2021. Kind: algorithm paper with an open-source system (CCSynth) plus a companion explanation tool (ExTuNe).

## In one paragraph

The paper defines "conformance constraints": arithmetic bounds on linear combinations of a dataset's numeric columns (called projections), learned so almost all training rows satisfy them. The key finding is that the best projections are the ones with the lowest variance, found by running PCA and keeping the low-variance components instead of discarding them as usual. For each low-variance projection, bounds are set at mean ± C standard deviations (C = 4), and a new row's violation is scored with a smooth 0-to-1 function of how many standard deviations it falls outside. Scores from several projections are combined with weights favoring lower variance. Categorical columns are handled by partitioning the data and learning separate constraints per partition (disjunctive constraints). The method is linear in row count, cubic in column count, needs no user-set thresholds, and tracks machine-learning failure and data drift better than prior PCA-based and change-detection baselines, on datasets from thousands to millions of rows.

## Core principles

1. **Low-variance projections make strong constraints.** A projection that stays almost constant across the data gives a narrow, informative bound; a high-variance one gives a bound too wide to ever flag anything (p. 2, p. 5).
2. **This is the opposite of normal PCA use.** Standard dimensionality reduction keeps high-variance components and drops low-variance ones; this method keeps the low-variance ones on purpose, since they generalize into tight bounds (p. 2, p. 7).
3. **Good projections must also be mutually uncorrelated.** Two correlated projections can always be combined into one with lower variance and a stronger constraint (Lemma 11), so PCA's orthogonal components give a non-redundant set in one shot (p. 6-7).
4. **Bounds come from mean and standard deviation, not min/max.** Raw min/max is fragile to a single outlier; mean ± C·std (C = 4) is stable and still covers nearly all data under wide distributional assumptions (p. 5).
5. **Violation is a graded score, not a yes/no.** A smooth score in [0, 1) grows with how far past the bound a value falls, since real data is noisy and a hard pass/fail throws that signal away (p. 5).
6. **Categorical columns split the data into partitions, each with its own bound (disjunctive constraints).** When one global linear trend does not fit well, partitioning by a categorical column and fitting per partition beats a forced global fit (p. 6, p. 16).
7. **No constraint minimization or user tuning is required.** No noise threshold, distance metric or hyper-parameter search is needed from the user, unlike functional-dependency or denial-constraint approaches (p. 3, p. 20).
8. **Violation is a proxy for whether a model's prediction can be trusted, even without knowing the model.** A learned model may implicitly rely on a coincidental training-data relationship; a serving row that breaks it is likely to get a bad prediction, checkable from the row alone (p. 1-2, p. 9-10).
9. **The method is fast: linear in rows, cubic in columns.** One pass builds a small m x m matrix (m = number of columns), then one eigendecomposition of it; seconds even on 6 million rows (p. 7, p. 10).
10. **Violations can be explained per column with a responsibility score (ExTuNe).** For a non-conforming row, reset one column to its training mean and count how many more columns must be reset before it conforms; fewer extra fixes means more of the "blame" (p. 18).

## The algorithm (projections, bounds, weights, violation score)

**Setup.** From dataset D, drop non-numeric columns to get matrix D_N (n rows, m columns), and prepend a column of 1s: D' = [ones | D_N]. This lets the method capture an additive-constant term inside each projection and works whether or not the data was pre-centered.

**1. Find projections (Algorithm 1).** Compute the (m+1) x (m+1) matrix D'^T D' and its eigenvectors (numpy: `M = Dp.T @ Dp; vals, vecs = np.linalg.eigh(M)`, symmetric matrix so `eigh` is right and returns eigenvalues ascending). For each eigenvector, drop its first coordinate (the constant-column weight) and normalize the rest to unit length: this gives K projection weight vectors w_1..w_K over the m numeric columns, so F_k(row) = w_k . row. Order by ascending std of F_k(D); the paper proves (Theorem 13) this set contains the global minimum-variance projection and that any two projections in it are uncorrelated over D, so all K are usable, not just a few.

**2. Bounds per projection.** mu_k = mean(F_k(D)), sigma_k = std(F_k(D)); lb_k = mu_k - C·sigma_k, ub_k = mu_k + C·sigma_k, with C = 4 in the paper's experiments (for a normal distribution this covers 99.99% of mass; the method itself assumes no particular distribution). When sigma_k = 0 the paper sets the scaling factor to "a large positive number" rather than dividing by zero; in practice floor sigma_k at a small epsilon.

**3. Importance weight per projection.** gamma_k = 1 / log(2 + sigma_k) (unnormalized), then weight_k = gamma_k / sum(gamma). Lower sigma gets higher weight, so stronger projections count more when combined.

**4. Violation score for one bounded constraint.** `excess = max(0, F(t) - ub, lb - F(t))`; `score = 1 - exp(-excess / sigma_k)` (this is eta(alpha·excess) with alpha = 1/sigma_k and eta(z) = 1 - e^-z). Zero inside the band, approaching 1 further outside, scaled in units of standard deviation (p. 5).

**5. Combine.** `score(t) = sum_k weight_k * score_k(t)`, a weighted sum over the K projections (p. 4-5). On a ~150-row, ~50-column table this whole fit (build `Dp`, eigendecompose `Dp.T @ Dp`, derive the per-projection tuples, score rows) is trivial in numpy, well under a second.

**Disjunctive (categorical-partition) constraints.** For a categorical column with at most 50 distinct values (the paper's implementation cutoff, p. 6), split D by value into sub-datasets, run steps 1-5 separately on each to get a per-value constraint, and combine as "if column = v, use that value's constraint." Repeat per eligible categorical column, and conjoin the per-column disjunctions for the dataset's full compound constraint (p. 6).

## Rules of thumb

| Quantity | Value | Condition | Page |
|---|---|---|---|
| Bound width constant C | 4 (mean ± 4 sigma) | default in experiments, not theory-required | p. 5 |
| eta(z) normalization | 1 - e^-z | maps [0, inf) excess to [0, 1) score | p. 5 |
| Importance weight (unnormalized) | 1 / log(2 + sigma_k) | lower sigma gets higher weight, user-replaceable | p. 7, p. 15 |
| Max distinct values for categorical partitioning | 50 | implementation choice, not a theoretical limit | p. 6 |
| Runtime | O(n·m^2) build + O(m^3) eigendecomposition | linear in rows n, cubic in columns m | p. 7 |
| Memory | O(m^2) | incremental sum of row outer products | p. 7 |
| Correlation threshold for "combinable" projections | \|rho\| >= 1/2 | theoretical device (Lemma 11), not a tuning knob | p. 6-7 |
| Measured runtime | "a few seconds" | ~6M rows, ~40 attributes | p. 10 |
| Constraints applicable to one tuple | at most m_N · m_C, bounded by m^2/4 | m_N numeric, m_C categorical attrs | p. 6 |
| Violation-vs-accuracy correlation, HAR mixing experiment | pcc = 0.99, p = 0 | clean data | p. 11 |
| Same correlation with training noise added | pcc = 0.82, p = 0.002 | noisy data, still significant | p. 11 |

## Vocabulary

- **Projection**: a function mapping a row to a real number; here always a linear combination of numeric attributes.
- **Conformance constraint**: a formula almost all rows of a dataset satisfy, used to flag deviating rows.
- **Simple constraint (phi)**: a bound lb <= F(row) <= ub on one projection.
- **Compound constraint (Psi)**: a conjunction of disjunctive constraints, each switching which simple constraint applies by a categorical value.
- **Quantitative semantics**: the [0, 1) violation score, as opposed to a strict true/false reading.
- **Incongruous tuple**: for a pair of correlated projections, a tuple whose deviation from the mean goes against the general trend.
- **Stronger constraint**: constraint A is stronger than B if A's violation score is always at least as high as B's, so A catches more.
- **Unsafe tuple**: a row where two models that agree on all training data could still disagree, so its prediction cannot be trusted.
- **Trusted machine learning (TML)**: using constraint violation from a row's inputs alone as a trust signal for a model's prediction, without the model or ground truth.
- **Data drift**: a significant change in a new dataset versus a reference, measured as average tuple-level violation of the reference's constraints.
- **ExTuNe**: the paper's companion tool that explains a non-conforming tuple with a per-attribute responsibility score.

## Examples worth remembering

- **Flight duration (running example).** Departure time, arrival time and duration satisfy AT - DT - DUR ~ 0 for daytime flights. An overnight flight breaks this (arrival date is missing from the data), scoring a violation near 1, matching its large regression error (p. 2, p. 5).
- **Correlated vs. combined projections (Example 6-7).** With three near-collinear points, raw X and Y as projections give a wide, permissive zone; using X-Y and X+Y instead gives a much narrower zone that excludes points following neither trend jointly (p. 6).
- **A discovered, decomposable constraint (Example 14).** Real airline data yields 0.7·AT - 0.7·DT - 0.14·DUR - 0.07·DIST ~ 0, not interpretable alone, but equal to 0.7 times the duration identity plus 0.56 times an implied ~500 mph average speed constraint; PCA merged them because they are correlated in the data (p. 8).
- **Piecewise-linear data needs partitions (Example 18, Fig. 9).** One global PCA fit over data with several linear trends per sub-group gives weak, high-variance constraints; partitioning by the relevant category and fitting separately gives tight ones (p. 16).
- **Trusted ML on sensor data.** Training only on sedentary activities and mixing in mobile-activity data at serving time: classifier accuracy drop tracks average constraint violation almost perfectly (pcc = 0.99) as the mobile fraction rises (p. 11).
- **ExTuNe responsibility charts.** Training on healthy patients and serving on diseased ones: blood-pressure attributes get the highest responsibility. Training on cheap phones and serving on expensive ones: RAM dominates. For house prices, responsibility spreads across many attributes instead of concentrating (p. 18-19).

## Quotes

- "The key finding we present is that projections that incur low variance on a dataset construct effective conformance constraints." (p. 1)
- "low-variance components of a principal component analysis, which are usually discarded for dimensionality reduction, generate stronger conformance constraints than the high-variance components." (p. 1)
- "lb = mu(F(D)) - C * sigma(F(D)), ub = mu(F(D)) + C * sigma(F(D))" (p. 5)
- "In our experiments, we set C = 4, which ensures that in expectation, very few tuples in D will violate the constraint for many distributions of the values in F(D)." (p. 5)
- "conformance constraints do not require any parameter from the user and work on noisy datasets." (p. 3)
- "our overall procedure is cubic in the number of attributes and linear in the number of tuples." (p. 7)
- "If K additional attributes need to be altered, A_i has responsibility 1/(K+1)." (p. 18)

## Applying it to RESSLab-Hub

- **Per-table numeric bound rules (proposal layer 2, group ranges).** The mean ± C·sigma bound (p. 5) is a direct match for "group ranges": compute mean/std per numeric column, or per known derived-identity expression (h_over_t_cw, p_yn, f_u - f_y), and warn when a submitted row falls outside. This is the paper's method applied directly to single columns first, before any PCA discovery.
- **PCA-on-numeric-columns as the discovery-spike engine.** Running Algorithm 1 on one table with numpy's `eigh` is cheap even at a few hundred rows, and surfaces candidate linear cross-column constraints nobody wrote down (like E = 200 GPa as a near-constant projection). Treat its output as draft candidate rules for a human or LLM to turn into named YAML checks with a "why", never auto-applied, matching the proposal's "LLM may draft, never decide."
- **Disjunctive constraints per peer group.** The partition-by-categorical-column method (at most 50 distinct values, our steel grade and section family columns both qualify) is exactly the mechanism for "group ranges per peer group": separate mean/std bounds per steel grade instead of one global range.
- **Violation score as the severity signal.** The smooth 1 - exp(-excess/sigma) score turns "N standard deviations off" into a 0-1 number, useful for wording a wwPDB-style percentile message ("mild"/"severe"), though the proposal's error/warning severities should stay named checks with a reference, not be gated by this score alone.
- **ExTuNe-style responsibility for explaining a flagged row.** "Reset one column to the training mean, count remaining resets needed" cheaply points at which column is likely wrong, useful for automated "why" text or ranking which fix to suggest first (issue #366's "code, severity, suggestion, why").
- **Do not port PCA into production for iteration one.** The proposal rules out ML-based multivariate detection at first; keep PCA discovery as an offline research tool, and ship only hand-written or LLM-drafted YAML checks informed by what it finds.
- **Scale mismatch to state plainly.** The paper's smallest evaluation sets still run to thousands of rows; ours run 100 to a few thousand, with 30-80 numeric columns, sometimes more columns than rows once split by peer group. Expect noisier estimates than the paper ever tested, and prefer whole-table columns over per-group splits unless a group has enough rows.

## Limits and caveats

- No minimum sample size is stated anywhere for mean/std or PCA to be meaningful; every case study uses thousands to millions of rows. A small peer group (say, five submissions of one steel grade) will run the formulas but the result will be fragile.
- Small data is not discussed; it is a large-data, noisy-data paper aimed at ML training sets. The only zero-variance handling given is "set alpha to a large number when sigma = 0" (p. 5), which does not cover the near-zero-but-not-zero, few-rows case.
- The evaluation (Section 6) and the appendix proofs (B-E) were skimmed, not read in algebraic detail; Algorithm 1 and the bound/score formulas (p. 4-5, p. 7) were read closely.
- PDF-to-text conversion garbled some math notation (accents and hats lost, some formulas run into prose, notably around Theorem 13 and Lemma 11's proof); where unclear, this digest describes the idea in words rather than guessing a symbol.
- The kernel-PCA nonlinear extension (p. 9) is mentioned as future work only and not read further; only the linear method is described here.
- ExTuNe's own mechanism is only summarized as presented in this paper's Appendix I (p. 18); the original ExTuNe paper (SIGMOD 2020) was not consulted.
