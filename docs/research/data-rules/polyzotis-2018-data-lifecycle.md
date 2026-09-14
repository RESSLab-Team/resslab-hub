# Data lifecycle challenges in production machine learning: a survey

Polyzotis, Roy, Whang, Zinkevich, 2018, SIGMOD Record. Survey (extends a 2017 SIGMOD tutorial).

## In one paragraph

The paper looks at ML pipelines from a data point of view, not a training point of view. It splits the data lifecycle into three parts: data understanding (know what to expect), data validation and cleaning (find and fix errors), and data preparation (build features). For each part it surveys existing work and lists open problems. The core message for validation: small errors, a missing field, a unit change, a value that stops being capitalized, silently lower model accuracy instead of crashing, so they must be caught early. The paper gives no new algorithm or system. It is a map of the problem space, drawn from the authors' work on Google's TFX platform, meant to point database researchers at open questions.

## Core principles

1. **Small data errors do not crash, they erode accuracy quietly.** A feature pinned to an error value, a unit change, or a category changing case does not stop training but degrades the model, and can go unnoticed for days, after it has leaked into the next round of data (p. 17, p. 21).
2. **Catch errors as early as possible.** A bad feature value that reaches training can also reach serving, get logged, and come back as training data next cycle, so a small bug can taint the whole downstream flow (p. 17).
3. **Different people need different things from the same error.** The paper's three personas, ML expert, software engineer, site reliability engineer, react to the same alert differently. A validator's output should serve all three (p. 18).
4. **Sanity checks answer "does the data have the expected shape".** Range checks, expected categorical domain, presence rate, cardinality, and label trust checks are the basic first pass before any statistical work (p. 20).
5. **Setting the expectation is the hard part, not writing the check.** If you know the right range or domain, any SQL-like tool can check it. The real difficulty is deciding what "right" is when a feature has no clear owner (p. 20).
6. **Comparing against your own history is a strong, cheap baseline.** For continuously arriving data, checking a new batch against its previous version catches missing fields, timeouts, and format changes with no absolute ground truth needed (p. 23).
7. **Alerts must trade off recall and precision on purpose.** Alerting on everything makes people numb to alerts; alerting too little misses real problems. The test of a good alert is not "is something wrong" but "does it get fixed" (p. 22).
8. **An alert is actionable when it says what is wrong, how much, and where.** "Feature Country is missing" is weak; "missing from 18% of examples" is better; "missing where gender=female" is best, since it gives scope and a likely cause (p. 21).
9. **A surprising value can mean the constraint is wrong, not the data.** If Country holds 4 values and a 5th, "SS", appears, it could be a bug or a real new country (South Sudan) the constraint never covered (p. 22).
10. **Not all features are equally worth fixing.** A feature used in production is worth fixing before an experimental one; prioritizing by production impact, not just statistical strangeness, is still open (p. 22).
11. **Automatic fixes for some errors, human playbooks for the rest.** Consistent-casing fixes can be automated; the rest need a "playbook" of concrete actions, not just a raised flag (p. 21).
12. **Build for the real system, not an idealized one.** Do not assume data lives in one place; most real pipelines pull from several sources with different quality and trust (p. 24-25).

## Data validation and cleaning: what the paper proposes

Closest section to a rule-based validator, unpacked here rather than folded into the principles.

**Useful first-pass checks (3.1, "sanity checks"):** range / shape on a continuous feature (min, max, most common values, a "reasonable" histogram, e.g. latitude within [-90, 90]); categorical distribution as expected; presence (a feature in a minimum share of records, e.g. country code in >= 70%); cardinality (no more values than physically possible, e.g. one age per person); label trust (external labels checked against known ones).

**Detecting change with history (4.2):** three detectors need no statistics: a field disappearing, a timeout signature (most-common value's share drops), a format change (distinct values grow). Statistical tools in practice: homogeneity tests (chi-squared), ANOVA, time series / change-point analysis, distance metrics (L1, Earth Mover's, Kullback-Leibler, Jensen-Shannon). Pitfall: with enough rows, chi-squared finds a "significant" difference on almost every column, so significance alone is weak at scale (p. 23).

**The fix loop (Section 4 intro):** inconsistent value, auto-correct (e.g. force-capitalize country names); feature seen for the first time, add a field rather than reject; feature disappears, use provenance or root-cause tooling; anything else gets a playbook for a human. General cleaning techniques are cited as background, not re-derived.

**No single algorithm to reimplement.** This survey names techniques and cites sources rather than specifying one method fully. The one piece precise enough to reuse is the alert-quality framing: recall vs. precision, "good catch" = actionable and leads to a fix.

## Rules of thumb

| Quantity / example | Value / condition | Page |
|---|---|---|
| Latitude range sanity check | within [-90, 90] (or [-pi/2, pi/2] in radians) | p. 20 |
| Feature presence threshold example | country code present in >= 70% of examples | p. 20 |
| Missing-feature alert example | "Country" missing from 18% of examples | p. 21 |
| Distributional-shift alert example | age's Kolmogorov distance from previous day should stay below 0.1; alert fires at 0.11 | p. 22 |
| Chi-squared caveat | with large data, significant differences appear on almost every field, so significance alone is weak | p. 23 |

## Vocabulary

