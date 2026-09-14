# Data rules for scientific submissions: synthesis

This file merges 25 paper digests into one set of rules. The goal is to help design and write per-column and cross-column data rules, statistical warnings based on the existing database, and fix suggestions for RESSLab-Hub submissions, and to give an LLM helper the context it needs to explain them. It is written against the proposal in GitHub issue #366 and the current validator (`backend/resslab_hub/data/validator.py`).

Sources are cited as short name and page, for example (Breck p. 7). Each short name is the first word of a digest file in this folder (`breck-2019-data-validation-ml.md`). When a rule is a transfer to our case and not a claim of the paper, it says "transfer". Most transfers come from the digests themselves, a few are new here and say "this synthesis".

## 1. The shared idea

Two claims come back in almost every paper. First, a data check is only worth something if people act on it: rules must be few, precise and explained, because alerts that fire on valid data train people to ignore them (Breck p. 1-2, Polyzotis p. 21-22, Schelter p. 1790, Microsoft p. 4, Wang p. 2). Second, the expectations should come from the data, but a human must own them: profile the existing data to draft the rules, then have a person review, edit and version them like code (Breck p. 2-5, Schelter p. 1788, Chu p. 1508, Fariha, Strutovskiy p. 2). A third point follows from both, and every paper that tests it agrees: when a domain expert can write the rule, the hand-written rule beats the automatic detector (Redyuk p. 8, Wang p. 4 and p. 9, Bendinelli p. 5).

## 2. Rules by topic

### 2.1 Where rules live and who owns them

- Keep one machine-readable contract per table, readable alone by a human or a model. The rule and its explanation sit together (Andersen p. 3, transfer to `<table>_rules.yaml`).
- The schema is first inferred, then owned by humans and versioned with the data. Most pipelines edit their schema up to 5 times, then it stabilizes (Breck p. 8).
- A rule is a predicate over a metric or a row, with a severity level (Schelter p. 1783). One YAML rule is one constraint.
- Keep an independent validator that re-checks the whole table against the rules, not only at submission (Andersen p. 6, transfer: run it in the data repo CI and on the full table).
- When a rule changes, write why in the rule file itself, not only in the commit history (Andersen p. 1, transfer).
- A value outside a constraint can mean the constraint is wrong. "SS" as a fifth country may be South Sudan (Polyzotis p. 22). A curator override is a signal to widen or fix the rule (transfer).
- Rules on constants per group go stale when a new group arrives (Chu, Florida zip example). Review group rules when a new steel family or section family is added (transfer).

### 2.2 Row rules: identities, orderings, constants, formats

Our cross-column rules are one-row denial constraints: `f_u > f_y`, `th_80 <= th_50 <= th_20` and `p_yn = a_cn * f_yn` all compare columns of the same row (Chu p. 1497-1498, Rekatsinas p. 4). The row-pair part of denial constraints (two rows that conflict) is not needed for these.

| Rule kind | Catalog name elsewhere | Example in the hub | Source |
|---|---|---|---|
| Not null, share present | `isComplete`, `hasCompleteness`, presence >= 70 % | dictionary `nullable` | Schelter p. 1783, Polyzotis p. 20, Breck p. 4 |
| Range on one column | `isInRange`, `hasMin`, `hasMax` | E between 190 and 215 GPa | Schelter p. 1783-1784 |
| Ordering | `isLessThan`, DC `t.A op t.B` | `f_u > f_y` | Schelter p. 1784, Chu p. 1498 |
| Identity with tolerance | `satisfies` (row predicate) | `h_over_t_cw = h_c / t_cw` within 2 % | Schelter p. 1784 (transfer) |
| Uniqueness | `isUnique`, `unique_ratio` in [1, 1] | specimen id | Schelter p. 1783, Microsoft p. 3 |
| Domain of a categorical | value set | steel grade, boundary condition | Breck p. 4 |
| Format and hygiene | lints, patterns | trailing space in `W610x217 ` | Hynes p. 4, Huang, Raha p. 6 |
| Lookup in a reference list | matching dependency, external dictionary | section name to nominal dimensions | Rekatsinas p. 11, Strutovskiy p. 3 |

