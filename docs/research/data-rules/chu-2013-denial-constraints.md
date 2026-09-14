# Discovering denial constraints

Chu, Ilyas, Papotti, 2013, VLDB. Algorithm paper: a constraint language plus a discovery algorithm (FASTDC) and two extensions.

## In one paragraph

Denial constraints (DCs) say a certain combination of predicates over one or two rows can never be true at once. They cover key constraints, functional dependencies (FDs) and conditional FDs (CFDs), but also order and cross-column comparisons those languages cannot express, such as "no one earns less and pays a higher tax rate than someone in the same state". The paper builds a sound (not complete) inference system for DCs, so implied DCs can be dropped. It gives FASTDC, an algorithm that finds all minimal DCs holding on a table: it builds a space of candidate predicates, records for every row pair which predicates it satisfies (the evidence set), and reduces discovery to finding minimal set covers of that evidence set by depth-first search with pruning. A scoring function, interestingness, ranks DCs by succinctness (short is better) and coverage (well supported by data is better), so a human only checks the top ones. Two extensions handle real data: A-FASTDC allows a small percentage of violations, C-FASTDC adds constants to predicates. Tested on synthetic and real datasets, FASTDC recovers most expert-written "golden" constraints in its top-ranked output.

## Core principles

1. **A DC forbids one combination of predicates over one or two rows.** Written `q(P1 ^ ... ^ Pm)`, the predicates cannot all be true together; if they are, that is a violation. Keys, FDs and CFDs are special cases (p. 1497, p. 1500).
2. **DCs are more expressive than FDs and CFDs because they allow order and cross-column comparisons in one predicate.** "Lower salary implies lower tax rate" needs `<` and `>` on two columns at once (p. 1497).
3. **A DC is trivial if no data could violate it, and minimal if no subset of its predicates already holds alone.** Discovery only reports non-trivial, minimal DCs (p. 1500).
4. **Three inference rules (triviality, augmentation, transitivity) test whether one set of DCs implies another.** Sound in general, complete when predicates compare the same row pair on related operators (p. 1501).
5. **Discovery is a set-cover search, not testing every candidate DC against the data.** For every row pair, record which predicates it satisfies (evidence); a valid minimal DC is a minimal set of predicates intersecting every evidence set (p. 1502-1503).
6. **The predicate space is built column by column and column pair by column pair.** Per column: equality/inequality, plus order operators if numeric. Per "joinable" (same type, shared values) or "comparable" (both numeric, similar magnitude) pair: the same, across columns (p. 1502).
7. **Dynamic predicate ordering plus pruning make the cover search tractable, and splitting the search by "contains P or not" avoids rediscovering DCs.** Try next the predicate covering the most uncovered evidence; cut branches that would be trivial, non-minimal, or already implied (p. 1503-1504).
8. **A-FASTDC accepts a DC if its violating row-pair fraction stays under a threshold epsilon**, trading exactness for rules true "almost always" (p. 1504-1505).
9. **C-FASTDC adds constants (`state = 'FL'`) found with an Apriori-style search bounded by minimum support tau**, since many real rules apply to one column value only (p. 1505-1506).
10. **Interestingness ranks DCs by succinctness (shorter is better) plus coverage (better supported is better), each scaled 0 to 1**, cutting FASTDC's raw output to a short list worth checking (p. 1505-1506).
11. **The top 10-20 ranked DCs matched almost all expert "golden" constraints; implication testing removed 25%-73% of redundant DCs**, confirming pruning and ranking work in practice (p. 1507-1508).

## The denial constraint language

A DC is `q(P1 ^ ... ^ Pm)`, over one row or two rows (t-alpha, t-beta). Each predicate is `v1 op v2` (variable predicate) or `v1 op c` (constant predicate), with operators `=, <>, >, >=, <, <=`. All-variable DCs are VDCs; any constant makes it a CDC. Only DCs over at most two rows are considered (more rows are rare and explode the search space). Each operator has an inverse and implied operators (e.g. `<` implies `<=`), driving the inference rules and pruning.

