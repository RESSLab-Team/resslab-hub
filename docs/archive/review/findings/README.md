# Findings

Each work package writes one file here: `NN-<name>.md`, with the number and the name of its brief (`01-sign-in.md`, `10-workshop.md`). The agent writes it on its own branch, `review/NN-<name>`. Pierre merges the files, then triages each finding.

This folder is in the private hub repository. Never copy a finding to the data repository, which is public.

## Rules

- One section per question of the brief, in the same order.
- A finding has an id: the package number, then a number in the file. `03-4` is the 4th finding of package 03.
- A finding needs a place (`path:line`) and a proof: a failing test, or a Claude in Chrome transcript on your local server (a `fetch` call from the page, with the status and the body). `wtx curl` does not reach the servers from the sandbox. Without a proof, put it under "Not proven".
- When a finding confirms or rejects a suspicion of `review-plan.md`, write its id (B1 to B10, S1 to S11).
- Give the severity of the scale in `../README.md`: blocker, high, medium, low, note.
- Write what is wrong and why it matters. Give the fix in one or two sentences, without code. You do not fix.
- Keep the transcripts short: the request, the status, the lines that prove the point. Cut the rest. Replace any real address, token, cookie or code by `<redacted>`.
- Write in simple English. No em dash.

## Template

Copy from here to the end of the file.

````markdown
# Findings of package NN: <name>

- Branch: `review/NN-<name>`
- Commit reviewed: `<sha>` (from `dev`, with ORCID)
- Date: YYYY-MM-DD
- Tests run: yes / no (and why, for example "the sandbox hides `secrets/.env`")

## Summary

| Id   | Severity | Title                    | Suspicion | Proof                    |
| ---- | -------- | ------------------------ | --------- | ------------------------ |
| NN-1 | high     | Short title, plain words | B1        | test / curl / not proven |

## Question 1. <the question of the brief, short>

Answer in two to five sentences. Then the findings of this question, or "No finding".

### NN-1 <short title>

- Severity: high
- Suspicion: B1 (confirmed)
- Where: `backend/resslab_hub/routers/auth.py:123`
- Status: new

What happens, in a few sentences. Who it hurts and when.

Proof:

```text
Claude in Chrome, on http://127.0.0.1:<frontend port>/login
> fetch('/api/auth/email/start', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{"email":"<redacted>"}'})
429 Too Many Requests
```

Or: `backend/tests/test_review_NN_<topic>.py::test_<behavior>`, marked `xfail(strict=True)`.

Fix: one or two sentences.

To check by Pierre: what only Pierre can check (stage, prod, GitHub settings, a decision). Leave it out when there is nothing.

## Question 2. ...

## Rejected suspicions

| Suspicion | Why it is not a problem                                      | Where           |
| --------- | ------------------------------------------------------------ | --------------- |
| S5        | Why it is not a problem, with the line of code that shows it | `<path>:<line>` |

## Not proven

Things that look wrong but have no proof yet. One line each, with the place and what would prove it.

## Not checked

What the brief asked and you did not do, and why.
````

## Status values

Pierre sets the status when he triages:

| Status    | Meaning                                                |
| --------- | ------------------------------------------------------ |
| new       | Written by the agent, not triaged                      |
| confirmed | Real. It has an issue number and an owner              |
| won't fix | Real, but we keep it. The reason is written next to it |
| not a bug | The agent was wrong. The reason is written next to it  |
| fixed     | Fixed in a merged pull request, with its number        |
