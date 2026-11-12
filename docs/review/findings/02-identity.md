# Findings of package 02: identity

- Branch: `review/02-identity`
- Commit reviewed: `0e15c031` (from `dev`, with ORCID)
- Date: 2026-11-12
- Tests run: partly. The two tests on the pull request body (02-13) run without a database and fail as expected (`xfailed`). The other tests need the database, and the sandbox hides `secrets/.env`, so they are written but not run. The live proofs come from Claude in Chrome on this worktree's own servers.

## Summary

| Id    | Severity | Title                                                              | Suspicion | Proof                  |
| ----- | -------- | ------------------------------------------------------------------ | --------- | ---------------------- |
| 02-1  | low      | Two first sign-ins at once on one address give a 500               |           | Chrome + test (not run) |
| 02-2  | low      | An account can link a second GitHub or a second ORCID iD           |           | test (not run)         |
| 02-3  | low      | A bare join drops the role an admin gave the bare account          |           | test (not run)         |
| 02-4  | low      | An admin merge of two ORCID accounts is not refused                |           | test (not run)         |
| 02-5  | medium   | An admin merge can fold a locked admin away                        |           | test (not run)         |
| 02-6  | note     | An admin merge replaces a demotion with the higher role            |           | Chrome                 |
| 02-7  | low      | A link callback lands on an account disabled in the meantime       |           | test (not run)         |
| 02-8  | low      | The main address can end with no identity behind it                |           | Chrome + test (not run) |
| 02-9  | low      | Two unlinks at once can leave an account with no way in            |           | test (not run)         |
| 02-10 | medium   | Nobody can set their name or institution                           | B5 (confirmed) | Chrome + test (not run) |
| 02-11 | medium   | A GitHub or ORCID name over 200 characters breaks the sign-in      | S6 (confirmed) | test (not run)         |
| 02-12 | low      | Admin routes answer 500 to an id that is not a UUID                | S6 (confirmed) | Chrome + test (not run) |
| 02-13 | low      | The contributor name is raw Markdown in the pull request body      | S6        | test (run, xfailed)    |

All addresses used live are test addresses on `example.org`. Codes, tokens and the admin address are `<redacted>`.

## Question 1. Takeover by address

No takeover. An add-address code never gives a session on the holder of the address, except the bare join, which needs both proofs (02-3 is about that join). Capitals and spaces are normalized everywhere. A `+tag` makes another address, so another account, but that person proved the mailbox. The only problem found is a 500 when two sign-ins of a new address finish at the same time.

### 02-1 Two first sign-ins at once on one address give a 500

- Severity: low
- Where: `backend/resslab_hub/auth/users.py:124` (`sign_in_with_email` has no `IntegrityError` catch), called at `backend/resslab_hub/routers/auth.py:189`
- Status: new

A new address has no account yet. Two tabs (or a double click on the mail link) verify two challenges at the same time. Both look up the address, find nothing, and insert a user. The second insert hits the unique key `auth_user_email_key` and the generic handler answers 500. The person retries and gets in, so nobody loses anything. But at a workshop where 20 people sign in at once, this shows a scary error.

Proof:

```text
Claude in Chrome, on http://127.0.0.1:19247/
Two POST /api/auth/email/start for rev02.race@example.org, then the two links from the dev log:
> Promise.all([verify(link1), verify(link2)])   // POST /api/auth/email/verify {challenge, token}
[200, 500]
backend log: IntegrityError ... duplicate key value violates unique constraint "auth_user_email_key"
```

And `backend/tests/test_review_02_takeover.py::test_two_first_sign_ins_at_once_make_no_500`, marked `xfail(strict=True)`, not run.

Fix: catch the `IntegrityError` on the user insert, roll back, and read the user the other request just made.

## Question 2. Takeover by identity

No identity lands on another person's account. The provider subject is unique in the database, and a GitHub account whose primary address changed comes back to the same account by its numeric id. Two weak points: an account can collect a second GitHub or ORCID, and the link callback trusts the account stored at the start of the flow (02-7). A changed GitHub primary address is not added to the account: the old address stays the main one (by design, the identity is the GitHub id).

### 02-2 An account can link a second GitHub or a second ORCID iD

- Severity: low
- Where: `backend/resslab_hub/auth/users.py:179` (`attach_identity`), `backend/resslab_hub/routers/auth.py:539-544` and `:647-668`
- Status: new

