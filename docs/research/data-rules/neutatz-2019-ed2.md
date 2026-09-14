# ED2: Two-stage active learning for error detection

Felix Neutatz, Mohammad Mahdavi, Ziawasch Abedjan, 2019, technical report extending a peer-reviewed paper; algorithm and system paper with an evaluation.

## In one paragraph

ED2 finds errors in a table by training one classifier per column and asking the user to label a small number of cells as correct or wrong. It picks which column to label next (the least certain model), then which cells inside that column to label (a diverse batch chosen by query-by-committee). Each cell becomes a feature vector: character n-grams, metadata (occurrence count, string length, data type, numeric value), a word-embedding of cell values across the row, and the current error probability of the other columns in the same row. A classifier (XGBoost works best) trains per column and retrains after each batch of labels. On four real datasets, ED2 reaches the best F1-score of all methods tested using less than 1% of all cells as labels. The claim: two-stage active learning plus multi-column features let a small number of labels find both syntactic errors (bad format) and semantic errors (wrong value, right format), with no rule written by the user.

## Core principles

1. **Detect errors as classification, not rules.** The user labels cells as erroneous or correct and a model learns the pattern, instead of writing rules or outlier thresholds. Needs only domain knowledge (p. 1).
2. **One classifier per column.** A single multi-label classifier over the whole table is not practical since not all cells of a row are wrong together; ED2 trains one classifier per column with its own training set (p. 2).
3. **Two-dimensional active learning.** First pick the column to label, then pick the cells inside it. Standard active learning only does the second step (p. 3).
4. **Min Certainty column selection wins.** Of three strategies tested, the column with the lowest average prediction confidence gives the fastest, most stable convergence across all datasets (p. 3, 8).
5. **Character-level features beat word-level.** Bag-of-character-n-grams (n=1) finds format errors (a missing "$", a truncated string) that a word-level bag-of-words misses (p. 4, 9).
6. **Metadata features alone are surprisingly strong.** Occurrence count, string length, data type, and numeric value, used alone, already detect a wide range of errors (p. 9).
7. **Cross-column features catch what single-column rules cannot.** Concatenating every column's features into each classifier lets it learn correlations like "if Position contains 'senior' then Salary must be above some value", with no rule written by hand (p. 4-5).
8. **Error correlation features help when errors are rare.** Feeding each classifier the predicted error probability of the other columns in the row helps most when the error fraction is small (p. 5).
9. **Start from frequency-based outliers, not random cells.** ED2 ranks values by frequency and samples both ends: rare (candidate errors) and frequent (candidate correct) (p. 4).
10. **XGBoost is the most stable model choice.** It beats Naive Bayes and linear SVM since it tolerates irrelevant features; Naive Bayes suffers from correlations violating its independence assumption (p. 8-9).
11. **Less than 1% of cells labeled beats state-of-the-art tools.** Across all four datasets, ED2's F1-score beats or matches six other methods, with far fewer labeled cells (p. 6-7).
12. **Explanations come from a second, simple model.** ED2 trains a decision tree to explain a prediction as a decision path, and the user can veto a feature (p. 5).

## The two-stage active learning loop

The loop (Figure 1, p. 2-3): extract features for every cell; give the user an initial batch per column, picked by the frequency-based outlier ranker (rare and frequent values), and get labels; train one classifier per column, tuning by grid search with cross-validation; apply each classifier to every cell, getting a per-cell error probability; feed those probabilities into the other columns' feature vectors; **Column Selector** picks the column with lowest average prediction certainty; **Batch Generator** runs query-by-committee inside that column (an ensemble votes on which unlabeled cells it disagrees on most) and picks the most disputed, diverse cells; show the user the full row for each cell, collect labels, retrain, repeat until the user stops.

Batch size was k=10, and did not significantly change performance (p. 6). Reimplementable on a small table: featurize columns, fit one classifier per column, rank columns by mean predicted-probability margin from 0.5 as a stand-in for "certainty", and inside the chosen column pick the cells an ensemble disagrees on most.

## Per-cell features

Four feature groups, concatenated per cell (Section 4, p. 3-5):

- **Character n-grams**: TF-IDF-weighted counts of character sequences of length n in the cell, per column. n=1 already performs well; higher n did not help much.
- **Metadata**: value occurrence count, string length, data type, and a numeric representation of the value.
- **Cell value correlation**: a Word2vec-style embedding (100 dimensions), treating each row as a "document" and each cell value as a "word", so co-occurring values end up close together. Varies a lot by dataset, depending on data redundancy.
- **Error correlation**: for column j, the current predicted error probability of every other column k in the same row, from the last trained model for k. Only available after the first prediction round.

Every column's features are also concatenated together, so a classifier sees the metadata and n-gram features of the other columns too, not just their error probabilities. This is how the paper's salary rule gets learned automatically.

## Rules of thumb

| Quantity | Value | Condition | Page |
|---|---|---|---|
| Label budget to beat state of the art | < 1% of all cells | avg. across 4 datasets | p. 1, 6 |
| Minimum labels to start training | 2 erroneous + 2 correct per column | before active learning starts | p. 4 |
| Batch size k | 10 | default, did not matter much | p. 6 |
| Word2vec embedding dims | 100 | cell value correlation features | p. 6 |
| Runtime, largest dataset | 12 min machine time | Address, 94,306 rows, 12 cols | p. 7 |
| Best F1, Flights | 0.87 (P 0.84, R 0.90) | 2,376 rows, 35% errors | p. 6 |
| Best F1, Movies | 0.75 (P 0.89, R 0.67) | 7,390 rows, 1% errors | p. 6 |
| Best F1, Beers | 1.00 (P 1.00, R 1.00) | 2,410 rows, 8% errors | p. 6 |
| Best F1, Address | 0.97 (P 0.99, R 0.96) | 94,306 rows, 14% errors | p. 6 |
| Repeats per experiment | 10 runs, mean +/- std | ED2 is not deterministic | p. 7 |

