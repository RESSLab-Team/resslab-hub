# Findings of package 01: sign-in

- Branch: `review/01-sign-in`
- Commit reviewed: `0e15c031` (from `dev`, with ORCID)
- Date: 2026-11-12
- Tests run: yes, by Pierre outside the sandbox (the sandbox hides `secrets/.env`). `uv run pytest tests/test_review_01_*.py -q` gives `13 xfailed`. With `--runxfail --tb=line`, each of the 13 fails on its own assert, not on a setup error. The browser proofs below were run with Claude in Chrome on `http://127.0.0.1:19464` (this worktree).

## Summary

| Id   | Severity | Title                                                       | Suspicion | Proof        |
| ---- | -------- | ----------------------------------------------------------- | --------- | ------------ |
| 01-1 | medium   | Bad input on the sign-in routes gives a 500                 | S6        | Chrome, test |
| 01-2 | low      | One code gives a session to each parallel request           | S5        | Chrome, test |
| 01-3 | medium   | The mail cap is silent for the user, visible for a stranger | B1        | Chrome, test |
| 01-4 | medium   | A 429 on sign-in shows "Something went wrong"               | B1        | Chrome       |
| 01-5 | medium   | Parallel wrong codes pass the five-attempt cap              | S5        | test         |
| 01-6 | low      | A link finished after sign-out still attaches the identity  | S3        | test         |

## Question 1. Email code: double use and attempt counter

Problem. `verify_code` reads the challenge with a plain SELECT (`backend/resslab_hub/auth/email_login.py:123-144`), checks `attempts` and `consumed_at` in Python (`:171`), and sets `consumed_at` at `:179` with no lock. So two requests with the right code at the same time both pass (01-2). The counter update itself is atomic: `_count_failure` (`:147-157`) does `UPDATE ... attempts + 1 RETURNING`. But the gate at `:171` reads an old value, so every request that read the row before the updates still compares its code (01-5).

### 01-2 One code gives a session to each parallel request

- Severity: low
- Suspicion: S5 (confirmed)
- Where: `backend/resslab_hub/auth/email_login.py:170-180`
- Status: new

Five requests with the same right code, sent at the same time, all sign in. Each one gets its own session row. For a new address, 3 of 5 got a session and 2 got `invalid_or_expired`, all on the same new account, no 500. The harm is small: the person who has the code already owns the account. It breaks the "one use" promise, and it leaves extra sessions that nobody sees.

Proof:

```text
Claude in Chrome, on http://127.0.0.1:19464/login
Existing account review01-a@<redacted>, after one real /api/auth/email/start
> Promise.all(5 x fetch('/api/auth/email/verify', {method: 'POST', body: '{"code":"<redacted>"}'}))
200, 200, 200, 200, 200   (same user id in the 5 bodies)

New address review01-d@<redacted>
> same, 5 in parallel
200, 200, 200 (same new user id), 400 {"detail":"invalid_or_expired"} x 2
```

Test: `backend/tests/test_review_01_races.py::test_one_code_gives_one_session` fails with `assert [200, 200] == [200, 400]`. A barrier after the read makes both requests hold the row before any writes, so the test cannot flake.

Fix: consume the challenge in one step, for example an `UPDATE ... SET consumed_at = now() WHERE id = ... AND consumed_at IS NULL RETURNING`, and refuse when no row comes back. Or read the row with `SELECT ... FOR UPDATE`.

### 01-5 Parallel wrong codes pass the five-attempt cap

- Severity: medium
- Suspicion: S5 (confirmed)
- Where: `backend/resslab_hub/auth/email_login.py:171`
- Status: new

The cap of 5 tries is the only guard of a 6 digit code. Wrong codes sent at the same time all pass the gate at `:171`, because each one read `attempts` before the others counted. So more than 5 codes are compared on one challenge. To use it, an attacker starts a sign-in for the victim's address (they get the login cookie, the victim gets the mail) and sends a burst of guesses. In practice the window is a few ms, and `/auth/email/verify` allows 20 per minute per IP, so the gain is small: in the browser, 18 parallel wrong codes gave only 4 `invalid_code`. But the cap does not hold what it promises, and an attacker with many IPs gets more guesses.