`attach_identity` only refuses an identity that is on another account. It does not check that this account already has one of the same provider. The rule "one ORCID iD per account" exists in `absorb_bare_account` and the GitHub one in `merge_users`, but not here. A person who links a second GitHub ends with two GitHub identities, and `github_login` now names the second one. If they unlink it, the mirror is cleared while the first one stays linked. Same for ORCID and the `orcid` field, which goes into submissions.

Proof: `backend/tests/test_review_02_takeover.py::test_an_account_cannot_link_a_second_github` and `::test_an_account_cannot_link_a_second_orcid`, marked `xfail(strict=True)`, not run.

Fix: in the link branch, refuse with a clear error (for example `already_linked`) when the account already has an identity of that provider.

## Question 3. Bare join

The docstring of `absorb_bare_account` says the join gives no new power and loses nothing. Most of it holds: a bare account cannot make an access request (`auth.py:427-432` needs an address) nor a submission (`contributions.py:141` needs an address). Its sessions in other browsers go with it, and those browsers then get a clean 401. But a role an admin set on the bare account is lost.

### 02-3 A bare join drops the role an admin gave the bare account

- Severity: low
- Where: `backend/resslab_hub/auth/users.py:370` (`absorb_bare_account` copies the name, the iD and the GitHub mirror, not `role_override`)
- Status: new

An admin can set a role on any account, also on a GitHub or ORCID account with no address. When that person later adds the address of their main account, the bare account joins it and is deleted. Its `role_override` is not copied, so the curator role the admin gave is gone, with no word. The admin merge (`merge_users`) does keep the higher override, so the two joins disagree.

Proof: `backend/tests/test_review_02_join_merge.py::test_a_bare_join_keeps_the_role_an_admin_gave`, marked `xfail(strict=True)`, not run.

Fix: copy `role_override` with the same rule as `merge_users` (the higher one wins), or refuse the self join when the bare account has an override and ask for an admin merge.

## Question 4. Admin merge

What moves: identities, sessions are deleted (cascade, the other browser gets a 401), the higher `role_override`, access requests, the mirrors. `institution` of `other` is lost when `keep` has one. A self merge is refused (`same_account`), a merge into a disabled account too (`account_disabled`), and two GitHub accounts (`both_github`). Two ORCID iDs and a locked admin are not refused.

### 02-4 An admin merge of two ORCID accounts is not refused

- Severity: low
- Where: `backend/resslab_hub/auth/users.py:425-447` (`merge_users` checks `both_github` only)
- Status: new

The admin merges two accounts that each have an ORCID iD. The merge goes through. `keep` ends with two ORCID identities and one `orcid` field, which names only one of them. Same state as 02-2, reached by an admin.

Proof: `backend/tests/test_review_02_join_merge.py::test_a_merge_of_two_orcid_accounts_is_refused`, marked `xfail(strict=True)`, not run.

Fix: refuse `both_orcid` like `both_github`.

### 02-5 An admin merge can fold a locked admin away

- Severity: medium
- Where: `backend/resslab_hub/routers/admin.py:130-160` (`merge_user`), compare with `admin.py:110-113` (`update_user` refuses `locked_admin`)
- Status: new

A locked admin comes from `ADMIN_EMAILS` or from GitHub. The admin page refuses to change their role or disable them (`locked_admin`). The merge does not check it. An admin can merge a config admin into any account: the config admin's account is deleted, and its address moves to the other account. That other account would then be admin through `admin-email` (any verified address counts). It needs an admin to do it, so it is a weak protection, not an open door.

Proof: `backend/tests/test_review_02_join_merge.py::test_a_merge_cannot_fold_a_locked_admin_away`, marked `xfail(strict=True)`, not run.

Fix: refuse the merge with `locked_admin` when `other` is a locked admin, like `update_user`.

### 02-6 An admin merge replaces a demotion with the higher role

- Severity: note
- Where: `backend/resslab_hub/auth/users.py:451-452`
- Status: new

An admin sets `viewer` on account A on purpose (a demotion). Later the admin merges R (curator by override) into A. A becomes curator. `test_admin.py:603` chose "the stronger decision wins" on purpose, so this is the planned behaviour. But a demotion is a decision too, and the merge dialog says nothing.

Proof:

```text
Claude in Chrome, on http://127.0.0.1:19247/, signed in as the admin
A: role_override viewer. R: role_override curator.
> POST /api/admin/users/<A>/merge {"from_user_id": "<R>"}
200, A now: role curator, role_source override
```

