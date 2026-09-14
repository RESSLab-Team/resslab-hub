# RetClean: Retrieval-based data cleaning using LLMs and data lakes

Naeem, Ahmad, Eltabakh, Ouzzani, Tang, 2024, PVLDB, demo paper, 4 pages.

## In one paragraph

RetClean fills missing or wrong values in a table with an LLM, three ways. Scenario 1 sends each dirty row to a public LLM (GPT3.5, Gemini), using only what it already knows. Scenario 2 adds retrieval: the user points to a data lake, RetClean indexes it, finds tuples close to the dirty one, reranks them, and asks the LLM to pick a value from a retrieved tuple, showing the tuple and attribute it came from. Scenario 3 is the same retrieval flow with a small local model (3B-13B parameters), for data that cannot leave the building. Plain GPT3.5 does well on common world knowledge but is nearly useless on a private dataset (5% accuracy); retrieval fixes that (94%), and a local model with retrieval comes close to GPT3.5 while keeping data private.

## Core principles

1. **A plain LLM only fixes what it already knows.** Scenario 1 fails on private facts (5%, QCRI Personnel) (p. 4).
2. **Retrieval grounds the answer and makes it explainable.** Scenario 2 shows the source tuple, better explainability than Scenario 1 (p. 2).
3. **Retrieval is two stages: recall then precision.** A large top-n set (e.g. n=100), reranked to a small top-k set (e.g. k=5) (p. 3).
4. **Two index types cover different similarity.** Syntactic (Elasticsearch/BM25, shared terms) and semantic (Faiss/BERT or Qdrant, same meaning) (p. 4, p. 2).
5. **Reranking compares field by field.** Tuples split into attribute-value chunks, scored by best-matching (maxsim) cosine similarity per chunk (p. 4).
6. **Pivot columns cut noise before anything runs.** User-marked relevant columns; the rest dropped before indexing, reranking, reasoning (p. 2, p. 4).
7. **Reasoning is pairwise, two questions in one prompt**: same entity, then (if yes) the value (p. 4).
8. **A local model with retrieval can match a public LLM**, "competitively effective" to GPT3.5, while keeping data local (p. 4).

## System architecture

Retrieval scenarios (2, 3) run three modules:

1. **Indexer.** Every data-lake tuple is indexed, offline or online: syntactic (Elasticsearch/BM25) and semantic (Faiss/BERT, or Qdrant), connected to the chosen LLM through LlamaIndex (p. 2, p. 4).
2. **Reranker.** Reduces top-n candidates to top-k, ColBERT-like: split each tuple into attribute:value chunks, encode with a sentence transformer, compute maxsim between every query chunk and every candidate chunk, sum per-chunk scores to rank (p. 3-4).
3. **Reasoner.** For the dirty tuple and each top-k candidate: same entity, then (if yes) the attribute's value. The local setup uses two fine-tuned RoBERTa models instead: a Matcher (same entity, attribute present) and, for pairs that pass, an Extractor (pulls the value) (p. 3-4).

Scenario 1 skips indexer and reranker: each tuple is serialized as attribute:value pairs plus a question, sent to the LLM, with post-processing to extract the value (p. 4). The output always pairs the value with lineage: the retrieved tuple and attribute it came from (p. 3-4).

## Rules of thumb

| Quantity | Value | Condition | Page |
|---|---|---|---|
| Recall / precision set size | top-n=100, top-k=5 (examples) | before / after reranking | p. 3 |
| Local model size | ~3B-13B parameters | Scenario 3 | p. 2 |
| Fine-tuning sample size | 10 or 20 examples | adapting Matcher to a new dataset | p. 4 |
| Prompts to public LLM | m * k | m dirty tuples, k candidates each | p. 4 |
| Accuracy, Cricket Players / Animals / Shows-Movies / QCRI Personnel (Scenario 1 / 2 / 3) | 97-79-27-5% / 96-96-57-94% / 97-96-74-88% | 100, 100, 100, 18 rows | p. 4 |

## Vocabulary

- **Data lake**: user-provided tables used as a grounding source for cleaning.
- **Pivot column**: a non-dirty column marked as relevant to the dirty one.
- **Indexer**: builds a syntactic and/or semantic index over the data lake.
- **Reranker**: reorders top-n candidates into a smaller top-k set by chunk-level similarity.
- **Reasoner**: runs the LLM over a query and candidate tuple to decide the value and source.
- **Maxsim**: the maximum cosine similarity between a query chunk and any candidate chunk.
- **Lineage**: the retrieved tuple and attribute a value came from, shown for explainability.
- **Matcher / Extractor**: local models; Matcher checks same entity, Extractor pulls the value.

## Examples worth remembering

- **health.csv, Gender, non-retrieval.** Pivots "Name", "Age", public model, fills Gender from world knowledge only (p. 2).
- **health.csv, Blood Type, retrieval.** Not world knowledge, so a local hospital data lake plus a local model (p. 2).
- **QCRI Personnel.** Department is fully private; GPT3.5 alone scores 5%, retrieval-based public (94%) and local (88%) work because the answer must come from the data lake (p. 4).

## Quotes

- "such LLMs may struggle with datasets that they have never encountered before ... or when the user requires an explanation of the source of the suggested clean values" (p. 1)
- "we retrieve the top-k relevant tuples ... and leverage LLM inference power to infer the correct value" (p. 1)
- "the Reranker and Reasoner are designed as separate modules ... so we can easily use any arbitrary LLM ... as the Reasoner" (p. 3)
- "The module not only infers the imputed value ... but also identifies the tuple and attribute from which the value is obtained" (p. 3)
- "it is clear that the stand-alone GPT model is useless" (p. 4)

## Applying it to RESSLab-Hub

- **Ground fix suggestions in similar archive rows, not the LLM's memory.** Retrieve rows from our own archive (same peer group: steel family, section family) as context before asking the LLM for a fix. Matches proposal step (1)/(2): the LLM drafts, never decides (transfer, p. 4).
- **Skip the heavy indexing stack; our tables are too small.** Elasticsearch + Faiss/Qdrant targets many-table lakes; a plain pandas filter plus nearest-rows lookup on the peer group is enough (transfer, does not fit our scale, p. 4).
- **Show the source rows next to the suggestion, like RetClean's lineage** (p. 3): display which archive row ids grounded a fix, matching the proposal's "why" field.
- **Use pivot columns to scope the peer group**: steel grade family and section family, like RetClean's user-marked relevant columns (p. 2, transfer).
- **Skip Scenario 3 and the two-stage retrieval machinery.** Local models solve a privacy problem we do not have; one similarity pass over the peer group is enough at our scale. Keep only showing a few comparison rows (around k=5, p. 3) (transfer, does not fit our needs/scale).

## Limits and caveats

This is a 4-page demo paper: no ablations, no detail on how index scores combine, no runtime or cost figures. The accuracy table (p. 4) covers only 100, 100, 100 and 18 tuples, with no description of how accuracy was scored, so treat the numbers as indicative. The paper has nothing on rule discovery, schema constraints, or statistical range checks; the proposal's group-ranges and unit-factor-detector pieces are not addressed here. It has no cross-column checks: RetClean fixes one dirty cell at a time. Figures 1 and 2 are referenced but not visible in this conversion.
