# Raha: A configuration-free error detection system

Mahdavi, Abedjan, Castro Fernandez, Madden, Ouzzani, Stonebraker, Tang. 2019, SIGMOD. System paper.

## In one paragraph

Error detection tools usually need a user to pick algorithms and tune their parameters (thresholds, patterns, rules, reference data). Raha removes that step. It auto-generates a bounded set of configurations for four families of error detection (outlier, pattern, rule, knowledge base), runs all of them, and turns each cell's strategy outputs into a binary feature vector. It clusters cells per column by vector similarity, and asks the user to label only a handful of whole tuples (one per iteration, biased toward under-labeled clusters). Labels propagate to every cell in the same cluster, giving many noisy training labels from a few real ones. A classifier per column trains on this and predicts the rest. With a budget of 20 labeled tuples, Raha beats stand-alone tools (dBoost, NADEEF, KATARA), ActiveClean and three aggregators on 7 real datasets, by 12 to 42 F1 points against the stand-alone tools.

## Core principles

1. **Combine many weak, unconfigured strategies instead of tuning one.** A single detector gives poor recall; Raha runs many pre-configured strategies from 4 families and lets a classifier decide what matters (p. 1).
2. **A strategy is an (algorithm, configuration) pair,** enumerated automatically so the "configuration space" becomes the input, not something the user supplies (p. 4).
3. **Each strategy output is one bit per cell.** No strategy needs to be individually accurate, only consistent in its own logic (p. 6, p. 7).
4. **Stack the bits into a feature vector per cell, one vector set per column,** since "dirty" only makes sense compared to values in the same column (p. 6).
5. **Cluster cells by feature vector similarity, per column.** Similar cells are assumed to share the same label (the cluster assumption); clustering turns one user label into many (p. 6, p. 7).
6. **Sample whole tuples, not cells, weighted toward unlabeled clusters,** since people label a row, not a lone cell (p. 7).
7. **Propagate the label from one clicked cell to its whole cluster.** Conflicts resolve by majority vote, safer against user mistakes than requiring full agreement (p. 7, p. 8).
8. **Train one classifier per column, not one global model,** since features and errors differ by column and predictions must be cell-level (p. 6, p. 8).
9. **Cross-column signal still reaches a per-column model,** since rule and knowledge base features come from pairs of columns (p. 8).
10. **No single family dominates, but each covers a blind spot.** Removing rule violation features hurts most on FD-rich data; removing outlier features hurts most where most errors are outliers (p. 11).
11. **Historical cleaned data can filter which strategies to run,** cutting runtime by more than 10x at small cost, if past cleaned datasets exist (p. 8, p. 9, p. 12).
12. **The system claims "no more than 20 labeled tuples,"** beating every baseline tested at that budget (p. 1).

## The four strategy families and their configurations

- **Outlier detection**, single-column, unsupervised. Histogram: flags a cell if its relative frequency in the column is below threshold `tf`, 9 fixed values 0.1 to 0.9. Gaussian (numeric only): flags a cell if its distance from the column mean, in standard deviations, exceeds threshold `dist`, 9 fixed values from the 68-95-99.7 rule: {1, 1.3, 1.5, 1.7, 2, 2.3, 2.5, 2.7, 3} (p. 5, p. 6).
- **Pattern violation**: "bag of characters". For every distinct character `ch` in a column, one strategy flags every cell containing it, implicitly encoding length and character type (p. 6).
- **Rule violation (functional dependencies)**: only single-attribute-left FDs. For every ordered column pair `(a, a')`, one strategy checks FD `a -> a'` and flags violating cells, `|A| * (|A| - 1)` strategies total (p. 6, p. 7).
- **Knowledge base violation**: for each relationship in an external knowledge base (DBpedia, 2064 relationships), a strategy matches two columns to the relationship's sides and flags contradicting data. Not realistic at our scale (p. 6, p. 3).

