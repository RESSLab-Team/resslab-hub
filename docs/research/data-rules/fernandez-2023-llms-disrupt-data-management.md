# How large language models will disrupt data management

Fernandez, Elmore, Franklin, Krishnan, Tan, 2023, PVLDB 16(11). A vision paper: it argues a position with small hand-picked examples, no benchmark, no evaluation. Page numbers are the printed PVLDB page numbers (3302-3309).

## In one paragraph

The authors argue LLMs are a real break in how database systems can work, not just a new tool bolted on. First, a set of database problems that never got fully automated (entity resolution, schema matching, data discovery, query synthesis) stayed hard because systems could not understand what the data means. LLMs, trained on huge mixes of natural language, structured data and code, can ground tuples and schemas in real world concepts, so these problems get easier. Second, LLMs blur the line between a predictive model and an information retrieval system: they answer questions about data never explicitly stored, by extrapolating from what they learned. The paper is a set of short arguments and ChatGPT transcripts, not a method. It flags what is still broken: LLMs are static, costly to keep current, sometimes subtly wrong, and their provenance is hard to trace. The authors close by asking whether ChatGPT should have been a co-author, which sets the tone: enthusiastic, a bit informal, meant to start a discussion, not to give a solid recipe.

## Core principles

1. **LLMs are a technology break for data management**, on the scale of the web, cloud computing or statistical ML (p. 3302).
2. **Some hard database problems stayed hard for lack of semantic understanding, not lack of algorithms.** Entity resolution, schema matching, data discovery, query synthesis "hit a ceiling of automation" for this reason (p. 3302).
3. **An LLM can be read three ways: information retrieval tool, synthesis tool, or data enrichment tool.** None is a full description alone (p. 3303).
4. **LLMs are not a database.** Databases store symbols with explicit meaning; LLMs store text as vectors, and "query evaluation" is algebra on vectors, not symbol lookup (p. 3304).
5. **LLMs synthesize content not seen in training and combine it in new ways.** A strength and a risk at once (p. 3304).
6. **LLMs are unpredictable and can change behavior between versions**, citing an early report of regressions after GPT-4's release (p. 3304).
7. **Data integration is a long tail problem: easy cases are handled, hard cases still need a human driving the work.** LLMs should help at both ends (p. 3304).
8. **LLMs are "sometimes wrong, and, worse, subtly wrong."** This combines badly with people's confirmation bias (p. 3304).
9. **Text to SQL will work for most queries, but very complex ones will likely still need a human expert for a while** (p. 3305).
10. **An LLM answer should come with an explanation so it can be checked.** ChatGPT justified a generated SQL query in plain language, including its key assumptions (p. 3305).
11. **LLM cost worries are, in the authors' opinion, overstated as a permanent limit; retraining from scratch will stay rare.** Vision model training cost fell about 480x in 6 years, a precedent they expect to repeat (p. 3302).
12. **LLMs are static and go stale.** Updating one with new data without full retraining is an open problem (p. 3306).
13. **LLM provenance is much harder than database provenance.** A database traces which input rows produced an output; an LLM output is a function of all training input at once (p. 3306).
14. **The authors propose grading data like wheat grades, instead of exact input attribution**, citing the historical US wheat grading system (p. 3306-3307).
15. **Easier ETL pipelines mean more of them, which raises maintenance cost.** A stated tradeoff, not solved (p. 3307).
16. **The authors frame data governance as a data market**, agents exchanging data under a social welfare standard (p. 3308).

## The paper's own structure

**Section 2, three readings of an LLM.** Information retrieval tool, synthesis tool (write code or a policy draft from a prompt), and data enrichment tool (bring outside knowledge into a database that only trusted its own facts). None fits perfectly (p. 3303-3304).

**Section 3, hard problems that get easier.** Data integration (3.1), data discovery (3.2), natural language to SQL (3.3), and system support for the storage and compute LLMs need, such as vector databases (3.4). Section 3.5 names ETL pipeline sprawl and trust as new problems this creates (p. 3304-3307).

**Section 4, new horizons.** Provenance (4.1), incentives for data sharing (4.1), and governance as a data market (4.3). More speculative, no worked examples.

**Worked examples.** Two ChatGPT transcripts anchor Section 3: aligning address columns, and translating an English request into a SQL join with the model explaining its key assumptions. A third, in the conclusion, has the authors ask ChatGPT for its own best and worst case view; a rhetorical device, not evidence.

## Rules of thumb

The paper is an opinion piece and gives very few numbers.

| quantity | value | unit | condition | page |
| --- | --- | --- | --- | --- |
| training time reduction, ImageNet-class model | about 480x | fold reduction | AlexNet (2012, 6 days) vs ResNet-50 on AWS (2018, 18 min) | p. 3302 |
| GPT-3 parameter count | over 175 | billion parameters | scale reference | p. 3305 |
| GPT-4 parameter count | rumored 100 | trillion parameters | authors flag it as unconfirmed | p. 3305 |