- **Data understanding**: knowing what to expect from the data.
- **Data validation and cleaning**: finding and fixing errors before they reach training.
- **Data preparation**: engineering features and gathering examples (out of scope here).
- **Training-serving skew**: a mismatch between the data trained on and the data seen when serving.
- **Backfilling**: reapplying a data fix to all historical input data, not just new data.
- **Playbook**: concrete actions a person should take when a given alert fires.
- **Sanity check**: a basic first-pass check (range, domain, presence, cardinality) before training a first model.
- **Coarse- vs. fine-grained provenance**: coarse tools (Goods) track which dataset came from which process; fine tools (ProvDB) track individual features but are tied to one system.
- **Concept drift**: a change over time in what "normal" data looks like, updated by a person's judgement.
- **Alpha feature**: a new, untested feature coexisting with established ones; lower fix priority.

## Examples worth remembering

**The pinned error value.** A bug pins a feature to an error value (e.g. -1). Training does not crash, accuracy drops over days, and since serving output gets logged back as training data, the bad value keeps re-entering the pipeline until traced (p. 17).

**The silently broken refactor.** An engineer refactors a backend, introduces a bug, and a feature starts getting wrong values, with no new feature and no schema change. Only a validation step catches it before a broken model trains (p. 19).

**"US" versus "us".** A model has learned "US" for a country. If the next batch quietly switches to lowercase "us" with no validation, the model treats it as a brand new, unseen country (p. 21).

**Age in days versus hours.** A feature's unit silently changes. No exception is raised; the model just gets steadily worse at using it (p. 21).

**"SS" as a fifth country.** Country is defined with 4 known values. A 5th, "SS", appears: could be a bug, or a legitimate new country (South Sudan) the constraint never included (p. 22).

**Three phrasings of one alert.** "Country is missing" versus "missing from 18% of examples" versus "missing where gender=female": the same fact, more actionable with more scope and context (p. 21).

## Quotes

- "Models cannot answer questions they are not asked." (p. 21)
- "A common response is to overcompensate, by setting alerts for every conceivable issue with the data." (p. 21-22)
- "the question is not whether something is wrong if an alert fires, but whether it gets fixed." (p. 22)
- "'SS' could also be a valid country (say South Sudan), which means the constraint should now include five countries." (p. 22)
- "statistically significant changes may be common on all fields if the data is large enough." (p. 23)
- "in production ML it is equally important to design actionable alerts with humans in mind." (p. 21)
- "it is unreasonable to assume that data lives in a single source." (p. 24-25)

## Applying it to RESSLab-Hub

- **Issue message format.** Use the paper's what/how-much/where example (p. 21) as the template: state the failed check, the share of rows affected, and a likely cause where possible ("column X looks like inches, not mm"). Transfer to our (row, column, value, message) tuple, which today only carries the bare fact.
- **Frame severity around "does it get fixed".** The recall/precision framing (p. 21-22) supports the error/warning/info split: "error" for near-zero-false-positive checks (h_over_t_cw, p_yn, orderings like f_u > f_y), "warning" for peer-group range checks with real exceptions, "info" for anything worth showing but not acting on alone. Our transfer, the paper does not name these levels.
- **A value outside the constraint may mean the constraint is wrong.** The "SS" example (p. 22) supports phrasing warnings as "outside what we have seen before" rather than "invalid", and treating an override as a signal the peer-group range may need widening. Our transfer.
- **The unit-factor detector matches a named failure mode (p. 21).** "Age in days vs hours" is the unit bug the proposal's factor-of-25.4/6.895/1000 detector targets, backing its inclusion; the paper names the failure class, not an algorithm.
- **Presence and cardinality checks are cheap to add.** The "feature in >= 70% of examples" and "one age per person" checks (p. 20) map to non-null thresholds by peer group (columns are often sparse by section family) and duplicate-id checks. Our transfer: info/warning, not hard errors.
- **Skip the paper's drift-detection machinery (chi-squared, ANOVA, EMD/KL over time) as is.** It targets continuously arriving, large, streaming data compared "yesterday vs today" (p. 23). Our tables are static, small, uploaded rarely, with no previous-day distribution, and the chi-squared over-sensitivity flagged (p. 23) would be worse here. The proposal's percentile ranges per peer group (wwPDB style) are the right-sized substitute.
- **The three-persona framing checks the LLM-drafted "why" text.** The ML expert / engineer / SRE split (p. 18) argues an explanation should read without ML background; our audience is closer to domain experts. Our transfer: keep "why" in plain structural-engineering language plus a reference.
- **The paper does not fit our scale beyond the sanity-check layer.** It targets continuous arrival, millions of rows, dedicated SRE staff. Its architecture (TFX, provenance systems, data cube slicing) does not transfer; only the alert vocabulary and sanity-check list are portable here.

## Limits and caveats

- This is a survey: it names and cites systems rather than fully specifying one method. Only the alert-design framing (recall/precision, actionability, playbooks) is precise enough to apply directly; the statistical techniques are named, not specified.
- The paper is from 2018 and describes a large, continuously-updated production pipeline. It predates open-source validators (TensorFlow Data Validation, Great Expectations) that operationalized some of these ideas; this digest covers only this paper.
- Section 5 (feature engineering, selection, enrichment) was read but is out of the brief's focus and not summarized, since it added no validation lesson beyond Sections 3 and 4.
- No formulas were garbled in the parts used here; the main conversion artifact is broken ligatures ("di↵erent"), affecting no number or quote above.
- Page numbers follow the PDF markers, matching the printed page numbers (17-28).
