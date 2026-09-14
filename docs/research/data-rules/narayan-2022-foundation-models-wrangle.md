# Can foundation models wrangle your data?

Narayan, Chami, Orr, Ré, 2022 (VLDB / arXiv 2205.09911). A research paper, not a book. Page numbers below are the paper's own printed page numbers (1 to 13).

## In one paragraph

The paper asks if large foundation models (FMs), tested with GPT-3, can do classical data cleaning and integration with no task-specific training. Method: serialize each row into a short text string, write the task as a natural language question, and add a few worked examples (few-shot prompting) before asking the model to answer. They test five tasks (entity matching, error detection, data imputation, data transformation, schema matching) against each task's prior best method (SoTA), mostly fine-tuned models trained on labeled data for that one task. Main finding: with hand-picked examples, GPT-3-175B beats or matches SoTA on most benchmarks, with no fine-tuning. This is fragile though: small changes in wording, in which columns stay in the row, and in which examples are shown, all move scores by many points. The paper ends with a research agenda: where FMs help most (early prototyping, low-label settings), what they cannot do (act on a GUI, guarantee correctness), and open problems (domain data, privacy, debuggability). Core message for a validation pipeline: FMs are a strong zero-effort baseline for classifying rows as correct or wrong, but need careful prompt design, are not stable, and have no built-in way to explain or be trusted on a single answer.

## Core principles

1. **FMs handle data tasks by turning rows into text**, `attr1: val1 ... attrm: valm` (serialization) (p. 3).
2. **A data task becomes a text generation task.** Entity matching and error detection get a yes/no question, imputation gets the missing attribute name with a question mark (p. 3-4).
3. **Few-shot beats zero-shot by a wide margin on hard tasks**, often 20 to 30 F1 points below few-shot with 10 examples on entity matching (Table 1, p. 4).
4. **GPT-3-175B reached SoTA on most benchmarks tested**: 4 of the entity matching sets, 2 of imputation, 2 of data transformation, 2 of error detection, 1 of schema matching, with no fine-tuning (p. 4-5).
5. **Column selection during serialization has a large effect.** Dropping noisy columns raised F1 by 13.7 points on average across three datasets (p. 6).
6. **Prompt wording moves scores a lot.** Changing "the same" to "equivalent" changed F1 by 9.4 points on average (p. 6).
7. **Manually chosen examples beat random ones by 14.7 F1 points on average.** Random choice also has high run-to-run variance (p. 5-6).
8. **The model is not forced to answer yes/no; when it does not, the paper defaults to "No."** A hidden failure mode (p. 4, footnote 1).
9. **The model fails most on domain jargon rare in normal text**, for example dense product codes in Amazon-Google (p. 6).
10. **Zero-shot imputation already beat classic statistical repair engines**, suggesting general world knowledge even with no examples (p. 5).
11. **Manual prompt tuning is cheap: at most one hour per task**, spent reading validation errors and adjusting examples by hand, and needs far less time and compute than hyperparameter tuning a fine-tuned model (p. 5).
12. **FMs cannot act on graphical interfaces directly; text in, text out only.** A pipeline that must click or edit needs a translation layer (p. 8).
13. **Debuggability of FM decisions is named as an open problem, not solved.** Ideas mentioned: model confidence scores, and breaking a task into a chain of small checkable steps (p. 8).
14. **Domain specialization is costly**: it needs either continued pretraining on domain text, or a smaller adapter layer on a frozen model (p. 8-9).
15. **The paper frames FMs as best for early prototyping, before enough labeled data exists**, moving to a fully trained model once labels accumulate (p. 7-8).

## The method (serialize, prompt, demonstrate)

Three steps. Serialization: turn a row into `attr: val` pairs joined into one string; NULLs become empty strings; only a chosen subset of columns is used (p. 3). Casting as text generation, a fixed template per task. Entity matching: "Product A is [row A]. Product B is [row B]. Are Product A and Product B the same?" Imputation: "attr1: val1 ... attrj?" (target attribute left for the model to fill in). Error detection: "Is there an error in attrj: valj?" (p. 3-4). Task demonstrations: worked question-answer pairs go before the real question, to show the expected format and hint at the data's finer semantics. Examples are picked at random, or built by hand after reading a held-out validation set (10% of the labeled data) and fixing the model's errors there (p. 4-5).

## The experiments and the numbers

Main model: GPT-3-175B (`text-davinci-002`); a smaller GPT-3-6.7B appears in one Table 2 row (p. 5). Baselines are each task's SoTA: Ditto (fine-tuned BERT) for entity matching, IMP and HoloClean for imputation, HoloDetect for error detection, TDE for transformation, SMAT for schema matching (p. 4-5).

Error detection is the weak spot worth flagging for database validation: on Hospital, GPT-3-175B zero-shot scored only 6.9 F1 (HoloDetect: 99.1); with 10 few-shot examples it reached 99.1. On Adult, zero-shot scored 2.1, jumping to 99.1 with 10 examples. GPT-3-6.7B with 10 examples scored 0.0 on Hospital, 97.8 on Adult (Table 2, p. 4). Error detection needs both a large model and good examples; without examples it is close to useless here. The paper does not explain in depth why zero-shot error detection collapses, beyond noting that demonstrations teach format and finer semantics.

## Rules of thumb