Format rules worth writing:

- Number stored as text, enum stored as a float, integer stored as a float, a sentinel like -9999 with the wrong sign (Hynes p. 4).
- Duplicate rows and empty rows (Hynes p. 4).
- Two string shapes in the same column that never appear together in good data ("2011-01-01" and "2011/01/02"). Build a shape by folding digits, letters and symbols into classes, then flag a value whose shape is rare in its column (Huang p. 5, transfer: count shapes inside the column, no outside corpus).
- Values that differ only by case or spaces, or are 1 to 2 edits apart (Strutovskiy p. 3, Schelter p. 1791 for "en-gb" and "en-GB", Baran p. 4-5 for naming the edit: "remove trailing space").
- A categorical value seen once or twice while the rest repeat (Neutatz p. 4 and p. 7). Use `value_counts()` (transfer).
- A section name that maps to more than one set of dimensions: group by section name, count distinct dimension tuples (Strutovskiy p. 3, transfer).

Before a rule runs on data, check that it is consistent with the dictionary units: both sides of `p_yn = a_cn * f_yn` must reduce to the same dimension with `pint` (Williams p. 2 and p. 5-6, transfer). A rule that does not balance is an error in the rule file.

### 2.3 Discovering candidate rules (step 0)

All discovery papers are built for tables far larger than ours. At a few hundred rows, brute force in numpy or pandas takes seconds (Bleifuss p. 319-320, Chu p. 1507). Keep the ideas, skip the search machinery.

1. **Restrict the predicate space first.** Compare only columns of the same type with shared values or similar magnitude. Without this, the number of rules explodes with the number of predicates, and most found rules are trivial or coincidental (Bleifuss p. 319-320, Chu p. 1502). Transfer: only pair columns of the same dictionary `group`, or with compatible `unit`.
2. **Identities and orderings by brute force.** Test each candidate on every row, count violations, keep those under a small tolerance (A-FASTDC epsilon, Chu). Denial constraints are more general than functional dependencies: up to 99 % of valid DCs could not be written as FDs (Bleifuss p. 320).
3. **Near-constant linear combinations with PCA.** Center the numeric block, keep eigenvectors with low variance, bound each projection at mean plus or minus 4 sigma, weight each by 1 / log(2 + sigma), turn the excess into a score with 1 - exp(-excess / sigma) (Fariha p. 5 and p. 7). Run it per categorical value to get disjunctive constraints, for columns with at most 50 distinct values (Fariha p. 6). numpy `eigh` is enough (Fariha, transfer).
4. **Constants per group.** C-FASTDC adds constant predicates with a support threshold tau: "steel family = X implies f_y in range" (Chu, transfer).
5. **Profiling heuristics.** "If a column is complete in the sample, suggest isComplete" and similar rules for ranges, types and value sets (Schelter p. 1788). Heuristics can be wrong: `isUnique` was suggested for a column only 64 % unique on held-out data (Schelter p. 1791-1792).
6. **Rank, then prune.** Rank candidates by succinctness and coverage (a = 0.5), drop the ones implied by others: implication testing removed 25 % to 73 % of discovered DCs (Chu p. 1508). The top 10 discovered DCs were all correct on clean data (Chu p. 1509).
7. **Test the rules with injected errors.** Inject nulls, unit scale changes, swapped values and typos, then see which rules catch them (Microsoft p. 6, 10 issue types and 60 variants; Huang distant supervision; Breck p. 7-8 fuzz testing, "in the 100s" of examples).
8. **A human confirms every candidate.** Discovery gives drafts. There is no automatic cutoff for "loose enough" (Strutovskiy p. 3), so pick tolerances by hand and write the choice in the rule's `why`.

