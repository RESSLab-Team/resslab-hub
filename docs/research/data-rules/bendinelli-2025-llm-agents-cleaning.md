# Exploring LLM agents for cleaning tabular machine learning datasets

Tommaso Bendinelli, Artur Dox, Christian Holz (ETH Zurich, CSEM SA), 2025, ICLR 2025 Workshop on Foundation Models in the Wild. Empirical study / benchmark, no new algorithm.

## In one paragraph

The paper asks: if the training pipeline stays fixed, can an LLM alone raise a model's test score just by cleaning the training data? The authors take three Kaggle datasets, inject three kinds of synthetic errors into each (a numerical shift, a NaN corruption, a categorical shift), then give an LLM two tools: an IPython shell to inspect and edit the CSV, and a performance-evaluation tool that trains the fixed pipeline on the edited CSV and returns a score. The LLM loops, editing and resubmitting, until a token budget runs out; the best-scoring submission counts. Four models are tested (gpt-4o, o3-mini, claude-3-5-sonnet, gemini-2.0-flash-exp). All improve on the dirty baseline, but none reaches the score of the original clean data. Models are good at errors visible in a single row (an illogical Sex value, a negative age). They largely miss errors that only show up across many rows, such as a whole year's values shifted, or one subgroup's distribution moved (p. 1, p. 8).

## Core principles

1. **Row-level errors are learnable, distribution-level errors are not.** LLMs catch a value that looks wrong given the other values in its own row, using world knowledge. They fail at errors that only appear as a pattern across many rows, such as a trend or a bias in one subgroup (p. 1, p. 8).
2. **A fixed evaluation pipeline isolates the effect of data quality.** Pre-processing, training and evaluation code stay frozen; only the training CSV changes, so score change comes from data edits alone (p. 2).
3. **Errors are injected in three simple families.** Numerical shift (a value or range moved), NaN corruption (values replaced with NaN under some condition), categorical shift (a category changed to one uncommon or wrong for that subset) (p. 3-4).
4. **A good injected error must be detectable and fixable without the clean copy.** It must be findable by statistics or context (or both), and the fix must not need the original clean values (p. 4).
5. **No model reaches the ceiling.** None of the four models gets back to PClean, the score on the never-corrupted data; the gap is largest on the harder datasets (p. 5-6).
6. **Detection and correction are two separate failures.** A model can correctly flag a problem (claude-3-5 spots landlocked countries with high fish consumption) and still apply an arbitrary fix (a 0.3 scale factor) instead of a quantile cap (p. 6).
7. **Models default to a naive fix for wrong categories.** When 70% of a country column was NaN, models filled it with a new label ("Other") rather than inferring the true majority value from other years (p. 6).
8. **More tokens help, with diminishing returns.** Improvement rises roughly log-like with cumulative tokens (25k to 200k); pushing gemini-2.0-flash-exp to a 2M token budget gave a further gain on two of three datasets (p. 6-7, Table 2).
9. **Hints generally help, but not always.** A weak hint (error location only) or strong hint (location plus partial fix guidance) usually raises the score, but sometimes causes a wrong fix on a column that would have been fine left alone (p. 7-8).
10. **Much of the loop is not real analysis.** 30% to 85% of tool calls are dataset resubmissions rather than exploratory code; models tend to brute-force submit repeatedly instead of investigating first (p. 8, Table 4).
11. **Models often fail to submit a valid dataset, and ignore that the shell keeps state.** 8% to 14% of submissions were invalid, a bad path or extra columns (p. 8, Table 3); most models (not gpt-4o) also regenerate exploration code from scratch each call instead of building on earlier variables, limiting how deeply they explore (p. 8).

## The experimental setup (method a model could reproduce)

For each Kaggle dataset: split into a train set and a held-out test set, never touched by the LLM. Train the fixed model on clean train data, score on the test set to get PClean. Inject three errors (one numerical shift, one NaN corruption, one categorical shift) into the train set; retrain, score again to get PDirty. The gap PClean minus PDirty is the ceiling the LLM tries to close.

Agent loop: a prompt P0 (task, tool descriptions, dataset path, a target F1 score, optionally a hint) plus two tools: `execute_code_ipython_shell(code)`, a persistent IPython session returning stdout and errors; and `submit_clean_data(path)`, which runs the fixed pipeline on the given CSV and returns its score. Each iteration the LLM may call one or both tools; outputs feed back into the conversation. Rules given: edit or drop rows/columns, never add new ones, never touch the row-id column, no plotting. The loop stops at a token budget (200k main runs, up to 2M in one follow-up); the best-scoring submitted dataset is kept (p. 3, Appendix A.2).

Datasets: Titanic (408 x 12, human-rated "easy"), Meat Consumption (9160 x 10, "medium"), Hotel Bookings (100000 x 28, "hard"), each with its own three errors and a matching hint text (Appendix A.1). Two data scientists also got the dirty data and one hour to fix it by hand, as a human baseline (p. 4, Table 1).

## Rules of thumb

| Quantity | Value | Condition | Page |
|---|---|---|---|
| Human 1h improvement | 6.2% / 2.5% / 0% | Titanic / Meat Consumption / Hotel Bookings | p. 5 |
| Best LLM improvement, Hotel Bookings | < 1%, all models | 200k token budget | p. 5-6 |
| gemini-2.0-flash-exp, 200k -> 2M tokens | 3.69% -> 8.88% / 1.51% -> 1.79% / 0.08% -> 1.90% | Titanic / Meat Consumption / Hotel Bookings | p. 7, Table 2 |
| Invalid submission rate | 7.94% to 13.53% | by model, bad path/columns | p. 8, Table 3 |
| Dataset-submission share of tool calls | 29% to 84.70% | gpt-4o lowest, o3-mini highest | p. 8, Table 4 |
| Runs per condition | 6 repeats | for consistency | p. 5 |
| Token budget, main / extended | 200k / 2,000,000 | main runs / gemini-2.0-flash-exp only | p. 5, 7 |
| Hotel Bookings NaN corruption | 70% of country entries | non-2015 years, true value PRT | p. 4, A.1.3 |

