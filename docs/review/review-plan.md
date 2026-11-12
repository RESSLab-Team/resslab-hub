# Review plan

This is Pierre's plan for the review. It has two parts:

1. Things to check first. They came up while I read the code to write this plan. None is confirmed with a test yet. Each one can hurt the workshop.
2. The 11 work packages. Each has an owner, files, questions, a method and an output. The agent packages have a brief in [briefs/](briefs/).

Paths are from the repo root. `backend/resslab_hub/` is shortened to `rh/` in the tables.

## Things to check first

### Workshop blockers

| #   | Suspicion                                                                                                                                                                                                                                                                           | Where                                                                                                          | Package     |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | ----------- |
| B1  | Limits are per IP, and a room shares one IP. Sign-in mails: 20 per IP per hour. `/validate`: 30 per minute, and the editor validates 2 s after each edit. Submit: 5 per hour. Edit: 10 per hour. The docstring of `_check_queue_capacity` says "per account", but the key is the IP | `rh/utils/rate_limit.py`, `rh/auth/email_login.py:44`, `rh/routers/root.py`, `rh/routers/contributions.py:105` | 10          |
| B2  | Which IP does the backend see behind the nginx ingress? `FORWARDED_ALLOW_IPS=*`, and the comment in `rate_limit.py` still says Traefik. If the backend sees the ingress pod, every user of an environment shares the limits today. Check on stage first                             | `rh/utils/rate_limit.py`, k8s overlays                                                                         | 09          |
| B3  | Queue cap. A new submission gets 503 when 25 `contrib/` pull requests are open. Pull requests from forks with a `contrib/` head count too                                                                                                                                           | `rh/config.py:61`, `rh/routers/contributions.py:103`                                                           | 05, 10      |
| B4  | Each new pull request asks a review from every admin of the data repo, so each one gets a mail                                                                                                                                                                                      | `DATA_REPO_REVIEWERS=admins` (`rh/config.py:55`), `rh/contributions/reviewers.py`                              | 05          |
| B5  | The profile cannot be edited. No endpoint writes `display_name` or `institution` (ORCID branch included). The name is the local part of the address, the institution stays empty. So the public commit says `Jdoe <jdoe@uni.edu>`, with no institution                              | `rh/auth/users.py` (`name_from_email`), `rh/routers/auth.py`                                                   | 02, 10      |
| B6  | Only academic addresses (swot list) are contributors. `CONTRIBUTOR_DOMAINS` is empty on the three overlays. Other attendees are viewers until an admin invites them or sets their role                                                                                              | `rh/auth/roles.py`, k8s overlays                                                                               | 03, go-live |
| B7  | Prod config. `CONTRIBUTIONS_ENABLED=false` today. Prod needs `SMTP_*`, the GitHub OAuth pair, the GitHub App keys, an ORCID production client, and a restart                                                                                                                        | k8s prod overlay, Infisical                                                                                    | 09, go-live |
| B8  | One backend replica, and validation runs inside the request. One big archive can block everybody for its whole run                                                                                                                                                                  | `rh/routers/root.py`, `rh/data/validator.py`                                                                   | 04, 10      |
| B9  | Workshop pull requests land on the real public data repo, with real names and addresses in the commits. Decide if attendees submit real data or exercises                                                                                                                           | `rh/contributions/submission.py`, `trailers.py`                                                                | 07, go-live |
| B10 | Lost work. A reload loses a draft that is not submitted. There is no "my submissions" list, so a person who closes the result page must find their pull request on GitHub                                                                                                           | `frontend/src/stores/contribution.ts`, `ContributeView.vue`                                                    | 10          |

### Security and privacy