Fix: show both roles in the merge dialog, or keep the override of `keep` and let the admin change it after.

To check by Pierre: is "the stronger wins" still what you want when `keep` was demoted?

## Question 5. Disable

Disabling revokes every session at once (`test_admin.py::test_disabling_signs_the_person_out_everywhere`). A disabled account cannot sign in again by mail or provider. The person can come back with a new address, GitHub or ORCID that is not on the old account: that makes a new account, and nothing links it to the old one. That is expected. An invitation to the old address is refused (`already_member`). One gap: the link callback.

### 02-7 A link callback lands on an account disabled in the meantime

- Severity: low
- Where: `backend/resslab_hub/routers/auth.py:534-549` (GitHub) and `:647-670` (ORCID)
- Status: new

The link branch reads `link_user_id` from the challenge and loads that account. It does not check `disabled_at`, and it does not check that the browser is still signed in as that account. So if an admin disables the account between "Link GitHub" and the callback, GitHub is linked anyway. The sign-in branch checks `disabled_at` (`auth.py:566`, `:680`), the link branch does not. Nobody gets a session, so the harm is small.

Proof: `backend/tests/test_review_02_lifecycle.py::test_a_link_does_not_land_on_an_account_disabled_meanwhile`, marked `xfail(strict=True)`, not run.

Fix: in the link branch, refuse a disabled account, and check that the current session is the account in `link_user_id`.

## Question 6. Remove an identity or an address

The last identity is protected (409 `cannot_unlink`), and the main address cannot be removed directly. Both rules are checked in Python on what the request read, so two requests at the same time break them. Removing an academic address works the role out again. A role from an invitation stays, which `docs/auth.md:424-426` says on purpose (see "Rejected suspicions").

### 02-8 The main address can end with no identity behind it

- Severity: low
- Where: `backend/resslab_hub/auth/users.py:307-327` (`set_main_email`) and `:330-356` (`remove_identity`)
- Status: new

Two tabs: one makes an added address the main one, the other removes it. Each request checks against the state it read, so both pass. The account ends with `User.email` set to an address that is no longer an identity. `get_by_email` still finds the account by `User.email`, so the removed address still signs in, and it still counts as verified for the role. This breaks the rule of `docs/auth.md:74-76`.

Proof:

```text
Claude in Chrome, on http://127.0.0.1:19247/, signed in as A (rev02.a + rev02.a2)
> Promise.all([POST /api/auth/identities/<a2>/main, DELETE /api/auth/identities/<a2>])
[204, 204]
> GET /api/auth/me
user.email = rev02.a2@example.org, identities = [rev02.a@example.org]
```

And `backend/tests/test_review_02_lifecycle.py::test_the_main_address_always_has_its_identity`, marked `xfail(strict=True)`, not run.

Fix: lock the user row (`SELECT ... FOR UPDATE`) in both functions, then check again.

### 02-9 Two unlinks at once can leave an account with no way in

- Severity: low
- Where: `backend/resslab_hub/auth/users.py:341` (`len(identities) <= 1`)
- Status: new

An account with no address, a GitHub login and an ORCID iD. Two tabs unlink one each. Both read two identities and both delete. The account has no way in left, and only an admin can help (and only by merging). Same cause as 02-8.

Proof: `backend/tests/test_review_02_lifecycle.py::test_two_unlinks_at_once_keep_one_way_in`, marked `xfail(strict=True)`, not run. Not shown live.

Fix: the same row lock as 02-8.

## Question 7. Profile (B5)

B5 is confirmed. No route writes `display_name` or `institution`: `PATCH` and `PUT /auth/me` answer 405, the admin patch has `role_override` and `disabled` only, and the account page only shows them.

| Way in   | `display_name`                                    | `institution` |
| -------- | ------------------------------------------------- | ------------- |
| Mail     | local part, capitalised (`name_from_email`, `users.py:67`) | empty |
| GitHub   | GitHub name, or the login                         | empty         |
| ORCID    | ORCID name, or the iD when the name is private    | empty         |

A submission refuses an empty name (`contributions.py:136`, never empty in practice) and leaves out an empty institution. So the public commit is signed like `Jdoe <jdoe@uni.edu>`, or with the ORCID iD as the name.

### 02-10 Nobody can set their name or institution

