# The techniques behind #366, explained simply

A plain-words guide to the nine techniques picked from the paper digests in this folder. Each one says what problem it solves, how it works, and gives an example from another database or from our own tables. The citations and the full argument are in [synthesis.md](synthesis.md), sections 2.3 and 2.4.

| Technique | From | Use in #366 |
|---|---|---|
| Median and MAD instead of mean and std | ED2, Uni-Detect, Auto-Validate | Layer 2 ranges, per peer group with 20+ rows |
| ECDF percentile in the message, tail picked by skewness | ECOD, COPOD | The "8th percentile of A992 columns" message, no p-value |
| Chebyshev bound for the threshold | Deequ, Auto-Validate | Warning near 4 spreads, never an error |
| Denial constraints | Chu 2013, Hydra | The spike: pairwise and triple identity search |
| Conformance constraints (PCA) | Fariha 2021 | The spike: linear invariants the pairwise search misses |
| Approximate functional dependencies | Desbordante | The spike: section name to nominal dimensions |
| Unit inference from ratios | Williams 2020 | The unit-factor detector |
| Retrieval of similar rows | RetClean | Give the LLM 5 peer rows when it explains an issue |
| Schema-driven fuzz rows | Breck 2019 | Sanity-test a new rule file before merge |

## 1. Median and MAD instead of mean and standard deviation

**The problem.** To know if a value is unusual, you compare it to the "typical" value and the "typical" spread. The mean and standard deviation are the usual choice, but one bad value moves them a lot. If someone typed a yield strength in psi (50,000 instead of 345 MPa), the mean of the column jumps and the standard deviation explodes. Now the bad value looks normal, and good values look odd.

**The fix.** Use the median (the middle value when sorted) as the center, and the MAD (median of the distances to the median) as the spread. One wrong value cannot move the middle of a sorted list. In practice you compute `score = |x - median| / (1.4826 * MAD)` (the constant makes it comparable to a standard deviation on normal data).

**Example.** Columns table, `f_ymf` (measured yield strength), 153 rows. Median about 380 MPa, MAD about 30. A submission with 51 (a ksi value) gets a score of (380 - 51) / 44 ≈ 7.5. Very far. A submission with 51,000 (psi) gets 1,150. Both flagged, and the median did not move.

## 2. ECDF percentile in the message

**The problem.** "Score 7.5" means nothing to a contributor. "Outside 3 standard deviations" is not much better.

**The fix.** ECDF stands for empirical cumulative distribution function. It is just the rank of a value in the sorted archive column, as a percentage: "your value is lower than 97 % of what we have". Every person understands that. You compute it by counting how many archive values are below the new one.

**The tail.** Some columns are skewed: ductility, for example, has most values small and a long tail of large ones. A large value there is less surprising than a small one. So you pick which tail to report from the skewness of the column (a one-line computation). ECOD does this to avoid flagging the normal long tail.

**Example (wwPDB, the protein structure database).** Every deposited structure gets a report with sliders: "clashscore: 12, better than 45 % of structures, better than 60 % of structures at the same resolution". Two percentiles, whole archive and peer group. The translation for us: "th_80 = 0.02 rad is at the 4th percentile of W-section columns (153 rows)".

## 3. Chebyshev bound for the threshold

**The problem.** Where do you put the warning line? At 2 standard deviations? 3? 4? A wrong choice means spam or silence.

**The fix.** Chebyshev's inequality is an old maths result: whatever the shape of the data, at most 1/k² of values are more than k spreads away from the center. So at k = 3, at most 11 % of clean rows fire, at k = 4, at most 6 %. On normal-looking data the real numbers are far smaller (0.3 % and 0.006 %). It is a guaranteed worst case, no assumption about the shape.