**Predicate space.** For `m` columns: two equality predicates per column, plus four order predicates for numeric columns; the same sets again across joinable or comparable column pairs. Space size is `6 * 2m * (2m-1)`; the raw DC search space is `2^|P|`.

**Evidence set.** For every row pair, record which predicates from P it satisfies; that set is one element of `EviI`. A predicate set X is a minimal cover if it intersects every element of `EviI` and no smaller subset does. Theorem 2: `q(X1 ^ ... ^ Xn)` is a valid minimal DC exactly when `{X1,...,Xn}` is a minimal cover of `EviI`, turning discovery into a combinatorial search, no further data scans.

**FASTDC, reimplementable on a small table:** build P from the schema; for every row pair compute satisfied predicates into `EviI`; depth-first search over P for all minimal covers, reordering candidates dynamically (best coverage of remaining evidence first) and pruning trivial, non-minimal, or implied branches; each minimal cover, inverted, is a candidate minimal DC; finally drop DCs implied by others already found (closure-based implication testing).

**Extensions.** A-FASTDC changes the stopping rule: a cover is "epsilon-minimal" if uncovered evidence stays under `epsilon * |I| * (|I|-1)`. C-FASTDC builds a constant predicate space, keeps only tau-frequent constant sets (Apriori search), restricts the table to matching rows, and reruns FASTDC for the variable part.

## Rules of thumb

| Quantity | Value | Condition | Page |
|---|---|---|---|
| Predicate space size \|P\| | 6 * 2m * (2m-1) | m = number of columns | p. 1498 |
| DC search space | 2^\|P\| | any subset of P is a candidate | p. 1498 |
| Shortest DC length | 4 | length = distinct alphabet symbols used, not predicate count | p. 1505 |
| Joinable-column threshold | 30% shared values | stable predicate space below this | p. 1502, 1507 |
| Interestingness weight a | 0.5 default | peak F-measure for a between 0.5 and 0.8 | p. 1508 |
| Implication reduction, Tax/Hospital/Stock (10k rows) | 61% / 73% / 25% | DCs removed as redundant | p. 1508 |
| U-Precision, FASTDC top-10, clean data | 1.0 | all three datasets | p. 1509 |
| Scalability | quadratic in rows, exponential in predicates | Tax data, up to 1M rows, 50 predicates | p. 1507 |

## Vocabulary