### 2.4 Statistics from the archive

The existing rows play the role of "history" in the pipeline papers. A new row is compared to the accepted rows of its table or peer group (Microsoft p. 4, Redyuk p. 3, transfer).

| Method | Threshold or default | Condition | Source |
|---|---|---|---|
| Mean plus or minus C sigma | C = 4 | default in experiments, not required by theory | Fariha p. 5 |
| Mean and std, anomaly check | warn at 3 sigma, error at 4 sigma | example of `OnlineNormal` | Schelter p. 1783 |
| Chebyshev false-positive bound | FPR <= (sigma / beta)^2 | any distribution | Microsoft p. 4 |
| Cantelli, one-sided | FPR <= sigma^2 / (beta^2 + sigma^2) | distance-like metrics | Microsoft p. 5 |
| CLT bound | normal tail past beta / sigma | sum-like metrics (mean, count) | Microsoft p. 5 |
| Target FPR | 0.01 % to 0.1 % | thousands of pipelines | Microsoft p. 1, p. 4 |
| MAD score | abs(v - median) / MAD | per column | Wang p. 10 |
| Perturbation | remove 1 row or 1 % of rows, compare spread before and after | per column | Wang p. 6, p. 10-11 |
| ECDF tail probability | -log(p), cutoff -log(0.01) = 4.61 | tail chosen by the sign of skewness | Li 2022 p. 5-6, Li 2020 p. 4 |
| Gaussian distance grid | 1, 1.3, 1.5, 1.7, 2, 2.3, 2.5, 2.7, 3 | one detector per value | Mahdavi 2019 p. 5-6 |
| Percentile of kNN distances | (1 - contamination) percentile, 1 %, k = 5 | batch level | Redyuk p. 4 |
| Minimum history | 8 past batches | before any detection | Redyuk p. 6 |
| Conformal interval | alpha = 0.1, slack 1 / (n_calibration + 1) | predict one column from others | Romano p. 5, p. 8 |
| Clauses per column | 2 to 3 checks capture most of the benefit | history-based rules | Microsoft p. 17-18 |

Rules for this layer:

- **Screen one column at a time first.** Flag a row that is extreme on one column alone, within its peer group, before any multi-column view (Vinh p. 9). Explanations stay readable up to about 5 columns (Vinh p. 23).
- **Pick the tail by skewness.** Loads, rotations and dimensions are rarely symmetric. Quote the percentile on the side the column is skewed toward, not a two-sided distance (Li 2022 p. 5, transfer).
- **Report position, not a p-value.** Chi-squared flagged 7 of 10 trials where only 0.01 % of the data was changed (Breck p. 7). With enough rows, every field looks "significantly" different (Polyzotis p. 23). Use a percentile and a named comparison value instead (Breck p. 7, transfer).
- **A far value is not a wrong value.** Say "unusual for this peer group", never "invalid" (Huang, Polyzotis p. 22, transfer).
- **Keep per-column scores separate.** ECOD and COPOD compute one score per column, then sum or max them. Keep the per-column part and show one line per column (Li 2022 p. 6, Li 2020 p. 4). A summed score hides the reason and assumes independent columns (Li 2022 p. 2 and p. 12).
- **Watch small groups.** Estimates get noisy when a table is split by peer group, sometimes with more columns than rows (Fariha, transfer). A 100-row group gives a coarse ECDF, so messages should state the group size (Li 2020, transfer). For conformal intervals, below about 30 to 50 calibration rows say "few comparable specimens" instead of a percentage (Romano, transfer).
- **Two-distribution drift metrics do not apply.** L1, KS or Jensen-Shannon between batches assume batches of data. A submission adds a few rows to a stable table (Microsoft, Breck, Redyuk, transfer). Row-level checks against the accepted rows are the right size.

### 2.5 Units