**Example (Amazon Deequ, and Microsoft's Auto-Validate).** Both let the user say "alert if today's value is more than k spreads from the history", and Auto-Validate picks k by the false alarm budget: "I accept 1 alert in 100 clean runs, so k ≥ 10". For us: warning near k = 4 on the MAD score, never an error.

## 4. Denial constraints

**The problem.** We know some rules hold in the data (`f_u > f_y`, `h_over_t_cw = h_c / t_cw`), but writing them by hand for 9 tables and 300 columns is long, and we would miss some.

**The fix.** A denial constraint is a rule of the form "no two rows (or no single row) can satisfy this combination". The discovery algorithms (FASTDC by Chu, Hydra by Bleifuss) try every pair of columns with every operator (`<`, `>`, `=`, `≠`) and keep the ones that no row breaks. Rows first, rules after.

**Example.** On the columns table, a search over pairs found `th_80 <= th_50 <= th_20` (rotation at 80 % of peak load happens before rotation at 50 %) with zero violations on 153 rows. Nobody wrote it, the data says it. The spike does the same with three columns and a tolerance: `c ≈ a / b` within 5 % on 95 % of rows. That is how `a_cn ≈ 2 b t_f + (d - 2 t_f) t_w` showed up, with 10 rows off by more than 5 % (fillets, or an error).

## 5. Conformance constraints (PCA)

**The problem.** Pairwise search finds `c = a / b`. It does not find `a - 2b - 3c + d ≈ 0`, a combination of four columns.

**The fix.** PCA (principal component analysis) takes all numeric columns and finds the directions in which the data varies. The interesting ones are the directions where it does *not* vary: a combination of columns that is nearly constant on every row. Fariha's paper calls these conformance constraints. A new row whose combination is far from the constant is not like the others, and the message can name the columns with the biggest weights.

**Example (Fariha's paper).** On an airline dataset, PCA found `arrival_time - departure_time - flight_duration ≈ 0` without anyone writing it. Rows breaking it had a wrong time zone. On our columns table it would find the area identity and `p_yn = a_cn * f_yn` in one pass, plus any we have not thought of.

## 6. Approximate functional dependencies

**The problem.** Does the section name (`W610x217`) determine the nominal dimensions (`d`, `b_f`, `t_f`, `t_w`)? If yes, we can check them against a catalog instead of asking for them. If no (mixed catalogs, built-up sections), a lookup rule would spam.

**The fix.** A functional dependency `A → B` means "same A, same B" on every row. An *approximate* FD allows a few exceptions and reports the share. `desbordante` computes these over a CSV in seconds.

**Example (Desbordante demo).** On a medical dataset, `patient_id → birth_date` held on 99.8 % of rows. The 0.2 % were typos in the birth date. For us: run `section_c → d, b_f, t_f, t_w`. If it holds on 98 % of rows, the 2 % are errors or catalog differences, and a catalog lookup (`steelpy`, `eurocodepy`) is worth a rule.

## 7. Unit inference from ratios

**The problem.** The most common real error in engineering data is a unit mix: inches instead of mm, ksi instead of MPa, kN instead of N. The value is a valid number, so a type check passes.

**The fix.** Williams' paper (Microsoft, spreadsheets) reads the header and the values and infers the unit of each cell, then flags cells whose unit does not match the column. We don't need the inference: the dictionary already says the unit. We only need the detector: divide the new value by the group median and see if the ratio is close to a known factor (25.4, 1/25.4, 6.895, 1000, 4.448).

**Example.** Median `f_ymf` = 380 MPa. Submitted value 55. Ratio 380 / 55 = 6.9 ≈ 6.895. Message: "f_ymf = 55 looks like ksi; in MPa it would be 379". That is the fix the LLM wrote by hand in the #272 spike, but now it is 5 lines of deterministic code.

## 8. Retrieval of similar rows for a suggestion

**The problem.** When you ask an LLM "is this value wrong, and what should it be?", it guesses from general knowledge. It does not know our tables.

**The fix.** RetClean's idea: before asking, fetch the rows most similar to the one being checked (same steel grade, same section family, closest dimensions), and put them in the prompt. The model then explains "the 5 closest A992 W-section columns have f_ymf between 345 and 400" and suggests a value from them. The suggestion is grounded, and the row ids can be shown to the contributor so they can check.

**Example (RetClean).** Cleaning a table of companies, the model alone got the CEO name wrong often. Given 5 similar rows from a data lake, it copied the right one and cited it. For us: the peer rows come from the archive, the prompt gets them as `column: value` pairs, and the answer names their ids.

## 9. Schema-driven fuzz rows

**The problem.** When someone adds a rule to the YAML file, how do we know it is right and does not fire on good data?

**The fix.** Breck's team generates fake rows from the schema (random values inside each column's allowed range) and runs the code on them. If the training code crashes, it assumed something the schema did not say. Our version is simpler: run every new rule on the whole existing table in CI. A rule that fires on 30 real rows is either wrong or found 30 errors. Either way, a human looks before merge. Plus a few random rows built from the dictionary ranges to catch a rule that never fires at all (a typo in a column name).

**Example (Google).** Training code did `log(feature)`, the schema said "float", nothing said "positive". A fuzzed row with 0 crashed it, before serving data did. For us: a rule written as `h_over_t_cw = h_c / t_cw` with a typo in `t_cw` never fires, and a fuzz row with a broken ratio shows it.

## Tools

- **`simpleeval`**: evaluate the `check` expression of a YAML rule. Small, sandboxed, no engine.
- **`pint`**: lint the units in a rule (both sides of `p_yn = a_cn * f_yn` must balance). A one-time check on the rules file, not at runtime.
- **`desbordante`** (pip): approximate FD discovery, pandas-friendly. Spike only.
- **`pyod`** (ECOD, COPOD): parameter-free, per-column contribution. Not for now, but the ECDF idea is what Layer 2 uses by hand.
- **numpy / pandas**: the PCA conformance pass is 30 lines, no library needed.

## What not to build at our size

Deequ and Great Expectations (need Spark or a warehouse), drift and skew between batches (we have PRs, not daily batches), HoloClean, Baran and Raha (learned repair, need labels and thousands of rows), ML novelty detectors (Mahalanobis, isolation forest) until the rules and per-group ranges are in use and we see what slips through.
