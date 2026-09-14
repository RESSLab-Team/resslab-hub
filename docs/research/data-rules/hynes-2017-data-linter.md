# The data linter: lightweight, automated sanity checking for ML data sets

Hynes, Sculley, Terry, 2017, NIPS workshop paper. System paper: introduces a new tool class and reports a small evaluation.

## In one paragraph

Developers cleaning data for machine learning often miss issues that do not break the pipeline but hurt the model: a number stored as a string, a category encoded as a float, values on very different scales. The authors build a "data linter", modeled on code linters like Pylint. It runs independent detectors over summary statistics, individual instances, and feature names, and for each issue prints a warning, an explanation, a fix, and a real example from the data. They implement it for deep neural network training data with Apache Beam, group lints into miscoding, outlier/scaling, and packaging errors, and test it two ways: eight engineers on their own data, and 600 public Kaggle CSVs. Most data sets triggered several lints; one suggestion (normalize inputs) measurably improved a model. The tool never decides, it only flags and explains (p. 1-2).

## Core principles

1. **A lint is a potential defect, not a proven error**, worth a look, not a certain bug (p. 1).
2. **Lints teach best practice, not just catch bugs**; one engineer learned normalization helps (p. 1, p. 5).
3. **Every lint gives a warning, a fix suggestion, and a real example from the data** (p. 2-3).
4. **Valid data can still be a bad representation for a model**; schema-valid and model-friendly are different (p. 2).
5. **Detectors are independent, pluggable classes**; adding one does not touch others (p. 3).
6. **Detectors read three inputs: summary stats, instances, feature names.** Names carry signal values alone cannot, e.g. "lat"/"zip" (p. 3).
7. **Cost scales with what a detector reads, not how many run**; row-scanning detectors are far slower than stats-only ones (p. 3, p. 5).
8. **Lints are framed per model type, but some generalize**; DNN examples dominate, but unnormalized features apply broadly (p. 3-4).
9. **Users want to silence lints**, per type or input, once understood or fixed (p. 5).
10. **Almost every real data set has at least one lint**; only 7% of 600 Kaggle sets were lint-free (p. 5-6).

## The lint taxonomy

**Miscoding** (wrong representation for the model): number as string (represent as a number); enum as real (convert to integer, embedding or one-hot); tokenizable string, long mostly-unique strings (tokenize, word embeddings); circular domain as linear, e.g. lat/long, day of week (bucket or trigonometric transform); date/time as string (timestamp); zip code as number (bucket or embed); integer as float (check whether it is really an enum).

**Outliers and scaling**: unnormalized feature, values vary widely (normalize); tailed distribution, extreme values pull the mean off (check histograms); uncommon list length, most instances share one length (check varying-length handling); uncommon sign, e.g. -9999 as a missing marker (replace with a neutral value).

**Packaging errors**: duplicate values (check data generation); empty examples, whole rows empty, not just fields (remove, check generation). (All p. 4.)

A detector is a LintDetector subclass with a `lint` method returning a LintResult (triggered columns, sample instances) (p. 3). The DataLinter engine runs every detector; a LintExplorer renders results with explanation, fix, and example (p. 2-3).

## Rules of thumb

| Quantity | Value | Condition | Page |
|---|---|---|---|
| Kaggle data sets tested | 600 | pandas type inference; 40 used to design lints | p. 5 |
| Lint-free data sets | ~7% | of 600, typical set had ~4 lints | p. 5-6 |
| False negatives found | 0 | in 35 manually re-checked sets (self-reported limit) | p. 5 |
| Precision gain, one case | 0.48 to 0.59 | one DNN, after normalizing, hyperparameters tuned | p. 5 |
| Detector runtime, stats-based | seconds | ~100k rows, few CPUs | p. 5 |
| Detector runtime, linear-time | minutes | same setting | p. 5 |
| Detector runtime, duplicate/enum | up to hours | same setting, "inefficient" hashing | p. 5 |

## Vocabulary

- **Lint**: a potential defect, not necessarily an actual error (p. 1).
- **Data lint**: a data- and model-specific inspection rule plus recommendation (p. 3).
- **LintDetector**: a pluggable detector class for one issue type (p. 2-3).
- **DataLinter**: the engine running all LintDetectors (p. 2).
- **LintExplorer**: renders lints with explanation, fix, sample data (p. 2).
- **LintResult**: a detector's output, triggered features plus samples (p. 3).
- **Miscoding**: valid data in a representation the model learns poorly from (p. 3).

## Examples worth remembering

- A number stored as text: valid data, wrong type, the plainest miscoding case (p. 4).
- The -9999 missing-value marker: opposite sign from the rest of the column, skews training unless replaced (p. 1, p. 4).
- Latitude, longitude, day of week: circular data wrongly treated as linear (p. 4).
- Zip codes: numeric-looking but not ordered, flagged as miscoding and findable from the column name (p. 3-4).
- One engineer's DNN precision rose 0.48 to 0.59 after normalizing on the linter's suggestion (p. 5).

## Quotes

- "a linter warning does not necessarily indicate an error exists" (p. 1)
- "the data is valid, in that the model will accept the inputs, but it is not in a representation the model can best learn from" (p. 2)
- "only about 7% of the data sets in this study had no data lints, and most data sets presented multiple data lints" (p. 5)
- "We found no false negatives, but acknowledge that the validity of this analysis is limited by our own knowledge of what could be considered problematic" (p. 5)
- "One common request from users was to be able to silence lints, either for specific inputs or specific lint types." (p. 5)

## Applying it to RESSLab-Hub

- Taxonomy matches the brief directly: number-as-string, enum-as-real, uncommon sign. Transfer: add type-consistency checks per column in `<table>_rules.yaml`, beyond today's null/type check; the paper only names the categories generically (p. 4).
- Duplicate values and empty examples map to specimen-id duplicate checks; reuse "check the data generation" for our "why" field (p. 4).
- Tailed distribution matches the brief's case and the peer-group range idea (issue #366 point 2). No threshold given, only "check the histogram"; we need our own statistic (p. 4).
- Template our issue objects (code, severity, suggestion, why) on the warning + fix + real example pattern, fitting the wwPDB-style messages already proposed (p. 2-3).
- Carry "silence a lint" into curation: let a curator dismiss one warning per submission instead of only fix-or-block (p. 5).
- Skip the scale-driven design (Apache Beam, HyperLogLog, performance tiering): a pandas or simpleeval pass is enough for our tables (p. 3, p. 5). Skip circular-domain, tokenizable-string, zip-code lints too: DNN concerns outside our non-ML use (p. 4).

## Limits and caveats

Short paper (7 pages), informal evaluation: 8 engineers, no statistical test, "no false negatives" is limited by reviewer judgment (p. 5). No formulas or thresholds are given for any detector. The Beam-based, DNN-oriented architecture does not match our scale. Figures 1 and 2 were not read beyond captions, the source is a text-only conversion. The reference list was not read.
