# Large language models on tabular data: prediction, generation, and understanding, a survey

Fang, Xu, Tan, Zhang, Hu, Qi, Nickleach, Socolinsky, Sengamedu, Faloutsos (Amazon / AWS / NUS), 2024, Transactions on Machine Learning Research. A research survey paper, not a book. Page numbers below are the paper's own printed page numbers (1 to 29).

## In one paragraph

This paper surveys how LLMs are used on tabular data, across three tasks: prediction, generation, and understanding (question answering, fact checking, table reasoning). Its method is a literature review, building a shared vocabulary (serialization, table manipulation, prompt engineering) across all three. For this digest the useful core is table understanding and data-cleaning-adjacent work: how tables become text for an LLM, which formats work better, where LLMs fail at numbers, how missing values and hallucination get handled, and the survey's own open problems. The paper has no chapter for error or outlier detection as its own task. Missing value handling appears mostly inside data generation (masked models fill missing cells as a side effect of training) and inside one hallucination pipeline (an LLM audit step that filters rows and cross-checks its own output against source values). The paper is clear LLMs are unreliable at arithmetic on serialized numbers, that performance is sensitive to table format and size, and that the field lacks standard benchmarks. It closes with a limitations list (numerical and categorical representation, benchmarks, bias, hallucination, interpretability, ease of use), an open problem list for anyone putting an LLM step inside a data pipeline.

## Core principles

1. **Tabular data resists position tricks that work for text or images**, since tables are heterogeneous, sparse, and mostly order invariant (p. 2-3).
2. **Serialization, turning a table into text, is the first and most consequential design choice** for what an LLM can do with it (p. 8).
3. **No single serialization format wins every task.** DFLoader and JSON did better for fact finding, HTML or XML did better for QA and fact verification; markup beat plain separated formats, likely because GPT models saw a lot of HTML and XML in training (p. 9).
4. **LLM-generated table-to-sentence serialization is worse than plain templates for few-shot classification**, since the LLM tends to hallucinate extra or wrong values while writing the sentence (p. 9).
5. **Large tables must be cut down to fit context and control cost.** Beyond roughly 1000 tokens, one study found GPT-3's table QA accuracy drops close to random guessing (p. 10).
6. **Extra table metadata helps selectively.** Dimension, measure and semantic type info raised accuracy; header hierarchy info hurt it (p. 10).
7. **LLMs break on structural changes.** Transposing a table drops GPT3.5 accuracy to about 50%, even though it names the header row or column correctly 94-97% of the time (p. 10-11).
8. **Instructions before the table in the prompt, and few-shot over zero-shot, both help.** One study reports a 30.38% accuracy drop going from 1-shot to 0-shot (p. 10).
9. **Masked language models can do missing value imputation as a side effect of training**, by masking every cell with probability 1, with no separate imputation step (p. 20).
10. **Bigger models handle table numbers better.** A 6.7B GPT-3 scored about half of the 175B model on one QA benchmark; models 6.7B and under were near random on a fact-verification benchmark (p. 24).
11. **Number tokenization breaks whole numbers into misaligned pieces**, hurting arithmetic; digit-by-digit tokenization helps arithmetic but is impractical for large tables (too many tokens) (p. 27).
12. **Reported benchmark scores for the same method, dataset and task disagree between papers** (TabLLM on Blood: 0.70 in one paper, 0.66 in another), why the authors call for standard benchmarks (p. 28).
13. **One published hallucination fix filters rows by a data quality score, drops clearly false cell values, then has the LLM restate each value and re-prompts on mismatch**, flagged as needing several LLM calls per row and hard to deploy (p. 27-28).

## The serialization taxonomy and prompt-building steps

Three serialization families: text-based (a string: DFLoader code, JSON, a list-of-lists matrix, Markdown, LaTeX, separated values, attribute:value pairs, HTML, or hand-written sentences), embedding-based (a fine-tuned table encoder like TAPAS or TABERT turns the table into a vector), and graph or tree based (rare, still converted back to text) (p. 8-9). Markdown is the most common format in the reviewed literature (p. 8).

After serialization, three steps shape the prompt: table manipulation (filtering, sorting, truncating, sampling to fit context), prompt engineering (wording, example choice, chain-of-thought, self-consistency), and, for QA, search and retrieval (finding the right table, rows or cells before answering, since a full database rarely fits in context) (p. 8, 25-26).

## Table understanding, numbers, and data cleaning links

For QA and fact checking, the survey lists benchmarks (WikiTableQuestions, FetaQA, HybridQA, TabFact, Spider, WikiSQL) and reports GPT3.5 and GPT4 doing well on table reasoning, especially with chain-of-thought prompting (p. 24). Numerical QA (questions needing arithmetic, like an average per transaction) is a named weak spot: on DOCMATH-EVAL, GPT-4 with chain-of-thought clearly leads while open-source LLMs lag, tied to the tokenization problem, not reasoning ability alone (p. 24, 27).

The paper does not treat error or anomaly detection as a named task. The closest content is missing value imputation, a side effect of masked-model data generation and one of four ways to judge synthetic data quality, alongside column statistics, correlation fidelity, and privacy distance (p. 20); and the hallucination pipeline of principle 13 (p. 27-28), the clearest case of an LLM checking its own output against source data rather than deciding a value outright.

## Rules of thumb