- A silent unit change is a known failure class: age in days turned into hours, values off by 24 to 30 times (Polyzotis p. 21, Microsoft p. 1).
- Explicit unit annotations are the easy case. The hard case in spreadsheets is inferring units from headers, and indirect inference reaches only 49.7 % precision (Williams p. 8). Our dictionary already has a `unit` column, so skip inference (Williams, transfer).
- Count columns with a missing or ambiguous unit as a step 0 task, like the paper's "critical cells" (Williams p. 3, transfer).
- No paper describes a detector based on value / median near a conversion factor (25.4, 6.895, 1000, 4.448). It is our own design. Microsoft's "change of units" error type is the closest, and can be used to test it with injected errors (Microsoft p. 1 and p. 6).

### 2.6 Severity and alert fatigue

- Design alerts on purpose for precision against recall. A good alert is one that gets fixed (Polyzotis p. 22).
- Prefer false negatives to false positives, it builds trust (Schelter p. 1790). First-iteration warnings should be high precision and low recall (Wang p. 2).
- New categorical values are common and usually benign: warning or info, not error (Breck p. 4, p. 9, p. 13). Over 30 days, a new column fired in 10 % of pipelines, a wrong data type in under 1 %, but every type alert was fixed (Breck p. 9). Cheap strict checks rarely fire and are worth keeping. TFDV's automatic mode flagged valid columns just because a new batch had unseen values (Redyuk p. 8-9).
- About half of "almost unique" columns (over 99 % unique) are not real violations (Wang p. 2). Do not flag near-uniqueness as an error.
- Let users silence a lint per type or per input once understood (Hynes p. 5). Transfer: a curator can dismiss one warning for one submission.
- Not every column is worth the same attention. Fixing what is used in production comes first (Polyzotis p. 22). Transfer: columns shown on the dashboard and used by fragility curves matter more.
- Almost every real dataset has at least one lint: only 7 % of 600 Kaggle sets had none (Hynes p. 5-6). Expect hits on the existing tables when rules first run.

Resulting severity policy (transfer, backed by Breck p. 1-2 and p. 5, Polyzotis p. 21-22):

| Severity | Use for | Examples |
|---|---|---|
| error | checks with near-zero false positives on existing data | exact identities, hard orderings, type and nullability, a constant with a cited standard |
| warning | checks that have real exceptions | peer-group range, unit-factor hit, a new categorical value close to a known one |
| info | worth showing, not worth acting on alone | new categorical value, rare shape, value seen once |

### 2.7 Messages, suggestions and explanations

- **Say what, how much and where.** "Country is missing" is weak, "missing from 18 % of examples" is better, "missing where gender = female" is best (Polyzotis p. 21).
- **Name the culprit.** Give the failing value and the broken constraint (Breck p. 3-4), plus the compiled expression (Schelter p. 1785).
- **Warning, fix and a real example.** Every lint prints all three (Hynes p. 2-3).
- **Say why in plain domain words,** for a reader without ML background (Polyzotis p. 18, transfer).
- **Tie every fix to an explicit rule.** Do not pick the "closest" value without a rule behind it (Rekatsinas, transfer).
- **Row-based fix.** When a formula links columns and one input looks wrong, propose the value that satisfies the formula (Baran, vicinity models, transfer: evaluate the `fix` expression).
- **Column-based fix.** For a categorical value close to a known one, suggest the nearest known value by edit distance (Baran, domain models, transfer).
- **Give a confidence.** HoloClean's error rate fell from 0.58 in the lowest confidence bucket to 0.04 in the highest (Rekatsinas p. 11-12). Transfer: "high" for an exact identity, "low" for a peer-group percentile.
- **Point at the column.** Reset one column to its typical value and see whether the row becomes normal: that column is the likely culprit (Fariha, ExTuNe, transfer). A per-column bar with a percentile line reads better than one score (Li 2022 p. 6).
- **Show the comparison rows.** Show which archive rows grounded a suggestion, around 5 rows (Eltabakh p. 3, transfer).

