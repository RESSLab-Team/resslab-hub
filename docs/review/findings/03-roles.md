# Findings of package 03: roles

- Branch: `review/03-roles`
- Commit reviewed: `0e15c031` (from `dev`, with ORCID)
- Date: 2026-11-12
- Tests run: yes, from the host shell (the sandbox hides `secrets/.env`). With `--runxfail`, the three `test_review_03_*` tests fail on their assert, as expected. The browser proofs were made on the local servers.

## Summary

| Id   | Severity | Title                                                                  | Suspicion        | Proof                    |
| ---- | -------- | ---------------------------------------------------------------------- | ---------------- | ------------------------ |
| 03-1 | medium   | A role stays after its source is gone, until the next sign-in          |                  | test                     |
| 03-2 | medium   | An admin can merge a locked admin away                                 |                  | test                     |
| 03-3 | low      | The GitHub role is read by login name, a renamed login reads someone else | S4 (confirmed) | test                     |
| 03-4 | low      | `/curation/:prNumber` refuses an owner who is a viewer                 |                  | Python call + code       |
| 03-5 | note     | With contributions off, nobody can sign out                            |                  | existing test            |
| 03-6 | note     | `CONTRIBUTOR_DOMAINS` is empty, and `alumni.epfl.ch` counts as academic | B6 (confirmed)  | k8s config + Python call |
| 03-7 | note     | Curation answers 404 before the access check                           |                  | Chrome                   |
| 03-8 | note     | `/validate` lets any signed-in viewer in, with no flag check           |                  | Chrome + code            |
| 03-9 | note     | The 403 body names the role that is needed                             |                  | Chrome                   |

## Question 1. The matrix

159 operations in `openapi.json`, plus the hidden `POST /validate/` (`backend/resslab_hub/routers/root.py:243`, `include_in_schema=False`, same handler as `POST /validate`). The codes come from the dependencies and the checks in the handlers. Cells proven in the browser are marked with `(c)`.

Columns: Anon = no cookie. Viewer, Contrib, Curator, Admin = signed in with a session cookie. Machine = `API_PASSWORD` with Basic auth and no cookie. Off = `CONTRIBUTIONS_ENABLED=false`, any caller.

Rules that apply to every row:

- A write (`POST`, `PUT`, `PATCH`, `DELETE`) from another site gets 403 from the CSRF middleware before any check.
- The machine credential never passes `require_user` or `require_role`: it gets 401 there, with no `WWW-Authenticate`.
- A signed-in person never passes `require_service` (`/upload`, `/user`): 401 with `WWW-Authenticate: Basic`.
- "own" means the person who made the submission (`owns_submission`, `backend/resslab_hub/contributions/trailers.py:184`). Rows marked `*` answer 503 when the GitHub App is not set, and 404 when the PR does not exist or is not open, before the access check.

### Root, features, analytics, dictionary, map

| Route                         | Anon | Viewer | Contrib   | Curator | Admin | Machine | Off  |
| ----------------------------- | ---- | ------ | --------- | ------- | ----- | ------- | ---- |
| GET /                         | 200  | 200    | 200       | 200     | 200   | 200     | 200  |
| GET /features                 | 200 (c) | 200 | 200       | 200     | 200   | 200     | 200 `false` |
| GET /healthz, GET /readyz     | 200  | 200    | 200       | 200     | 200   | 200     | 200  |
| POST /upload                  | 401  | 401    | 401       | 401     | 401   | 200     | 200  |
| POST /validate, /validate/    | 401 (c) | 200 (c) **(!)** | 200 (c) | 200 | 200 | 200     | 200 **(!)** |
| GET /user                     | 401  | 401    | 401       | 401     | 401   | 200     | 200  |
| GET /analytics/users          | 200  | 200    | 200       | 200     | 200   | 200     | 200  |
| GET /dictionary               | 200  | 200    | 200       | 200     | 200   | 200     | 200  |
| GET /dictionary/{db}/readme   | 200  | 200    | 200       | 200     | 200   | 200     | 200  |
| GET /map/sites                | 200  | 200    | 200       | 200     | 200   | 200     | 200  |

For `/validate`, "200" means the request gets in (the browser proof answered 422 on a bad body, past the auth). `(!)` see 03-8.

