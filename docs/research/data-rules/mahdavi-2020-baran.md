# Baran: effective error correction via a unified context representation and transfer learning

Mahdavi and Abedjan, 2020, PVLDB (VLDB Endowment, Vol. 13, No. 11). System paper (algorithm plus a full data cleaning system).

## In one paragraph

Baran fixes data errors already flagged by an upstream detector, in two steps. First, several "error corrector models" each propose correction candidates, using one of three contexts: the erroneous value itself, the other clean values in the same row (vicinity), or the other clean values in the same column (domain). This step aims for high recall, proposing many candidates, even bad ones. Second, Baran turns each (error, candidate) pair into a feature vector (one probability per model) and trains one binary classifier per column on a small set of user-labeled tuples (10 to 20), which decides which candidate, if any, is the real fix. Baran also picks which tuple to ask the user to label next, favoring tuples covering error types and columns still under-labeled. Value-based models can also be pretrained on an external source of value corrections (Wikipedia revisions), adding candidates before any label is given. On 7 datasets, Baran beats 4 baseline systems in F1, with only 20 labeled tuples.

## Core principles

1. **Split candidate generation from candidate selection.** Generate many candidates first, even wrong ones, to raise the recall ceiling; then pick the right one with a classifier, to keep precision high (p. 1, p. 4).
2. **Three contexts cover most fixable errors.** Value (the string itself), vicinity (other columns, same row), and domain (other values, same column) are independent candidate sources, run in parallel (p. 2-3).
3. **Every model is the same simple formula.** Each model is a conditional probability: count(correction seen with this context) / count(context seen), easy to update one label at a time (p. 4).
4. **Value-based models combine an encoder and an edit operator.** Two encoders (identity; Unicode-category, abstracts each character to its class) times four operators (remove, add, replace, swap whole value) give 8 value-based models (p. 4-5).
5. **Vicinity-based models are one-attribute functional dependencies.** For every ordered pair of columns, a model learns how often one column's value determines the other's (p. 5-6).
6. **Domain-based models use frequency inside the same column.** One model per column; a candidate's probability is its frequency among clean values seen so far (p. 6).
7. **Binary, not multiclass, classification avoids sparse features.** For each (error, candidate) pair, ask: is this the real fix, yes or no. The feature vector is one probability per model, always the same size (p. 6-7).
8. **One user label yields many training points.** One positive example plus many negatives (every other candidate), which makes the classifier conservative and keeps precision high (p. 7).
9. **One classifier per column.** Error types and useful contexts differ by column; vicinity features still carry signals from other columns (p. 7).
10. **Tuple sampling targets under-labeled columns.** The next tuple maximizes a score rewarding more unfixed errors, under-fixed columns, and error values frequent among unfixed ones (p. 5-6).
11. **Pretraining widens the candidate pool.** Only value-based models are schema independent enough to pretrain offline; vicinity- and domain-based models would need a same-schema source, not used here (p. 8-9).
12. **More context in the data means better results.** Datasets with duplicate rows and correlated columns (Hospital, Flights) reach the highest F1; datasets dominated by missing values (Address, IT) are limited, since no context can propose a fill-in value on its own (p. 8-9).

## The error correction engine (method detail)

Input: a dirty table with detected errors E and a labeling budget (default 20 tuples).

1. Generate candidates. Every model looks at its own context for an error and proposes candidates with a probability, using the count-ratio formula.
2. Build features. For every (error, candidate) pair, build a fixed-size vector: one entry per model, its probability for that pair (0 if not proposed).
3. Sample and label. Pick the next tuple with the scoring formula above; the user types the correct value for each error in it.
4. Update models. Every model whose context matches the labeled error updates its counts, O(1) per model per label.
5. Train and apply classifiers. Train one binary classifier per column, label 1 for the real correction, label 0 for every other candidate. Apply it to every unlabeled error; keep the highest-confidence candidate labeled 1, or leave unfixed if none is.
6. Repeat 3-5 until the budget is spent; keep the last iteration's predictions as output.

Reimplementable in Python: count-ratio models are dictionaries of counters; the classifier is any scikit-learn binary classifier (AdaBoost by default).

## Pretraining (transfer learning)

Only value-based models are pretrained, since they need no fixed schema; vicinity- and domain-based models are schema-dependent, not pretrained here (p. 8-9). Steps: take an external revision history (Wikipedia page revisions), split text into segments, align segments across consecutive revisions with a text-diff, discard pairs with a null value, and feed the (before, after) pairs into the value-based model updates used online. Pretraining does not change the classifier, it only widens the candidate pool.

## Rules of thumb

| Quantity | Value | Condition | Page |
|---|---|---|---|
| Default labeling budget | 20 labeled tuples | Baran default setting | p. 8 |
| Labels needed elsewhere | 1% to 10% of rows | prior approaches, vs. Baran's 10-20 tuples | p. 6 |
| Value-based model count | 8 = 2 encoders x 4 operators | identity/Unicode, remove/add/replace/swap | p. 5 |
| Vicinity-based model count | \|A\|x(\|A\|-1) | one per ordered column pair | p. 5 |
| Domain-based model count | \|A\| | one per column | p. 6 |
| Baran F1, no pretraining | 0.43 to 1.00 across 7 datasets | best on Flights (1.00), worst on Address (0.43) | p. 9-10 |
| Baran F1, with transfer learning | up to +0.04 vs. no pretraining | biggest gains on Hospital and Tax | p. 9-10 |
| Labels for same F1, Hospital/Rayyan/Tax | 13 / 18 / 19 instead of 20 | pretraining adds 455390 / 77569 / 7134254 candidates | p. 9 |
| Default classifier | AdaBoost | less prone to overfitting than alternatives tested | p. 8, p. 11 |
| Classifier choice impact | minor | Decision Tree, Gradient Boosting, SGD close, except Address | p. 11 |
| Removing vicinity models | sharp F1 drop | Hospital, Flights (high inter-column dependency) | p. 10 |
| Removing vicinity or domain models | F1 rises | Tax (large table, huge search space) | p. 10 |

