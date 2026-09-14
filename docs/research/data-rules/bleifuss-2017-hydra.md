# Efficient denial constraint discovery with Hydra

Bleifuss, Kruse, Naumann, 2017, PVLDB. An algorithm paper with a working system (Hydra) and an evaluation against the prior state of the art (FastDC).

## In one paragraph

A denial constraint (DC) is a rule of the form "no two rows can satisfy this set of predicates at once", for example "no two rows can share a department and have the newer hire earn more". DCs generalize keys, functional dependencies, and order dependencies in one framework, but finding all valid DCs is expensive: the standard method (FastDC) compares every pair of rows, quadratic in the number of rows. Hydra instead samples a small number of row pairs, computes a preliminary set of DCs from that sample, then efficiently finds every pair that would violate those DCs (without comparing all pairs) and folds the violations back in to get the final, complete set. This "approximate, then correct" idea makes Hydra's measured runtime grow linearly in the number of rows instead of quadratically. On real datasets with 100,000 to 1,000,000 rows, Hydra finishes in seconds to tens of minutes where FastDC needs hours or does not finish.

## Core principles

1. **A denial constraint forbids a combination of predicates across two rows**: "for all row pairs, not (predicate1 and predicate2 and ...)". Predicates compare a column of one row to a column of the other (or same) row with =, ≠, <, ≤, >, ≥ (p. 311).
2. **DCs subsume keys, functional dependencies, and order dependencies**, plus rules none of those express, such as "same department, newer hire, then not higher salary" (p. 311-312).
3. **An evidence is the set of predicates a row pair satisfies.** The full, deduplicated evidence set of a table determines which DCs are valid: a DC is valid exactly when no evidence contains all of its predicates (p. 313).
4. **Comparing every row pair is the main cost, and it is avoidable**: many pairs give the same evidence and are redundant. Hydra looks for a small, non-redundant subset instead (p. 312-313).
5. **Hydra's strategy is approximate first, then correct**: it samples pairs for preliminary DCs, then only hunts for pairs violating them (the "delta evidence set"), provably enough for a correct, complete result (p. 313, Theorem 2).
6. **Sampling has two stages**: random sampling (20 partner rows per row) estimates predicate selectivity, then focused sampling repeatedly applies whichever strategy currently looks most likely to reveal a new, unseen evidence (p. 314).
7. **Violation checking works on groups of row pairs, not single pairs**, via "cluster pairs", far cheaper than testing pairs one by one, with specialized algorithms per predicate type (equality, inequality, a combined join for two inequalities) (p. 315-317).
8. **DCs sharing a first predicate are checked together in one tree**, refining a row-pair group once for a shared prefix instead of once per DC; redundant DCs, implied by other kept DCs, are dropped before checking (p. 318).
9. **Runtime grows almost linearly in the number of rows in experiments, versus quadratically for FastDC**, an empirical finding on three datasets, not a worst-case guarantee (p. 319-320).
10. **Runtime grows exponentially in the number of predicates, for both algorithms**, because the number of valid DCs itself grows exponentially (p. 320).

## The algorithm: sampling, evidence inversion, evidence completion

Hydra runs five steps (Figure 2, p. 313): sample row pairs, invert the sample into preliminary DCs, find all pairs violating those DCs, merge their evidence back in, invert the completed evidence set into the final DCs.

**Sampling.** Random sampling picks k=20 other random rows per row and computes each pair's evidence, used only to estimate predicate selectivity. Focused sampling clusters columns by shared value; a "sampling focus" is a column plus a strategy (equal, different, greater, smaller). Hydra keeps a priority queue of foci ranked by "sampling efficiency" (new evidences found per evidence computed), samples with the best one repeatedly, and drops a focus once its efficiency falls below a threshold (0.005 default) (p. 313-314).

**Evidence inversion (Algorithm 1, p. 315).** Turns an evidence set into the minimal, valid DCs. Start assuming every single predicate alone is a valid DC. For each evidence, find current candidates it violates (their predicates are a subset of the evidence), remove them, and add back a candidate with one more predicate not in that evidence, unless an existing kept candidate already covers it. What remains after all evidences is sound, complete, and minimal (Theorem 1).

**Evidence set completion.** Preliminary DCs may be wrong because some unseen pair violates them. Theorem 2: the evidence of every pair violating a preliminary DC (the delta evidence set), combined with the preliminary set and inverted again, gives the exact answer, no need to touch untouched pairs. To find violating pairs without comparing all pairs, Hydra groups pairs into "cluster pairs" and refines them through each predicate with a matched algorithm, ordered by frequency divided by selectivity so selective, common refiners run first. Redundant DCs, found via implication rules, are dropped from the check list first.

## Rules of thumb

| Quantity | Value | Condition | Page |
|---|---|---|---|
| Samples per row (random sampling), k | 20 | Default | 314, 320 |
| Focused sampling efficiency threshold | 0.005 | Default | 314, 321 |
| Hydra vs FastDC speedup (Tax, 1M rows) | about 360x | vs single-threaded FastDC (~1 week est.); Hydra ~40 min | 320 |
| FastDC runtime, Hospital / Stock (~120k rows) | ~90 min / >14 hours | vs Hydra's under 2 min for both | 320 |
| Hydra memory, Hospital / Stock / Tax | 256 MB / 256 MB / 2 GB | Peak | 320 |
| Largest Tax instance handled | 50M rows in 7h (120 GB heap) | 75M rows ran out of memory | 320 |
| Minimization speedup on DC checking | up to 4x fewer DCs | Bigger with more predicates | 322 |
| Runtime growth vs rows / vs predicates | roughly linear / exponential | Empirical, all three datasets | 319-320 |
| Predicate space restriction effect | up to 3x slower without it | Cross-column needs >=20% shared values or similar magnitude | 319 |
| DCs not expressible as FDs | up to 99% of valid DCs | Tested datasets | 320 |

