# Discovering outlying aspects in large datasets

Nguyen Xuan Vinh, Jeffrey Chan, Simone Romano, James Bailey, Christopher Leckie, Kotagiri Ramamohanarao, Jian Pei (2016), Data Mining and Knowledge Discovery. Algorithm paper: new scoring functions plus a search method, with an experimental evaluation.

## In one paragraph

Given one query row and a background dataset, which small set of columns (a subspace) makes that row look most unusual? The paper calls this outlying aspects mining. It shows common scoring functions are biased by the number of columns used: distance-based scores grow with more dimensions, density-based scores shrink, so naive scores cannot be compared across subspaces of different sizes. It defines "dimensionality unbiasedness" formally (the score's average value over random data must stay constant as dimensions are added) and proposes two fixes: the density Z-score (standardize density by its mean and standard deviation across the dataset) and the cheaper isolation path score (how few random splits it takes to isolate the query, inspired by isolation forest). Since checking all column subsets is exponential, it proposes beam search: score all 1D and 2D subspaces exhaustively, then grow only the best W subspaces one column at a time. Experiments on synthetic and UCI data show both new scores beat older ones at recovering known outlying subspaces, with isolation path far faster on large data.

## Core principles

1. **Outlying aspects mining is not outlier detection.** It starts from one query object and asks which subspaces explain it; outlier detection scans a whole dataset for unusual points without explaining why (p. 2).
2. **Raw scores are biased by dimensionality.** Distance-based outlying degree (OD) grows as columns are added; kernel density usually shrinks, though it can jump orders of magnitude on one added column (pp. 3, 10-11).
3. **Dimensionality unbiasedness means a constant baseline.** A score is unbiased if its average value, over random uniform data, stays the same regardless of subspace size (p. 16).
4. **Rank and Z-score normalization make any score unbiased.** Converting a raw score to its rank, or to (value - mean) / std over the dataset, always gives a constant expected value, for any data distribution, not only uniform (p. 17).
5. **The isolation path score is unbiased without normalization.** Its expected value equals 2·H(n) - 2 (harmonic number of the sample size), independent of dimensionality, proven by recursion (p. 18).
6. **Density rank and Z-score are accurate but expensive.** Both need the density of every point (cost order n^2 * d); rank keeps only the order, Z-score also keeps the magnitude of the deviation (pp. 12-13, 34).
7. **Isolation path is cheap and scales to very large data.** Average time per query stays near constant in n, with no distance computation, since it only builds the branch of a random tree that isolates the query (pp. 14-15, 23).
8. **Trivial outlying columns should be pulled out first.** A column where the query is already extreme alone (top epsilon percent) should be filtered before multi-column search, or it swamps results with "trivial column + anything" (p. 9).
9. **Beam search relies on a "good subspaces show up small" heuristic.** A strong subspace usually already looks promising in some lower-dimensional projection of itself, though not always: a point at the center of a sphere looks normal in every 1D projection (p. 20).
10. **No single scoring measure wins everywhere.** In the spirit of no-free-lunch, different measures suit different situations; the paper suggests combining several as future work (p. 35).
11. **Local outlying subspaces are a known blind spot.** Isolation path, built on isolation forest, cannot catch subspaces where the query is only a local outlier relative to its own neighborhood (p. 35).

## The isolation path score and the beam search procedure

Isolation path score, in words: take a random sample of the data (default 256 rows), repeatedly pick a random column and a random split point inside its range, keep only the rows (query included) on the query's side, and count splits until the query is alone. Average over many repeats (default 500). Few splits means unusual; many means an inlier deep in a cluster. If every remaining row ties on the chosen column, stop and add a correction term: 2*(ln(remaining rows) + 0.5772) - 2, the expected tree height for that sample size. No distance computation, near-linear time, and the baseline does not depend on subspace size, so a 2-column and 5-column score are directly comparable. In Python: sample rows, loop random-column/random-split/filter, count splits, average.

Beam search, in words: 2^d - 1 possible subspaces, too many once d exceeds about 20. Stage 1 scores every single column and screens out "trivial" ones (query in the top epsilon percent alone). Stage 2 scores every 2-column subspace exhaustively. From stage 3 on, keep only the W best subspaces from the previous stage, add each remaining column to each, score, keep the new best W. Stop at a chosen maximum size. This checks roughly d^2 + W*d*d_max subspaces instead of 2^d, assuming a genuinely outlying subspace already looks outlying in a smaller sub-combination.

## Rules of thumb

| Quantity | Value | Condition | Page |
|---|---|---|---|
| Isolation path subsample size (n_s) | 256 rows | default; use ~n/4 if n not much larger than 256 | p. 21 |
| Number of random paths averaged | 500 | default; converges after ~100 paths | p. 21 |
| Trivial outlying column threshold (epsilon) | 0.5 % | KDD Cup cutoff for a column alone being trivially outlying | p. 24 |
| Beam width (W) | ~100 | performance flattens near W = 100 on a 75-dim benchmark | pp. 21, 29 |
| Max subspace size for interpretability | up to 5 columns | scoring work focuses on d <= 5, higher is hard to read | p. 23 |
| Beam search cost | O(d^2 + W*d*d_max) | vs O(d^d_max) for naive exhaustive search | p. 20 |
| Isolation path time | O(n_s) avg, O(n_s^2) worst | one isolation path on a subsample of size n_s | p. 15 |
| Density rank / Z-score cost | O(n^2 * d) | density of every point needed to rank or standardize | pp. 12-13 |
| Isolation path baseline | 2*H(n) - 2 | H(n) = n-th harmonic number | p. 18 |

## Vocabulary

- **Subspace / aspect**: a subset of the dataset's columns.
- **Query object**: the one row being explained; may or may not be a global outlier.
- **Outlying aspects mining**: finding which subspaces make the query look most unusual.
- **Score-and-search**: score how outlying the query is per subspace, then search for the best score.
- **Dimensionality unbiasedness**: a score whose average value over random uniform data stays constant across subspace sizes.
- **Trivial outlying feature**: a column where the query alone scores in the top epsilon percent.
- **Non-trivial outlying subspace**: a top-scoring subspace built only from non-trivial columns.
- **Density rank**: rank of the query's kernel density among all rows in a subspace.
- **Density Z-score**: (query density - mean density) / standard deviation of density.
- **Isolation path score**: expected splits needed to separate the query from a data subsample.
- **Beam width (W)**: number of best-so-far subspaces kept at each beam search stage.
- **Consensus Index**: generalization metric used on UCI data with no known ground-truth subspace.

## Examples worth remembering

**The UCI Vowel trivial-feature example.** After pushing one column (D1) for the query to 1.1 (outside the scaled [0,1] range), the top-10 subspaces from density rank were all "D1 plus something else". Removing D1 revealed a genuinely different subspace, {D3, D6, D9} (p. 9).

**Synthetic clusters showing bias (10-cluster Gaussian mixture, d 1 to 10).** OD rose and log kernel density fell as columns were added, purely from adding dimensions; both then preferred higher-dimensional top subspaces, while density rank gave a more even spread (p. 12).

**Uniform-data baseline (d 2 to 20).** LOF and isolation path stayed flat as dimensions grew, isolation path matching the predicted 2*H(n) - 2 curve; OD, log density and LOGP all rose with dimensionality (p. 22-23).

**KDD Cup'99 trivial-feature check (118,049 records, 38 columns).** With isolation path and a 0.5 % threshold, 34.3 % of labeled attack records had a trivial outlying column, against 4.1 % of normal records; land attacks mostly triggered on column "land" (p. 24-25).

**Ground-truth high-dimensional benchmark (Keller et al. data, d 10 to 100).** Density Z-score and isolation path scored best on sensitivity and precision; OD had high precision but always returned the maximum allowed size, hurting sensitivity since true subspaces were often only 2-3 columns (p. 27-29).

**Beam width sensitivity (75-dimension benchmark).** Performance improved gradually as W grew from 10, then flattened around W = 100; density rank was the exception, worsening slightly (p. 29).

## Quotes

- "We formalize the concept of dimensionality unbiasedness, a desirable property of outlyingness measures." (p. 1)
- "Coupling trivial outlying features with other features can potentially increase confusion and false discoveries." (p. 9)
- "A larger negative Z-score corresponds to a lower density, i.e. a possible outlier." (p. 13)
- "The isolation path score admits a fixed time and space complexity that is independent of the data size and dimensionality." (p. 15)
- "A dimensionally unbiased outlyingness measure ... [has a] baseline value ... independent of the dimension of the subspace." (p. 16)
- "A good outlying subspace will show some telltale sign in at least one of its lower dimensional projections." (p. 20)
- "In the spirit of the no-free-lunch theorem, it is likely that no measure is optimal in all settings." (p. 35)

## Applying it to RESSLab-Hub

- Our tables (about 100 to a few thousand rows) would only ever need 1-3 of the 30-80 numeric columns to explain a row: the "d <= 5" regime the paper targets for readability (p. 23). Its scale concerns (n up to 10^7, d up to 100) do not apply to us. My transfer, not the paper's claim.
- For "why is this row odd," implement density Z-score, not density rank or isolation path: our n is small, so the O(n^2 * d) cost the paper calls expensive (p. 13, p. 34) is trivial, and Z-score keeps the magnitude, reading like a wwPDB-style percentile message, matching proposal item (2). Transfer from principles 4 and 6.
- Before any multi-column check, screen for trivial single-column outliers (principle 8, p. 9): flag a row extreme on one column alone, within its peer group, before checking 2-3 column combinations. Maps to proposal item (2).
- Use beam-search style incremental building only if discovery (item 0) needs more than a handful of columns: score all pairs exhaustively (about 3160 at 80 columns), then grow only the best few triples (p. 20).
- Do not implement OD or raw kernel density: both bias toward reporting more columns as "more outlying" for reasons unrelated to the data (principle 2, p. 3, p. 10-11).
- Keep the "why" text column-scoped: the paper's interpretability order is rank first, Z-score second (p. 19), fitting item (3)'s plain-language explanations.
- The isolation path's tuning numbers (500 paths, n_s = 256) come from a bigger-data regime; do not copy them as defaults here (p. 21, p. 23).

## Limits and caveats

Read in full: introduction, related work, problem definition, the outlyingness-score sections, the dimensionality-unbiasedness proofs (Theorem 4's algebra skimmed), the beam search section, experiments 7.1 and 7.3. Skimmed: the KDD Cup section (7.2) and the UCI/Consensus Index section (7.4). Several figures and one results table (Table 3) converted as scrambled text, so no numbers from Table 3 or the KDD Cup attack-type figure are used here; those findings come from the surrounding prose, which read cleanly. References were not read beyond noting which prior methods (HOS-Miner, OAMiner, LOF, LOGP, GlobalFS) the paper positions against. It is from 2016, with nothing on deep-learning or LLM-based outlier explanation; its method is classical statistics and combinatorics, so it translates directly to a Python spike with numpy/pandas.