- Severity: medium
- Suspicion: B5 (confirmed)
- Where: `backend/resslab_hub/routers/auth.py` (no write route on `/auth/me`), `backend/resslab_hub/auth/users.py:67`
- Status: new

Every contribution goes to a public repository with the author name and institution from the account. Neither can be changed by the person or by an admin. Workshop people who sign in by mail will publish as their address local part, with no institution.

Proof:

```text
Claude in Chrome, on http://127.0.0.1:19247/, signed in as rev02.a
> fetch('/api/auth/me', {method: 'PATCH', body: '{"display_name":"Rev Two"}'})
405 Method Not Allowed
> GET /api/auth/me
display_name "Rev02 A", institution ""
```

And `backend/tests/test_review_02_profile_input.py::test_a_person_can_set_their_name_and_institution`, marked `xfail(strict=True)`, not run.

Fix: add `PATCH /auth/me` for `display_name` and `institution` (trimmed, with the column lengths), and a small form on the account page. Ask for the name before the first submission.

## Question 8. Bad input (S6)

Addresses are safe: `EmailStr` refuses an address that is too long with a 422, so the 320 column is never reached. Bad ids on `/auth/identities/{id}` answer 404. The provider names and the admin ids are not safe.

### 02-11 A GitHub or ORCID name over 200 characters breaks the sign-in

- Severity: medium
- Suspicion: S6 (confirmed)
- Where: `backend/resslab_hub/routers/auth.py:559` and `:678`, `backend/resslab_hub/models/database/auth.py:73` (`display_name` String(200))
- Status: new

The name from the provider goes into `display_name` without a cut. A name over 200 characters fails on the database insert, and the callback answers 500. The person can never sign in with that provider. GitHub names are short in practice, an ORCID name (given plus family names) is less sure. A GitHub login over 100 characters (`github_login` String(100)) would do the same, but GitHub logins are at most 39.

Proof: `backend/tests/test_review_02_profile_input.py::test_a_long_github_name_does_not_break_the_sign_in` and `::test_a_long_orcid_name_does_not_break_the_sign_in`, marked `xfail(strict=True)`, not run.

Fix: cut the name to the column length before the insert (and the login and handle too).

### 02-12 Admin routes answer 500 to an id that is not a UUID

- Severity: low
- Suspicion: S6 (confirmed)
- Where: `backend/resslab_hub/routers/admin.py:96` (patch user), `:130` and `:144` (merge, path and `from_user_id`), `:227-231` (revoke invitation), `:300` and `:314` (approve, decline)
- Status: new

The ids are plain `str`. asyncpg refuses a value that is not a UUID, and the generic handler answers 500. The zero UUID gives a 404, so only a bad string fails. Only admins reach these routes.

Proof:

```text
Claude in Chrome, on http://127.0.0.1:19247/, signed in as the admin
> PATCH /api/admin/users/not-a-uuid                         500 {"detail":"Internal server error"}
> POST /api/admin/users/not-a-uuid/merge                    500
> POST /api/admin/users/<A>/merge {"from_user_id":"x"}      500
> DELETE /api/admin/invitations/not-a-uuid                  500
> POST /api/admin/access-requests/not-a-uuid/approve        500
> POST /api/admin/access-requests/not-a-uuid/decline        500
> PATCH /api/admin/users/00000000-0000-0000-0000-000000000000   404
```

And `backend/tests/test_review_02_profile_input.py::test_an_id_that_is_not_a_uuid_is_a_404`, marked `xfail(strict=True)`, not run.

Fix: type the path params and `from_user_id` as `UUID`, so FastAPI answers 422, or turn the `DataError` into a 404.

### 02-13 The contributor name is raw Markdown in the pull request body

- Severity: low
- Suspicion: S6
- Where: `backend/resslab_hub/contributions/submission.py:293` (`build_pr_body`), read back by `backend/resslab_hub/routers/curation.py:165-189` (`_parse_pr_body`)
- Status: new

