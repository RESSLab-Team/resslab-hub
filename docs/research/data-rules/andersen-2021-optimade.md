# OPTIMADE, an API for exchanging materials data

Andersen, C. W. et al., 2021, Scientific Data. System / demo paper: a consortium API specification, reference implementation, worked examples.

## In one paragraph

Materials science has many databases (AFLOW, Materials Project, COD, NOMAD, and more), each with its own query API, its own names for the same property, and even different meanings for the same term (is "chemical formula" a count per cell or a reduced ratio?). Pulling data from several means learning each API by hand. The OPTIMADE consortium built one shared REST API, v1.0, that many of these databases now implement: one URL shape, one JSON response shape (JSON:API), one filter grammar to query by property. Few properties are mandatory; each provider describes its own attributes through a self-documenting `/info` endpoint, and can add its own fields as long as they carry a provider prefix so names never collide. A validator checks every registered provider daily and reports compliance on a public dashboard. The paper shows this working: the same filter string, sent to nine databases, returns matching entries from each in the same shape.

## Core principles

1. **Replace many query dialects with one filter grammar.** The same SiO2 search, written three ways for AFLOW, Materials Project and COD, differs syntactically, taxonomically (different names) and semantically (different meaning of "formula"). OPTIMADE fixes one grammar so the same filter string works against any implementation (p. 2-3).
2. **Keep the mandatory schema small, let providers self-describe the rest.** Very few properties are required. Each database exposes what it actually serves, per entry type, through an introspective `/info` endpoint (p. 3).
3. **Prefix everything that is not standard.** A provider-specific property must be named `_<prefix>_<name>`, prefix bookended by underscores, so extra fields never collide with each other or with the standard schema (p. 3).
4. **Standardize the envelope, not the content.** Every response has the same top-level shape (attributes, id, links, relationships, meta), following JSON:API; only the attribute values and the provider-prefixed extras differ between databases (p. 3-5).
5. **Make discovery federated, not centralized.** A public providers list is open to pull requests, and each implementation can serve its own `/links` endpoint to other providers (p. 3).
6. **The bar to be listed is low, on purpose.** Some entries only signal an intent to implement; the paper states plainly that "the requirements for appearing in the above providers list are very loose" (p. 3).
7. **Check conformance with an automated validator, not with trust.** A standalone CLI / GitHub Action validator runs against every listed provider once a day and publishes the result on a public dashboard (p. 6).
8. **Version the spec, don't let it silently drift.** Development follows Semantic Versioning, so implementations can track a spec version and clients know what changed (p. 1-2).
9. **Govern the spec in the open, by a consortium.** The spec is developed publicly on GitHub with releases archived on Zenodo; the author list is itself the group who wrote and reviewed the spec across four workshops (2016 Leiden, 2018/2019/2020 CECAM Lausanne) (p. 1, p. 9-10).
10. **Ship a reference implementation, not just a document.** `optimade-python-tools` gives pydantic models, a FastAPI reference server, the validator, a filter parser (Lark) and back-end transformers; several production providers are built on it (p. 6-7).

## The filter language

The grammar the paper walks through, by example, from simplest to most composed:

- Equality on a string attribute: `filter=chemical_formula_reduced="O2Si"`.
- Set membership on a list attribute: `elements HAS ANY "C", "Si", "Ge", "Sn", "Pb"` (true if the entry's `elements` list contains at least one of the given values).
- Equality on a numeric attribute, combined with `AND`: `elements HAS ANY "C", "Si", "Ge", "Sn", "Pb" AND nelements=2`.
- Negation and a length comparison, combined with `AND`/`NOT`: `elements HAS ANY "C", "Si", "Ge", "Sn" AND NOT elements HAS "Pb" AND elements LENGTH 3`.

The reusable core, reimplementable on any small table: (a) per-property comparison operators (`=`, membership/`HAS ANY`, length/count), (b) boolean combinators (`AND`, `NOT`), (c) a parser turning the string into a tree, then (d) a transformer from that tree to whatever the storage layer understands (the paper's tools target MongoDB and Elasticsearch; the same shape maps to a pandas or SQL predicate). The paper does not give the formal grammar (it points to the separate spec, ref. 10); only worked examples are shown here.

## The response anatomy and the info/validator loop

Every entry returns four sections: `attributes` (mandatory ones like `elements`, plus provider-prefixed extras like `_tcod_a`), `id` and a self-`link`, `relationships` to other entries, and top-level `meta` (result counts, provider identity, timestamp). Large result sets are paged with `page_limit` and `page_offset`. Before querying, a client can call the entry type's `/info` endpoint to learn which attributes a provider serves and how they are typed, since the mandatory set is small. The consortium closes the loop with an external check: the same validator implementers run locally is also run by the consortium daily against every provider in the federated list, so conformance is checked continuously, not only claimed once at submission.

## Rules of thumb

| Quantity | Value | Condition | Page |
|---|---|---|---|
| Default page size | `page_limit` = 10 | Default JSON:API-style pagination, overridable per request | p. 5 |
| Spec versioning scheme | Semantic Versioning (major.minor.patch) | Governs backward compatibility of the spec itself | p. 1-2 |
| Provider prefix format | `_<prefix>_<name>`, underscore-bookended | Any non-standard, provider-specific attribute | p. 3 |
| Validator run frequency | daily | Against the full federated providers list, dashboard published | p. 6 |
| Total aggregate scale | over 10,000,000 results | Across all databases reachable through OPTIMADE, cited as the opportunity for benchmarking / high-throughput screening | p. 8 |
| Workshops that shaped the spec | 4 | Leiden 2016, CECAM Lausanne 2018, 2019, 2020 | p. 1, p. 9-10 |
| Spec 1.0.0 release date | 1 July 2020 | License: CC-BY 4.0 | p. 8 |

## Vocabulary

- **OPTIMADE**: Open Databases Integration for Materials Design, the consortium and the API spec it maintains.
- **Entry resource type**: a kind of record the API serves (e.g. `structures`), with a fixed set of possible attributes.
- **Attribute**: one property of an entry, mandatory (like `elements`) or provider-specific.
- **`/info` endpoint**: introspective endpoint per entry type; tells a client what a provider actually serves.
- **Provider prefix**: a short token unique to one database, namespacing its extra fields (e.g. `tcod`, `aflow`).
- **JSON:API**: the general JSON response-shape spec OPTIMADE follows (envelope, pagination links, relationships).
- **Filter**: the query string expression (comparisons and combinators) passed as `?filter=...`.
- **`/links` endpoint**: lists related provider resources for cross-provider discovery.
- **Providers list**: the consortium's open, federated catalogue of implementations, editable by pull request.
- **Validator**: the conformance-checking tool (CLI or GitHub Action) run against implementations.

## Examples worth remembering

**The SiO2 query across three APIs (p. 2).** AFLOW, Materials Project and COD each need a different URL for the same search and do not agree on what counts as a match: AFLOW's `species(Si,O),nspecies(2)` returns anything containing both elements, not necessarily in a 1:2 ratio, while Materials Project and COD match the exact reduced formula. This is the paper's motivating case for one shared filter grammar.

**AFLOW's own inconsistency (p. 2-3).** Even within one database, `compound(SiO2)` returns nothing, while `compound(O2Si1)` (alphabetical elements, explicit "1" suffixes) works: query syntax details are easy to get wrong and hard to guess.

**The Group 14 worked example (p. 3-6).** One filter, `elements HAS ANY "C", "Si", "Ge", "Sn", "Pb"`, sent unchanged to nine databases, returns different counts per database (Table 1) because holdings differ, not the query's meaning. Refining it with `AND nelements=2` (binary), then `AND NOT elements HAS "Pb" AND elements LENGTH 3` (ternary, lead-free), shows filters composing across databases.

**Provider-specific fields in a real response (p. 4).** The TCOD response for a tin compound carries mandatory `elements` and `lattice_vectors`, plus `_tcod_a` and other `_tcod_`-prefixed lattice parameters only TCOD serves: mandatory fields let a generic client work at all, prefixed fields let a TCOD-aware client use more without name clashes.

**The providers dashboard as a running conformance signal (p. 6).** Rather than a one-time compliance claim, the validator's daily run against the whole federated list, published on a dashboard, is governance enforced by a running check, not by review alone.

## Quotes

- "The three APIs vary syntactically (in format), taxonomically (having different names for terms), and semantically (in the conflicting definitions of chemical formula as an intensive or extensive property)." (p. 2)
- "Specification development adheres to Semantic Versioning to avoid surprises and enable backwards-compatibility where possible, without impeding further development." (p. 1)
- "To avoid naming collisions, each provider-specific property name must be prefixed by a provider-specific token, itself bookended by underscores (_)." (p. 3)
- "The requirements for appearing in the above providers list are very loose." (p. 3)
- "The specification mandates that several relevant properties must be queryable." (p. 5)
- "This validator is run against the federated list of OPTIMADE providers every day, with a live dashboard indicating compliance with the specification." (p. 6)

## Applying it to RESSLab-Hub

- **Direct fit**: keep the data dictionary as the one shared, machine-readable contract, the way OPTIMADE keeps `/info` as the place that says what a provider serves; treat the dictionary, not the code, as the source of truth an LLM reads first (principle 2, p. 3).
- **Loose transfer**: RESSLab-Hub has one provider, so the prefix mechanism itself does not apply. What transfers is the naming discipline: tag a rule's `why` field with its source (peer-review check versus data-discovered), so a reader can tell without reading code (from principle 3, p. 3).
- **Does not fit our scale**: the filter grammar (`HAS ANY`, `AND`, `NOT`, `LENGTH`) is built for querying millions of rows across external databases over REST. RESSLab-Hub tables hold a few hundred to a few thousand rows read by one backend; no case for a public filter language here (p. 5-6).
- **Transfer**: the filter grammar's four-part shape (comparison operators, combinators, a parser, a transformer) maps to `<table>_rules.yaml` in issue #366, where each rule's `check` is already a small boolean expression evaluated with `simpleeval`. Keep the operator set small and document it with worked examples (p. 5-6).
- **Direct fit**: build a validator the same way, an independent tool that re-checks conformance to the rules file, runnable in CI and by hand, separate from upload. The paper's validator checks spec conformance daily; the hub's analogue runs against the dictionary and existing rows regularly, not only at submission, showing a pass/fail per table (principle 7, p. 6).
- **Transfer**: self-description through `/info` argues each `<table>_rules.yaml` should be readable stand-alone by a human or an LLM, matching issue #366's plan (check, severity, message, fix, why): keeping rule and explanation together is what let independent teams implement the same spec correctly (p. 3).
- **Does not fit**: governance by open consortium and workshops is out of scale for one lab. The sliver that transfers: when a rule changes, record why in the rule file itself, not only in commit history (principle 9, p. 1).
- **Not covered**: robust statistics per peer group, percentile messages, and the unit-factor detector from issue #366 are not discussed in this paper; that part of the design has no support or counter-evidence here.

## Limits and caveats

This is a short (10-page) system/demo paper, not a methods paper: it shows OPTIMADE working, not an algorithm beyond the filter grammar examples above. The full grammar, exact mandatory property list, and `/info` response schema live only in the separate specification document (ref. 10, Zenodo), not read here (out of scope). The paper covers crystal structure data, not steel test results; nothing here covers physical units, tolerances, cross-column identities, or peer-group statistics, so "Rules of thumb" and "Applying it" lean on structural, not scientific, parallels. Author contributions, references and acknowledgements (pages 7-10) hold nothing relevant to data rules.