## Vocabulary

- **PClean / PDirty**: performance (F1) on never-corrupted versus corrupted training data, same held-out test set.
- **Numerical shift**: a systematic error moving numeric values for a chosen subset of rows.
- **NaN corruption**: values replaced with missing values for a chosen subset.
- **Categorical shift**: a category value changed to one uncommon or wrong for that subset.
- **Weak / strong hint**: prompt text naming the error location (weak) or location plus partial fix guidance (strong).
- **Cumulative tokens**: input plus output tokens summed over a run, the stopping condition.
- **DBest**: among all datasets the LLM submitted, the one with the highest score.

## Examples worth remembering

- **Titanic sex corruption**: 50% of female survivors (name has "Miss." or "Mrs.") had Sex flipped to male, a row-level contradiction that LLMs catch well (p. 12).
- **Meat Consumption poultry near-zero**: in eight specific years, poultry values across all countries were forced near zero, a cross-row pattern models did not reliably find (p. 12).
- **Meat Consumption fish outliers, wrong fix**: claude-3-5-sonnet correctly flagged landlocked countries with abnormally high fish consumption, but fixed it with an arbitrary 0.3 scale factor instead of a quantile cap (p. 6).
- **Hotel Bookings lead-time bias**: 10 days added to every lead_time value in 2016 only. No model, in any run, detected this shift, restricted to one year (p. 6).
- **Hotel Bookings country NaN, wrong fix**: 70% of country entries set to NaN except in 2015 (true value overwhelmingly PRT). Only one run (gpt-4o) correctly inferred PRT; the rest filled with a new "Other" label (p. 6).
- **First-response pattern**: o3-mini's first code on Meat Consumption was `.head()`, `.describe()`, then counts of negative and max values and nulls per column, simple univariate checks, not cross-row analysis (p. 6).

## Quotes

- "LLMs can identify and correct erroneous entries ... by leveraging contextual information from other features within the same row ... However, they struggle to detect more complex errors that require understanding data distribution across multiple rows, such as trends and biases." (p. 1)
- "models begin their analysis by exploring the data using pandas functions such as .describe(), .info(), and .head() ... models rarely investigate more complex relationships within the data." (p. 6)
- "no model was able to detect the numerical shift introduced in the Hotel Bookings dataset, where 10 was added to all values in the lead time column only for the year 2016." (p. 6)
- "instead of applying a statistically meaningful approach, such as using quantiles, it applies an arbitrary scaling factor." (p. 6)
- "Models frequently fail to submit a valid dataset. ... Models tends to apply a brute-force approach by repeatedly submitting datasets without meaningful analysis." (p. 8)
- "no model reaches the maximum potential performance improvement, i.e., achieving PClean." (p. 5)

## Applying it to RESSLab-Hub

- Transfer: keep the split the proposal sets out. Row-level checks (per-column and cross-column YAML rules) fit what LLMs do well; multi-row judgment (peer-group ranges, percentiles) must stay code, never the LLM's free judgment (principles 1, 6).
- Transfer: the arbitrary-0.3-scale and "fill with Other" cases back "LLM may draft rules and explain issues, never decide" (issue #366). Fix expressions should come from simpleeval formulas backed by code-computed statistics (median, percentile), not a number the LLM invents.
- Transfer: the lead-time-in-2016 case (a whole year shifted, missed by every model) matches the planned peer-group ranges. A global min/max check would miss the same subgroup shift; build that layer in code, not by prompting an LLM to notice it (proposal step 2).
- Transfer: the unit-factor detector (value / median near 25.4, 6.895, 1000) is a whole-column pattern like the shifts the paper's LLMs missed. Keep it a pure statistics job.
- General practice, not a paper claim: Table 3's failure modes (bad paths, extra columns) argue for validating any LLM output as strictly as contributor CSVs already are, if a future step lets the LLM write files.
- Caveat, my extrapolation: do not expect an LLM agent, unaided, to do rule discovery by exploring our tables the way this paper's agents explored Kaggle data. Our tables are smaller than even Titanic (408 x 12), rated "easy", where humans improved only 6.2% in an hour and LLMs did worse. So the rule-discovery spike (proposal step 0) should stay code-driven, with the LLM only drafting rule text.

## Limits and caveats

- The paper studies an LLM cleaning data to raise a downstream ML score, not an LLM writing rules or explaining violations. The hub's use (drafting rules, explaining, never deciding) is adjacent, not the same task; the transfer above is mine, not the paper's conclusion.
- All three datasets are unrelated Kaggle domains; none has strict formulas like our E = 200 GPa or exact area identities. The paper gives no evidence on LLM behavior against a physics identity, only against common-sense facts.
- The datasets are larger than ours (smallest 408 x 12 versus our few hundred rows), and the largest, hardest one (100000 rows) is where LLMs did worst. What this implies for a smaller table is assumed above, not tested.
- Figures 2, 3 and 4 (bar and line charts) could not be read as exact values from the converted text; only numbers in the running text and Tables 1-4 are used, all exact and page-cited.
- I read the full paper and Appendix, but did not chase cited works (Raha, HoloDetect, Baran, IterClean); I only report what this paper says of them, and did not search the web.