## Vocabulary

- **Denial constraint (DC)**: a rule that no two distinct rows may jointly satisfy a given conjunction of predicates.
- **Predicate**: a comparison between a column of one row and a column of the other (or same) row, using =, ≠, <, ≤, >, or ≥. **Predicate space**: the full set considered for a table.
- **Evidence**: for a row pair, the subset of the predicate space it satisfies. **Evidence set**: all distinct evidences seen.
- **Minimal DC**: a valid DC where no subset of its predicates is itself valid. **Trivial DC**: one holding for any possible data, so it carries no information.
- **Evidence inversion**: the algorithm turning an evidence set into minimal valid DCs.
- **Delta evidence set**: the evidence of all row pairs violating the preliminary DCs.
- **Cluster / cluster pair / partition**: a cluster groups rows sharing a value; a cluster pair represents all row pairs between two clusters; a partition is a compact set of cluster pairs.
- **Sampling focus**: a (column, strategy) pair directing focused sampling. **Sampling efficiency**: new evidences found per evidence computed.
- **Selectivity**: the fraction of pairs satisfying a predicate.
- **IEJoin**: a join algorithm (reused from prior work) checking two inequality predicates on a pair in one pass.
- **FastDC / A-FastDC / C-FastDC**: the prior DC discovery algorithm (exact / approximate / with constants), the comparison baseline.

## Examples worth remembering

- **The staff table (Table 1, p. 312).** Five employees with ID, name, department, department code, hire year, salary. Gives a UCC (name+hire-year), an FD (department to department code), an OD (ID order implies hire-year order), and a DC none of the three can express: same department, newer hire must not earn more.
- **Redundant row pairs.** In theory no pair is redundant in the worst case (a diagonal matrix), but on tested datasets most pairs are redundant, which is why sampling works in practice (p. 313).
- **Evidence inversion worked example (p. 315).** From the candidate "name equal", an evidence where two rows share a name forces it to grow to "name equal and department equal".
- **Tax dataset scale (p. 320).** FastDC could not finish the 1,000,000-row Tax dataset inside 15 hours; Hydra finished it in about 40 minutes.
- **Predicate space restriction (p. 319).** Without it, Hydra runs (up to 3x slower) but surfaces mostly uninteresting DCs, such as comparing a zip code to a hospital owner field, columns that correlate by coincidence, not meaning.

## Quotes

- "A denial constraint ψ is a statement of the form ∀t, t′: ¬(...)" (p. 311, Definition 1).
- "Hydra is specifically designed to not compare all tuple pairs and, hence, to avoid this quadratic trap" (p. 312).
- "The full evidence set immediately determines the valid DCs in a dataset" (p. 313).
- "This threshold can influence only Hydra's runtime, but never its result quality." (p. 314).
- "A large share of valid DCs (up to 99%) on these datasets cannot be expressed as FDs." (p. 320).

## Applying it to RESSLab-Hub

- **This paper does not fit our scale, plainly.** Hydra exists to avoid comparing all row pairs on tables of 100,000+ rows. Our tables have a few hundred to a few thousand rows: at most tens of millions of comparisons, seconds of brute force. None of Hydra's sampling or its data structures (partitions, cluster pairs, IEJoin) is worth building; a Python spike can vectorize pairwise comparisons with numpy or pandas directly (transfer, principle 4, scale numbers p. 319-320).
- **For the discovery spike (issue #366, step 0), do brute-force DC discovery, not Hydra.** Compute each row pair's evidence directly, then invert with Algorithm 1 (p. 315): no clustering, no sampling, simple to write in Python (transfer, Section 5).
- **The predicate space restriction is worth taking even at our scale.** Their rule: only compare numeric columns of similar magnitude, or categorical columns sharing enough values (their claim, p. 319, their zip-code-vs-hospital-owner example of a useless comparison). Our transfer: only propose cross-column rules within the same data-dictionary `group`, or between columns with matching or ratio-related `unit`.
- **Use "evidence" and minimality as a sanity filter for LLM-drafted rules (proposal step 1).** Drop a proposed check if a simpler, already-accepted rule already implies it (minimality, p. 311, our transfer to YAML rule review).
- **On how many DCs come out and how to rank them: the paper is a warning, not a recipe.** DC count and search time explode exponentially with predicates (principle 10, p. 320); with 30-80 columns per table, an unrestricted search would flood the output with trivial or coincidental rules. Our transfer: restrict the predicate space heavily, then rank survivors by whether they match known identities in the brief (h_over_t_cw, p_yn, gross area, f_u > f_y, th_80 <= th_50 <= th_20), keeping only non-trivial DCs not already implied by another kept one.

## Limits and caveats

- Exact DC discovery only; approximate DCs (tolerating some violations, relevant for real data with typos) are future work, only sketched in the conclusion (p. 322).
- All evaluation datasets have far more rows than columns (7-15 attributes, 100,000+ rows); the opposite regime is never tested, so "almost linear in rows" says nothing about our case.
- Figures 5-11 (runtime, memory, phase breakdown) could not be read as numeric data: conversion turned axis labels and data series into scattered numbers and stray characters. Only the surrounding prose was used.
- Nothing here covers fix suggestions, contributor messages, or percentile warnings; those parts of the proposal need other sources.
- The refinement operators get only a paragraph each; reimplementing them exactly needs the IEJoin paper cited (reference [10]), not read.
