# Go-live checklist for the workshop

This list is for Pierre. On the workshop day, prod runs with contributions switched on, for the first time with real people. T is the workshop day.

Each line is a box to tick. A line that names a finding of the review (`findings/`) waits for its triage.

## Where each setting lives

The overlay is `overlays/prod/kustomization.yaml` in `enack8s-app-config/epfl-resslab/resslab-hub`, under `configMapGenerator` > `resslab-hub-backend` > `literals`. Secrets live in Infisical, environment `prod`. The backend reads them at startup, so a change needs a restart of the backend pod (ArgoCD rolls it when the ConfigMap changes).

| Setting                                                                 | Where                                  | Prod today                      | For the workshop                                                         |
| ----------------------------------------------------------------------- | -------------------------------------- | ------------------------------- | ------------------------------------------------------------------------ |
| `CONTRIBUTIONS_ENABLED`                                                 | overlay                                | `false`                         | remove the line (default `true`)                                         |
| `PUBLIC_BASE_URL`                                                       | Infisical                              | to check                        | `https://resslab-hub.epfl.ch`                                            |
| `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`                               | Infisical                              | missing                         | the `noreply-resslab-hub` relay, as on stage                             |
| `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`, `GITHUB_APP_INSTALLATION_ID` | Infisical                              | to check                        | the App installed on `RESSLab-Team/resslab-hub-data`                     |
| `GITHUB_OAUTH_CLIENT_ID`, `GITHUB_OAUTH_CLIENT_SECRET`                  | Infisical                              | to check                        | the pair of the same App                                                 |
| `ORCID_CLIENT_ID`, `ORCID_CLIENT_SECRET`                                | Infisical                              | missing                         | a production ORCID client. `ORCID_SANDBOX` not set                       |
| `DATA_REPO`                                                             | default                                | `RESSLab-Team/resslab-hub-data` | keep                                                                     |
| `DATA_REPO_REVIEWERS`                                                   | overlay                                | `admins` (default)              | the logins of the curators of the day                                    |
| `MAX_OPEN_CONTRIBUTIONS`                                                | overlay                                | 25 (default)                    | more than the open `contrib/` pull requests plus the number of attendees |
| `CONTRIBUTOR_DOMAINS`                                                   | overlay                                | empty                           | the mail domains of the attendees, or invitations instead                |
| `ADMIN_EMAILS`                                                          | base                                   | `pierre.ripoll@epfl.ch`         | keep                                                                     |
| Rate limits                                                             | code (`@limiter.limit` in the routers) | per IP, in memory               | after package 10: per account, or higher for the day. Needs a release    |
| Backend replicas                                                        | base                                   | 1                               | keep 1 while the limits and caches are in memory                         |

## Two weeks before (T minus 14 days)

Decisions:

- [ ] Get the list of attendees and their mail domains.
- [ ] Choose how they become contributors: `CONTRIBUTOR_DOMAINS` for whole domains, or one invitation per person from the admin page. An academic address (swot list) is already enough.
- [ ] Choose real data or exercises. Each pull request is public, on a public repository, with the name and the address of the person, for ever in the git history. For exercises, give the attendees ids with a prefix, for example `WS-`.
- [ ] Choose who reviews the pull requests on the day, and set `DATA_REPO_REVIEWERS` to their logins.
- [ ] Choose what happens to the pull requests after the day: merge after review, or close.

Access and accounts:

- [ ] Register a production ORCID client on orcid.org (Developer Tools), with the redirect URI `https://resslab-hub.epfl.ch/api/auth/orcid/callback`. Put the pair in Infisical `prod`.
- [ ] On the GitHub App, add the callback URL `https://resslab-hub.epfl.ch/api/auth/github/callback`.
- [ ] Put the `SMTP_*` keys in Infisical `prod` (the same relay as stage and dev).
- [ ] Make sure that `PUBLIC_BASE_URL` in Infisical `prod` is `https://resslab-hub.epfl.ch`. The mailed link and the OAuth callbacks are built from it.

The review:

- [ ] Every blocker and high finding is fixed, merged on `dev`, then on `stage`.
- [ ] The tester ran the failed cases of the guide again on stage, and they pass.
- [ ] Package 09: you know which IP the backend sees behind the ingress. If it is the IP of the ingress, every user shares one limit today.
- [ ] Package 10: the decision on the rate limits is made and in the release.

