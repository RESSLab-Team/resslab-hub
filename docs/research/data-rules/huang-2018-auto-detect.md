# Auto-Detect: data-driven error detection in tables

Zhipeng Huang and Yeye He, 2018, SIGMOD. Algorithm and system paper.

## In one paragraph

Existing single-column error detectors (Potter's Wheel, regex type-checkers) look only inside the column: they build a pattern from the values they see and flag whatever does not fit. This fails on mixed but valid formats (integers plus one value with a thousands separator) and misses true errors that each form a clean pattern (half a column in "2011-01-01" dates, half in "2011/01/02" dates). Auto-Detect instead asks whether two value patterns are known to co-occur in the same column across a huge corpus of other tables. It generalizes each value into a pattern with a "generalization language" (a mapping from characters to classes like digit, letter, symbol), measures how often pairs of patterns appear together using pointwise mutual information (PMI), and calls two patterns incompatible when they almost never co-occur. Since one language is not sensitive to every error type, Auto-Detect selects an ensemble of complementary languages under a memory budget and precision target, using a greedy algorithm with a proven approximation guarantee. On Wikipedia and enterprise Excel files, it finds tens of thousands of real errors at over 0.98 precision, beating ten baselines.

## Core principles

1. **Compatibility is global, not local.** Whether two formats belong together should be judged from how often they co-occur across many other tables, not the distribution inside one column (p. 3).
2. **PMI measures co-occurrence strength.** PMI(v1, v2) = log( p(v1,v2) / (p(v1)·p(v2)) ), using column-level corpus probabilities. Zero means random co-occurrence, positive more than chance, negative less (p. 3-4).
3. **Generalize before measuring, to fight data sparsity.** Exact values rarely co-occur enough to trust PMI directly; mapping characters to classes (digit, letter, symbol) pools evidence across values sharing a pattern (p. 4).
4. **A generalization language is one character-to-class mapping**, from a tree of groupings (root, then letter/digit/symbol, down to each character). Coarser copes with sparse data but blind to fine differences; finer is sensitive but needs more data and memory (p. 4).
5. **No single language catches every error type.** One tells date separators apart but not letters from digits; another does the opposite (p. 4-6).
6. **Choosing the best set of languages under a memory and precision budget is NP-hard**, both with a free per-language threshold and with a fixed target precision (p. 6-7). A greedy algorithm still gets a 1/2(1 - 1/e) approximation by picking languages with best gain per memory size (p. 7).
7. **Training labels come from the corpus itself (distant supervision), not humans.** Compatible pairs come from the same clean column; incompatible pairs from injecting a value from one column into an unrelated column (p. 5-6).
8. **Smoothing and sketching keep the statistics practical**: blending counts with their independence expectation stabilizes near-zero counts, and a count-min sketch cut memory from about 4 GB to about 40 MB per language (p. 7-8).
9. **Final compatibility uses max confidence across languages, not average.** If one language is confident of incompatibility, trust it, since each language only sees some error types (p. 14).
10. **Outlier detection and error detection differ.** An outlier is local deviation (a CEO's salary among employees) and is not automatically an error; error detection should not depend on local mixture ratio (p. 12).

## The generalization language and the selection algorithm

**Generalizing a value.** A generalization tree groups characters into classes at increasing levels (root, then letters/digits/symbols, down to individual characters). A language L is one path through this tree, mapping each character to a tree node. A language keeping symbols but folding letters and digits turns "2011-01-01" into "\A[4]-\A[2]-\A[2]". Values are compared by generalizing both with the same language and computing NPMI on the patterns, using corpus counts of how often each pattern (and each pattern pair) appears. The restricted tree yields 144 candidate languages, each catching different error types, so a single language always misses some.

**Training data without humans.** Pick columns C+ whose values are mutually PMI-compatible. Positive pairs come from values in the same C+ column; negative pairs come from injecting a value from one C+ column into an unrelated C+ column (checked for accidental similarity). This gives over 100M labeled pairs, used to calibrate thresholds and select languages, never touched by a human.

**Calibrating and selecting languages.** For a language and an NPMI threshold, precision on the labels is correct incompatible predictions over all predictions below threshold. Static-threshold aggregation fixes a target precision P for every language and solves for the loosest threshold that still meets P; selection then means choosing a subset of languages, each calibrated to P, whose union of caught negative examples is largest under a memory budget (NP-hard). The greedy algorithm starts empty and repeatedly adds the candidate, within budget, with best marginal gain per unit memory, then compares to the single best language alone and returns whichever covers more, giving a 1/2(1 - 1/e) approximation.

**Scoring a new pair.** A pair is flagged incompatible if any selected language scores it below its own calibrated threshold. A confidence score is the max, over languages, of that language's precision-at-threshold applied to the pair's score, since trusting the most confident language beats averaging incomparable scores.

## Rules of thumb

| Quantity | Value | Condition | Page |
|---|---|---|---|
| Precision target, example | 0.95 (also 0.75 in worked examples) | design goal for automatic detection | p. 2 |
| Manual precision achieved | over 0.98 | top-1000 predictions, WIKI and Ent-XLS | p. 1, 9 |
| Wikipedia / web columns clean | 97.8% / 93.1% | 1000 sampled columns each, human-labeled | p. 3 |
| Estimated true errors in WIKI | 294K ± 24K | extrapolated from 100K sampled columns, 99% CI | p. 9 |
| Candidate languages | 452,310,333 raw, 144 restricted | full tree vs. classes forced to generalize together | p. 5 |
| Memory, sketch vs no sketch | about 4 GB down to about 40 MB per language | negligible quality loss | p. 8 |
| Precision at minimum memory | over 0.93 at relative recall 0.1 (k=500) | M = 1 MB | p. 11 |
| Languages selected | 2, 5, 7 | M = 1MB, 1GB, 4GB | p. 11 |
| Smoothing factor | best f in [0.1, 0.3], default f = 0.1 | Ent-XLS, main experiments | p. 9, 15 |

## Vocabulary

- **Generalization tree**: tree over an alphabet where each leaf is one character and each internal node is the union of its children.
- **Generalization language**: one mapping from characters to tree nodes; applying it to a value produces a pattern.
- **PMI / NPMI**: log of observed joint co-occurrence probability over the probability expected if independent; NPMI normalizes PMI to [-1, 1].
- **Distant supervision**: building large, imperfect training labels automatically instead of hand-labeling.
- **Static-threshold (ST) aggregation**: each language's threshold fixed so it alone hits a target precision P.
- **Jelinek-Mercer smoothing**: blending an observed count with its independence-assumption expectation to stabilize sparse statistics.
- **Count-min (CM) sketch**: probabilistic counting structure estimating frequencies in small fixed memory.
- **Precision@K**: fraction of correct predictions among the top K ranked predictions.

## Examples worth remembering

- **Thousands separator (Col-1)**: "0".."999" plus "1,000". A local method (MDL) flags "1,000" as an outlier because the separator breaks the fitted pattern. Auto-Detect sees separated and unseparated numbers commonly co-occur, so it is not flagged (p. 2-3).
- **Mixed integer/float (Col-2)**: mostly integers plus one "1.99", judged compatible because integers and floats co-occur often enough, unlike a local approach (p. 2-3).
- **Two date formats (Col-3)**: half "2011-01-01", half "2011/01/02". A local method reports nothing, regardless of mixture ratio; globally these patterns almost never co-occur, so Auto-Detect flags them (p. 3).
- **Two languages on the same pair**: for "2011-01-01" vs "2011.01.02", a symbol-sensitive language scores NPMI -0.5 and flags it, while one folding letters and digits sees both as identical and misses it. For "2014-01" vs "July-01" the roles reverse (p. 4-5).
- **Top real WIKI predictions**: pairs like "1976" vs "1976." (trailing dot) are flagged; a dot in the middle of a number (decimal point) is common and not flagged (p. 9).
- **CEO salary counter-example**: a CEO's salary can be far from other employees' without being an error, showing local-distribution outlier scores are not automatically quality signals (p. 12).

## Quotes

- "Existing approaches typically employ regex-like rules to detect errors... without considering a more global notion of compatibility." (p. 1)
- "The average cell error rate is between 1% to 5%." (p. 1)
- "Data compatibility/incompatibility is a global notion, irrespective of local value distribution within a specific column." (p. 3)
- "Values like '1,000,000' and '100' can be syntactically dissimilar... but semantically compatible when their co-occurrence in columns is analyzed more globally." (p. 3)
- "Errors that are automatically detected... should be a global property of the data... and not a function of the local data distribution." (p. 12)
- "Using max confidence... put our trust to the one with most confidence." (p. 14)

## Applying it to RESSLab-Hub

- Transfer idea: treat two string formats in the same categorical column as suspect when they almost never appear together in known-good data, not only checking a fixed allowed list. Fits the rule-discovery spike (proposal item 0), e.g. noticing "W610x195" vs "W610X195" (case) or a trailing-space value never sitting next to the dominant format.
- Our tables are far smaller (hundreds to a few thousand rows) than the paper's 100M-column corpus, so real PMI/NPMI over an external corpus does not apply (paper does not fit our scale, p. 8-9). What transfers is the principle: check a shape against shapes already accepted in that column and peer group, not just regex membership.
- For format hygiene (trailing spaces, mixed section-name spelling, grade formatting): write per-column pattern rules by hand in `<table>_rules.yaml` (proposal item 1). This is our transfer, not the paper's method: with a few hundred distinct values per column, a same-column frequency count of a normalized pattern (strip, casefold, digit/letter/symbol generalization, principle 3-4) flags a value whose pattern never appears elsewhere, no external corpus needed.
- The "ensemble beats one fixed regex" idea (principle 5, 9) suggests two or three cheap generalizers for section-name and grade columns (case-preserving, digit-folded, letter-folded), flagging a value if any generalizer marks it unseen in that column. Sized for our cardinality, not a re-implementation of language selection or PMI.
- Skip the NP-hard language-selection optimization and sketch compression (principle 6, 8): those solve choosing among 144 languages under a large-corpus memory budget, no equivalent at our scale, matching the proposal's "no ML-based multivariate detection."
- The distant-supervision idea (principle 7) could inform a self-check for LLM-drafted rules: inject a known-wrong value into a clean column and see whether the rule catches it, before curator review (proposal item 3).
- The outlier-vs-error distinction (principle 10) matters for the existing global-min/max warning and peer-group percentiles (proposal item 2): a far-off value is not automatically wrong, so messages should say "unusual for this peer group," not "wrong."

## Limits and caveats

- Covers only single-column, corpus-scale string-format detection. No cross-column rules (functional dependencies, derived-value identities like h_over_t_cw or p_yn); the paper calls multi-column detection "orthogonal to the focus of this work" (p. 12).
- All quality numbers (0.98 precision, 294K errors, memory figures) are measured on web-scale corpora and do not transfer as numbers to a database of a few hundred rows; only the ideas transfer.
- I did not fully read Appendix A (commercial offerings), the hardness proofs (Appendix C-E) beyond their theorems, or Appendix G beyond the numbers listed.
- Some inline math in the conversion is garbled (dropped subscripts/superscripts, an equation number); described in words rather than guessed.
- The paper assumes a client-side, memory-constrained tool; our validator is server-side batch with no such constraint, so the sketch memory optimization (principle 8) is not a real concern for us.