| Quantity | Value | Condition | Page |
|---|---|---|---|
| F1 gain from column sub-selection | +13.7 pts avg | entity matching, 3 datasets | p. 6 |
| F1 gain, manual vs. random examples | +14.7 pts avg | entity matching ablation | p. 5-6 |
| F1 swing from wording change | 9.4 pts avg | entity matching ablation | p. 6 |
| Time for manual prompt tuning | at most 1 hour per task | validation-set analysis | p. 5 |
| Validation set size for tuning | 10% of labeled dataset | all tasks | p. 4-5 |
| Ablation sample size | up to 200 per dataset | cost limit, Table 4 | p. 6 |
| Error detection F1, zero-shot 175B | 6.9 (Hospital), 2.1 (Adult) | k=0 | p. 4 |
| Error detection F1, few-shot 175B | 99.1 (Hospital), 99.1 (Adult) | k=10 | p. 4 |
| Error detection F1, few-shot 6.7B | 0.0 (Hospital), 97.8 (Adult) | k=10, smaller model | p. 4 |
| Entity matching F1, zero vs. k=10 | e.g. Walmart-Amazon 60.6 to 87.0 | Table 1 | p. 4 |
| Adult evaluation set | 1K rows, random sample | budget limit | p. 4 |

## Vocabulary

- Foundation model (FM): trained on broad data, adapts to many tasks without task-specific retraining (p. 1).
- Zero-shot: prompt has a task description only, no worked examples (p. 2).
- Few-shot / in-context learning: prompt has a task description plus k worked examples, no weight updates (p. 2).
- Serialization: turning a structured row into one text string of `attribute: value` pairs (p. 3).
- Attribute (column) selection: choosing which columns to serialize, dropping noisy ones (p. 6).
- Entity matching (EM): deciding if two records describe the same real thing (p. 2).
- Error detection (ED): deciding if an attribute value in a row is wrong (p. 2).
- Data imputation (DI): filling in a missing attribute value (p. 2).
- Data transformation: rewriting a value into another format (p. 4).
- Schema matching: matching columns across two schemas describing the same thing (p. 4).
- SoTA: best previously published method for a task and dataset.
- Prompt tuning: picking wording, columns and examples by hand, compared to hyperparameter tuning (p. 5).

## Examples worth remembering

- Figure 1 (p. 1): the paper's reference example. Two "Macbook" rows are serialized and the model is asked "Are product A and product B the same?" The template every task variant follows.
- Figure 2 (p. 2): zero-shot vs. few-shot side by side for error detection, with two worked examples before the real question. Shows what a demonstration looks like in prompt text.
- Amazon-Google failure (p. 6): the model fails to match two rows of the same product because the text is full of alphanumeric product codes, not natural language. Main evidence that the model struggles with domain jargon.
- Table 2 error detection collapse (p. 4): near-zero F1 at zero-shot jumping to near-perfect at k=10 on both Hospital and Adult, the strongest signal that this task depends on demonstrations more than the others.

## Quotes

- "We find that large FMs generalize and achieve SoTA performance on data cleaning and integration tasks, even though they are not trained for these data tasks." (p. 1)
- "FMs can be sensitive to the prompt format and the specific serialization used." (p. 3)
- "The ordering of examples in the prompt can have a non-trivial impact on the downstream performance." (p. 4)
- "In our manual prompt tuning experiments, we spend at most 1 hour per task analyzing errors on the validation set." (p. 5)
- "We find that, on average, attribute selection results in a 13.7 F1 point performance improvement." (p. 6)
- "Manually curated examples outperform randomly selected examples by an average of 14.7 F1 points." (p. 6)
- "This minor modification results in an average 9.4 F1 point performance gap." (p. 6)
- "The model has difficulty reasoning over the data" on jargon-heavy domains (p. 6).
- "FMs are non-deterministic and can make unexpected errors. In order to use these models in data management pipelines, we need mechanisms for increasing transparency and debuggability of pipelines." (p. 8)

## Applying it to RESSLab-Hub (issue #366)

- Phrase an LLM row-error check close to the paper's template: "Is there an error in [column]: [value]?", with a few worked yes/no examples from the archive as demonstrations. Source: principle 2, p. 3-4.
- Error detection needs real examples, not just a rule description: near-zero F1 with none, near-perfect with 10 good ones on this task shape. Give the model known good and bad rows before it judges a new one. Source: principle 3, p. 4.
- Send only the columns relevant to the check: worth about 14 F1 points in the paper. Source: principle 5, p. 6.
- Lock down prompt wording once it works, and keep it stable across versions, since small wording changes swing results by high single digits. Argues for a small set of fixed, tested templates. Source: principle 6, p. 6.
- The LLM should draft and explain, never decide: it gives no confidence, can be wrong either way. Archive statistics and a human or hard rule stay the real gate; the model's answer is a suggestion attached to the issue message. Our transfer, from principle 13 and the "non-deterministic" quote, p. 8.
- Expect weak spots on ID-like columns (specimen IDs, standards), matching the paper's failure case. Flag those for extra scrutiny. Our transfer, from the Amazon-Google example, p. 6.
- Treat numeric plausibility checks with caution: the paper's tasks are short-string, nothing on physical ranges. Use archive per-group statistics as the real rule, the LLM only to phrase the message. Our transfer.

## Limits and caveats

Covers the full main text (Sections 1 to 6, pages 1 to 8) and all four result tables. Does not cover the references list (pages 9 to 13), citations only. The paper points to a longer companion report ([76], same authors) for smaller-model results and deeper analysis of encoded knowledge; not supplied here, so not in this digest. The source text was fully readable. The paper is from 2022 and tests only GPT-3, nothing about instruction-tuned chat or newer models, so exact numbers may not transfer, though the qualitative lessons (examples matter, wording matters, column selection matters) likely still hold. No images were consulted; all numbers come from the text tables.