The name comes from GitHub or ORCID and nobody can change it. In the pull request body it is plain Markdown, not in a code span like the dismissed warnings (`_code_span`, #264 H4). A name with `@someone` pings that GitHub user on the public data repo, and a `[text](url)` shows a link. A name with a line break can add a `- **ORCID**:` line, and the review page then shows that iD as the contributor's. The mail notice and the commit trailers clean the name already. Whether GitHub or ORCID let a name hold a line break is not checked.

Proof: `backend/tests/test_review_02_profile_input.py::test_the_name_in_the_pull_request_is_plain_text` and `::test_a_name_cannot_add_a_line_the_review_page_reads`, marked `xfail(strict=True)`. Run: both `xfailed`, they fail on the asserts (`'@victim' is contained here`, `'0000-0002-1825-0097' == ''`).

Fix: put the name and the institution in `_code_span`, and drop line breaks, like the trailers do.

## Question 9. Database rules

| Rule                                                        | Kept by                                     | Broken by |
| ----------------------------------------------------------- | ------------------------------------------- | --------- |
| One account per main address                                | unique `auth_user.email` (`models/database/auth.py:71`) | 02-1 (gives a 500, not a duplicate) |
| One account per provider identity                           | unique `(provider, subject)`                | none      |
| One open invitation per address                             | partial unique index `auth_invitation_pending_email` | none |
| One open access request per account                         | partial unique index, `IntegrityError` caught at `auth.py:451` | none |
| Sessions, identities go with the account                    | `ON DELETE CASCADE`                         | none      |
| An address is on one account only (main and email identities) | Python only (`add_email`, `get_by_email`)  | not proven (see below) |
| One GitHub and one ORCID per account                        | Python only, and not on the link            | 02-2, 02-4 |
| The main address is one of the identities                   | Python only                                 | 02-8      |
| The last identity stays                                     | Python only                                 | 02-9      |
| Addresses are lower case                                    | Python only (`normalize_email`)             | none found |
| `github_login` and `orcid` mirror the identities            | Python only                                 | 02-2, 02-4 |

No `test_review_02_db_rules.py`: each broken rule has its test in the file of its question.

## Rejected suspicions

| Suspicion | Why it is not a problem | Where |
| --------- | ----------------------- | ----- |
| Capitals and spaces in an address make a second account | `"  Rev02.A@Example.ORG  "` signs in to `rev02.a@example.org`, checked live | `users.py:59-60` |
| An address over 320 characters gives a 500 | `EmailStr` answers 422 first, checked live | `models/auth.py:62`, `:84` |
| A bad id on `/auth/identities/{id}` gives a 500 | 404 for `DELETE` and `/main`, checked live | `routers/auth.py:233-285` |
| The last identity can be removed | 409 `cannot_unlink`, checked live (two requests at once: 02-9) | `users.py:341` |
| Disable leaves sessions alive | already covered by `test_admin.py::test_disabling_signs_the_person_out_everywhere` | `routers/admin.py:96` |
| Removing the invited address leaves the role too high | Checked live: the curator role from the invitation stays. `docs/auth.md:424-426` says an override stays on purpose, and the person did prove that address | `access.py:55-75`, `users.py:356` |
| A disabled account uses up an invitation | An invitation to an address of an existing account is refused (`already_member`), and a disabled account cannot add an address | `routers/admin.py:209-212` |
| A bare account loses an access request or a submission in the join | Both need a verified address, a bare account has none | `routers/auth.py:427-432`, `routers/contributions.py:141` |
| B5 | Confirmed, see 02-10 | |

## Not proven

- `add_email` rolls back on `IntegrityError` (`users.py:296`), which also undoes `consumed_at` of the code, so the code might work a second time. It only happens in a race where another account takes the address between the check and the insert. A test would need two sessions and a pause inside `add_email`.
- `get_by_email` uses `scalar_one_or_none` (`users.py:85`). If address X is the main address of A and an email identity of B, every sign-in with X gives a 500. I found no path to that state other than a race between `add_email` on A and a first sign-in of X. Not reproduced.
- `POST /auth/emails` with someone else's address sends them a mail and uses their 5 mails per hour. Rate limits belong to package 01.
- The dev login link in the backend log uses port 5173, not the worktree's frontend port. Dev only, not a bug for users.

## Not checked

- The DB tests are not run: the sandbox hides `secrets/.env`, so pytest cannot reach the database. Pierre can run them with `cd backend && python3 ../scripts/with-db.py uv run pytest tests/test_review_02_*.py -rxX`. Every test should report `xfailed`.
- Real GitHub and ORCID: never called, by the brief. What a real provider allows in a name (length, line breaks, HTML) is not checked.
- The race tests (02-1, 02-8, 02-9) use `asyncio.gather` on one test client. If they pass by luck (no interleaving), strict xfail will report `XPASS`. The live proofs of 02-1 and 02-8 show the race is real.
