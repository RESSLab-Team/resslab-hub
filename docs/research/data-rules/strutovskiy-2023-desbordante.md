# Solving data quality problems with Desbordante: a demo

Chernishev, Polyntsov, Chizhov, Stupakov, Strutovsky et al., 2023, PVLDB (VLDB demo paper), a system and tool demo.

## In one paragraph

Desbordante is an open-source C++ data profiler for "science-intensive" profiling: mining and checking complex statistics such as functional dependencies (FDs), approximate FDs, metric FDs, inclusion dependencies, and association rules, not just min/max style stats. It has web, console, and Python interfaces; the Python one uses pybind11 bindings, accepts Pandas dataframes, returns plain Python lists. The paper shows three demo scenarios: typo detection (FD/AFD discovery plus clustering), data deduplication (AFD discovery plus a sorted-neighborhood pass), and anomaly detection over time (comparing FD sets across partitions, then metric FDs to explain drift). It also reports speed and memory gains over Metanome and OpenClean. These primitives, in short Python scripts, solve everyday data quality problems (p. 1-2).

## Core principles

1. **Profiling splits into naive and science-intensive.** Naive is min/max, counts, basic stats. Science-intensive mines hidden structures ("primitives") like FDs and association rules (p. 2).
2. **A primitive has two task types, and explanation is part of validation.** Discovery finds every holding instance. Validation checks one instance and, on failure, shows what prevents it holding (p. 2-3).
3. **A C++ core beats a JVM core here.** Speedups and memory gains over Metanome, see rules of thumb (p. 2-3).
4. **Typos surface as small, rare violation clusters of an almost-holding FD.** A cluster is rows sharing LHS values, disagreeing on RHS (p. 3).
5. **There is no principled way to pick an AFD error threshold.** The user has to experiment, no formula given (p. 3).
6. **Deduplication can reuse AFD discovery.** Attributes almost equal to a key point to attributes likely carrying typos (p. 3).
7. **A metric FD (MFD) can explain a break an AFD search cannot.** It relaxes RHS equality to "within some distance", chosen by hand (p. 4).

## The three demo scenarios

**Typo detection (p. 3).** Discover FDs and AFDs that "almost" hold; the user picks one LHS -> RHS dependency; Desbordante shows clusters (rows agreeing on LHS, disagreeing on RHS). Two parameters: radius (closeness to the cluster's central value to count as a typo) and ratio (show a cluster only if the share inside radius is below ratio). Distance is Levenshtein for strings, L2 for numbers.

**Data deduplication (p. 3).** Discover AFDs between attribute pairs; group, per LHS, the RHS attributes it approximately determines; pick the LHS with the largest group, excluding artificial keys; sort the table by it; slide a window, flagging duplicates when rows match on at least k attributes (user-set); pick which row to keep and which values to copy.

**Anomaly detection (p. 4).** A "mine-explore-validate" loop: mine exact FDs on a first partition as the reference FDc; as new partitions arrive, mine and compare; when X -> Y drops out, try AFD mining at several thresholds; if that fails, pick a distance range and run metric FD validation at increasing p, keeping the smallest p that holds (formula garbled by the conversion); replace the FD in FDc with the found MFD.

## Rules of thumb

| Quantity | Value | Condition | Page |
|---|---|---|---|
| FD discovery speedup | 1.19x-3.43x, avg 2.12x | Desbordante vs Metanome | p. 2-3 |
| Inclusion dep. speedup | 3x-7x | Faida/Spider, vectorized, profiled | p. 3 |
| Pyro memory use | About half of Metanome's | Same FD mining task | p. 3 |
| Typo-cluster distance | Levenshtein / L2 | String / numeric RHS values | p. 3 |
| MFD range example | Bound 1 std dev, step 1 | Integer RHS, chosen by hand | p. 4 |
| Dedup match rule | >= k attributes, k user-set | Sorted-neighborhood check | p. 3 |

## Vocabulary

- **Primitive**: a type of dependency, rule or constraint a profiler mines or checks (p. 2).
- **Discovery / validation**: find every holding instance vs check one instance and explain a failure (p. 2).
- **Functional dependency (FD)**: X -> Y, rows sharing X must share Y.
- **Approximate FD (AFD)**: an FD that "almost" holds, error threshold set by hand (p. 3).
- **Metric FD (MFD)**: an FD relaxed so RHS values only need to be close, not identical (p. 4).
- **Cluster**: rows agreeing on the LHS of a fixed FD but disagreeing on the RHS (p. 3).

## Examples worth remembering

- Typo detection treats small, rare disagreeing-RHS clusters of a fixed FD as candidate typos, using Levenshtein or L2 distance from the dominant value (p. 3).
- Deduplication excludes artificial primary keys from the candidate LHS list, since a real ID determines everything and finds no near-duplicates (p. 3).
- The anomaly example sets the MFD step to 1 for an integer RHS, capping the range at one standard deviation, both by hand (p. 4).

## Quotes

- "Desbordante covers a fairly broad range of primitives and algorithms such as functional/inclusion/graph dependencies, association rules, algebraic constraints, etc." (p. 2)
- "A cluster is shown if the share of records residing inside the radius is less than ratio." (p. 3)
- "We consider two records as duplicates if they match on at least k attributes, which is set by the user at start." (p. 3)
- "The notion of AFD provides no straightforward means to associate the threshold with the number of tuples." (p. 3)

## Applying it to RESSLab-Hub

- "Does the section name determine the dimensions" is an AFD question, `section_name -> {depth, flange_width, ...}` (p. 3). At our scale, a pandas groupby does this: group by `section_name`, count distinct dimension tuples per group, flag groups with more than one. My transfer, not a paper shortcut.
- "Values that differ only by spaces" matches the typo-cluster idea (p. 3), radius/ratio with Levenshtein distance on the RHS. Transfer: compute pairwise string distance between distinct values of a categorical column, flag close pairs (distance 1-2, or equal after whitespace normalization). No FD needed, the column compares to itself.
- The step 0 spike (#366) can reuse the discovery/validation split (p. 2): a script mines candidate FDs across columns, and `<table>_rules.yaml` becomes the validation side with simpleeval. Transfer of their architecture, not a claim about YAML or simpleeval.
- The metric FD idea (p. 4) maps to the proposal's group-range warnings: check a relationship within a tolerance and report the tolerance actually needed. Loose transfer, the MFD formula is not legible from the conversion.
- The AFD threshold problem (p. 3) is a caution: expect no automatic cutoff for "how loose is loose enough". Pick thresholds by hand per table, note the choice in the rule's "why". Installing Desbordante is probably not worth it here (its numbers are about large tables, p. 2-3); plain pandas should do, our call.

## Limits and caveats

- A 4-page demo paper (all of it read, nothing skipped): scenarios and headline numbers, not full algorithms. The companion paper [2], with the full primitive list, was not read here.
- The MFD formula on page 4 is garbled by the conversion; described in words only, no symbols guessed.
- No dataset or measured scenario results; described procedurally, not with numbers.
