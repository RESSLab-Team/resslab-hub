# Understanding and inferring units in spreadsheets

Williams, Negreanu, Gordon, Sarkar. 2020. VL/HCC. System and algorithm paper, with a small theory contribution and an empirical evaluation.

Note: the brief calls this paper "(XeLda)". That label is wrong. XeLda is an older system (Antoniu et al. 2004), cited here as prior work (p. 2), which checks units from user-given annotations but does not infer them. This digest covers the paper in SOURCE, the 2020 Williams et al. inference system.

## In one paragraph

Numbers in spreadsheets often carry a real unit (metres, dollars, percent), but cells cannot record it, and users rarely add it by hand. The paper builds a system that guesses the unit of every numeric cell with no user input. Step one turns formulas, detected tables and number formats ("$", "%") into equality constraints between cells and solves them with linear algebra (Gaussian elimination), as used for unit and type inference in programming languages. Cells left unsolved, called critical cells, carry no constraint, so a user would otherwise label them by hand. Step two tries to resolve those cells from nearby text, first matching a unit name directly in a header, then, if that fails, with a machine-learning model that guesses a dimension (length, mass, currency, etc.) from the header's words using word embeddings. On a hand-labelled set of 331 real spreadsheets, adding the text step raises recall a lot at some cost to precision, and clears a threshold the authors derive from a cost model of user attention. The paper also gives the first measurement of how many critical cells a real spreadsheet has (tens per workbook), showing why pure formula checking (like XeLda) asks too much of the user.

## Core principles

1. **A unit belongs to a dimension.** "Metre" or "dollar" is a concrete unit; length or currency is the dimension it belongs to. This system predicts units; an earlier one (Chambers and Erwig) only predicted dimensions (p. 1).
2. **Formulas generate unit constraints, not units.** `A1+A2` forces A1 and A2 to share a unit; `A1*A3` combines units without forcing a match. All constraints from a sheet solve as one linear system (p. 2, p. 5-6).
3. **A critical cell is one the constraints cannot resolve.** After solving formula, table and format constraints, cells still unconstrained are critical, and only those need a text guess or an annotation (p. 3).
4. **The critical-cell count is the real annotation burden.** Across 1936 Enron and 667 EUSES workbooks, the median was 16 and 3 critical cells (mean 102 and 25), real work even after all logical inference (p. 3, Table I).
5. **Inference is worth it only if it errs less often than the problem it prevents.** A cost model shows inference lowers total attention cost only if its error rate is below the natural unit-error rate it replaces (p. 4).
6. **Direct annotation beats indirect on precision, but covers far less.** Matching a unit name literally in text gets higher precision than guessing a dimension from word meaning, but alone resolves only a small share of critical cells (p. 7-8, Table III).
7. **Combining direct and indirect roughly triples recall at a precision cost.** Unit-prediction recall rises from about 10% to 14.5%; dimension recall from about 10% to 19%, precision drops (p. 8, Table III).
8. **A cross-check on seen headers filters bad guesses.** A second predictor groups previously seen headers into "correct", "unresolved" or "incorrect" by formula-derived agreement, and only calls the word-embedding model for new headers (p. 6-7).
9. **The measured precision clears the derived threshold, barely.** Prior work put the natural dimension-error rate at 42.5%; direct+indirect precision stays above the resulting 57.5% bar (p. 8).
10. **Detecting a unit mismatch is separate, unsolved.** The paper infers a cell's likely unit, but does not turn "these two units disagree" into a flagged error (p. 5).

## The unit inference algorithm

Two steps, over a spreadsheet with a unit variable per numeric cell.

**Step 1, constraints.** Three sources: formulas (an operator forces two cells to share a unit on add/subtract; multiply/divide combine units without forcing that), detected tables (rows or columns forced to share a unit; headers kept aside as text for step 2), and number formats (a currency- or percent-formatted cell yields a direct unit). All constraints become linear equations solved by Gaussian elimination (as in Fortran unit inference). A cell ends up **concrete** (known unit), **critical** (unconstrained), or **determined** (expressed via another cell, e.g. "$/A2"). Worked example: `A1="$1000"`, `A2=20`, `A3=A1/A2`, `D1=2000`, `D2=1500`, `D3=D1-D2`: A1 is concrete ($), A3 and D2/D3 are determined, A2 and D1 stay critical.

**Step 2, text synthesis.** For each critical cell, look at nearby text (distance 2 in the experiments, or a table header). Try direct match first: a template check for a literal unit name, e.g. text ending in "(acres)". If that fails, try indirect match: guess a dimension from the header text, then use the dataset's most frequent concrete unit for that dimension.

**Dimension inference (indirect path).** Predictor 1: for 14 dimensions, build unit names and synonyms mined from Wikidata, embed the header's words, score each unit by cosine similarity, score each dimension by its best unit (counted only if its synonyms also score close, so no outlier fakes a dimension), softmax into a distribution. Predictor 2 sits in front: for headers already pinned by formula agreement, cache "Correct", "Unresolved" or "Incorrect"; Correct returns instantly, Unresolved/Incorrect return "unknown", unseen falls back to Predictor 1.

Reimplementing the core idea on a small table only needs step 1: build a graph of "these columns share a unit" from known identities and orderings, solve for connected components. Step 2, for a known-unit column, is a direct lookup, no ML needed.

## Rules of thumb