Proof: `backend/tests/test_review_01_races.py::test_parallel_wrong_codes_stop_at_five` fails with `assert 8 <= 5`. 8 wrong codes held after the read, all 8 compared.

Fix: the same one-step update as 01-2, with the check inside it: `UPDATE ... SET attempts = attempts + 1 WHERE id = ... AND attempts < 5 RETURNING`, and compare the code only when a row comes back.

## Question 2. Email link

No problem. The link token has 256 bits, is stored as a hash and compared to it, and one challenge belongs to one address (`backend/resslab_hub/auth/email_login.py:184-194`). A link for address A can only sign in the account of A. The stored redirect goes through `safe_redirect` when it is written and again when it is used (`backend/resslab_hub/routers/auth.py:200`). Two notes, not findings:

- A link made by an attacker for their own address signs the person who clicks it in to the attacker's account. This is login CSRF by link, and it comes from the "no cookie needed" design.
- `verify_link` does not look at `attempts`. After 5 wrong codes, the link of the same challenge still works. That is fine: the token is not guessable.

## Question 3. Add-address challenge versus sign-in challenge

No problem. `_load` refuses a challenge when `challenge.link_user_id != link_user_id` (`backend/resslab_hub/auth/email_login.py:141`). Sign-in passes `None`, the add-address route passes the user id, so each kind is refused by the other route. An add-address challenge has no token (`:92`), so it has no link. `test_auth_flow.py` already covers both ways.

## Question 4. Hourly caps

Problem. The answer does not tell if an address has an account: a mail goes out for any address. But it tells that the cap is reached. When an address hit its 5 mails in the hour, `start` returns `None` (`backend/resslab_hub/auth/email_login.py:87-90`), and the route sends the same body but no login cookie (`backend/resslab_hub/routers/auth.py:158-161`).

### 01-3 The mail cap is silent for the user, visible for a stranger

- Severity: medium
- Suspicion: B1 (confirmed)
- Where: `backend/resslab_hub/routers/auth.py:158-161`, `backend/resslab_hub/auth/email_login.py:87-90`
- Status: new

Three problems come from the same lines:

- A capped person sees "We sent you a code" and waits for a mail that never comes. Nothing tells them to wait for the next hour.
- A stranger can tell a cap from a real start: no `Set-Cookie`, and the next verify says `invalid_or_expired` instead of `invalid_code`. A capped start also does no mail work, so it answers faster.
- Anyone who knows an address can burn its 5 mails per hour, and so lock that person out of email sign-in. With 20 mails per IP per hour, a room behind one IP has the same problem (see B1 and package 10).

Proof:

```text
Claude in Chrome, on http://127.0.0.1:19464/login
review01-b@<redacted>: 5 real starts (5 code lines in .wt-logs/backend.log), then sign in and log out
> fetch('/api/auth/email/start', {method: 'POST', body: '{"email":"review01-b@<redacted>"}'})   x 3
200 {"sent":true}  (15, 14, 14 ms; 5-7 ms in the server log; no new code line in the log)
> fetch('/api/auth/email/verify', {method: 'POST', body: '{"code":"100001"}'})
400 {"detail":"invalid_or_expired"}

After a real start for another address, the same wrong code gives:
400 {"detail":"invalid_code"}
```

Test: `backend/tests/test_review_01_caps.py::test_a_capped_start_looks_like_a_real_one` fails with `assert 'resslab_login' in <Cookies[]>`.

Fix: tell the user when the cap is reached (a slug like `too_many_mails` that the page can explain), since the address is typed by the person anyway. If the cap must stay hidden, set a login cookie for a dummy challenge so both answers look the same.

To check by Pierre: the time gap between a real start and a capped one on stage, where a real SMTP relay sends the mail. Decide if the cap should stay secret at all.

## Question 5. OAuth state

No problem worth a finding. The state is bound to the browser: the callback refuses it when it is not equal to the `resslab_login` cookie (`backend/resslab_hub/auth/oauth_state.py:53-69`). It is one use, but the use is not atomic (SELECT, check, then write), like the email code. The impact is low: GitHub and ORCID refuse to exchange the same code twice, so a second callback cannot finish. A callback from another browser is refused and does not burn the state. A state that is not a UUID gives a 500, see 01-1.

