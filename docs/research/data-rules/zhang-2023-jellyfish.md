# Jellyfish: A Large Language Model for Data Preprocessing

Haochen Zhang, Yuyang Dong, Chuan Xiao, Masafumi Oyamada, 2023 (arXiv, v6 Oct 2024). System paper: builds and evaluates an instruction-tuned LLM for data preprocessing.

## In one paragraph

The paper tunes small open LLMs (7B to 13B parameters, one GPU) to do four data preprocessing tasks: error detection, data imputation, schema matching, entity matching. Instead of calling GPT through an API, they build local models called Jellyfish so data never leaves the user's machine. The method: turn each labeled example into a natural language prompt (serialization), add domain knowledge as extra sentences (knowledge injection), and also build a longer prompt where a bigger model (Mixtral) writes out its reasoning before the answer (reasoning data). They fine-tune on both. The result beats older non-LLM methods on the tuned tasks, generalizes to two unseen tasks (column type annotation, attribute value extraction) about as well as GPT-3.5/4, and explains its answers better than GPT-3.5 does, per a head-to-head judged comparison. Knowledge injection and a small amount of reasoning data each measurably help; too much reasoning data hurts the 13B model.

## Core principles

1. **One instance at a time.** The prompt covers one record (or a pair of records, or a pair of attributes), not the whole table, so it stays short and easy to write (p. 3).
2. **A prompt has fixed parts: system message, task description, injected knowledge, instance content, question, output format.** Same structure across tasks, only the wording changes (p. 5, Figure 2).
3. **Knowledge injection has two levels: general and specific.** General applies to many datasets (how to treat missing values). Specific is tied to one dataset (compare product numbers first, author names can appear in different orders) (p. 6).
4. **Knowledge injected during training becomes built-in, even unrepeated at inference.** Knowledge given only at inference is optional and can add rules the model never saw during training (p. 6-7).
5. **Reasoning data teaches the model to state a rationale, not just the answer.** A larger model (Mixtral-8x7B) explains its answer, given a hint of the correct answer so it reasons in the right direction; that text becomes training data (p. 6-7).
6. **A little reasoning data helps, too much hurts, and it depends on model size.** For the 7B/8B models, accuracy rises then falls as reasoning data grows from 8k to 20k instances; for the 13B model it drops sharply then only partly recovers, so the authors skip it there (p. 15-16).
7. **Knowledge injection improves both seen and unseen datasets, more where the unseen one is close in domain to a seen one** (p. 12-13).
8. **Feature engineering and prompt engineering are separate levers.** Drop irrelevant attributes from instance content, or add few-shot examples and knowledge sentences at inference, without retraining (p. 7).
9. **Few-shot examples can be built cheaply**: inject synthetic errors for error detection/imputation, use rule-based blocking to find real matches for matching tasks (p. 31-32).
10. **A judge model rates its explanations above GPT-3.5's**, in a blind head-to-head test on the same questions (p. 16-18).
11. **The approach reaches unseen tasks by changing only the prompt**, using chain-of-thought step-by-step instructions (p. 8).
12. **The design is instance-based on purpose**, trading table-level context for a short prompt; the authors name this a limitation (p. 19-20).

## The prompt format (serialization and knowledge injection)

Every prompt is built from labeled parts, always in this order (p. 5-6, p. 28-29):

1. **System message**: the model's role, e.g. "You are an AI assistant that follows instruction extremely well. ... Your task is to answer as faithfully as you can." Reasoning prompts add "provide detailed explanation and justify your answer."
2. **Task description**: one or two plain sentences stating the task, naming relevant attributes, e.g. (error detection, Adult dataset, p. 28) "Your task is to determine if there is an error in the value of a specific attribute within the whole record provided. The attributes may include age, workclass, education, ..."
3. **Injected knowledge** (optional): general rules ("Errors may include, but are not limited to, spelling errors, inconsistencies, or values that don't make sense given the context of the whole record.") or dataset-specific rules ("You should compare the two product numbers first.").
4. **Instance content**: the record(s) as `attribute: "value"` pairs in brackets, e.g. (p. 5) `Product A: [name: "Sequoia American Amber Ale", factory: "Wig And Pen"]`.
5. **Question**: a direct yes/no or fill-in question, e.g. "Are Product A and Product B the same Product?"
6. **Output format**: exact answer format, e.g. "Choose your answer from: [Yes, No]." Reasoning prompts finish on a separate line with only the final answer.

For reasoning data, the ground truth comes from a bigger model (Mixtral) given the same prompt plus a hidden hint of the correct answer ("Hint: the final answer is 'No'"), told not to repeat the hint's text; the hint never reaches the trained model. Answers that just restate the instance are filtered out (p. 6-7, p. 29-30).

To reimplement on a small table in Python: for a check on one row (or pair of rows), build a string with these six sections in order, fill instance content from the row's columns as `col: "value"`, and vary only task description, injected knowledge and question per rule.

## Rules of thumb

| Quantity | Value | Condition | Page |
|---|---|---|---|
| Base model sizes | 7B, 8B, 13B | Mistral-7B, Llama 3-8B, OpenOrca-Platypus2-13B | p. 8 |
| Reasoning data used for tuning | 14k / 8k / none | Jellyfish-7B / 8B / 13B | p. 16 |
| Few-shot examples per dataset | 3 | Positive and negative cases | p. 9 |
| Interpretation win rate vs GPT-3.5 | 46% / 73% | Jellyfish-7B / 8B, judged by GPT-4o | p. 17 |
| NLP performance change after DP tuning | -1.32 / -0.56 / -0.36 | 7B / 8B / 13B average | p. 12 |
| Inference time per instance | 0.07 / 0.08 / 0.15 s | Jellyfish-7B / 8B / 13B (GPT-4: 1-8 s) | p. 18 |
| VRAM use | 18 / 20 / 30 GB | Jellyfish-7B / 8B / 13B | p. 18 |
| LoRA rank / alpha | 32 / 32 | Tuning hyperparameters | p. 28 |