Column selection ranking (qualitative): Min Certainty > Round-Robin > Max Prediction Change ~ Max Error > Random (p. 8).

## Vocabulary

- **Error detection**: finding cells whose value differs from the (unknown) ground-truth value.
- **Syntactic error**: a value outside the valid format or domain of its column ("Londonnn").
- **Semantic error**: a value syntactically valid but wrong in context ("London" as capital of the wrong country).
- **Active learning**: a training loop where the model asks for the labels it needs most, instead of a random sample.
- **Query-by-committee**: several models vote on unlabeled points; the most disagreed-on are chosen.
- **Column Selector**: decides which column to ask for labels next.
- **Batch Generator**: decides which cells inside the chosen column to ask for labels next.
- **Min Certainty (MC)**: picks the column with lowest average prediction confidence.
- **Max Error (ME)**: picks the column with worst cross-validation F1-score.
- **Max Prediction Change (MPC)**: picks the column whose predictions changed most since last round.
- **F1-score**: 2 x precision x recall / (precision + recall).
- **TF-IDF**: term frequency times inverse document frequency, weights n-gram counts per cell.

## Examples worth remembering

- **Table 1, the motivating example** (p. 1-2): columns Position, Salary, Phone, Company. Errors: a wrong phone prefix, a Salary too low for a "Senior" position, and a Company from the wrong universe ("Stark Industries"), syntactically fine but wrong in context. Motivates all four feature types.
- **The salary rule learned automatically** (p. 5, Figure 4): given labeled Salary and Position, a decision tree finds "IF Position contains 's' (senior) AND Salary < 10,000 THEN Salary is erroneous", with nobody writing that rule.
- **City vs Middle Name convergence** (Figure 2, p. 3): City converges in about 2 iterations while Middle Name needs many more, why a fixed round-robin wastes labels.
- **Movies has few errors and unstable results** (p. 7): with only 1% error fraction, F1-score varies a lot run to run.

## Quotes

- "we can also formulate error detection as a semi-supervised classification problem that only requires domain expertise" (p. 1).
- "ED2 requires, on average, less than 1% labels to outperform existing error detection approaches" (p. 1).
- "as a minimum, we should start active learning with two erroneous and two correct cells per column" (p. 4).
- "a surprising outcome is that metadata features ρ_meta alone can be very powerful to detect a wide range of errors" (p. 7).
- "these methods require configuration, such as rules, hyperparameters, and external data, whereas ED2 does not" (p. 6).

## Applying it to RESSLab-Hub

- **Do not adopt ED2 as-is.** Its smallest dataset is 2,376 rows; our tables run 100 to a few thousand, and ED2 needs "2 correct + 2 erroneous per column" before it can start, plus volume for TF-IDF and word-embedding features to mean anything. A 100-row, 60-column table rarely has enough errors to train a useful classifier. My own judgment, not a paper claim.
- **The two-dimensional idea (which column, then which cell) transfers as a prioritization heuristic for curators, not as trained classifiers.** In the curation queue (proposal item 3), sort columns by how many rule violations they show, in the spirit of "label the column that needs attention first" (p. 3). No machine learning needed.
- **The metadata features are worth reusing directly.** Occurrence count, string length, data type are cheap checks for `<table>_rules.yaml` (proposal item 1) with no classifier: flag a value occurring only once as a warning, echoing the paper's finding that metadata alone catches many errors (p. 7, principle 6).
- **The frequency-based outlier ranker is usable for categorical columns** like steel grade or section name: flag values appearing once or twice against a peer group that otherwise repeats (p. 4, principle 9). A `value_counts()` call.
- **Error correlation across columns (principle 7-8) is close to the proposal's cross-column checks**, but the paper's version needs a trained probability; write it as explicit expressions in the rules YAML (`f_u > f_y`, `p_yn == a_cn * f_yn` within tolerance) instead, since our column relationships are physical identities, not patterns to discover.
- **Do not build a curator labeling loop modeled on active learning.** Its convergence numbers assume thousands of rows and retraining after every batch; a curator reviewing a few hundred rows per pull request has neither the volume nor the repeat interaction it needs.
- **The XGBoost finding (principle 10) is not relevant now** since no classifier is proposed in the first iteration; keep only as a note for later.

## Limits and caveats

- The four benchmark datasets are thousands to tens of thousands of rows; nothing is tested at our scale (a few hundred rows), so "applying it" points about label counts and convergence are extrapolation, not a paper finding.
- The paper does not cover numeric physical identities or unit consistency; its errors are formatting, missing values, and pattern/rule violations, not the derived-quantity checks RESSLab-Hub needs.
- Read the full 10-page report, nothing skipped. Plot axis labels could not be read precisely from the converted text (OCR'd tick marks), so plot values beyond Table 2 and the prose were not used.
- This 2019 report predates LLM-based error detection or explanation, the direction RESSLab-Hub wants for its "why" layer. Its own explainability mechanism (a decision tree) is narrower than an LLM explaining a violation in plain language.