### Auth (`backend/resslab_hub/routers/auth.py`)

| Route                                  | Anon | Viewer | Contrib | Curator | Admin | Machine | Off |
| -------------------------------------- | ---- | ------ | ------- | ------- | ----- | ------- | --- |
| GET /auth/me                           | 200 `null` (c) | 200 | 200 | 200 | 200 | 200 `null` | 200 |
| POST /auth/email/start                 | 200  | 200    | 200     | 200     | 200   | 200     | 404 |
| POST /auth/email/verify                | 200  | 200    | 200     | 200     | 200   | 200     | 404 |
| POST /auth/logout                      | 204  | 204    | 204     | 204     | 204   | 204     | 404 **(!)** |
| GET /auth/identities                   | 401  | 200 (c) | 200 (c) | 200   | 200   | 401     | 404 |
| DELETE /auth/identities/{id}           | 401  | 204    | 204     | 204     | 204   | 401     | 404 |
| POST /auth/identities/{id}/main        | 401  | 204    | 204     | 204     | 204   | 401     | 404 |
| POST /auth/emails                      | 401  | 200    | 200     | 200     | 200   | 401     | 404 |
| POST /auth/emails/verify               | 401  | 200    | 200     | 200     | 200   | 401     | 404 |
| POST /auth/access-request              | 401  | 201    | 409 (c) | 409     | 409   | 401     | 404 |
| GET /auth/github/start, /callback      | 3xx  | 3xx    | 3xx     | 3xx     | 3xx   | 3xx     | 404 |
| GET /auth/orcid/start, /callback       | 3xx  | 3xx    | 3xx     | 3xx     | 3xx   | 3xx     | 404 |

The access request answers 409 `already_granted` when the role asked is not above the current one. `(!)` see 03-5.

### Contributions and curation

| Route                                       | Anon | Viewer              | Contrib             | Curator | Admin | Machine | Off |
| ------------------------------------------- | ---- | ------------------- | ------------------- | ------- | ----- | ------- | --- |
| POST /contributions                         | 401  | 403                 | 201                 | 201     | 201   | 401     | 404 |
| PUT /contributions/{pr}                     | 401  | 403                 | 200 own, 403 other  | 200 own, 403 other | 200 own, 403 other | 401 | 404 |
| GET /contributions                          | 401 (c) | 403 (c)          | 403 (c)             | 200     | 200   | 401     | 404 |
| GET /contributions/{pr} `*`                 | 401 (c) | 200 own, 403 other, 404 (c) | 200 own, 403 other | 200 | 200 | 401 | 404 |
| GET /contributions/{pr}/validation `*`      | 401  | same as above (c)   | same                | 200     | 200   | 401     | 404 |
| GET /contributions/{pr}/comments `*`        | 401  | same                | same                | 200     | 200   | 401     | 404 |
| GET /contributions/{pr}/files `*`           | 401  | same                | same                | 200     | 200   | 401     | 404 |
| GET /contributions/{pr}/curves `*`          | 401  | same                | same                | 200     | 200   | 401     | 404 |

`PUT` needs the contributor role and ownership. `GET /contributions/{pr}` and its sub-routes need only a session and ownership, so a viewer who owns a submission reads it. That is on purpose (a contributor can lose the role), but the frontend disagrees, see 03-4.

### Verification (`backend/resslab_hub/routers/verification.py`)

| Route                                      | Anon | Viewer | Contrib | Curator | Admin | Machine | Off |
| ------------------------------------------ | ---- | ------ | ------- | ------- | ----- | ------- | --- |
| GET /verification                          | 401  | 403    | 403 (c) | 200     | 200   | 401     | 404 |
| POST /verification                         | 401  | 403    | 403     | 201     | 201   | 401     | 404 |
| GET /verification/{db}/batch               | 401  | 403    | 403 (c) | 200     | 200   | 401     | 404 |
| GET /verification/{db}/validation          | 401  | 403    | 403     | 200     | 200   | 401     | 404 |
| GET /verification/{db}/files               | 401  | 403    | 403     | 200     | 200   | 401     | 404 |

### Admin (`backend/resslab_hub/routers/admin.py`, router deps at line 54)

