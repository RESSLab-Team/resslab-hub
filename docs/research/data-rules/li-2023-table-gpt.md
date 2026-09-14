# Table-GPT: table-tuned GPT for diverse table tasks

Li, He, Yashar, Cui, Ge, Zhang, Fainman, Zhang, Chaudhuri (Microsoft), 2023, arXiv preprint. A research paper, not a manual. No printed page numbers; citations below use PDF page order (about 16 pages of running text, then an appendix of prompts).

## In one paragraph

The paper asks whether large language models like GPT-3.5 and ChatGPT can really "read" two-dimensional tables, since they are pre-trained mostly on one-directional text. Simple tests show they often cannot: a model asked to find the one missing cell in a table gets the column wrong up to 74% of the time, and answers change if you just reorder the columns. The authors propose "table-tuning": keep training a model on (instruction, table, completion) triples built from real tables, the way "instruction-tuning" turned GPT into ChatGPT. Hand-labeled table benchmarks are too narrow to use as training data, so they build a "synthesize-then-augment" pipeline: sample real web and database tables, generate 18 kinds of table tasks with checkable ground truth where possible, then augment at the instruction, table and completion level (paraphrase the instruction, permute rows and columns, add step-by-step reasoning) to avoid overfitting. Table-GPT models beat vanilla GPT-3.5 and ChatGPT on 98 of 104 tests, including tasks never seen during tuning, and gains grow with model size, tasks and data, then level off.

## Core principles

1. **Tables are two-dimensional, text is one-dimensional.** Models read left to right; tables also need vertical (column) reading, causing real errors (p. 1-2).
2. **Tables are permutation-invariant, text is not.** Swapping rows or columns should not change meaning; text-trained models do not fully get this (p. 2-3).
3. **Models cannot reliably find the one missing cell in a table.** Zero-shot GPT-3.5: 0.26 accuracy with no separator, 0.38 with a separator (p. 4).
4. **Missing-row detection is easier than missing-column detection**: row-id accuracy 0.76-0.87 versus 0.26-0.38 for column-header (p. 4).
5. **A simpler unique-value lookup still fails often**: naming the column of one unique value, GPT-3 scores 0.46 (p. 4).
6. **Column order changes model answers, even when it should not**, for entity matching, error detection and schema matching (p. 4-5).
7. **Table-tuning mirrors instruction-tuning**, trained on (instruction, table, completion) triples instead of pairs (p. 5-6).
8. **Hand-labeled table benchmarks are unfit as training data**: too few tasks and datasets, caused overfitting in the authors' own attempt (p. 6-7).
9. **Synthesizing tasks from real tables gives diversity**: 2.9M web tables and 188K database tables, deduped to about 125k (p. 7, p. 10).
10. **Synthesized ground truth beats manual labeling for volume.** 14 of 18 task types are synthesized; only entity matching and NL-to-SQL reuse labeled data (p. 10).
11. **Augmentation happens at four levels**: paraphrase, permute rows/columns, add reasoning, mix zero- and few-shot templates (p. 11-12).
12. **Step-by-step reasoning in training completions cuts false positives.** A yes/no label alone makes error detection invent wrong "errors"; the true correction fixes this (p. 12).
13. **Chain-of-thought completions come from two sources**: GPT-generated for entity matching, built from ground truth for error detection (p. 12).
14. **Table-tuning improves seen and unseen tasks alike**: across 26 datasets, 2 base models, 2 settings, wins 98/104 tests (p. 9).
15. **The benefit appears mainly at large model scale**: little gain under 175B, a clear jump at GPT-3.5/ChatGPT scale (p. 13).
16. **More training tasks helps; one task alone can hurt**: with 1 task, results fall below the untuned baseline (p. 13).
17. **More training data helps, then plateaus**, for both seen and unseen tasks (p. 13).
18. **Table-tuned models help downstream single-task tuning too**, needing less labeled data (p. 8-9, p. 13).
19. **Markdown edges out CSV/JSON** slightly, likely because GPT is pretrained on GitHub markdown tables (p. 13-14).
20. **Every augmentation type helps; synthesized tasks matter most.** Dropping them drops overall score 0.705 to 0.608 (p. 14).

## The task list and the four focus tasks (Table 2, p. 6, plus appendix prompts)

18 tasks, grouped: **unseen hold-out** (never trained on) missing-value identification, column-finding, table-QA, column type annotation (CTA); **seen** (trained on, tested on held-out data) row transform, entity matching, schema matching, data imputation, error detection; **train-only** (10 more: list extraction, head-value matching, NL-to-SQL, summarization, augmentation, swapping, filtering, sorting).

The four focus tasks, from the appendix prompts: **missing value identification** shows a table with one cell removed (with or without its separator) and asks for JSON `{"missing_col": "..."}`; removing the separator is harder, since the model must align values vertically. **Column type annotation** shows one column plus a closed candidate list of semantic types and asks for JSON `{"chosen_semantic_type": "..."}`, one list entry or "None", no new types. **Error detection** asks for JSON `{"erroneous_cells": [...]}` or "None", "with high confidence"; COT versions ask the model to "think step by step" first, stating the correction (e.g. "Repp" to "Rep") in the reasoning. **Data imputation** shows a table with `[MISSING]` in one cell and asks for JSON `{"value": "..."}`; worked examples are simple categorical columns inferred from other rows.

## Rules of thumb

