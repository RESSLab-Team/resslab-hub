# Using ChatGPT for entity matching

Peeters and Bizer, 2023, arXiv preprint (research paper, not a manual). Pages cited are printed page numbers (p. 1 to p. 10).

## In one paragraph

The paper tests ChatGPT (gpt-3.5-turbo-0301) on entity matching: deciding if two product descriptions describe the same product. This stands in for row-level matching and cleaning tasks. The benchmark (WDC Products, 80% hard cases) is newer than the model's training data, so it cannot have memorized answers. The authors test prompt wording, in-context example pairs, and written matching rules. Zero-shot ChatGPT reaches 82.35% F1, close to RoBERTa fine-tuned on 2000 examples. Adding 20 similar examples raises F1 by almost 8 points. Adding a short set of natural-language rules to a zero-shot prompt raises F1 by about 6 points, almost as much as 20 examples, for a fraction of the cost. Combining rules and examples lowers recall instead of helping further. Main message: wording matters a lot, examples help but cost more per F1 point, and explicit rules give most of the gain cheaply. This maps to an LLM checking or explaining one row against known rules, not fine-tuning on many labeled rows.

## Core principles

1. **Zero-shot ChatGPT can match a fine-tuned model:** 82.35% F1, near RoBERTa fine-tuned on 2000 pairs (p. 5-6).
2. **Forcing a short answer format raises accuracy:** "Yes"/"No" only beats free answers everywhere (p. 5).
3. **Simple wording beats complex wording** in almost every case (p. 5).
4. **Domain-specific wording is more stable than generic wording** (p. 5).
5. **Extra fields are not always better:** an unnormalized price field hurt performance a lot (p. 5).
6. **Zero-shot ChatGPT over-predicts matches:** recall at or above 98%, precision lower (p. 4-5).
7. **In-context examples raise precision, lower recall,** more with more examples (p. 6-7).
8. **Examples similar to the queried pair work best,** beating random and fixed hand-picked sets (p. 6-7).
9. **A small hand-picked set is strong and cheap:** 10 hand-picked pairs gave +4.92 F1, close to similarity-selected examples, for far less labeling (p. 6-8).
10. **In-context cost rises much faster than F1:** 0 to 20 examples multiplies cost ~13-14x for single-digit gains (p. 7-8).
11. **Explicit rules give almost the same gain as the best examples, far cheaper:** rules reach 88.29% F1 at about a quarter the added cost (p. 8-9).
12. **Rules do not hurt recall the way examples do:** recall stays at 98%, precision rises ~10 points (p. 8-9).
13. **Rules plus examples did not add up:** recall dropped 10 points, F1 lower than either alone (p. 9).

## Method, prompt variants

Task: match two offers by brand, title, description, price. Test set 433 pairs, example pool 2025 pairs (p. 2-3).

Prompt axes (Section 3): General vs Domain wording, Complex vs Simple phrasing, Free vs Forced answer, serialized fields (Title, Brand+Title, Brand+Title+Price) (p. 4).

In-context learning (Section 4): Hand-picked, Random, Related selection, at 6, 10, 20 shots (p. 6-7).

Matching knowledge (Section 5): asking ChatGPT to explain its decisions showed it names product features; the authors then wrote a rule set for common features plus a catch-all rule, tested alone and combined with 20 related examples (p. 8-9).

## Rules of thumb

| Quantity | Value | Unit | Condition | Page |
|---|---|---|---|---|
| Zero-shot best F1 | 82.35 | % | best wording | p. 5 |
| Zero-shot F1 with rules | 88.29 | % | rules, no examples | p. 9 |
| F1 gain, 20 related examples | +7.85 | pts | vs zero-shot | p. 7 |
| F1 gain, 10 hand-picked examples | +4.92 | pts | vs zero-shot | p. 7 |
| Recall, zero-shot | ≥98 | % | most variants | p. 4-5 |
| Precision gain from rules | ~+10 | pts | zero-shot | p. 8 |
| Cost, zero-shot / +rules / +20 examples | 0.14/0.28/~2.0 | cents/pair | p. 8-9 |
| Cost per F1 pt, rules vs 20 examples | 17 / 167 | % increase | rules cheapest | p. 9 |
| RoBERTa F1, 20,000 pairs | 89.32 | % | recall 6-8 pts below ChatGPT | p. 6 |
| Recall drop, rules+examples combined | -10 | pts | vs rules alone | p. 9 |

## Vocabulary

- **Entity matching**: deciding if two descriptions refer to the same real thing.
- **Zero-shot**: no example answers in the prompt.
- **In-context learning / demonstrations**: example pairs placed in the prompt to guide the model.
- **Serialization**: a row's fields turned into prefixed text.
- **Related demonstrations**: examples picked by similarity.

## Examples worth remembering

1. **The price mistake (p. 5).** Unnormalized price hurt F1 sharply: an inconsistent-format field can hurt more than help.
2. **Forced answers (p. 5).** Requiring "Yes"/"No" beat free-form answers everywhere.
3. **Wording gap (Table 2, p. 5).** Best domain-simple-forced prompt (84.96 F1) beat a general-complex-free prompt (66.23 F1) by 19 points, same data.
4. **Selection strategy matters (Table 4, p. 7).** At 20 shots: related 90.20 F1, hand-picked 86.24, random 84.11.
5. **Rules near-matched 20 examples cheaply (Table 5, p. 9).** Rules: 88.29 F1 at 0.28 cents. 20 related examples: 90.20 F1 at 1.97 cents, 7x the cost for 2 more points.

## Quotes

- "ChatGPT is competitive with a fine-tuned RoBERTa model, reaching a zero-shot performance of 82.35% F1." (p. 1)
- "forcing the model to answer with a short 'Yes' or 'No' leads to a significant increase in every scenario." (p. 5)
- "adding the price ... leads to a significant decrease in performance likely due to the format and currency of the prices not being normalized." (p. 5)
- "providing demonstrations consistently leads to an increase in precision while the recall decreases." (p. 6-7)
- "Adding matching rules increases the zero-shot performance by 6% F1 to 88.29%." (p. 9)

## Applying it to RESSLab-Hub (issue #366)

- Write validation rules as explicit text the LLM reads (the planned YAML file): rules gave nearly the gain of examples at a fraction of the cost (principle 11).
- Force a fixed, constrained output (severity code, short reason), not open text: the biggest lever in the paper (principle 2).
- Normalize or flag unit/format-mixed columns before the LLM judges them: an unnormalized field made results worse (example 1).
- Use plain, domain-specific wording in prompts and rules ("brace test", not "entity") (principles 3-4).
- Expect an unguided LLM to over-flag, like zero-shot's high recall, low precision (principle 6). Rules and archive statistics should bound what counts as a real issue.
- Do not assume rules plus examples is better: combining them lowered recall and F1 (principle 13).

## Limits and caveats

The paper is about entity matching, not row plausibility checks or archive statistics, so the RESSLab-Hub bullets are transfers, not direct findings. Only gpt-3.5-turbo-0301 and an older GPT-3 model are tested (2023); nothing covers newer models. Cost figures are 2023 pricing, out of date. Nothing is said about severity levels or suggested fixes. Figures 1 and 2 (example prompts, exact rule wording) are described in prose but not reproduced as quotable text (lost in the pdftotext conversion). Full text (10 pages plus references) was read; no page images were opened.