| Route                                         | Anon | Viewer  | Contrib | Curator | Admin | Machine | Off |
| --------------------------------------------- | ---- | ------- | ------- | ------- | ----- | ------- | --- |
| GET /admin/users                              | 401 (c) | 403 (c) | 403 (c) | 403  | 200   | 401     | 404 |
| PATCH /admin/users/{id}                       | 401  | 403     | 403     | 403     | 200, 403 self or locked | 401 | 404 |
| POST /admin/users/{id}/merge                  | 401  | 403     | 403     | 403     | 200, 403 self only **(!)** | 401 | 404 |
| GET /admin/invitations                        | 401  | 403     | 403 (c) | 403     | 200   | 401     | 404 |
| POST /admin/invitations                       | 401  | 403     | 403     | 403     | 201   | 401     | 404 |
| DELETE /admin/invitations/{id}                | 401  | 403     | 403     | 403     | 204   | 401     | 404 |
| GET /admin/access-requests                    | 401  | 403     | 403 (c) | 403     | 200   | 401     | 404 |
| POST /admin/access-requests/{id}/approve      | 401  | 403     | 403     | 403     | 200, 409 decided | 401 | 404 |
| POST /admin/access-requests/{id}/decline      | 401  | 403     | 403     | 403     | 200, 409 decided | 401 | 404 |

`(!)` see 03-2.

### Data routers

The nine data routers (`braces`, `columns`, `connections`, `materials`, `residual-stress`, `hss-column`, `eccentric-braced-frame`, `tensile-coupon`, `ductile-fracture`) have only `GET` routes and no auth dependency. Every one answers 200 to every caller, also with contributions off. 104 operations:

| Router                   | Paths                                                                                                                                                        |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| every router             | `""`, `/fields`, `/counts`, `/range`, `/matrix`, `/csv`, `/distinct` (`/materials` also has `/date-range`)                                                   |
| /braces                  | `/{id}/displacement`, `+/csv`                                                                                                                                |
| /columns                 | `/{id}/axial-shortening`, `/{id}/moment-strong`, `/{id}/moment-weak`, each `+/csv`                                                                           |
| /connections             | `/{id}/beam`, `/beam-west`, `/global`, `/global-west`, `/panel-zones`, each `+/csv`                                                                          |
| /materials               | `/{id}/stress-strain`, `+/csv`                                                                                                                               |
| /residual-stress         | `/{id}/distribution-f1`, `/distribution-f2`, `/distribution-w1`, `/qp-coefficient`, each `+/csv`                                                             |
| /hss-column              | `/{id}/moment-rotation`, `+/csv`                                                                                                                             |
| /eccentric-braced-frame  | `/{id}/shear-link-angle`, `+/csv`                                                                                                                            |
| /tensile-coupon          | `/{id}/stress-strain`, `+/csv`                                                                                                                               |
| /ductile-fracture        | `/{id}/force-elongation`, `/force-elongation-simulation`, `/force-radial`, `/force-radial-simulation`, `/epeq-simulation`, `/lode-simulation`, `/triax-simulation`, each `+/csv` |