| Quantity | Value | Condition | Page |
|---|---|---|---|
| Missing-cell column accuracy, zero-shot | 0.26 / 0.38 | no sep / with sep | p. 4 |
| Missing-cell column accuracy, few-shot | 0.51 | with separator | p. 4 |
| Missing-cell row accuracy, zero-shot | 0.76-0.87 | with/without sep | p. 4 |
| Column-finding accuracy (unique value) | 0.46 | zero-shot, GPT-3 | p. 4 |
| Table-tuned vs vanilla win rate | 98/104 tests | 26 datasets, 2 models, 2 settings | p. 9 |
| Table-tuning benefit by model size | negligible vs "emerging" | small models vs 175B | p. 13 |
| Prompt-template stability gap | >10 points | across 5 templates | p. 13 |
| Table format score (overall) | Markdown 0.705, CSV 0.687, JSON 0.672 | Table-GPT-3.5 avg | p. 13-14 |
| Ablation scores (full 0.705) | NoSyn 0.608, NoColPer 0.702, NoPromptVar 0.693, NoCOT 0.701 | overall | p. 14 |
| Training instances per task type | 1000 | 50:50 zero/few-shot | p. 10 |
| Real tables for training synthesis | ~125k | deduped from over 2M | p. 10 |

## Vocabulary

- **Table-tuning**: training a model further on (instruction, table, completion) triples to improve table understanding.
- **Instruction-tuning**: the earlier (instruction, completion) pairs technique that turned GPT-3 into ChatGPT.
- **Synthesis-then-augment**: generate a task instance from a real table and task type, then augment it.
- **Seen vs unseen tasks**: seen means the task type was trained on (different data); unseen means never trained on.
- **Table foundation model**: a table-tuned model used as a starting point for further task-specific tuning.
- **Chain-of-thought (COT) completion**: a training completion with reasoning steps, not just the final answer.

## Examples worth remembering

1. **Figure 1, missing-cell test.** GPT-3.5 names the wrong column ("music" instead of "art"), showing the vertical-reading failure directly (p. 1-2).
2. **Figure 6, the two missing-cell variants.** Keeping the separator (`| |`) is an easy signal; removing it forces counting, much harder (p. 4).
3. **Error detection worked example ("Banetn" to "Banten").** States the misspelling and correction before the JSON verdict, a template for issue messages (appendix).
4. **Data imputation worked example (the "area" column).** A low-cardinality categorical column filled from row pattern (appendix).
5. **CTA worked example (closed candidate list).** Model picks only from a fixed list or "None", never a new type (appendix).
6. **Table 3, per-dataset spread.** Entity matching ranges from about 0.06 to over 0.9 by dataset: "good at X" needs a dataset caveat (p. 8).
7. **Figure 14, model-size sensitivity.** Gains appear clearly only at 175B parameters (p. 13).

## Quotes

1. "today's language models are still sub-optimal in many table-related tasks... pre-trained predominantly on one-dimensional natural-language texts, whereas relational tables are two-dimensional objects." (p. 1)
2. "they fail on a surprisingly large fraction (up to 74%) of such tests." (p. 2)
3. "language models are sensitive to the order in which columns are presented in a table." (p. 2-3)
4. "Our attempt to use only existing benchmark data for table-tuning leads to over-fitting, due to the lack of task and data diversity." (p. 7)
5. "vanilla language-models... produce lots of false-positives on the error-detection task... when no such misspellings exist upon close inspection." (p. 12)
6. "table-tuned models outperform their vanilla un-tuned counterparts in 98/104 tests." (p. 9)
7. "the benefit becomes suddenly significant on larger models (GPT-3.5 and ChatGPT), which appear to be an emerging ability." (p. 13)
8. "the Markdown format on average performs better than other formats, although the gap is not too significant." (p. 13-14)

## Applying it to RESSLab-Hub (issue #366)

- Do not trust an LLM to say which column a value is missing or wrong in (base rate 0.26-0.51). Source: principles 3-5. Transfer: locate the bad cell with deterministic code; the LLM only phrases the message about a cell whose location is known.
- When an LLM drafts an error message, give it the true expected value or range and ask it to state the correction, not just flag "looks wrong". Source: principles 12-13. Transfer: fits the planned issue message (code, severity, suggestion, why): the rule computes flagged and expected values, the LLM only phrases the "why".
- Closed-list classification (CTA) is the paper's model for constrained guesses. Transfer (mine): if an LLM guesses a column's group, give it the closed `group` list from `docs/variable-categories.md` and allow "None", not free text.
- Keep the LLM out of "is this row consistent" decisions unless grounded in known facts. Transfer: a YAML rule detects the inconsistency; the LLM only drafts the message, matching "drafts and explains but never decides".
- Expect accuracy to vary a lot by column type (Table 3 spread, p. 8): mostly categorical or text data, not physical measurements, so treat these numbers as a rough guide.
- If a table is serialized into a prompt, markdown edges out CSV/JSON slightly.
- My own extrapolation: continuous physical quantities should get less LLM-suggestion confidence than low-cardinality categorical fields; the paper never tests numeric imputation directly.

## Limits and caveats

- No explicit statement on "limits on numeric columns" or "small tables". Closest finding: table-tuning barely helps small base models, and tested tables are mostly categorical or short text, not scientific measurements. I flag this gap rather than invent a claim.
- Underlying models are 2023-era GPT-3.5 and an internal ChatGPT variant, not current models; treat the accuracy numbers as a lower bound from an older generation.
- I read the full main body and, from the appendix, only the sections named in the brief: missing value identification, CTA, error detection, data imputation. I skipped the other 14 task prompts and page images. No unreadable OCR was found. I did not read the reference list past the titles.