| Quantity | Value | Condition | Page |
|---|---|---|---|
| Table QA accuracy after transpose | ~50% | GPT3.5 | p. 10-11 |
| Header identification accuracy | 94-97% | GPT3.5, unmodified table | p. 10-11 |
| Accuracy drop, 1-shot to 0-shot | 30.38% | one study, all tasks | p. 10 |
| In-context example gain, curated vs random | +14.7 F1 | manually curated | p. 10-11 |
| Table size where GPT-3 nears random guessing | beyond ~1000 tokens | table QA | p. 10 |
| Score gap, 6.7B vs 175B GPT-3 | ~2x for 175B | WikiTableQuestions | p. 24 |
| GPT-4 accuracy gain from added documentation | +28.9% | term disambiguation docs | p. 10 |
| TabLLM score, same setup, two papers | 0.70 vs 0.66 | Blood dataset | p. 28 |

## Vocabulary

- Serialization: turning a table into a text string (or embedding) an LLM can read (p. 8).
- Table manipulation: filtering, sorting, truncating or sampling a table before it enters a prompt (p. 9).
- Chain-of-Thought (CoT): prompting the model to reason step by step before answering (p. 10).
- Self-consistency (SC): sampling several reasoning paths, picking the most common answer (p. 10-11).
- Data Shapley score: a score judging how much a row helps model quality, used to filter bad rows (p. 28).
- Masking probability: in masked models, the chance a cell is hidden in training; set to 1 to learn to fill any missing value (p. 20).

## Examples worth remembering

Table 1 (p. 9) lists eight text serialization formats with the exact string each produces for the same two-row example, a fast way to see what "Markdown" or "attribute:value pairs" mean as actual strings.

Singha et al. found DFLoader and JSON win for fact finding, while Sui et al. found HTML and XML win for QA and fact verification, at the cost of more tokens per table (p. 9). Different tasks, so not a real conflict, but "best format" depends on the task.

The transpose test (p. 10-11): GPT3.5 names the header row or column correctly 94-97% of the time, but drops to about 50% on a task that requires actually transposing the content. It can describe a table's shape without operating on it correctly.

The 1000-token cliff (p. 10): GPT-3 accuracy falls near random guessing past roughly 1000 tokens of table content, a figure to check any table export against before trusting an LLM's read of it whole.

The hallucination fix in Wang et al. (p. 27-28): filter rows by a quality score, drop false cell values, have the LLM restate each value and re-prompt on mismatch, flagged as hard to deploy since it needs several LLM calls per row.

## Quotes

- "LLM performance is sensitive to the input tabular formats." (p. 9)
- "LLMs respond with unrelated expressions, adding new data, or return incorrect feature values." (p. 9)
- "For table sizes beyond 1000 tokens, GPT-3's performance degrades to random guesses." (p. 10)
- "External information... should be placed before the tables in prompts for better performance." (p. 10)
- "LLMs suffer from structural bias in the interpretation of table orientations... poorly (50% accuracy)." (p. 10-11)
- "MLM can easily address the common challenge of missing data... through a masking probability setting of 1... without requiring separate data imputation steps." (p. 20)
- "The tokenization of integers lacks a coherent decimal representation... even basic mathematical operations require memorization rather than algorithmic processing." (p. 27)
- "This discrepancy in benchmark performance makes it impossible to come up with a classification performance benchmark against all methods." (p. 28)
- "Only a few systems expose a justification of their model output." (p. 28)

## Applying it to RESSLab-Hub (issue #366)

- Keep the LLM's input small: never a full CSV, only the dictionary rows and archive statistics for one column group at a time (principle 5, p. 10).
- Feed the LLM plain, simple text (Markdown or name:value), most used in the literature and easy to check by eye (principles 2-3, p. 8-9). The rules file itself stays YAML.
- Never let the LLM compute or judge a numeric threshold from serialized numbers. Given the reported weakness on arithmetic and number tokenization (principles 10-11, p. 24, 27), compute every bound (min, max, outlier score) in code, and let the LLM only draft the rule's wording and message. Matches the "LLM drafts and explains, never decides" design already planned for #366.
- Add a restate-and-check step before trusting an LLM-drafted rule, the same shape as the hallucination fix (principle 13, p. 27-28): show the LLM a value, ask which rule it breaks and why, route a mismatch to human review instead of auto-applying it. This becomes the "why" field of an issue message, checked by a curator.
- Treat any LLM-drafted "why" text as a first draft, not evidence: almost no system in this survey exposes a real justification for its output (p. 28).
- Always include the dictionary's column description and unit in the prompt, to avoid the metadata confusion the paper names for unclear categorical columns (p. 27-28).
- Keep a small hand-checked set of known-good and known-bad rows per table to test any LLM-drafted rule against; reported scores for identical setups disagreed between papers (principle 12, p. 28).
- Put the rule intent before the data snippet in the prompt, matching the prompt-ordering finding (principle 8, p. 10).

## Limits and caveats

This is a survey of methods, not a manual: mostly "who tried what," with few directly actionable thresholds beyond those listed above. It has no chapter on error, anomaly, or rule-based validation; those appear only indirectly, through missing-value imputation and one hallucination pipeline. Read in full: introduction and tabular data traits (p. 1-3), serialization, table manipulation and prompt engineering (p. 8-11), the masked-model missing-value paragraph (p. 20), table understanding including datasets, numerical QA, and search and retrieval (p. 21-27), and limitations and conclusion (p. 27-29). Not read: the prediction chapter (Section 3, roughly p. 11-20) and the rest of the data generation chapter (Section 4), per the brief's instruction to skip prediction and generation beyond one paragraph each. No page images or figures were opened separately; Table 1 was read as text. The OCR was fully readable everywhere I read. Page numbers here are the paper's own printed numbers, not image indexes.