## Question 6. Link flow

Partly a problem. The callbacks attach the identity to `challenge.link_user_id` and never read the session of the browser (`backend/resslab_hub/routers/auth.py:534-549` for GitHub, `:647-652` for ORCID). So if user A starts "Link GitHub", signs out, and the callback arrives, the identity still goes to A (01-6).

The case of the brief (B signs in on the same browser before the callback) is not reachable from the UI. Every sign-in sets or clears `resslab_login`: an email start writes B's challenge id in it, and the verify clears it. The callback then finds a state that does not match the cookie and refuses it. So the identity cannot go to B, and cannot go to A while B is signed in.

### 01-6 A link finished after sign-out still attaches the identity

- Severity: low
- Suspicion: S3 (confirmed in part)
- Where: `backend/resslab_hub/routers/auth.py:534-549`, `:647-652`
- Status: new

A starts "Link GitHub" (or ORCID), signs out in another tab, then finishes on GitHub. The identity is attached to A anyway, and A can later sign in with it. The harm is small: it is A's own flow, on A's own browser, and the case of the brief (B signed in) cannot happen. But "signed out" should mean the browser can no longer change the account. One unlikely case: on a shared computer, A leaves the GitHub page of the link open and signs out. Within 10 minutes (the life of the login cookie, which logout keeps), the next person signs in to GitHub with their own account on that page. Their GitHub account is then attached to A's Hub account, and can sign in to it.

Proof: `backend/tests/test_review_01_link_session.py::test_a_link_finished_after_sign_out_attaches_nothing` fails with `assert ['email', 'github'] == ['email']`, and the same with `orcid`. GitHub and ORCID are faked with the monkeypatch of `test_auth_flow.py`, nothing was sent to them.

Fix: in the link branch of both callbacks, read the session and refuse when its user is not `link_user_id`. Logout could also clear `resslab_login`, which kills the open state.

## Question 7. `next` and `redirect_to`

No problem for the redirect. I ran `safe_redirect` (`backend/resslab_hub/auth/urls.py:54-69`) on the values of the brief:

| Value                  | Result                   |
| ---------------------- | ------------------------ |
| `//evil.example`       | `/`                      |
| `/\evil.example`       | `/`                      |
| `https://evil.example` | `/`                      |
| `/\t/evil.example`     | `/`                      |
| `/%2F%2Fevil.example`  | kept, a path on our host |
| `/%5Cevil.example`     | kept, a path on our host |
| `/%09/evil.example`    | kept, a path on our host |

End to end, `/login?next=%2F%255Cevil.example` then a sign-in in the real form lands on `http://127.0.0.1:19464/%5Cevil.example`, our host. `LoginView.vue:32-36` lets `/\evil.example` pass, but the value only goes to `router.replace` and to the backend, which drops it. A very long value and a NUL are not refused, and they give a 500 (01-1).

## Question 8. Cookies

No problem. Both cookies are `HttpOnly`, `SameSite=Lax`, path `/` (`backend/resslab_hub/auth/sessions.py:122`). `Secure` is on when `PUBLIC_BASE_URL` is https. The session lives 30 days, the login cookie 10 minutes. Each sign-in makes a new token. Logout deletes the server row (`sessions.py:96`), and then `/auth/me` gives no user:

```text
> POST /api/auth/email/verify {"code":"<redacted>"}  -> 200
> GET /api/auth/me                                    -> user review01-c@<redacted>
> POST /api/auth/logout                               -> 204
> GET /api/auth/me                                    -> {"user": null}
> POST /api/auth/logout                               -> 204
```

Notes, not findings:

- A new sign-in does not revoke the old session of the same browser. In 01-2, five sessions stayed in the table.
- Logout does not clear `resslab_login`. It expires after 10 minutes anyway.
- The cookies have no `__Host-` prefix, so another site on the same parent domain could set a cookie with the same name. Not proven, see "Not proven".

To check by Pierre: that `PUBLIC_BASE_URL` is https on prod, so the cookies get `Secure`.

## Question 9. CSRF

No problem. `CSRFMiddleware` (`backend/resslab_hub/auth/csrf.py:44-51`) runs on every POST, PUT, PATCH and DELETE. It accepts `Sec-Fetch-Site` `same-origin` or `none`, else an `Origin` whose host equals `Host`, else no header at all (not a browser). A form on another site cannot sign someone in or out:

```text
Claude in Chrome, on http://127.0.0.1:18464/docs (another origin, same site)
> fetch('http://127.0.0.1:19464/api/auth/logout', {method: 'POST', mode: 'no-cors', credentials: 'include'})
> fetch('http://127.0.0.1:19464/api/auth/email/start', {method: 'POST', mode: 'no-cors', ...})
403 for both in the server log
```

The GET routes `/auth/github/start` and `/auth/orcid/start` write a state row and are not covered, but they only start a flow that the browser must finish itself.

## Question 10. Bad input

Problem. The challenge id and the OAuth state go straight into a SELECT on a Postgres UUID column, and `redirect_to` goes into a `String(500)` column. Nothing checks them first. The session cookie is hashed before the lookup, so a bad session cookie gives no 500. `code` has `max_length=12`, and letters or spaces in it give a normal 400.

### 01-1 Bad input on the sign-in routes gives a 500

- Severity: medium
- Suspicion: S6 (confirmed)
- Where: `backend/resslab_hub/auth/email_login.py:123-144` (`_load`), `backend/resslab_hub/auth/oauth_state.py:53-69` (`consume_state`), `backend/resslab_hub/models/database/auth.py:165` (UUID id) and `:173` (`redirect_to String(500)`), `backend/resslab_hub/models/auth.py:64` and `:77` (no limit on `redirect_to` and `challenge`)
- Status: new

Any of these gives a 500 instead of a 400:

- a `challenge` that is not a UUID, or that has a NUL, on `/auth/email/verify`;
- a `resslab_login` cookie that is not a UUID, on `/auth/email/verify` (code) and on the GitHub and ORCID callbacks;
- a `redirect_to` longer than 500 characters, or with a NUL, on `/auth/email/start`;
- a GitHub name over 200 characters at the first sign-in: `display_name` is `String(200)` (`backend/resslab_hub/models/database/auth.py:73`) and the callbacks copy the name without cutting it (`routers/auth.py:559`, and `:678` for ORCID). GitHub allows names up to 255.

It hurts nobody directly, and no mail goes out. But each one is an error in Sentry and a noisy log, and a broken link (a cut challenge id in a mail client) shows the person a server error instead of "this link is no longer valid".

Proof:

```text
Claude in Chrome, on http://127.0.0.1:19464/login
> POST /api/auth/email/verify {"challenge":"not-a-uuid","token":"x"}         -> 500
> POST /api/auth/email/verify {"challenge":"00000000-0000-...","token":"x"}  -> 400 invalid_or_expired
> POST /api/auth/email/start  {"email":"<redacted>","redirect_to":"/" + 600 x "a"} -> 500
> POST /api/auth/email/start  redirect_to with a NUL                          -> 500
> POST /api/auth/email/verify challenge with a NUL                            -> 500
> cookie resslab_login=abc, POST /api/auth/email/verify {"code":"123456"}    -> 500
> cookie resslab_login=abc, GET /api/auth/github/callback?state=abc&code=x   -> 500
> cookie resslab_login=abc, GET /api/auth/orcid/callback?state=abc&code=x    -> 500
```

Tests: `backend/tests/test_review_01_bad_input.py`, 8 tests, each fails with `assert 500 < 500`.

Fix: check the challenge id and the state as UUIDs before the query and answer `invalid_or_expired` when they are not. Put `max_length=500` on `redirect_to` and refuse a NUL, or let `safe_redirect` return `/` for them. Cut the provider name to 200 characters.

## Question 11. Rate limits

Problem for the message. The decorators, all keyed on the client address, in memory, per replica (`backend/resslab_hub/utils/rate_limit.py:13`):

| Route                                                              | Limit     | Line                  |
| ------------------------------------------------------------------ | --------- | --------------------- |
| `POST /auth/email/start`                                           | 10/minute | `routers/auth.py:132` |
| `POST /auth/email/verify`                                          | 20/minute | `routers/auth.py:165` |
| `POST /auth/emails`                                                | 10/minute | `routers/auth.py:289` |
| `POST /auth/emails/verify`                                         | 20/minute | `routers/auth.py:330` |
| access request                                                     | 5/hour    | `routers/auth.py:413` |
| `/me`, `/logout`, `/identities*`, both `start` and both `callback` | none      |                       |

