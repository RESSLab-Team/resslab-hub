# HoloClean: Holistic Data Repairs with Probabilistic Inference

Rekatsinas, Chu, Ilyas, Ré, 2017, arXiv preprint (system paper, data cleaning).

## In one paragraph

HoloClean repairs errors in a table by combining several signals in one model instead of one at a time: denial constraints (logic rules), matching dependencies to external dictionaries, and quantitative statistics such as value co-occurrence. Each cell becomes a random variable over candidate values. HoloClean compiles the signals into a probabilistic program (a factor graph) and runs statistical learning plus inference (Gibbs sampling) to compute, per noisy cell, a probability for every candidate value, then picks the most likely value as the repair, so each repair carries a confidence number. Because a full model over all value pairs does not scale, the paper prunes candidates by co-occurrence and links only rows that can actually conflict. On four real datasets, HoloClean beats systems using only one signal type, about 90% precision and 76% recall on average, more than double the F1-score of prior methods.

## Core principles

1. **Combine signals, do not pick one.** Constraints, external dictionaries, or statistics alone each fix only part of the errors and can add new ones; combined, they cover each other's blind spots (p. 1-2, food-inspection example).
2. **A repair is a value with a probability, not a binary decision.** Each cell gets a probability distribution over candidate values; the repair is the value of highest probability (p. 4).
3. **The probability has real meaning.** A repair with probability 0.6 means "60% confident": 60 out of 100 such repairs are expected correct, so a human can check only the low-confidence ones (p. 4).
4. **Confidence tracks correctness in practice.** Buckets of repairs by marginal probability show falling error rate as probability rises, from about 58% wrong at [0.5-0.6) to about 4% wrong at [0.9-1.0] (p. 11-12).
5. **Denial constraints are a general hard-rule language.** They cover functional, conditional, and tolerance dependencies as special cases: "for all rows, not (predicate1 and predicate2 and ...)" (p. 4).
6. **Minimality (change as little as possible) is not enough alone.** The smallest edit is not always correct; HoloClean uses minimality only as a weak prior (p. 1-2, p. 6).
7. **Hard constraints do not scale; soften them.** Checking a hard rule over all row pairs explodes combinatorially, so constraints become weighted (soft) signals (p. 3, p. 5-6).
8. **Prune candidates and row comparisons before scoring.** Keep only values that co-occur often enough with other values in the row, and only compare rows sharing a detected violation; both are needed for tractable inference (p. 7).
9. **Relaxing constraints to independent per-cell features helps speed and, often, quality.** It keeps variables independent so sampling converges fast, matching or beating the strict joint version (p. 8, p. 11).
10. **External dictionaries helped less than expected here.** Adding one improved F1-score by under 1%, only because the dictionary used had limited coverage, not a flaw in the idea (p. 11).
11. **Error detection is a separate, replaceable step.** HoloClean takes noisy cells as input from any detector and only does the repair step (p. 4).

## The method, from signals to a confidence per repair

Worth reimplementing in spirit, in plain words rather than the paper's Datalog-like rule language (DDlog), specific to their engine (DeepDive).

1. **Define the unit.** Each cell (row, column) is a variable over candidate values ("domain"). Cells not flagged as noisy are fixed as evidence; flagged cells are solved for.
2. **Prune the candidate domain.** Do not allow every value ever seen in the column. Keep only candidates co-occurring often enough with other values in the row: keep value v if P(v | other cell's value v') is at least a threshold tau (tested at 0.3, 0.5, 0.7, 0.9). Lower tau, more candidates, better recall, slower; higher tau, the opposite (p. 7).
3. **Turn each signal into a weighted vote for a candidate value.** A denial constraint votes against a value that would violate it, weighted by a learned or fixed strength; the default "relaxed" setting turns each constraint into one independent penalty per attribute rather than one joint rule, keeping cells independent (p. 8-9). A matching dependency votes for the dictionary's value on a match, weighted by trust in it (p. 6). Statistics vote through co-occurrence features, weight learned. Minimality votes weakly to keep the original value (p. 6).
4. **Combine votes into one distribution per cell.** All weighted votes are factors in one factor graph: exp(sum of weight times feature) over a normalizing constant. Weights not fixed by hand are learned from evidence cells by maximizing their likelihood (p. 4).
5. **Infer a probability per candidate.** Exact computation is intractable once hard constraints are involved, so HoloClean uses Gibbs sampling: resample each cell from its conditional distribution given the rest, until stable (p. 5, p. 8-9).
6. **Repair and report confidence.** Pick the candidate of highest estimated probability, and report that probability as the confidence (p. 5, p. 11-12).

**Tuple partitioning (p. 7-8):** group rows sharing a detected constraint violation and only compare rows within a group, instead of every pair.

## Rules of thumb

| Quantity | Value | Condition | Page |
|---|---|---|---|
| Average precision / recall | about 90% / 76% | across 4 datasets | p. 1 |
| F1-score improvement vs prior methods | over 2x on average | across 4 datasets | p. 2 |
| Precision / recall / F1, 4 datasets | Hospital 1.0/0.713/0.832, Flights 0.887/0.669/0.763, Food 0.769/0.798/0.783, Physicians 0.927/0.878/0.897 | at best tau per dataset | p. 9 |
| Pruning threshold tau tested | 0.3, 0.5, 0.7, 0.9 | co-occurrence cutoff for candidates | p. 9, p. 11 |
| Recall drop, Food, tau 0.5 to 0.7 | 0.77 down to 0.36 | precision/recall tradeoff of pruning | p. 11 |
| Speed-up / F1 cost, tuple partitioning | up to 2x faster / under 0.5% avg F1 loss (6% worst case) | large domains (low tau) | p. 7 |
| Factor graph size reduction from pruning | 7x to 96,000x | small vs largest dataset | p. 3 |
| External dictionary gain | under 1% F1-score | limited by dictionary coverage | p. 11 |
| Error rate by confidence bucket | 0.58, 0.36, 0.24, 0.07, 0.04 | buckets [0.5-0.6) to [0.9-1.0], avg across datasets | p. 11-12 |
| Largest dataset handled | 2.7 million tuples, 37M cells | Physicians dataset | p. 3, p. 11 |