A strategy constant across the whole column is pruned as non-informative (p. 6).

## The clustering, sampling and label propagation loop (Algorithm 1)

In plain steps, reimplementable on a small table:

1. Build the strategy set S, run each on the dataset, get a binary feature vector per cell, grouped by column.
2. Start `k = 2` clusters per column.
3. Loop while the label budget is not used up:
   a. Per column, run hierarchical agglomerative clustering (cosine similarity, average linkage) on its feature vectors, into `k` clusters.
   b. Score every unlabeled tuple by a softmax that rewards cells in clusters with few labels so far (`exp(-N_c)` per cell, `N_c` = labels already in its cluster, normalized over tuples).
   c. Draw one tuple from that distribution, get a clean/dirty label per cell from the user.
   d. Add the tuple to `L`; increment `k` by 1.
4. After the budget is spent, per column: propagate every user label to all cells in its cluster (noisy label set `L'`). Mixed clusters resolve by majority vote, safer than requiring full agreement.
5. Train one classifier per column on `(feature vector, propagated label)` pairs (Gradient Boosting), predict the rest.

At the end, `k` equals `labeling_budget + 1`, and labeled tuples equal the budget exactly (p. 4, p. 6, p. 7, p. 10).

## Rules of thumb

| Quantity | Value | Condition | Page |
|---|---|---|---|
| Histogram outlier thresholds `tf` | 0.1-0.9, step 0.1 (9) | per column | p. 5 |
| Gaussian outlier thresholds `dist` | {1, 1.3, 1.5, 1.7, 2, 2.3, 2.5, 2.7, 3} (9) | numeric, from 68-95-99.7 rule | p. 5, p. 6 |
| Pattern strategies per column | one per distinct character | bag-of-characters | p. 6 |
| Rule violation strategies | `\|A\| * (\|A\|-1)` | single-attribute-left FDs, ordered pairs | p. 6 |
| Knowledge base strategies | 2064 | one per DBpedia relationship | p. 6 |
| Default labeling budget | 20 tuples | default for all results | p. 10 |
| Starting clusters per column | k = 2, +1 per iteration | until budget spent | p. 4, p. 7 |
| F1 improvement vs. stand-alone tools | +12 to +42 points | budget = 20 labels, 7 datasets | p. 10 |
| Runtime speedup, strategy filtering | over 10x | leave-one-out, 8 datasets | p. 12 |
| Classifier | Gradient Boosting | default model | p. 10 |

## Vocabulary

- **Error detection strategy**: one (algorithm, configuration) pair, e.g. histogram outlier detection with `tf = 0.3` (p. 4).
- **Feature vector of a cell**: the binary outputs of every strategy on that cell, concatenated (p. 6).
- **Column profile**: a column's character and value distributions, used to transfer strategies between similar columns (p. 8).
- **Cluster assumption**: points in the same cluster likely share the same label (p. 6, 7).
- **Label propagation**: assigning one cell's user label to every cell in its cluster (p. 7).
- **Homogeneity- / majority-based resolution**: propagate only on full cluster agreement, versus propagate the majority label anyway (p. 7, 8).
- **Strategy filtering**: dropping strategies unlikely to help, based on past runs on similar columns (p. 8, 9).
- **Syntactic vs. semantic error**: syntactic breaks the format or domain; semantic is valid but wrong in context (p. 3).

## Examples worth remembering

The "Lord of the Rings" example (Table 2): 6 (Lord, Kingdom) tuples, one Kingdom cell empty/garbled, one a stray number "123", one a wrong-but-valid name "Shire" instead of "Rohan". Two histogram outlier strategies (`tf = 2/6` and `tf = 3/6`) flag different subsets, showing how a threshold change alters what "rare" means (p. 3).

Table 3 turns that example into feature vectors: 8 strategies become an 8-bit vector per cell, and near-identical vectors fall into the same cluster (p. 4, p. 5).

