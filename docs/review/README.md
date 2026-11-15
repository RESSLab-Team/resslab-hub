# Review of sign-in, roles and contributions

People will try the Hub at a workshop, on prod, with contributions switched on. Prod never ran the contribution pipeline with real people. This review looks for what can break, leak or surprise before that day.

It covers:

- Sign-in: email code and link, GitHub, ORCID (#250), sessions.
- Accounts: several addresses, linked identities, bare accounts, merge, disable.
- Roles: viewer, contributor, curator, admin, and who can call what.
- The contribution pipeline: editor, validation, submit, edit, curation, verification.
- Security and privacy around all of it.

It does not cover the public dashboards, the model and fragility pages, or the data upload jobs (except `/upload` itself).

## Who does what

| Who        | What                                                                                                                                  | Where                                    |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| Pierre     | The parts that need access or a decision: secrets, GitHub App and repo settings, privacy choices, prod config. Triage of the findings | `review-plan.md`, `go-live-checklist.md` |
| Agents     | Code review, one work package each, in their own worktree. They write findings, they do not fix                                       | `briefs/`, `findings/`                   |
| The tester | Every user flow by hand, on stage, from the guide                                                                                     | `test-guide.md`                          |

## The files

| File                                         | For whom       | What                                                                        |
| -------------------------------------------- | -------------- | --------------------------------------------------------------------------- |
| [review-plan.md](review-plan.md)             | Pierre         | Things to check first, then the 11 work packages                            |
| [briefs/](briefs/)                           | agents         | One brief per work package, ready for `wtx go --prompt`                     |
| [test-guide.md](test-guide.md)               | the tester     | Accounts to prepare, numbered cases, expected results, cleanup              |
| [go-live-checklist.md](go-live-checklist.md) | Pierre         | What to set and check on prod, before, during and after the workshop        |
| [findings/README.md](findings/README.md)     | agents, Pierre | The finding template. Each agent adds `findings/NN-<name>.md` on its branch |

## Environments

| Name  | URL                                | Branch        | Data repo for submissions                   | Used for                                               |
| ----- | ---------------------------------- | ------------- | ------------------------------------------- | ------------------------------------------------------ |
| local | `http://localhost:$FRONTEND_PORT/` | your worktree | test fork `EPFL-ENAC/resslab-hub-data-test` | agents                                                 |
| dev   | `https://resslab-hub-dev.epfl.ch`  | `dev`         | test fork                                   | tester parts 15 and 16 (merge, verification, flag off) |
| stage | `https://resslab-hub-test.epfl.ch` | `stage`       | real repo `RESSLab-Team/resslab-hub-data`   | tester, most parts                                     |
| prod  | `https://resslab-hub.epfl.ch`      | tags `v*.*.*` | real repo                                   | the workshop only                                      |

On stage and prod a submission opens a real pull request on the real, public data repo. Never merge one. Close it and delete its branch the same day.

Nobody attacks stage or prod. Agents test on their local worktree. The tester only does what a normal user can do in a browser.

## Timeline

T is the workshop day.

| When            | What                                                                                                 |
| --------------- | ---------------------------------------------------------------------------------------------------- |
| Now             | Documents written. Pierre merges ORCID (`feat/orcid-login-250`) to `dev`, then `stage`               |
| T minus 4 weeks | Agents of wave 1 (packages 01 to 05). Tester starts parts 1 to 10. Pierre does his part of 05 and 09 |
| T minus 3 weeks | Agents of wave 2 (06 to 10). Tester does parts 11 to 19. Triage twice a week                         |
| T minus 2 weeks | Fixes for blockers and high findings. Wave 3: test gaps (package 11)                                 |
| T minus 1 week  | Tester runs the failed cases again. Prod go-live and rehearsal (`go-live-checklist.md`)              |

Waves have about 5 worktrees each, because more fill the RAM of the laptop.

## Severity

| Level   | Meaning                                                                          | Example                                        |
| ------- | -------------------------------------------------------------------------------- | ---------------------------------------------- |
| blocker | The workshop fails, or personal data leaks                                       | Nobody in the room can sign in after 20 mails  |
| high    | A real person loses work, gets the wrong access, or sees something they must not | A viewer can submit. A draft is lost on reload |
| medium  | A bug with a workaround, or a weak protection that needs a second bug to hurt    | Wrong error message. 500 on bad input          |
| low     | Cosmetic, or a very unlikely case                                                | Text too long on a phone                       |
| note    | Not a bug. A question, an idea, a missing doc                                    | "Should a curator verify their own data?"      |

## How to report

- Agents write `findings/NN-<name>.md` on their branch, with the template in [findings/README.md](findings/README.md). One file per package, one section per finding.
- The tester writes the result in the guide (tick box and note) and opens one issue per bug on `RESSLab-Team/resslab-hub` (private repo), with the bug template from Part 0 of the guide.
- Nothing goes on the data repo. It is public.
- Pierre triages: each finding gets a severity, an owner and an issue, or "won't fix" with a reason.