## Vocabulary

- **Error corrector model**: proposes correction candidates for an error, using one of the three contexts, as a conditional probability.
- **Value / vicinity / domain context**: the erroneous value itself; other clean values in the same row; other clean values in the same column.
- **Identity encoder / Unicode encoder**: keeps a value's original characters, vs. replaces each character with its Unicode category to generalize syntactic patterns.
- **Remover / adder / replacer / swapper operator**: the four string edits a value-based model learns.
- **Correction candidate**: any value a model proposes as a possible fix.
- **Feature vector v(e, c)**: for one (error, candidate) pair, the probability each model assigns.
- **Tuple sampling**: choosing which row to ask the user to label next.
- **Transfer learning (here)**: pretraining value-based models on an external source before the online phase.
- **Configuration-free**: no upfront rules or parameters, only a few labeled examples.

## Examples worth remembering

**The toy Name/Address table.** A 4-row table with errors like "H" for "Hana" and "9th Str" for "9th Street" shows why older systems fail: "9th Street" appears nowhere else (no redundancy to copy), and the one candidate functional dependency (Name determines Address) fails for two rows. Baran learns an edit pattern from a similar fix elsewhere ("5th Str" to "5th Street") and applies it (p. 3, p. 5).

**Diff checking "Chris Edward NoLan" into "Christopher Nolan".** One label yields three edit operators: add "topher" after "Chris", remove "Edward ", replace "L" with "l" (p. 5).

**Vicinity fix for "Gandom".** Once the model learns Name = "Gandom" always pairs with Address = "7th Street", any future error in Address next to "Gandom" gets that fix with probability 1.0 (p. 5).

**Pretraining recovers "Chris" to "Christopher".** With 2 labels the classifier has no candidate for "Chris". After pretraining on a Wikipedia edit adding "topher" to "Chris" elsewhere, "Christopher" becomes a candidate with a high feature value and gets picked, with no further label (p. 9).

**Ablation on Tax.** Removing vicinity- or domain-based models improves F1 on this 200000-row dataset: those models propose thousands of candidates, slowing convergence under a fixed 20-label budget (p. 10).

## Quotes

- "Error detection is a binary classification task... However, the class space for error correction is infinite." (p. 2)
- "Our error corrector models are designed to propose as many potential corrections as possible in the first place." (p. 4)
- "When a feature vector contains mostly close-to-one probabilities... it is more likely that the correction candidate is the actual correction." (p. 7)
- "This highly imbalanced training set... makes our classifier conservative in predicting a correction... That is why the precision of our system is generally high." (p. 7)
- "In Baran, the number of labels scales with the number of data error types of dataset (i.e., 10-20 tuples)." (p. 6)

## Applying it to RESSLab-Hub

- **Do not port the classifier pipeline as-is.** Baran needs many (error, candidate) pairs per column and fits tables with duplicate rows or strong redundancy. Our tables are small, with mostly unique specimens and near-exact known formulas, so there is rarely more than one plausible fix; a learned classifier is more than needed. My own transfer judgment, not the paper's claim.
- **Reuse the vicinity-based idea for the `suggestion` field, not the ML.** For a rule like h_over_t_cw = h_c / t_cw, when one input looks trustworthy and the other wrong, propose the value that satisfies the formula, with the formula as the "why" (principle 5), using simpleeval instead of learned functional dependencies.
- **Reuse the domain-based idea as a soft suggestion, not a hard fix.** For categorical columns (steel grade, section name), when a value is close to a known value but not exact, suggest the nearest known one (principle 6), with edit distance instead of a learned frequency model.
- **Borrow the value-based edit-operator framing for format issues.** For string columns with a known pattern, describe the transform in words ("remove trailing space") like Baran's operators (p. 4-5), for clear "why" text, not a learned model.
- **Do not adopt pretraining from an external corpus.** No Wikipedia-scale source of steel corrections exists; the closest analogue, the data repo's own history of accepted fixes, is small and already per-schema, so this collapses to principle 6 applied to history. My own read, the paper does not cover a source this small.
- **Reuse the confidence idea for the issue schema.** Baran's per-candidate probability (p. 6-7) needs no training here, but attaching a confidence to each suggestion fits the schema (code, severity, suggestion, why) from issue #366.
- **Tuple sampling and per-column classifiers do not fit us.** Curators review every row by hand, so principles 9 and 10 do not transfer.

## Limits and caveats

- The paper assumes error detection is already done and mostly correct; it studies imperfect detection briefly (Section 6.6) but our validator does detection separately, so that part matters less here.
- Results depend on strong redundancy or a same-schema corpus to pretrain on; the paper does not test tables as small and unique as ours, so its F1 numbers are not predictive here.
- Read in full: the method (Sections 3-5) and the experiment section (Section 6); skimmed Related Work and Conclusion; did not read the reference list beyond identifying baselines.
- Formulas in the source markdown were garbled by conversion; every formula is described in words instead of guessed.