| Quantity | Value | Page |
|---|---|---|
| Critical cells per workbook, mean/median | 102/16 (Enron), 25/3 (EUSES) | p. 3 |
| Same, format counted as annotation | 87/13 (Enron), 19/1 (EUSES) | p. 3 |
| Text-search distance used | 2 cells | p. 5 |
| Dimensions modeled | 14 (percent, dimensionless, length, mass, angle, power, energy, speed, temperature, time, volume, force, currency, area) | p. 5 |
| Test set (Annotated) | 331 evaluable workbooks, 1130 critical cells | p. 6 |
| Unit prediction, direct vs direct+indirect | 91.1%P/9.9%R vs 49.7%P/14.5%R | p. 8 |
| Dimension prediction, direct vs direct+indirect | 93.5%P/10.2%R vs 65.2%P/19.0%R | p. 8 |
| Naive baseline (precision = recall) | always-currency 42.5% | p. 7-8 |
| Estimated natural dimension-error rate | 42.5% (cited, not remeasured) | p. 4, p. 8 |
| Minimum precision to justify inference | > 57.5% (derived, 1 minus 42.5%) | p. 8 |

## Vocabulary

- **Unit**: a concrete measure, e.g. metre, gram, dollar, percent.
- **Dimension**: the abstract kind a unit belongs to, e.g. length, currency.
- **Concrete / critical / determined assignment**: a unit variable resolved to a known unit / left unconstrained / expressed via another cell's variable.
- **Annotation burden**: manual unit labelling a user needs without inference, measured by counting critical cells.
- **Direct annotation**: a unit name matched literally in nearby text, e.g. "Area (acres)".
- **Indirect annotation**: a dimension guessed from text meaning, no unit named, e.g. "Credit Card Charges" implying currency.
- **Attention investment**: Blackwell's theory that a user invests upfront effort only if a later payoff is expected.

## Examples worth remembering

- **The critical-set example.** `A1=10, A2=20, A3=30, A4=(A1+A2)*A3`. Addition forces A1 and A2 to the same unit, so one annotation fixes both; multiplication does not, so A3 needs its own. Two annotations out of four cells resolve the sheet (p. 3).
- **The worked example.** A1 formatted "$1000", A2=20 near header "Area (acres)", A3=`A1/A2`, D1=2000, D2=1500, D3=`D1-D2` near header "Credit Card Charges". Constraints alone solve A1, A3, D2, D3, leaving A2 and D1 critical. The direct header resolves A2 to acre; the indirect header resolves D1 (and D2, D3) to dollar (p. 5-6).
- **The mis-predicted headers.** Of 140 headers the human baseline got right but the model missed: distractor words ("Average Life of Loan" pulled to currency by "Loan"), outside knowledge needed ("National Gross Domestic Product" predicted as mass) (p. 7).

## Quotes

- "A numeric calculation must respect the algebra of units [1] and unit checking for spreadsheets is an effective way to find spreadsheet errors" (p. 1).
- "XeLda does not support unit inference; a user must annotate every numeric cell in the spreadsheet with its concrete unit." (p. 2)
- "only two cells must be annotated to determine the units for the complete program—these are the critical cells." (p. 3)
- "the rate of inference error must be less than the natural rate of the error that the system is designed to prevent." (p. 4)
- "We have not implemented any such error-detection step" (p. 5)

## Applying it to RESSLab-Hub

- **Do not port the ML dimension model, and skip Step 2 entirely.** It targets messy, unlabelled Excel headers (our judgment). Our `unit` column is already the "direct annotation" the paper's template step looks for (p. 5); no "Credit Card Charges" case to resolve, and the paper's own numbers show indirect inference is the weakest link anyway (49.7% precision, p. 8).
- **Reuse the constraint-solving idea (Step 1), not the tool.** Treat each dictionary `unit` string as a concrete assignment and each rule expression (`h_over_t_cw = h_c / t_cw`, `p_yn = a_cn * f_yn`) as a formula constraining the columns it touches, as the paper turns formulas into unit constraints (p. 2, p. 5-6). With pint (proposal item 1): build a pint quantity per side of a check, assert both reduce to the same dimension, and flag a `<table>_rules.yaml` check that does not balance as an error before it ever runs on data. Our transfer of the paper's idea to a static authoring check, not inference over unlabelled cells.
- **"Critical cells" maps to "columns with no declared unit or an ambiguous one".** As a rule-discovery spike (proposal item 0), count columns whose `unit` is missing or ambiguous, mirroring how the paper counts critical cells (p. 3). At 30-80 columns per table this is cheap to fix by hand.
- **The unit-factor detector (value/median near 25.4, 6.895, 1000) is not from this paper.** It echoes the paper's use of a cheap signal (number format, p. 3) but runs the other way: an unexpected scale hints at a wrong unit. Our own design, only loosely inspired here; keep as a separate statistical check (proposal item 2).
- **Adopt the paper's Predictor-2 pattern in spirit, not its ML form.** Trusting a cached answer only when independent evidence confirms it, and refusing to guess otherwise (p. 6-7), fits the rule that an LLM may draft or explain but never decide: accept an LLM-suggested rule automatically only when the pint check confirms it, else leave it for curator review.
- **Do not adopt the attention-investment cost model as a design gate.** It needs an error rate we do not have, and its stated assumptions (p. 4) make it a framing device, not a formula to use here.

## Limits and caveats

- The paper targets Excel spreadsheets with implicit, absent unit labels; RESSLab-Hub already has explicit units in a data dictionary, so most of the paper's hard problem does not apply to us.
- Evaluation numbers (Tables III, IV) are on business spreadsheets, not engineering data; they do not transfer as expectations for our dataset.
- Word-embedding training details (dictionary sizes, softmax temperature) are not given beyond what feeds the precision/recall discussion.
- Some inline formulas in the source (the cost derivation around p. 4) were garbled by conversion; this digest describes it in words rather than reconstructing exact notation.
- The error-detection step (a flagged warning) is explicitly not implemented in the paper (p. 5); nothing here about wording, confidence or fixes comes from this paper.
- All nine pages were read in full, including references, only to check the XeLda mislabel in the brief.