Browser proofs (local servers, http://127.0.0.1:19225, `fetch` from the page):

```text
anonymous
> GET /api/auth/me                   200 {"user":null}
> GET /api/features                  200 {"contributions":true}
> GET /api/contributions             401 {"detail":"Sign in to continue"}
> GET /api/contributions/1           401 {"detail":"Sign in to continue"}
> GET /api/verification              401 {"detail":"Sign in to continue"}
> GET /api/admin/users               401 {"detail":"Sign in to continue"}
> POST /api/validate                 401 {"detail":"Sign in to continue"}

viewer (<redacted>@example.com, role viewer, source default)
> GET /api/contributions             403 {"detail":"This action needs the curator role."}
> GET /api/contributions/1           404 {"detail":"This pull request is not open."}
> GET /api/contributions/1/validation 404 {"detail":"This pull request is not open."}
> POST /api/validate?type=braces     422 (enum error on the body, so past the auth)
> GET /api/admin/users               403 {"detail":"This action needs the admin role."}
> GET /api/auth/identities           200

contributor (<redacted>@epfl.ch, role contributor, source academic-email)
> GET /api/contributions             403 {"detail":"This action needs the curator role."}
> GET /api/verification              403 {"detail":"This action needs the curator role."}
> GET /api/verification/braces/batch 403 {"detail":"This action needs the curator role."}
> GET /api/admin/users               403 {"detail":"This action needs the admin role."}
> GET /api/admin/invitations         403 {"detail":"This action needs the admin role."}
> GET /api/admin/access-requests     403 {"detail":"This action needs the admin role."}
> POST /api/validate                 422 (past the auth)
> POST /api/auth/access-request {}   409 {"detail":"already_granted"}
> GET /api/auth/identities           200
```

The admin and curator columns are not shown in the browser: the local `ADMIN_EMAILS` is empty, so no local account is admin (see "Not checked").

## Question 2. Open routes that write or return personal data

No finding. The only routes with no auth are `GET` on the data routers, `/dictionary`, `/map/sites`, `/analytics/users`, `/features`, `/`, `/healthz`, `/readyz`, plus the sign-in starts. The data tables have no person column: `reference` is a paper citation, and `/map/sites` returns the lab, the program and the investigator name of a published test program. `/analytics/users` returns one number. Every route that needs a session sits under a prefix that the response cache skips (`backend/resslab_hub/utils/caching.py:160-178`: `/auth`, `/account`, `/admin`, `/contributions`, `/verification`, `/user`, `/features`), so a cached answer of one person is never served to another. `ROOT_PATH=/api` does not change this: Traefik strips `/api` and the middleware reads `scope["path"]`.

## Question 3. The owner rule

No finding. `owns_submission` (`backend/resslab_hub/contributions/trailers.py:184`) compares the submitter address of the commit trailers, stripped and lowercased, with the verified addresses of the account, lowercased. An address in a different case is the same address on both sides, so it does not open someone else's submission and does not hide one's own. To add the other person's address, an account needs the code mailed to that address (`POST /auth/emails` then `/auth/emails/verify`), and gets `EmailTaken` when another account already holds it. So the only way in is to control the mailbox, which is what ownership means here. One case stays: a submitter who never made an account. Anyone who later proves that address owns the submission. That is the intent.

## Question 4. Role precedence and the last admin

An admin cannot change a locked admin (an `ADMIN_EMAILS` address or a GitHub admin) with `PATCH`: 403 `locked_admin` (`backend/resslab_hub/routers/admin.py:110`). An admin cannot change their own account with `PATCH` (`cannot_change_self`, line 106) and cannot merge their own account away (line 147). So the last admin who is not locked cannot remove themself. Another admin can lower them, which is the intent. But the merge does not check `is_locked_admin`.

### 03-2 An admin can merge a locked admin away

- Severity: medium
- Suspicion: none
- Where: `backend/resslab_hub/routers/admin.py:147`, `backend/resslab_hub/auth/users.py:425`
- Status: new

`POST /admin/users/{keep}/merge` with `from_user_id` set to a locked admin only refuses when that account is the caller's own. `merge_users` then moves the identities and the main address of the locked admin to the kept account, deletes the locked admin's account and ends its sessions. The `ADMIN_EMAILS` address now signs in to the kept account, which becomes admin. So an admin can do with a merge what `locked_admin` refuses with `PATCH`: remove a configured admin, or give its address (and the admin role) to another account. It needs an admin who clicks the wrong pair, or who wants to do it.

Proof: `backend/tests/test_review_03_admin.py::test_an_admin_cannot_merge_a_locked_admin_away`, marked `xfail(strict=True)`. Run with `--runxfail`: fails with `assert 200 == 403`. The test first checks that `PATCH` on the same account answers `locked_admin`, then that the merge does too.

Fix: refuse the merge with 403 `locked_admin` when `other` is a locked admin, like `PATCH`. Keep merging into a locked admin allowed (that is how a configured admin gathers their own accounts).

### 03-1 A role stays after its source is gone, until the next sign-in

- Severity: medium
- Suspicion: none
- Where: `backend/resslab_hub/auth/deps.py:92`, `backend/resslab_hub/auth/github_sync.py:53`, `backend/resslab_hub/auth/sessions.py:54`
- Status: new

The stored `role` is worked out again (`apply_role`) only at a sign-in, an address change, an admin `PATCH`, a merge, and the hourly GitHub sync. The sync returns at once for an account with no GitHub login (`github_sync.py:53`), so for an email or ORCID account nothing recomputes the role on a request. When Pierre removes an address from `ADMIN_EMAILS` and restarts the backend, the person keeps the admin role on every request until their session ends. A session lasts 30 days from its creation (`session_ttl_days`, it does not slide). The same holds when `CONTRIBUTOR_DOMAINS` loses a domain. `docs/auth.md` ("When a change shows") speaks only of adding an entry, not removing one.

The workaround: once the address left `ADMIN_EMAILS`, the account is no longer locked, so another admin can disable it or lower it with `PATCH`, which recomputes the role and ends the sessions.

Proof: `backend/tests/test_review_03_roles.py::test_an_address_removed_from_admin_emails_is_no_longer_admin`, marked `xfail(strict=True)`. Run with `--runxfail`: fails with `assert 200 == 403`.

Fix: recompute the role in `get_current_user` when it is cheap (`derive_role` reads only the row and the settings), or revoke the sessions whose `role_source` no longer matches at startup.

To check by Pierre: is "at the next sign-in" enough for a removed admin, or should the doc say how to remove one now?

## Question 5. GitHub sync (S4)

The permission is read at a GitHub sign-in or link (`backend/resslab_hub/routers/auth.py:547`, `:571`), at an ORCID or email sign-in when a login is stored (`:198`, `:685`), when an address absorbs a bare account (`:403`), and on any request once it is older than one hour (`backend/resslab_hub/auth/deps.py:92`, `MAX_AGE` in `backend/resslab_hub/auth/github_sync.py:26`). The read runs on the request path with a 5 s timeout. On any error (rate limit, 5xx, timeout) the old permission stays and the next try is in 5 minutes (`github_sync.py:60-67`): the role neither drops nor goes up, which is safe. A 404 from GitHub gives `none`. With no GitHub App, the stored permission stays as it is forever.

### 03-3 The GitHub role is read by login name, a renamed login reads someone else

- Severity: low
- Suspicion: S4 (confirmed)
- Where: `backend/resslab_hub/auth/github_sync.py:58`, `backend/resslab_hub/routers/auth.py:544`, `:570`, `backend/resslab_hub/models/database/auth.py:88`
- Status: new

The GitHub identity is stored by its numeric id, but the permission is asked for `user.github_login`, the name saved at the last GitHub sign-in or link. When a person renames their GitHub login and keeps signing in by email or ORCID, the Hub keeps asking for the old name every hour. If someone else takes that name, the Hub gives the person the permission of the new holder on the data repo, up or down. `github_login` is not unique, so two accounts can also hold the same name. It needs a rename, then a stranger who takes the name and has access to the data repo: very unlikely.

Proof: `backend/tests/test_review_03_roles.py::test_a_github_role_is_not_read_from_a_login_someone_else_took`, with the `github_permissions` fixture, marked `xfail(strict=True)`. Run with `--runxfail`: fails with `assert 'admin' != 'admin'`.

Fix: read the login from the GitHub id before asking the permission (`GET /user/{id}`), or store the id and refresh `github_login` at each sync.

## Question 6. Academic addresses (B6)

`is_academic`, called directly:

| Address               | Result |
| --------------------- | ------ |
| `x@epfl.ch`           | True   |
| `x@ethz.ch`           | True   |
| `x@gmail.com`         | False  |
| `x@student.epfl.ch`   | True   |
| `x@sub.uni.edu`       | True   |
| `x@nus.edu.sg`        | True   |
| `X@EPFL.CH`           | True   |
| `x@epfl.ch.`          | False (and the API refuses it before: "An email address cannot end with a period") |
| `x@alumni.epfl.ch`    | True   |
| `x@epfl.ch.evil.com`, `x@evil-epfl.ch`, `x@edu` | False |

A role that comes from an academic address leaves with it: removing the address or changing the main one calls `apply_role`. A role from an invitation or an access request is a `role_override` and stays after the address is removed. `docs/auth.md` says so, it is the intent.

### 03-6 `CONTRIBUTOR_DOMAINS` is empty, and `alumni.epfl.ch` counts as academic

- Severity: note
- Suspicion: B6 (confirmed)
- Where: `~/code/enack8s-app-config/epfl-resslab/resslab-hub/base/kustomization.yaml:30` (only `ADMIN_EMAILS` is set), `backend/resslab_hub/auth/roles.py:89`
- Status: new

No overlay sets `CONTRIBUTOR_DOMAINS`. At the workshop, a person with a company or a gmail address signs in as viewer and must send an access request, then wait for an admin. The swot stoplist removes `alumni.stanford.edu` and the like, but `alumni.epfl.ch` passes, so a former student is a contributor.

Proof: the grep of the three overlays finds no `CONTRIBUTOR_DOMAINS`, and the `is_academic` table above.

Fix: none in code. Decide before the workshop.

To check by Pierre: should the workshop domains (the companies and firms that come) go into `CONTRIBUTOR_DOMAINS` on prod, or should an admin approve requests during the session? Should alumni addresses count?

## Question 7. Invitations and access requests

An invitation is redeemed by every path that proves an address: email sign-in, GitHub or ORCID sign-in with that verified address, adding the address later (`POST /auth/emails/verify`), and a merge (`backend/resslab_hub/auth/access.py:55`). So an account that adds the address later gets it, after the mailed code. The role is the one written by the admin on the invitation, and `grant` only raises a role, never lowers it. With two invitations for the same address, the higher one wins. No role above the intended one.

Two admins who decide the same access request at the same time can both pass the `pending` check (see "Not proven").

## Question 8. Feature flag

No finding in the code. `contributions`, `curation`, `verification` and `admin` have `require_contributions_enabled` on the router. In `auth.py`, every route has `_ENABLED` except `GET /auth/me`, checked one by one (lines 131 to 611). `/features`, `/validate`, `/upload`, `/user`, the data routers, `/dictionary`, `/map` and `/analytics` have no flag, on purpose. The existing test `backend/tests/test_features.py:72-101` already proves the 404 sweep and `/auth/me`.

### 03-5 With contributions off, nobody can sign out

- Severity: note
- Suspicion: none
- Where: `backend/resslab_hub/routers/auth.py:209`
- Status: new

`POST /auth/logout` has the flag. When the flag goes back to `false` after the workshop, a person who is still signed in keeps a valid session (30 days, `session_ttl_days`) and `/auth/me` still returns them. They cannot sign out: the route answers 404. The session does nothing while the flag is off, so it is harmless, but it comes back to life if the flag is turned on again within 30 days. `test_features.py:85` asserts the 404, so this is on purpose today.

Proof: `backend/tests/test_features.py::test_pipeline_answers_404_when_switched_off` with `("POST", "/auth/logout")`.

Fix: leave `/auth/logout` out of the flag, like `/auth/me`.

To check by Pierre: is a 404 on sign-out the intent?

## Question 9. Frontend guard

`resolveGuard` (`frontend/src/router/guards.ts`) sends to home when contributions are off, then to Login, then to Forbidden by rank. The ranks match the backend for `/curation` (curator), `/curation/verify/:type` (curator), `/admin` (admin), `/contribute/new` and `/contribute/edit/:prNumber` (contributor). On `/curation/:prNumber`, a contributor who is not the owner gets the page then a backend 403, which is the intent.

### 03-4 `/curation/:prNumber` refuses an owner who is a viewer

- Severity: low
- Suspicion: none
- Where: `frontend/src/router/index.ts:210`, `backend/resslab_hub/routers/curation.py:506`
- Status: new

The route asks `auth: 'contributor'`. The backend asks only a session and ownership. A person who submitted as contributor, then lost the role (the academic address removed, or the role lowered by an admin), is sent to the Forbidden page for their own submission, while the API would let them read it. The reverse (the page shown, the API refusing) only happens for the non-owner contributor, on purpose.

Proof:

```text
uv run python, calling the backend check directly
> curation._check_access(request with a viewer whose verified address is <redacted>,
>                        pull 1, owner address in another case)
passes, no exception (role = viewer)
```

and `index.ts:210`: `meta: { auth: 'contributor', contributions: true }`. Not shown in the browser: the viewer session was lost on navigation, see "Not proven".

Fix: give `/curation/:prNumber` `auth: 'viewer'` and let the backend decide, or make the backend ask contributor too.

## Question 10. The 401 and 403 answers

No address and no owner name in any 401 or 403 body. The 401 says "Sign in to continue". The owner refusal says "Only curators and the person who made this submission can see it." (`backend/resslab_hub/routers/curation.py:519`).

### 03-9 The 403 body names the role that is needed

- Severity: note
- Suspicion: none
- Where: `backend/resslab_hub/auth/deps.py:117`, `:153`
- Status: new

`require_role` answers "This action needs the curator role." The role names are in the public docs and the frontend, so this says nothing secret. It helps the person, keep it.

Proof: the browser transcript of question 1.

Fix: none.

### 03-7 Curation answers 404 before the access check

- Severity: note
- Suspicion: none
- Where: `backend/resslab_hub/routers/curation.py:262-290` (called before `_check_access` at line 506)
- Status: new

Any signed-in person learns whether a pull request number exists and is open, before the owner check. The data repo is public, so this shows nothing new.

Proof: the viewer lines of question 1 (`404 This pull request is not open.`).

Fix: none needed.

### 03-8 `/validate` lets any signed-in viewer in, with no flag check

- Severity: note
- Suspicion: none
- Where: `backend/resslab_hub/routers/root.py:238-250`
- Status: new

`require_user_or_service` lets every signed-in account in, viewer included, also with contributions off. With `check_duplicates=true` it reads GitHub (`flag_repo_duplicates`), limited to 30 per minute. The comment at lines 229 to 236 says any signed-in account passes on purpose (contributors check a batch before they ask for the role). Only noted because it is the one write-like route open to a viewer.

Proof: the viewer and contributor lines of question 1 (422, past the auth).

Fix: none needed.

## Rejected suspicions

| Suspicion | Why it is not a problem | Where |
| --------- | ----------------------- | ----- |
| S4, the error part | A GitHub error or rate limit keeps the old permission and retries in 5 minutes. The role does not drop and does not go up. | `backend/resslab_hub/auth/github_sync.py:60-67` |
| Q3, case | Both sides are lowercased before the compare. | `backend/resslab_hub/contributions/trailers.py:184` |
| Q3, adding the other person's address | Adding an address needs the mailed code, and `EmailTaken` refuses an address held by another account. | `backend/resslab_hub/auth/users.py:272` |
| Q8, a route without the flag | Every pipeline route has the flag on the router or `_ENABLED`. | `backend/resslab_hub/routers/auth.py:78`, `admin.py:54`, `contributions.py:59`, `verification.py:66` |
| Q2, cached personal answers | Every route with a session is excluded from the response cache. | `backend/resslab_hub/utils/caching.py:160-178` |
| Q4, the last admin removes themself | `cannot_change_self` on `PATCH` and on merge of one's own account. | `backend/resslab_hub/routers/admin.py:106`, `:147` |

## Not proven

- Approve and decline at the same time (Q7). `_decide` (`backend/resslab_hub/routers/admin.py:272-296`) reads the request without a row lock, checks `status != "pending"`, grants, then writes. Two admins who click approve and decline at the same moment can both pass the check: the role is given, the request ends "declined" (the last commit wins), and the approved mail is sent. Needs two real concurrent sessions, no test written. Fix: `SELECT ... FOR UPDATE`, or an `UPDATE ... WHERE status = 'pending'` that checks the row count.
- A non-owner makes the server read GitHub. `_check_access` calls `_owner` (`backend/resslab_hub/routers/curation.py:489`), which builds the full detail from GitHub before it refuses a non-owner. So any signed-in viewer can make the backend do several GitHub API calls per request, 30 per minute per address. Not measured.
- The Forbidden page for 03-4 in the browser. The viewer session was lost when the tab navigated to `/curation/1` (`/api/auth/me` then answered `{"user":null}`). The cause is not known (maybe the Chrome profile), not looked at further.

## Not checked

- The admin and curator columns in the browser: the local `ADMIN_EMAILS` is empty, so no local account is admin, and giving one a role needs an admin. These cells come from the code and the existing tests (`test_admin.py`, `test_curation.py`, `test_verification.py`).
- `POST /contributions`, `PUT /contributions/{pr}` and `POST /verification` in the browser: they write on GitHub.
