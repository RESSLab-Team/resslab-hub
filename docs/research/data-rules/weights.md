# How much to trust each paper

The 30 digests are not equal. This page ranks them so we do not take a workshop paper from an unknown group as seriously as a foundational one. Three signals: how much the community cites it, who wrote it and where it was published, and whether the idea shipped in a tool people use.

Citation counts are approximate (Google Scholar order of magnitude, checked against OpenAlex on 2026-09-14, which undercounts because it splits the arXiv and venue versions). Read them as "hundreds" versus "tens", not as exact numbers.

## Tier A: foundational, well known, safe to build on

| Paper | Citations | Why it counts |
|---|---|---|
| Rekatsinas 2017, HoloClean | ~700 | The reference for probabilistic data repair. Stanford and Waterloo. Every later cleaning paper compares to it. |
| Romano 2019, Conformalized quantile regression | ~1500 | NeurIPS, Candès (Stanford). The standard method for prediction intervals with a guarantee. |
| Chu 2013, Discovering denial constraints | ~500 | VLDB, Ilyas (Waterloo), the main name in data cleaning. Defines the rule language everyone uses since. |
| Breck 2019, Data validation for ML (TFDV) | ~500 | Google, the system that runs on thousands of pipelines. The only paper with deployment numbers on which alerts get fixed. |
| Schelter 2018, Deequ | ~400 | Amazon, the tool ships in AWS (Glue Data Quality). Shipped code, widely used. |
| Li 2022, ECOD and Li 2020, COPOD | ~600 and ~500 | TKDE and ICDM. The authors maintain `pyod`, the most used outlier library in Python. |
| Polyzotis 2018, Data lifecycle survey | ~300 | Google, SIGMOD Record. A survey, so a map of the field, not a result. |
| Narayan 2022, Can foundation models wrangle your data | ~400 | VLDB, Stanford (Ré). The paper that opened LLMs for data cleaning. Shows both the gains and the fragility. |
| Fang 2024, LLMs on tabular data survey | ~400 | TMLR. A survey, a map of what works on tables and where numbers fail. |

## Tier B: solid, peer reviewed at a top venue, known in the sub-field

| Paper | Citations | Why it counts |
|---|---|---|
| Mahdavi 2019, Raha | ~250 | SIGMOD, TU Berlin (Abedjan) with MIT (Stonebraker, Madden). Standard error detection baseline. |
| Bleifuss 2017, Hydra | ~150 | VLDB, HPI (Naumann), the group that owns dependency discovery. |
| Mahdavi 2020, Baran | ~150 | VLDB, same group as Raha. |
| Hynes 2017, Data linter | ~150 | Google, NIPS workshop. Small paper, big influence on how people phrase "lint for data". |
| Andersen 2021, OPTIMADE | ~150 | Scientific Data, a consortium of the main materials databases. The only paper here from open scientific databases. |
| Huang and He 2018, Auto-Detect | ~100 | SIGMOD, Microsoft Research. |
| Vinh 2016, Outlying aspects | ~100 | DMKD journal, Melbourne. |
| Wang and He 2019, Uni-Detect | ~80 | SIGMOD, Microsoft Research. |
| Neutatz 2019, ED2 | ~60 | TU Berlin. Technical report of a peer-reviewed paper. |
| Fariha 2021, Conformance constraints | ~50 | SIGMOD 2021, Microsoft and UMass. Young but at the top venue, and the PCA idea is simple to check on our own data. |
| Fernandez 2023, How LLMs will disrupt data management | ~200 | VLDB vision paper, Chicago and Berkeley. Opinion, no experiment, but the framing everyone quotes: LLMs at the edges, not inside the checks. |
| Li 2023, Table-GPT | ~150 | Microsoft. Shows base GPT cannot locate a bad cell, and how table-tuning fixes part of it. |
| Peeters and Bizer 2023, ChatGPT for entity matching | ~100 | Mannheim. Narrow task, but the cleanest numbers on rules versus examples in a prompt. |

## Tier C: recent or narrow, useful ideas, not yet judged by the community

| Paper | Citations | Why it counts |
|---|---|---|
| Zhang 2023, Jellyfish | ~60 | arXiv, NEC Labs. Numbers on LLM cleaning benchmarks, fast moving field. |
| Redyuk 2021, Dynamic data ingestion | ~40 | EDBT, TU Berlin, with Schelter. |
| Eltabakh 2024, RetClean | ~30 | VLDB demo track, QCRI. The retrieval idea is sound, the evaluation is small. |
| Tu, He et al. 2023, Auto-Validate by-History | ~20 | KDD, Microsoft. Deployed at Microsoft, but young. |
| Williams 2020, Units in spreadsheets | ~15 | VL/HCC, Microsoft Research (Gordon). Small venue, but the only paper on unit errors in tables. |
| Bendinelli 2025, LLM agents for cleaning | under 20 | ICLR workshop, ETH and CSEM. Workshop paper, one year old. |
| Strutovskiy 2023, Desbordante demo | under 10 | Demo paper. The tool matters more than the paper. |

## What this changes in the synthesis

- The core of #366 (rules as a human-owned file, cheap strict checks as errors, statistics as warnings, no p-values) rests on Tier A: Breck, Schelter, Chu, Polyzotis. Safe.
- Median and MAD, ECDF percentiles and the Chebyshev threshold come from Tier A and B (ECOD, Deequ, Uni-Detect). Safe.
- Denial constraint and FD discovery for the spike come from Tier A and B (Chu, Hydra, Desbordante as a tool). Safe.
- The PCA conformance constraints come from one Tier B paper (Fariha). Treat it as a thing to try in the spike, not a given. If it finds nothing beyond the pairwise search on our tables, drop it.
- The unit-factor detector cites one Tier C paper (Williams). It does not matter: the detector is five lines, and the idea is common sense. The paper only gives the vocabulary.
- The LLM part (drafts and explains, never decides; give it rules and peer rows in the prompt; code locates the cell and computes every number) now rests on Tier A (Narayan, Fang) and Tier B (Fernandez, Table-GPT, Peeters). Tier C (Bendinelli, Zhang, RetClean) fills in the numbers. What no tier covers: an LLM judging physical measurements. That stays a transfer.
- OPTIMADE (Tier B) is the only voice from open scientific databases. The unread wwPDB paper (Gore 2017, ~300 citations) would be Tier A for the percentile message format; that idea is used here on the strength of the wwPDB reports themselves, which anyone can open.