On Hospital (1000 x 20, error rate 3%, mostly typos and dependency violations), removing rule violation features hurt the most, since it is FD-rich. On Movies (7390 x 17, error rate 6%), removing outlier features hurt the most, since most errors there are outliers (p. 11).

Strategy filtering: for Address, the promising historical strategies were FD checkers on ZIP, City and State, transferred from Hospital and Beers; for Hospital itself, histogram outlier detectors (p. 12).

ActiveClean's TF-IDF features, reused with Raha's sampling scheme, scored higher than ActiveClean's own pipeline but lower than Raha's full feature set (p. 11, p. 12).

## Quotes

- "Raha outperforms the state-of-the-art error detection techniques with no more than 20 labeled tuples on each dataset." (p. 1)
- "As each cluster contains values with a similar feature vector, we ask the user to only label one instance per cluster." (p. 2)
- "We suggest that each cluster that is classified as dirty represents an implicit type of data errors." (p. 2)
- "Our approach outperforms all the stand-alone error detection tools on all the datasets in terms of F1 score by at least 12% and up to 42%." (p. 10)
- "Raha is robust against removing feature groups as its performance does not collapse when a feature group is excluded." (p. 11)

## Applying it to RESSLab-Hub

- **The full clustering/classifier pipeline does not fit our scale.** Raha targets datasets large enough to train a per-column classifier; ours run a few hundred to a few thousand rows. Transfer only the idea of cheap, unconfigured checks per column, matching proposal #366's "no ML-based multivariate detection in the first iteration" (p. 1, our transfer).
- **Reuse "a family of strategies with a small fixed config grid" for group ranges.** Instead of Raha's 9 fixed `tf`/`dist` thresholds, our percentile ranges per peer group could report 2-3 fixed severities (info/warning/error) (p. 5, transfer of principle 2).
- **The FD-style rule violation strategy is a template for `<table>_rules.yaml` cross-column checks**, e.g. "if steel_grade is the same, f_y should be close". Our identities (h_over_t_cw, p_yn, f_u > f_y, th ordering, E = 200 GPa) are exact formulas, not FDs, so this is inspiration for the rule language, not a rule to copy (p. 6, our transfer).
- **The character-bag pattern idea can auto-suggest format rules for categorical columns** (steel grade strings, section names like "W610x195"): an LLM helper could scan distinct characters and propose a pattern for a curator to confirm (p. 6, our transfer).
- **Skip the knowledge base family**: it needs a public base like DBpedia; nothing comparable exists for steel data (p. 6, our judgment).
- **Reuse "majority vote over conflicting labels" for curator review, in spirit only.** This supports letting a curator's few flagged-cell reviews raise a threshold or add an override without every cell in a peer group confirmed. Design analogy, not code to copy (p. 8, p. 13).
- **The "20 labels goes a long way" finding backs keeping curator effort minimal**: a few confirmations can separate real problems from noise once the signal is informative (p. 1, p. 10).
- **Does not fit**: Raha needs enough dirty cells to cluster meaningfully; our smallest tables are too small and too clean (identities hold near-exactly) for clustering-based sampling to beat direct rule checks. Strategy filtering could apply later with many past-reviewed submissions.

## Limits and caveats

- The clustering and sampling machinery targets datasets large enough for per-column classifiers; no guidance for tables of a few hundred rows, our regime.
- The knowledge base family needs a public knowledge base (DBpedia); no analogue exists for structural steel data.
- I read Sections 1-7 and skimmed related work; skipped Appendix A (baseline details), B (scalability, classifier choice) and C (labeling case study), covered adequately by Sections 3-6 for this brief.
- Figures 2 through 6 are charts; the conversion kept axis and legend text but not plotted values, so I only cite what the prose states.
- Some formulas (feature vector definition, softmax sampling score, Section 5 similarity/score) were garbled by the conversion; described in words, not guessed.