### 2.8 What the LLM does

- LLMs fix errors visible in one row (a negative age, an illogical category) and largely miss errors visible only across rows, such as one year of values shifted or one subgroup moved (Bendinelli p. 1, p. 8). All peer-group statistics and the unit-factor detector stay in code (Bendinelli, transfer).
- Row-level prompts cannot see relations across rows (Zhang p. 19-20). Compute the check outside the model, then give it the result to explain (Zhang, transfer).
- Prompt shape for an explanation: the task, knowledge sentences (the rule's `why`), the row as `column: value` pairs, the question, an output constraint (Zhang p. 3-6). Injecting knowledge helps measurably (Zhang p. 6-7).
- Ground suggestions in similar rows from our own data. A plain LLM reached 5 % accuracy on a private dataset, 94 % with retrieval (Eltabakh p. 4).
- LLM output that writes files fails format checks 7.94 % to 13.53 % of the time (Bendinelli p. 8). Validate any LLM-drafted rule file as strictly as a CSV (transfer).
- An LLM-drafted rule can be accepted automatically only when an independent check confirms it (for example the `pint` unit balance), otherwise a curator reviews it (Williams p. 6-7, transfer). A human approves every `error` rule (Breck p. 5, transfer).
- LLM agents do not discover rules well by exploring data: on the easiest dataset humans improved the score 6.2 % in one hour and LLMs did less (Bendinelli p. 5). Step 0 stays a script, the LLM only drafts rule text (Bendinelli, transfer).

### 2.9 What not to build at our size

| Machinery | Why skip it | Source |
|---|---|---|
| Spark, DynamoDB, incremental metric state | built for billions of rows | Schelter p. 1785-1787 |
| Hydra sampling, FASTDC depth-first search, set cover | brute force takes seconds on hundreds of rows | Bleifuss p. 319-320, Chu p. 1507 |
| Batch-level kNN novelty detection | needs 8+ batches of 45 to 2350 rows | Redyuk p. 5-6 |
| Greedy budgeted rule selection | a curator can pick 2 to 3 checks per column | Microsoft p. 7-8, p. 17 |
| Stationarity tests, differencing | our columns are not time series | Microsoft p. 5 |
| Corpus-based pattern statistics (PMI, likelihood ratio over 100M tables) | no outside corpus of steel tables | Huang p. 8-9, Wang |
| Per-column classifiers with active learning | smallest tested table is 2,376 rows, needs labeled errors per column | Neutatz p. 4, Mahdavi 2019, Mahdavi 2020 |
| Factor graphs and Gibbs sampling | built for million-row repair | Rekatsinas p. 3 |
| Fine-tuning a local LLM | we only explain, never decide | Zhang |
| ML unit inference from headers | we have explicit units | Williams p. 8 |
| Summed multivariate outlier score in production | excluded in iteration one, hides the reason | Li 2022, Li 2020 |
| Public query language across databases | one provider, one backend | Andersen p. 5-6 |

## 3. Where the papers disagree

**Center and spread: mean and sigma, median and MAD, or percentiles.** Fariha and Schelter use mean plus or minus k sigma. Wang uses median and MAD. Li (ECOD, COPOD) and Redyuk use empirical distributions and percentiles. Microsoft keeps mean and sigma but derives the threshold from a false-positive bound. *Resolution:* on small, skewed groups one wrong value moves the mean and sigma a lot, so use median and MAD for the flag (Wang p. 10) and the ECDF percentile for the message (Li 2022). Use the Chebyshev bound to explain what a threshold costs. From Microsoft's formula (this synthesis), 3 sigma fires on at most 11 % of clean rows for any distribution, and 4 sigma on at most 6.25 %. This is why 4 is a sane default for a warning when the distribution is unknown.

**Threshold value.** Fariha uses 4. Schelter warns at 3 and errors at 4. Raha tries a grid from 1 to 3. Microsoft targets 0.01 % to 0.1 % false positives. *Resolution:* the grid and the tiny target come from settings with labels or thousands of pipelines. Use one warning threshold near 4 (MAD-scaled) and never make a statistical check an error, since the error level is reserved for exact rules (2.6). Tune once on the existing tables in step 0 by counting how many accepted rows would fire.

**Restriction threshold.** Chu uses 30 % shared values for joinable columns (p. 1502), Bleifuss 20 % (p. 319). *Resolution:* use the dictionary `group` and `unit` instead.

**Hand-written rules against learned detectors.** Raha, Baran, ED2 and HoloClean learn detectors or repairs from about 20 labeled tuples or under 1 % of cells, and report large F1 gains over rule tools (Mahdavi 2019 p. 10, Neutatz p. 1, Rekatsinas p. 2). Redyuk finds that hand-tuned Deequ rules still beat the automatic method (100 % and 92 % against 95 % ROC AUC, p. 8), and Wang says complex constraints need human semantics (p. 4, p. 9). *Resolution:* the learned systems were tested on thousands to millions of rows with many repeated errors. Our tables are small, mostly clean, and our cross-column relations are known physics. Write rules by hand, use learned ideas only as features (metadata, value counts).

**One combined score or separate flags.** HoloClean combines rule signals and statistics into one probability (Rekatsinas). ECOD sums per-column scores, COPOD takes the max. Fariha sums weighted violations. *Resolution:* we have no ground truth to learn weights from (Rekatsinas, transfer), and a contributor needs one reason per issue. Keep rules and statistics as separate layers with separate severities, and show per-column contributions.

**Global or per peer group.** Fariha, Chu (C-FASTDC) and the proposal all favor bounds per categorical value. Fariha also warns that per-group splits get noisy on small data and advises whole-table columns unless a group has enough rows. *Resolution:* per group when the group is large enough, whole table otherwise, and always print the group and its size in the message. No paper gives a minimum group size for row checks. Uni-Detect's smallest row bucket is 0 to 20 (Wang p. 10-12), the current validator uses 20, keep 20 as the starting value and revisit in step 0.

**Is an unseen value an error.** Huang and ED2 flag rare shapes and rare values. Breck, Redyuk and Polyzotis show unseen categorical values are usually valid. *Resolution:* both hold: a rare shape ("W610X195" next to "W610x195") is a likely typo, a new well-formed value (a new steel grade) is likely valid. Flag both, as info or warning, with the nearest known value as a suggestion.

**LLMs for data quality.** Zhang shows a tuned model explains decisions better than GPT-3.5 (46 % and 73 % win rates, p. 17). Bendinelli shows LLM agents miss multi-row errors and do not reach clean-data quality (p. 8). Eltabakh shows plain LLMs fail on private data. *Resolution:* no real conflict, they test different jobs. Code detects, the LLM drafts rules and explains issues, with the rule's `why` and similar rows in the prompt.

**Batch history or static table.** Schelter (`OnlineNormal`), Microsoft and Redyuk compare a new batch to past batches. Our contributions are small additions to a table without a time axis. *Resolution:* treat the accepted rows as the history, compare one row to them. Keep per-version metric history as a later addition (Schelter p. 1791-1792, transfer), not iteration one.

## 4. Mapped to RESSLab-Hub

### 4.1 The current validator

| Today | Verdict | Source |
|---|---|---|
| Headers, types, nullability, dates, booleans | fits, this is the schema layer every paper starts with | Breck p. 4, Polyzotis p. 20 |
| Id form and duplicate ids (DB and data repo) | fits (`isUnique`) | Schelter p. 1783 |
| Missing header is an error, unexpected header a warning | fits, new columns are common and benign | Breck p. 9 |
| One range warning, one full span outside the global min/max, 20+ rows | watch: global, not per group, no position in the message, span-based so it misses values inside the span but far from the group | Fariha p. 6, Bendinelli p. 5-8 (subgroup shift missed by a global check) |
| Range stats computed on every request | watch, a cached profile per data version is enough | Schelter p. 1785 (transfer) |
| Issue = (row, column, value, message) | missing: code, severity, suggestion, why, confidence, comparison values | Breck p. 3-4, Hynes p. 2-3, Polyzotis p. 21 |
| No cross-column rules | missing, and our identities hold within 1 % to 3 % on the columns table, so they will not be noisy | Chu, Schelter p. 1784 |
| No format hygiene beyond types | missing: trailing spaces, case variants, rare shapes | Hynes p. 4, Huang, Strutovskiy p. 3 |
| No info level | missing | 2.6 above |

### 4.2 Step 0: the discovery spike

Fits: pairwise identities and orderings by brute force (Chu, Bleifuss), near-constants, PCA conformance constraints (Fariha), section name to dimensions by groupby (Strutovskiy), string hygiene by shapes and edit distance (Huang, Strutovskiy).

Add from the papers:

- restrict candidate pairs by dictionary `group` and `unit` (Bleifuss p. 319);
- prune implied rules and rank by coverage and succinctness (Chu p. 1508);
- run Deequ-style profiling heuristics on each column to draft completeness, range and domain rules (Schelter p. 1788);
- count columns with missing or ambiguous units (Williams p. 3);
- for each candidate range rule, count how many accepted rows would fire, per severity, to size alert volume before shipping (Polyzotis p. 22, transfer);
- inject errors (nulls, factor 25.4, 6.895 or 1000, swapped columns, typos) and record which candidates catch them (Microsoft p. 6).

Watch: the 5 % on 95 % of rows keep rule in the issue is a hand-picked tolerance, as the papers expect (Strutovskiy p. 3). Record the observed maximum deviation so the lab can pick the final tolerance.

### 4.3 Layer 1: the rules file

Fits: check, severity, message, fix and why match Deequ's Check and Constraint (Schelter p. 1783) and the lint pattern (Hynes p. 2-3). `simpleeval` on one row matches one-row DCs (Chu).

Add from the papers:

- a `source` tag on each rule: discovered, standard, curator (Andersen p. 3, transfer);
- a `confidence` or a rule kind that implies it: exact identity is high, statistical is low (Rekatsinas p. 11-12, transfer);
- a unit balance check of each expression against the dictionary with `pint`, as a lint of the YAML itself (Williams, transfer);
- a per-rule `silence` or dismiss path for curators (Hynes p. 5);
- validate the whole existing table against a new rule before merge, like Breck's fuzz tests (Breck p. 7-8, transfer).

Watch: rule counts. Two to three checks per column already get most of the benefit (Microsoft p. 17). An unrestricted discovery output would flood the file (Bleifuss p. 320).

### 4.4 Layer 2: statistics per peer group

Fits: per-group ranges (Fariha p. 6, Chu C-FASTDC), percentile messages (Li 2022, Wang p. 10-12), computed once per data version (Schelter, transfer).

Add from the papers:

- MAD score for the flag, ECDF percentile for the message, tail picked by skewness (Wang p. 10, Li 2022 p. 5);
- group size in every message, and a fallback wording for small groups (Romano, Li 2020, transfer);
- a "most extreme value" test by removal: if removing the value shrinks the group MAD a lot, the warning is stronger (Wang p. 10-11, transfer);
- a rare categorical value check (value count 1 or 2 in a repeating column) and nearest known value (Neutatz p. 4, Baran);
- trivial single-column outliers first, multi-column explanations later (Vinh p. 9).

Watch: the unit-factor detector has no paper behind it. Test it with injected factor errors in step 0 and count false hits on the existing data. Watch skewed and two-clump columns: ECDF methods are not built for multimodal ranges (Li 2022 p. 12), and a section family can mix very different sizes.

Missing, for later: conformal intervals to predict one column from others (Romano), density Z-score to find the 2 or 3 columns that make a row odd (Vinh p. 13, p. 19), per-version metric history (Schelter p. 1791-1792).

### 4.5 Layer 3 and the LLM helper

Code, severity, suggestion and why fit the lint and culprit patterns. Add the affected share, comparison values with group size, a confidence, the failed expression and the ids of rows behind a suggestion (2.7). "Drafts and explains, never decides" is backed by every LLM paper read (2.8).

## 5. What the papers do not cover

- **Small tables.** No paper tests row checks on tables of a few hundred rows. Every threshold and minimum size in sections 2.4 and 3 for our scale is a transfer. Step 0 is where to measure them.
- **The unit-factor detector.** No paper proposes value / median near a conversion factor. Microsoft and Polyzotis only name the failure class.
- **wwPDB-style percentile reports.** The digests support percentile messages (ECOD, Uni-Detect, Breck) but none describes the wwPDB report itself. Gore et al. 2017 (wwPDB validation) was not available and is the paper to read.
- **Explaining a flagged row with two plots.** LookOut (Gupta et al. 2018) was not available. Vinh covers the column-subset idea only.
- **LLMs drafting rules from documentation.** The "Quality by Prompt" chapter (Springer) was not available. Zhang covers explanation, not drafting.
- **Feature attribution with SHAP for autoencoder outliers.** Antwarg et al. 2021 was not available, and it is out of iteration one anyway.
- **Structural steel domain knowledge.** No paper covers section catalogs, steel grade vocabularies, or test protocols. The `why` texts and references must come from the lab and the standards (AISC 360, EN 1993).
- **Rule file format.** No paper specifies a YAML rule language with severity, fix and why. Deequ is a Scala API, Andersen a query grammar. Our format is our own design.
- **Curator workflow on pull requests.** The papers assume data engineers on pipelines, not curators reviewing contributions.
- **A naming error in the brief.** The Williams 2020 paper was listed as "XeLda". XeLda is an older tool (Antoniu et al. 2004) that checks user-given unit annotations. The issue #366 text reuses this label (Williams p. 2).

## 6. Checklist

Run these against a rule file, a validator change or a design note.

1. Does every rule have an id, severity, message and a why with a reference or its source?
2. Is every `error` rule an exact identity, a hard ordering, a type or nullability check, or a constant backed by a standard, with zero hits on the accepted rows?
3. Is every statistical check a warning or info, never an error?
4. Do both sides of each identity reduce to the same dimension given the dictionary units?
5. Was each new rule run on the full existing table, and is the number of hits known?
6. Is each cross-column candidate restricted to columns of the same group or compatible units?
7. Were rules implied by other kept rules removed?
8. Does each statistical message give the value, the group name, the group size and a position (percentile or comparison values), without a p-value?
9. Does the flag use median and MAD or an ECDF, not mean and sigma alone, on small or skewed groups?
10. Does the check fall back to the whole table, and say so, when the peer group has fewer than 20 rows?
11. Is a new categorical value treated as info or warning, with the nearest known value suggested?
12. Does every suggestion come from an explicit expression or code-computed statistics, never from a number the LLM chose?
13. Does each issue carry a code, a severity, a suggestion when one exists, and a why?
14. Can a curator dismiss a warning for one submission without editing the rule?
15. Is the LLM only drafting rule text or explaining a finished check, with the rule's why and the group stats in its prompt?
16. Is any LLM-written rule file validated by the same lint as a hand-written one before review?
17. Was the unit-factor detector tested on injected factor errors and on the existing data for false hits?
18. Did the design avoid machinery built for large data (sampling search, learned classifiers, batch drift tests) where brute force or a groupby is enough?