## Vocabulary

- **Data preprocessing (DP)**: umbrella term for error detection, imputation, schema matching, entity matching and related tasks (p. 3).
- **Instance**: one unit of input, e.g. one record for error detection, one pair of records for entity matching (p. 4).
- **Instance serialization (contextualization)**: turning a raw row or pair of rows into a text prompt (p. 5).
- **Knowledge injection**: adding domain or task rules as extra prompt sentences, at training time (built-in) or inference time (optional) (p. 6).
- **General / specific knowledge**: rules that apply broadly vs. rules tied to one dataset (p. 6).
- **Reasoning data**: training examples where the answer is preceded by a natural-language explanation, distilled from a larger model (p. 6).
- **Instruction tuning**: fine-tuning on (instruction, output) pairs so the model follows instructions (p. 5).
- **CTA / AVE**: column type annotation / attribute value extraction, the two unseen tasks (p. 4).
- **Blocking**: grouping likely-matching pairs before pairwise comparison, to cut entity-matching cost (p. 19).

## Examples worth remembering

- **Beer entity matching prompt** (p. 5-6): system message, task description, knowledge about missing values, two `Product: [name: ..., factory: ...]` blocks, question, output restricted to `[Yes, No]`. Reasoning version explains that names and factories both differ, then answers "No."
- **Adult error detection prompt** (p. 28): task description lists possible attributes, knowledge says errors can be spelling mistakes, inconsistencies, or context-implausible values, record shown with one attribute marked for verification.
- **Restaurant imputation prompt** (p. 28-29): task description names which fields help, record has one missing field, free-text question asks for the missing city.
- **MIMIC-III schema matching prompt** (p. 29): compares two attributes given only as (name, description) pairs, no row data, so the structure works beyond record-level tasks.
- **Mixtral ground-truth prompt** (p. 30): reasoning prompt plus a hidden answer hint and dataset knowledge, told not to repeat the hint text.
- **Adobe head-to-head case** (p. 17): Jellyfish-8B infers one product is a single application, the other a bundle. GPT-4o, judging blind, picks it over GPT-3.5's shallower version.
- **CMS knowledge-injection gain** (p. 13): an unseen schema-matching dataset where turning injection back on gave the largest accuracy jump of any dataset tested, sharing a domain with a seen one.

## Quotes

- "By instance serialization, raw data is serialized into instruction tuning prompts. By knowledge injection, task- and dataset-specific knowledge ... is infused to the prompts." (p. 3)
- "There are two types of injected knowledge: (1) general knowledge that applies to many datasets, and (2) specific knowledge that only applies to the given dataset." (p. 6)
- "Such knowledge injection may prevent the model incorrectly handling certain values in the dataset, especially when training data is noisy." (p. 6)
- "Small amount of reasoning data ... can enhance the model's DP performance." (p. 16)
- "This observation suggests that the domain knowledge learned through tuning indeed enhances the model's generalizability to unseen datasets." (p. 13)
- "Our prompt is designed as instance-based, rather than the table-based approach that some traditional solutions employ." (p. 19-20)

## Applying it to RESSLab-Hub

- Use the six-part prompt structure for the "explain an issue" step in proposal item (3): state the task, inject the rule's own `why`/`reference` as knowledge sentences, serialize the row as `column: value` pairs (like the paper's brackets), ask the question, constrain the output (one short paragraph, cite the column). This matches our per-row validator output (row, column, value, message): one issue per prompt, not one prompt per table. Paper's method (p. 3-6), transferred here.
- Map our rules YAML to the paper's injection categories: a rule's `message`/`why` is specific knowledge (one column or table); a fact reused across tables ("E is always 200 GPa") could be general knowledge. We only ever do inference-time prompting, never training, so every injected fact stays inference-time (p. 6-7); we cannot get the "built-in even unrepeated" effect of trained-in knowledge (p. 6). Transfer, not a paper claim.
- For the rule-discovery spike (issue #366 item 0), the reasoning-data recipe is useful: give a drafting LLM the row, the check result, and a hint of the expected verdict, ask it to explain, then filter shallow explanations by hand. Inspired by (p. 6-7, p. 29-30), not a paper claim.
- Do not adopt fine-tuning: the LLM only drafts and explains, never decides, and our tables (hundreds to a few thousand rows) are too small to justify instruction-tuning a 7B+ model. Skip the tuning and LoRA details, and the caution about too much reasoning data (p. 15-16): out of our scale unless a later iteration trains a local model.
- For peer-group percentile messages and the unit-factor detector (item 2), the paper has no direct method, but its bracket-style instance content is a good way to hand the LLM the row plus peer-group stats (median, percentile, flagged value) as context. Transfer only.

## Limits and caveats

- Covers four fixed DP tasks plus two unseen ones; nothing about cross-column algebraic rules, unit detection, or peer-group statistics, central to our proposal. All datasets are general-purpose, not engineering data; no evidence here on dense numeric tables like ours.
- Result tables in the converted source (Tables 4, 9, 10) have columns and values running together in places; only the top-line results above were clean enough to report.
- Section 6.6, Figures 4-6, related work (Section 7), and appendix D examples for CTA/AVE were only skimmed, per the brief's instruction to skip training details; they do not change the core method reported here.
- Instance-based prompts cannot see relations across rows (p. 19-20), so our cross-column and peer-group rules must be computed outside the LLM call, with only the result handed to it to explain.