The data repository:

- [ ] Count the open `contrib/` pull requests on `RESSLab-Team/resslab-hub-data`. Close the old test ones and delete their branches. Each one counts against `MAX_OPEN_CONTRIBUTIONS`.
- [ ] The CI of the data repository validates against prod (`/api/validate`). Make sure that prod runs the new validator before the first pull request of the day, or the CI can refuse good data.
- [ ] The `filters:` list of `data-validation.yml` has all 9 folders.

## One week before (T minus 7 days)

Release:

- [ ] Dump the prod database before the tag (the `pg_dump` command of `backend/README.md`, see `docs/releasing.md`).
- [ ] Release to prod with the fixes (`docs/releasing.md`).
- [ ] Remove `CONTRIBUTIONS_ENABLED=false` from the prod overlay. Set the other overlay settings of the table. Let ArgoCD sync. If the backend pod did not roll, restart it:

```bash
kubectl -n epfl-resslab-resslab-hub-prod rollout restart deployment/resslab-hub-backend-prod
```

- [ ] `curl https://resslab-hub.epfl.ch/api/features` says `{"contributions":true}`.
- [ ] Run Part 1 of the test guide (smoke test) on prod.

Rehearsal with 3 people, on the EPFL network, in one room:

- [ ] Each one signs in a different way: mail code, GitHub, ORCID.
- [ ] Each one submits a small batch with `DEMO-` ids, then edits it once.
- [ ] A curator opens the review queue and a review page.
- [ ] The mail arrives in less than a minute, at an EPFL Outlook address and at a Gmail address, not in spam. The link works after Outlook rewrites it.
- [ ] No 429 and no 503 in the logs.
- [ ] Close the 3 pull requests and delete their branches.

Before the day:

- [ ] Send the invitations, or set the roles by hand, for the attendees who are not covered by their domain.
- [ ] Make sure that the nightly dump of the accounts runs on prod (CronJob `resslab-hub-db-dump-prod`, look at its last job).
- [ ] Write a one-page quick start for the attendees: the URL, the three ways to sign in, how to drop a folder, what is public, who to ask.

## The day

One hour before:

- [ ] `https://resslab-hub.epfl.ch/api/healthz` answers, and `/api/features` says `{"contributions":true}`.
- [ ] The number of open `contrib/` pull requests is far under `MAX_OPEN_CONTRIBUTIONS`.
- [ ] A terminal with the logs of the backend:

```bash
kubectl -n epfl-resslab-resslab-hub-prod logs -f deployment/resslab-hub-backend-prod
```

- [ ] The admin page open, signed in as admin.
- [ ] The review queue open, signed in as curator.
- [ ] The quick start printed or on the screen.

During the session:

- [ ] If a person gets no mail, they sign in with GitHub or ORCID, then you set their role on the admin page. An ORCID account with no address cannot submit: the person adds an address on "Your account" first.
- [ ] If a person with a non-academic address is a viewer, set their role to contributor on the admin page.
- [ ] Watch the logs for 429 (a rate limit) and 503 (the queue is full, or GitHub is not set up).
- [ ] If the room hits a rate limit, restart the backend pod between two steps of the session. The limits live in memory and go away. Sessions live in the database, so nobody is signed out.
- [ ] Tell the attendees to keep their batch folder on their laptop. A reload of the editor loses the work that is not submitted.
- [ ] Nobody merges a pull request during the session, unless you decided it before.

## After the workshop

The same day:

- [ ] Write the list of the pull requests of the day, with the person and the decision (merge or close).
- [ ] Close the exercise pull requests and delete their branches.

In the week after:

- [ ] Review and merge the pull requests with real data (squash merge). The upload workflow of the data repository sends them to prod. Restart the backend pod so they show at once.
- [ ] Put back the settings of the day: `MAX_OPEN_CONTRIBUTIONS`, `CONTRIBUTOR_DOMAINS` if it was for the day only, `DATA_REPO_REVIEWERS`, the rate limits.
- [ ] Choose: keep contributions on, or set `CONTRIBUTIONS_ENABLED=false` again.
- [ ] Disable the test accounts (tester and rehearsal). Set back to "Automatic" the roles that you set by hand and that must not stay.
- [ ] Write down what broke, with the times, and open an issue for each.
- [ ] Ask the attendees what was hard.