| #   | Suspicion                                                                                                                                                                                                                                                      | Where                                                                       | Package |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- | ------- |
| S1  | The response cache is keyed on the URL and sends `Cache-Control: public`. Only a list of excluded prefixes protects per-user answers. A new per-user route that nobody adds to the list leaks                                                                  | `rh/utils/caching.py:150`                                                   | 07      |
| S2  | Name and institution go into the pull request body with no escaping: markdown, HTML, `@mention`. The name can come from GitHub or ORCID. (Dismissed warnings are escaped, by `_code_span`)                                                                     | `rh/contributions/submission.py:278`                                        | 05      |
| S3  | The OAuth link callback attaches the identity to `link_user_id` from the stored state. The state is tied to the browser by the login cookie, but the callback does not check that the session is still the same user                                           | `rh/routers/auth.py` (GitHub and ORCID callbacks), `rh/auth/oauth_state.py` | 01      |
| S4  | The GitHub role is read by login name. A login can be renamed, and someone else can then take the old name                                                                                                                                                     | `rh/auth/github_sync.py`                                                    | 03      |
| S5  | Codes and OAuth states may not be consumed in one atomic step. Two requests at the same time could both pass                                                                                                                                                   | `rh/auth/email_login.py:179`, `rh/auth/oauth_state.py`                      | 01      |
| S6  | Bad input may give a 500: a bad UUID in a cookie or a path, non-ASCII Basic credentials, a long `redirect_to`, a long GitHub or ORCID name                                                                                                                     | `rh/auth/deps.py`, `rh/auth/sessions.py`, `rh/models/database/auth.py`      | 01, 02  |
| S7  | Raw exception text reaches the caller (#264 H3, still open)                                                                                                                                                                                                    | `rh/routers/contributions.py`, `rh/routers/root.py`                         | 05      |
| S8  | The CSP is report-only. No HSTS. The ingress sets no `proxy-body-size`: if the nginx default (1 MB) applies, an archive over 1 MB gets a 413, and if it does not, nothing bounds the body before the backend. The multipart body is read before the auth check | `frontend/nginx-security-headers.conf`, k8s ingress, `rh/routers/root.py`   | 08, 09  |
| S9  | A curator can verify their own submission                                                                                                                                                                                                                      | `rh/routers/verification.py`                                                | 06      |
| S10 | No account deletion, no data export, no cleanup of old sessions and challenges. Addresses stay public for ever in the data repo history. The consent is a sentence in the submit dialog, not a tick box                                                        | `rh/auth/`, `ContributeView.vue`, `locales/en.json`                         | 07      |
| S11 | The frontend switches the pipeline on when `GET /features` fails                                                                                                                                                                                               | `frontend/src/stores/features.ts`                                           | 08      |

When an agent confirms or rejects one of these, it writes the id (B1, S3, ...) in its finding.

## Work packages

Rules for every agent package:

- Review only. No fix, no refactor. A finding needs a file and line, and a proof: a failing pytest in a new test file, or a Claude in Chrome transcript on the local server (`wtx curl` does not reach it from the sandbox).
- Before any submit, make sure that `DATA_REPO` in `secrets/.env` is the test fork. If you cannot read it (the sandbox hides `secrets/`), do not submit. Write the case as "to test by Pierre".
- Never send a request to stage or prod.
- Output: `docs/review/findings/NN-<name>.md`, from the template in [findings/README.md](findings/README.md). Commit it on your branch.

Launch an agent from the main checkout, after ORCID is merged in `dev`:

```sh
wtx go review/01-sign-in --prompt docs/review/briefs/01-sign-in.md --no-attach --plan-effort high
```

Use the branch name `review/NN-<name>` and the brief with the same number.

### 01 Sign-in and sessions

- Owner: agent. Brief: [briefs/01-sign-in.md](briefs/01-sign-in.md).
- Scope: email code and link, GitHub, ORCID, OAuth state, the `resslab_login` and `resslab_session` cookies, CSRF, the `next` redirect, rate limits and SQL caps, account enumeration, logout.
- Files: `rh/routers/auth.py`, `rh/auth/email_login.py`, `rh/auth/oauth_state.py`, `rh/auth/github_oauth.py`, `rh/auth/orcid_oauth.py`, `rh/auth/sessions.py`, `rh/auth/csrf.py`, `rh/auth/urls.py`, `rh/auth/tokens.py`, `rh/auth/challenges.py`.
- Suspicions: S3, S5, S6.

### 02 Identity and account life

- Owner: agent. Brief: [briefs/02-identity.md](briefs/02-identity.md).
- Scope: several addresses, link and unlink, bare accounts and how they join, admin merge, disable, every way one person could take another person's account.
- Files: `rh/auth/users.py`, `rh/routers/auth.py`, `rh/routers/admin.py`, `rh/models/database/auth.py`, `rh/auth/access.py`.
- Suspicions: B5, S6.

### 03 Roles and access matrix

- Owner: agent. Brief: [briefs/03-roles.md](briefs/03-roles.md).
- Scope: every backend route against every role (anonymous, viewer, contributor, curator, admin, machine credential), role precedence, GitHub sync, invitations, access requests, the last admin, the 404 when the flag is off, the frontend guard.
- Files: `rh/auth/roles.py`, `rh/auth/deps.py`, `rh/auth/access.py`, `rh/auth/github_sync.py`, all of `rh/routers/`, `frontend/src/router/guards.ts`, `frontend/src/router/index.ts`.
- Suspicions: B6, S4.

### 04 Pipeline input

- Owner: agent. Brief: [briefs/04-pipeline-input.md](briefs/04-pipeline-input.md).
- Scope: what a user sends to `/validate`, `POST /contributions` and `PUT /contributions/{pr}`: archive format, paths, links, sizes, CSV parsing, formula cells, encodings, slow or crashing validation.
- Files: `rh/utils/safe_archive.py`, `rh/routers/root.py` (`enforce_request_size`), `rh/contributions/submission.py`, `rh/data/validator.py`, `frontend/src/utils/tar.ts`, `frontend/src/utils/intake.ts`.
- Suspicions: B8.

### 05 What we write to GitHub

- Owner: agent for the code. Pierre for the GitHub side: App permissions, the data repo ruleset, branch protection, who gets the review mails.
- Brief: [briefs/05-github-writes.md](briefs/05-github-writes.md).
- Scope: pull request title and body, commit trailers, branch names, the queue cap, the GitHub API rate limit, error text sent back, branches left behind when a step fails, the data repo workflows, `/upload`.
- Files: `rh/contributions/github.py`, `rh/contributions/trailers.py`, `rh/contributions/reviewers.py`, `rh/contributions/submission.py`, `rh/routers/contributions.py`, `rh/routers/root.py` (`/upload`), and in the data repo `.github/workflows/`.
- Suspicions: B3, B4, S2, S7.

### 06 Curation and verification

- Owner: agent. Brief: [briefs/06-curation.md](briefs/06-curation.md).
- Scope: who can open a submission (owner or curator), how ownership is decided (trailers, old JSON records), the per-process caches, self-verification, how GitHub text (comments, bodies) is shown in the Hub.
- Files: `rh/routers/curation.py`, `rh/routers/verification.py`, `rh/contributions/verification.py`, `rh/contributions/trailers.py`, `frontend/src/components/curation/ReviewThread.vue`, `frontend/src/views/CurationReviewView.vue`, `frontend/src/views/CurationQueueView.vue`.
- Suspicions: S9.

### 07 Privacy and leaks

- Owner: agent for the list and the code paths. Pierre for the decisions (retention, consent, deletion, real data at the workshop).
- Brief: [briefs/07-privacy.md](briefs/07-privacy.md).
- Scope: every piece of personal data the Hub stores or sends, where it goes (database, logs, mails, GitHub, analytics, HTTP caches), and for how long.
- Files: `rh/utils/caching.py`, `rh/auth/mailer.py`, `rh/contributions/submission.py`, `rh/main.py`, `rh/routers/root.py` (`/user`), `rh/routers/analytics.py`, `frontend/src/views/ContributeView.vue`, `frontend/src/locales/en.json`.
- Suspicions: B9, S1, S10.

### 08 Frontend

- Owner: agent. Brief: [briefs/08-frontend.md](briefs/08-frontend.md).
- Scope: `v-html` and DOMPurify, links that open new tabs, the CSP and what blocks it from enforcing, redirects after sign-in, local and session storage, the `/features` fail-open, hard-coded data repo links, error messages shown to the user.
- Files: `frontend/src/views/`, `frontend/src/stores/auth.ts`, `frontend/src/stores/features.ts`, `frontend/src/plugins/axios.ts`, `frontend/src/utils/contribution.ts`, `frontend/nginx-security-headers.conf`, `frontend/src/components/commons/UnitTableRow.vue`, `frontend/src/components/commons/tools/ToolSlider.vue`.
- Suspicions: S8 (frontend side), S11.

### 09 Deploy and config

- Owner: Pierre, with an agent that reads the k8s config only.
- Brief: [briefs/09-deploy-config.md](briefs/09-deploy-config.md).
- Scope: the ingress (headers, limits, body size, forwarded IP), secrets and what is missing on prod, public `/api/docs`, replicas and pod restarts, the CronJobs, a dependency audit.
- Files: `~/code/enack8s-app-config/epfl-resslab/resslab-hub/`, `rh/config.py`, `backend/Dockerfile`, `frontend/Dockerfile`, `backend/uv.lock`, `frontend/pnpm-lock.yaml`.
- Suspicions: B2, B7, S8 (ingress side).
- Pierre's part: compare the secrets of the three environments in Infisical, and make sure that each key that prod needs exists (see [go-live-checklist.md](go-live-checklist.md)).

### 10 Workshop readiness

- Owner: Pierre, with an agent that writes a load script for the local server.
- Brief: [briefs/10-workshop.md](briefs/10-workshop.md).
- Scope: 30 people on one network, signing in and submitting in the same 30 minutes. Limits, the queue cap, slow validation, and the UX gaps (profile, lost draft, no list of my submissions).
- Files: `rh/utils/rate_limit.py`, `rh/auth/email_login.py`, `rh/routers/contributions.py`, `rh/routers/root.py`, `frontend/src/stores/contribution.ts`, `frontend/src/views/ContributeView.vue`.
- Suspicions: B1, B3, B5, B8, B10.

### 11 Test gaps (wave 3)

- Owner: agent, after triage. This one writes tests, not findings.
- Brief: [briefs/11-test-gaps.md](briefs/11-test-gaps.md).
- Scope: tests for what the review found untested: 429 answers, cookie flags, every branch of the OAuth callbacks, specs for the auth views (`LoginView`, `LoginVerifyView`, `AccountView`, `ForbiddenView`, `AdminView`, `AccessRequestForm`).
- Files: `backend/tests/test_auth_flow.py`, `backend/tests/test_auth_units.py`, `backend/tests/test_admin.py`, `frontend/src/views/__tests__/`.

## Waves

| Wave | Packages           | When            |
| ---- | ------------------ | --------------- |
| 1    | 01, 02, 03, 04, 05 | T minus 4 weeks |
| 2    | 06, 07, 08, 09, 10 | T minus 3 weeks |
| 3    | 11, then the fixes | T minus 2 weeks |

Each wave has about 5 worktrees. Stop the server panes of an agent while it plans, to save RAM.

## Triage

Twice a week, Pierre reads the new findings and the tester's notes. For each one:

1. Give a severity (scale in [README.md](README.md)).
2. Open one issue on `RESSLab-Team/resslab-hub`, or merge it into an issue that exists, or write "won't fix" and why.
3. Blockers and high go to the fix list for T minus 2 weeks.
