# Data rules for scientific submissions: paper digests

Digests of 25 papers on data validation, rule discovery, outlier detection with explanations, units, and LLM data cleaning. Made for issue #366 (per-column and cross-column rules for RESSLab-Hub submissions, follow-up of #272).

Goal: know enough to design the rules file, the archive statistics and the issue messages of #366, and to decide what not to build at our size (tables of a few hundred to a few thousand rows, submissions of a handful of rows).

## Start here

Read [techniques.md](techniques.md) for a plain-words guide to the nine techniques we picked, with examples. Then [synthesis.md](synthesis.md). It merges the papers by topic, lists where they disagree and how we resolve it, maps everything to the layers of #366, and ends with a checklist. Open a single digest only when you need the detail behind a claim (each claim in the synthesis cites a paper and page).

## Digests

| File | Paper | Source form |
|---|---|---|
| [andersen-2021-optimade.md](andersen-2021-optimade.md) | Andersen et al. 2021, OPTIMADE, an API for exchanging materials data | PDF, pdftotext |
| [bendinelli-2025-llm-agents-cleaning.md](bendinelli-2025-llm-agents-cleaning.md) | Bendinelli, Dox, Holz 2025, Exploring LLM agents for cleaning tabular ML datasets | PDF, pdftotext |
| [bleifuss-2017-hydra.md](bleifuss-2017-hydra.md) | Bleifuss, Kruse, Naumann 2017, Efficient denial constraint discovery with Hydra | PDF, pdftotext |
| [breck-2019-data-validation-ml.md](breck-2019-data-validation-ml.md) | Breck et al. 2019, Data validation for machine learning | PDF, pdftotext (Table 1 read from a page render) |
| [chu-2013-denial-constraints.md](chu-2013-denial-constraints.md) | Chu, Ilyas, Papotti 2013, Discovering denial constraints | PDF, pdftotext |
| [eltabakh-2024-retclean.md](eltabakh-2024-retclean.md) | Naeem, Ahmad, Eltabakh et al. 2024, RetClean | PDF, pdftotext |
| [fariha-2021-conformance-constraints.md](fariha-2021-conformance-constraints.md) | Fariha et al. 2021, Conformance constraint discovery | PDF, pdftotext |
| [huang-2018-auto-detect.md](huang-2018-auto-detect.md) | Huang, He 2018, Auto-Detect | PDF, pdftotext |
| [hynes-2017-data-linter.md](hynes-2017-data-linter.md) | Hynes, Sculley, Terry 2017, The data linter | PDF, pdftotext |
| [li-2020-copod.md](li-2020-copod.md) | Li et al. 2020, COPOD | PDF, pdftotext |
| [li-2022-ecod.md](li-2022-ecod.md) | Li et al. 2022, ECOD | PDF, pdftotext |
| [mahdavi-2019-raha.md](mahdavi-2019-raha.md) | Mahdavi et al. 2019, Raha | PDF, pdftotext |
| [mahdavi-2020-baran.md](mahdavi-2020-baran.md) | Mahdavi, Abedjan 2020, Baran | PDF, pdftotext |
| [microsoft-2023-auto-validate-by-history.md](microsoft-2023-auto-validate-by-history.md) | Tu, He et al. 2023, Auto-Validate by-History | PDF, pdftotext |
| [neutatz-2019-ed2.md](neutatz-2019-ed2.md) | Neutatz, Mahdavi, Abedjan 2019, ED2 | PDF, pdftotext |
| [polyzotis-2018-data-lifecycle.md](polyzotis-2018-data-lifecycle.md) | Polyzotis et al. 2018, Data lifecycle challenges in production ML | PDF, pdftotext |
| [redyuk-2021-dynamic-ingestion.md](redyuk-2021-dynamic-ingestion.md) | Redyuk et al. 2021, Automating data quality validation for dynamic data ingestion | PDF, pdftotext |
| [rekatsinas-2017-holoclean.md](rekatsinas-2017-holoclean.md) | Rekatsinas et al. 2017, HoloClean | PDF, pdftotext |
| [romano-2019-cqr.md](romano-2019-cqr.md) | Romano, Patterson, Candès 2019, Conformalized quantile regression | PDF, pdftotext |
| [schelter-2018-deequ.md](schelter-2018-deequ.md) | Schelter et al. 2018, Automating large-scale data quality verification (Deequ) | PDF, pdftotext |
| [strutovskiy-2023-desbordante.md](strutovskiy-2023-desbordante.md) | Chernishev et al. 2023, Desbordante demo | PDF, pdftotext |
| [vinh-2016-outlying-aspects.md](vinh-2016-outlying-aspects.md) | Vinh et al. 2016, Discovering outlying aspects in large datasets | PDF, pdftotext |
| [wang-2019-uni-detect.md](wang-2019-uni-detect.md) | Wang, He 2019, Uni-Detect | PDF, pdftotext |
| [williams-2020-units-in-spreadsheets.md](williams-2020-units-in-spreadsheets.md) | Williams et al. 2020, Understanding and inferring units in spreadsheets | PDF, pdftotext |
| [zhang-2023-jellyfish.md](zhang-2023-jellyfish.md) | Zhang et al. 2023, Jellyfish | PDF, pdftotext |

Not read, no open PDF found: Gore et al. 2017 (wwPDB validation reports), Gupta et al. 2018 (LookOut), "Quality by Prompt", Antwarg et al. 2021 (SHAP for anomalies). The synthesis says where they would matter.

## What is not in git

The PDFs and their full-text conversions live in `raw/`, which is gitignored. Only the digests, the synthesis and this index are committed. To rebuild, download the papers again into `raw/`.

## How the digests were made

1. Each PDF was converted to text with `pdftotext` (no layout mode, to avoid mixed columns).
2. One brief per paper (goal, focus, word cap of 1,200 to 2,000 words) was given to a small model, one agent per paper, in parallel.
3. A style and structure check ran on every digest.
4. The synthesis was written on a larger model from the digests only.

Known limits: formulas are partly garbled in the text conversion, so the digests describe them in words. Values plotted in charts are not recovered (Bleifuss, Bendinelli, Neutatz, Mahdavi 2019, Microsoft figures). Lost tables are Breck Table 1 (recovered from a page render), Zhang Tables 4, 9, 10 (LLM benchmarks, not relevant) and Vinh Table 3 (minor).