No thresholds or pass/fail rules appear anywhere. Nothing here reads as a testable data quality rule.

## Vocabulary

- **Closed world assumption**: facts not stored in the database are treated as false or irrelevant to a query (p. 3303).
- **Data integration**: the authors' umbrella for schema matching, entity resolution, alignment and data quality (p. 3304).
- **Long tail (data integration)**: the many rare, special cases that resist one general rule, versus the easy bulk cases (p. 3304).
- **Data discovery**: finding and retrieving data that satisfies an information need (p. 3305).
- **Provenance**: the traceable link between an output and the inputs that produced it; solid in databases, weak in LLMs (p. 3306).
- **Data sharing consortium**: organizations pooling data and cost to build or use an LLM (p. 3306).
- **Data market**: agents exchanging data, used to reason about governance and value (p. 3308).
- **Grading (data grading)**: sorting input data into a few quality grades instead of scoring each record's own contribution, modeled on wheat grading (p. 3306-3307).

## Examples worth remembering

1. **Address alignment transcript.** ChatGPT gets two address columns written differently and aligns them into one mapping, no tuning. Shows an LLM handling the ambiguous "what does this schema mean" step (p. 3304).
2. **Address standardization transcript.** Asked to standardize one address, ChatGPT adds city, state, zip and says plainly these are assumed, not verified. The clearest case of an LLM stating its own uncertainty (p. 3304).
3. **Zip code check code.** Asked for a program to check US zip code constraints, ChatGPT "immediately offered a detailed program that was easy to plug in" (p. 3304-3305).
4. **Natural language to SQL join.** Given two toy schemas, ChatGPT writes a correct join and explains, unprompted, its foreign key assumption (p. 3305).
5. **Wheat grading analogy.** The 19th century US wheat grading system as the model for valuing data without tracing every record (p. 3306-3307).

## Quotes

- "LLMs challenge the raison d'être of the data management community: effective and accurate question answering over data." (p. 3302)
- "A number of hard database problems... hit a ceiling of automation because the system does not fully understand the semantics of the underlying data." (p. 3302)
- "LLMs have well-known failure modes with factual inaccuracies and hallucinations." (p. 3303)
- "Simply put, LLMs are a different technology." (p. 3304)
- "Still, LLMs are sometimes wrong, and, worse, subtly wrong." (p. 3304)
- "It would be useful if LLMs provided an explanation of their answer, so those querying it can verify its correctness." (p. 3305)
- "Lowering the barrier to building these ETL pipelines will result in an increase in the total number of ETL pipelines, thus raising maintenance costs." (p. 3307)
- "The challenges of understanding the provenance of LLMs are daunting." (p. 3306)
- "Data governance is not a traditional data management problem but it must become one." (p. 3308)

## Applying it to RESSLab-Hub (issue #366: a YAML rules file per table, per-group archive statistics, issue messages with code, severity, suggestion and why, an LLM that drafts and explains but never decides)

- Keep the LLM at the drafting and explaining edge, never as decision-maker. Matches the point that trust needs explanation and LLMs are "sometimes wrong, and, worse, subtly wrong" (principle 8, p. 3304). Direct transfer, close to what #366 already plans.
- When the LLM proposes a rule or flags a row, have it state its assumptions in plain language, as ChatGPT did in examples 2 and 4. Issue messages should carry that "why". Direct transfer.
- Do not expect the LLM to hold the full rule set from memory across a long run: LLMs are static and can drift between versions (principle 6, 12). Keep the YAML rules file as the durable source of truth; use the LLM to draft or explain it, never to enforce it silently. Our transfer.
- For unusual but plausible values, expect the LLM to draft a rule faster than starting from scratch, but expect a human to resolve the truly hard cases (principle 7, p. 3304). Direct transfer.
- Keep an explicit audit trail outside the LLM: the paper argues database-style provenance is exactly what LLMs cannot give (principle 13, p. 3306). RESSLab-Hub's commit-trailer provenance stays the record; the LLM only phrases the summary. Direct transfer.
- Consider "grading" (principle 14, p. 3306-3307) as vocabulary for archive statistics: bucket values against per-group stats (in range, borderline, outlier) instead of one score. Our transfer, an analogy.
- Do not lean on this paper for validation logic or column rules: it gives none. Use it for framing only.

## Limits and caveats

This is a short vision paper (about 6 pages of body text plus references), meant to start discussion, not a study. It has no benchmark, no dataset, no evaluation beyond the numbers above. The examples are hand-picked ChatGPT transcripts from spring 2023, illustrations, not evidence of a general capability level. The paper predates most current agentic and retrieval-augmented approaches; its claims about cost trends and GPT-4 parameter count ("rumored", their word) are specific to mid-2023. It says almost nothing about tabular data validation rules or how to structure a rules file; its use for RESSLab-Hub is about where to place an LLM and how much to trust it, not what the rules should say. I read the full paper text, abstract through conclusion, but not the reference list. There were no figures, tables or images in the source file. No part of the text was unreadable.