## Vocabulary

- **Denial constraint**: "for all rows (or row pairs), not (predicate1 and predicate2 and ...)"; covers functional and conditional functional dependencies (p. 4).
- **Matching dependency**: if two records agree on some fields against an external source, they must agree on another field too (p. 4).
- **Cell**: one (row, attribute) value; the unit HoloClean repairs (p. 3).
- **Domain (of a cell)**: candidate values considered for repair; "active domain" is the naive version, every value ever seen in the column (p. 7).
- **Evidence / query variable**: a trusted fixed cell versus one to be inferred (p. 4-5).
- **Factor graph**: graph form of a joint distribution, hyperedges ("factors") linking correlated variables, each with a learned weight (p. 4).
- **Grounding**: instantiating concrete rule applications from rule templates and the data (p. 3).
- **Marginal probability**: probability a cell equals a given candidate value; picks and grades the repair (p. 4).
- **Gibbs sampling**: approximate inference resampling one variable at a time from its conditional distribution (p. 5).
- **Minimality principle**: prefer repairs changing fewer cells; used only as a weak prior here (p. 1-2, p. 6).
- **Conflict hypergraph / tuple partitioning**: grouping rows sharing a violation so checks run only within groups (p. 7).

## Examples worth remembering

**The food-inspection example (p. 1-2).** A wrong zip code in one row. A constraint-only repair fixes the zip but to the wrong value, and misses a wrong city and name. A dictionary-only repair fixes zip and city correctly but misses a misspelled name absent from the dictionary. A statistics-only repair fixes the misspelled name (an outlier) but not the zip. Combining all three fixes every error.

**Domain size blow-up (p. 6-7).** Checking every row pair against a constraint costs on the order of the row count squared times the domain sizes involved. On a 1,000-row dataset with no pruning, inference did not finish in a day.

**Hospital vs Physicians (p. 8-10).** Hospital (1,000 rows, about 5% wrong, many duplicates) reaches 100% precision, 71.3% recall, since duplicates give strong evidence. Physicians (about 2 million rows, mostly systematic errors) gets the best F1-score (0.897), since systematic errors are what co-occurrence statistics catch best.

**Confidence buckets as triage (p. 11-12).** Repairs below 0.6 confidence are wrong more than half the time; repairs above 0.9 are wrong about 4% of the time, supporting review focused only on low-confidence repairs.

## Quotes

- "these methods limit themselves to only one of the aforementioned signals, and ignore additional information that is useful to identify the correct value of erroneous records." (p. 1)
- "minimal repairs do not necessarily correspond to correct repairs." (p. 1)
- "each repair proposed by HoloClean is associated with a marginal probability that carries rigorous semantics ... a probability of 0.6 it means that HoloClean is 60% confident about this repair." (p. 4)
- "HoloClean allows users to relax hard constraints to soft constraints by assigning w to a constant value." (p. 6)
- "HoloClean treats error detection as a black box." (p. 4)

## Applying it to RESSLab-Hub

- Most transferable idea (principles 1-3): a repair should carry a confidence, not just a flag. Our transfer, not a learned number: give the fix-suggestion field in `<table>_rules.yaml` a rough label, "high" for an exact identity (h_over_t_cw = h_c/t_cw, p_yn = a_cn*f_yn), "low" for a peer-group percentile only.
- Principle 5 supports the proposal's simpleeval expressions: our identities (f_u > f_y, th_80 <= th_50 <= th_20, E = 200 GPa) are denial constraints in the paper's sense, but row-local, not row-pair; skip the paper's row-pair logic at our scale (p. 4).
- Principle 6 argues against silently picking the "closest" value without a rule behind it: tie every fix suggestion to an explicit expression, matching the proposal's "an LLM may draft rules, never decide."
- Principle 8 (co-occurrence pruning, conflict-graph row grouping) targets million-row scale, not us: skip that machinery entirely, no factor graph, no Gibbs sampling, no DDlog compiler.
- The "vote from a rule plus vote from stats, combined by weight" idea (principle 7) is close to the proposal's two layers (YAML rules, group ranges); do not merge them into one learned score, keep two ordered severities, since we have no ground truth to learn weights from.
- The confidence-bucket idea (p. 11-12) supports the wwPDB-style percentile messages already in the proposal, as our plain-language stand-in for confidence.
- External dictionaries (principle 10) are out of scope now: no reference dictionary beyond our own CSVs. Worth revisiting only for checking steel grades against an AISC or Eurocode table, a curated list, not a probabilistic model.
- Error detection as a separate step (principle 11) already matches our validator's shape.

## Limits and caveats

- The paper describes a 2017 stack (DDlog, DeepDive, Postgres, Gurobi baseline) not relevant to us; the proposal already commits to simpleeval and plain Python.
- The evaluation covers thousands to millions of rows and says nothing about the confidence idea on a few hundred rows with few known errors, our real situation; no small-data discussion was found.
- Sections 4 and 5 (DDlog rules, factor graph construction) were read in full but described in words above, since the PDF-to-text conversion mangled the math notation in places; nothing was guessed.
- The paper does not discuss plain "why" explanations for contributors, or generating editable fix text; both are proposal-specific needs it does not cover.
- The full paper was read end to end (all 13 pages plus references); no section was skipped.