On top of that, the SQL caps of question 4: 5 mails per address and 20 per IP per hour.

### 01-4 A 429 on sign-in shows "Something went wrong"

- Severity: medium
- Suspicion: B1 (confirmed)
- Where: `frontend/src/views/LoginView.vue:59` and `:74` (`sendCode`, `submitCode`), the 429 body comes from the handler in `backend/resslab_hub/main.py:94-99`
- Status: new

The 429 body is a sentence, not a slug. The page looks up `auth.errors.<detail>`, finds nothing, and shows the generic error. The person does not know they must wait one minute, so they click again, which keeps them limited. In a workshop room behind one IP, 10 starts per minute is reached fast.

Proof:

```text
Claude in Chrome, on http://127.0.0.1:19464/login
> 11 x POST /api/auth/email/start in one minute
200 x 10, then 429 {"detail":"Too many requests. Please slow down and retry."}
Then in the real form: type review01-b@<redacted>, click "Send me a code"
.login-error: "Something went wrong. Please try again."   (page stays on the email step)
```

Fix: send a slug like `rate_limited` on 429 (or map the status in the page) and show "Too many tries, wait a minute and try again".

To check by Pierre: how many people share one IP at the workshop, and if 10 starts per minute and 20 mails per hour per IP are enough (package 10).

## Question 12. Disabled account

No problem. The code and the link answer 403 `account_disabled` (`backend/resslab_hub/routers/auth.py:195`). GitHub and ORCID redirect with `account_disabled` (`:568`, `:682`). Disabling a member calls `revoke_all` (`backend/resslab_hub/routers/admin.py:122`), and `resolve_session` refuses a session of a disabled user on every request (`backend/resslab_hub/auth/sessions.py:82`), so the sessions stop at once.

Note: the link callbacks (`routers/auth.py:534-549`, `:647-652`) do not check if the `link_user_id` user is disabled. It is harmless, since that user cannot sign in, but it can still get a new identity attached.

## Question 13. ORCID first sign-in with no address

No problem. The callback builds `/account?add_email=1&next=<redirect>` with a value that already went through `safe_redirect`, and url-encodes it (`backend/resslab_hub/routers/auth.py:629`, `:690`). `AccountView.vue` checks `next` like `LoginView` (starts with `/`, not `//`) and only gives it to `router.replace`.

## Rejected suspicions

| Suspicion | Why it is not a problem                                                                                                                    | Where                                             |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------- |
| S5        | Double use for a new address does not give a 500: the extra requests get `invalid_or_expired`                                              | `backend/resslab_hub/auth/email_login.py:170-180` |
| S3        | The case "A starts the link, B signs in, callback" cannot happen: B's sign-in replaces or clears the login cookie, so the state is refused | `backend/resslab_hub/auth/oauth_state.py:53-69`   |
| (Q7)      | Open redirect: `safe_redirect` refuses every value of the brief, encoded values stay on our host                                           | `backend/resslab_hub/auth/urls.py:54-69`          |
| (Q9)      | Login CSRF and sign-out CSRF by a form: refused with 403                                                                                   | `backend/resslab_hub/auth/csrf.py:32-51`          |

## Not proven

- No `__Host-` prefix on the cookies (`backend/resslab_hub/auth/sessions.py:122`). Another site on the same parent domain could set a `resslab_login` cookie. Needs a second site on that domain to prove.
- One odd run: after the 5 parallel verifies of 01-2, a new start for `review01-a` sent a mail, but the next 10 code verifies all gave `invalid_or_expired` in a few ms, as if the browser had no login cookie. The link of the same challenge then signed in fine. I could not explain it from the code (`sessions.py:142-149` looks right). It may be an artifact of my many parallel calls in one tab.

## Not checked

- Real round trips with GitHub and ORCID: the brief forbids calling them.
- Anything on stage or prod: the `Secure` flag, the `Host` header behind the ingress for the `Origin` check, the timing of a capped start with a real SMTP relay.
- The double use of an OAuth state (Q5): the provider refuses a code twice, so I did not write a test.