- **Denial constraint (DC)**: rule that a set of predicates over one or two rows cannot all be true at once.
- **Variable DC (VDC)** / **constant DC (CDC)**: all predicates compare columns to columns, vs at least one compares a column to a fixed value.
- **Trivial DC**: satisfied by any possible data, carries no information. **Minimal DC**: no subset of its predicates is already a valid DC alone.
- **Closure**: all predicates forced true given a set already true, under a set of DCs; used for implication testing.
- **Predicate space (P)** / **Evidence set (EviI)**: candidate predicates from columns and column pairs / one satisfied-predicate-set per row pair.
- **Minimal set cover**: minimal subset of P intersecting every evidence set; matches a minimal DC one-to-one.
- **Joinable / comparable columns**: same type with shared values / both numeric with similar magnitude.
- **Epsilon-minimal cover / tau-frequent constant set**: A-FASTDC cover leaving up to fraction epsilon of evidence uncovered / C-FASTDC constant predicates with support at least tau.
- **Interestingness (Inter)**: ranking score, weighted sum of succinctness (shortness) and coverage (support from weighted "k-evidence": a row pair satisfying exactly k of a DC's predicates without violating it).
- **G-Precision / G-Recall / G-F-Measure**: precision/recall/F against expert golden DCs. **U-Precision**: fraction a human judges interesting, no golden set needed.

## Examples worth remembering

- **The tax table (Table 1).** Eight people with name, gender, area code, phone, city, state, zip, marital status, children, salary, tax rate, exemptions. Carries the running examples: a key on (area code, phone), an FD zip to state, a CFD pinning Denver to Colorado, and "same state, lower salary implies lower tax rate", which FDs cannot express.
- **c6 implied by c2 and c4.** "Same zip, lower salary, higher tax rate is impossible" follows from "same zip implies same state" plus the salary/tax-rate rule within a state, showing why an inference system matters.
- **c7, "first name determines gender".** True on the small sample table, false in general. The running example of overfitting: a short, low-coverage DC a naive method would rank too high.
- **The manager-salary table (Employee: ID, Manager ID, Salary).** A 3-row worked example: ID is a key, and "a manager's salary is never less than the employee's" is a minimal two-predicate DC.
- **Florida zip range (discovered CDC).** `state='FL' and zip<30397` and `state='FL' and zip>=35363` are both impossible: a range recovered with no one specifying the bound.

## Quotes

- "an American citizen cannot have lower salary and higher tax rate than another citizen in the same state." (p. 1497)
- "Even if c7 is true on current data, common knowledge suggests that it does not hold in general." (p. 1499)
- "the search space for DCs discovery is of size 2^|P|." (p. 1499)
- "the approximate DCs discovery problem... is to find all valid DCs, where a DC is valid if the percentage of violations... is within threshold epsilon." (p. 1504-1505)
- "our implication testing algorithm, though incomplete, is able to prune a large amount of implied DCs." (p. 1508)

## Applying it to RESSLab-Hub

- **Column identities and orderings map to one-row variable DCs.** `f_u > f_y`, `th_80 <= th_50 <= th_20`, `p_yn = a_cn * f_yn` are `q(t.A op t.B)` in DC form (transfer, p. 1497-1498), exactly the proposal's `<table>_rules.yaml` `check` expression for simpleeval. Inference axioms are not needed, our rules are handwritten.
- **Run the discovery spike (step 0) as a plain Python double loop, not the paper's DFS.** Hub tables are far below where the quadratic evidence-set build becomes slow (tested to 1M rows, p. 1507). Build predicates per column and per joinable/comparable pair (principle 6), look for near-zero-violation predicates, skip the set-cover machinery (transfer).
- **Use the joinable/comparable test to filter candidate cross-column rules before an LLM sees them** (p. 1502): same type and shared values, or both numeric and similar magnitude.
- **A-FASTDC's epsilon-tolerant validity fits dirty contributed CSVs.** Count violations per candidate rule, keep those under a small threshold (transfer from principle 8), close to the statistical/warning layer, not strict `error` checks.
- **C-FASTDC's constant predicates map to per-peer-group range rules**, e.g. "steel family=X implies f_y in range" (transfer of "state='FL' implies zip in range"); its tau-frequency filter picks which peer groups are large enough for a rule, and the Florida-zip example warns it can go stale when a new family is added (matches principle 3).
- **Interestingness ranks LLM-drafted or spike-found candidates, never decides**, matching "LLM may draft, never decide". Exact coverage is cheap at hub scale, so the paper's sampling shortcut (p. 1506) is not needed. Do not port the DFS search or cluster scaling: a scale problem we lack.

## Limits and caveats

- The paper targets tables up to 1 million rows and 100+ columns; RESSLab-Hub tables (hundreds to a few thousand rows, 30-80 columns) are smaller, so most scalability engineering is not needed.
- Figures 3(a)-3(p) were not machine-readable here: labels and legends came through as scattered numbers with no reliable link to a curve. Numbers attributed to a figure are quoted from the surrounding prose (Exp-1 to Exp-9), not read off a plot.
- The paper does not cover multivariate or ML-based rule discovery, matching "no ML in the first iteration" but saying nothing about a later phase.
- Full formal proofs (completeness of Theorem 1, Theorem 5) sit in an extended technical report, reference [9], not in this source.
- I read the full converted text, related work and references included; nothing else skipped for length.
