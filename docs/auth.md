# Sign-in and accounts

How people sign in to RESSLab Hub, and what has to be set up outside the code
for it to work. Issue #247.

Browsing stays open to everyone. An account is only needed to submit data or to
open the review queue.

## What exists today (phase 1)

Two ways to sign in:

- **Email code.** You type an address, the backend mails a six-digit code and a
  link. Either one signs you in. The code is for when the mailbox is on another
  device, the link for when it is the same one.
- **GitHub.** The OAuth side of the same GitHub App that opens the contribution
  pull requests. You can also link GitHub to an account you already have, from
  the account page.

Linking GitHub is worth doing: a submission from an account with a GitHub login
mentions that login on its pull request, so GitHub notifies the contributor of
every review comment and they can answer where the review happens.

Roles exist in the database (`viewer < contributor < curator < admin`) but
phase 1 only enforces "signed in". The rules that hand out `contributor` and
`curator` come with #248.

## How it works

- **Session.** A random token in an httpOnly `resslab_session` cookie, whose
  sha256 is a row in `auth_session`. Server side so signing out, and later an
  admin revoking access, take effect at once. Thirty days.
- **Same-origin everywhere.** Traefik serves the app and the API from one host
  in the deployments; in development a Vite proxy does the same (`/api` to the
  backend, prefix stripped). So the cookie is first-party and there is no CORS
  layer at all. Open the dev app on the host the proxy serves, not on the
  backend port.
- **Cross-site writes** are refused by a middleware: every unsafe method must
  have `Sec-Fetch-Site: same-origin` or `none`, or an `Origin` matching the
  `Host`. Non-browser clients (the data repository's CI with its Basic
  credential) send neither header and pass.
- **Nothing mailed or cookied is stored**, only its sha256. Codes die after ten
  minutes, five wrong tries, or one use. An address can trigger five mails an
  hour and one IP twenty, counted in SQL because that has to hold across
  replicas. Finished challenges are purged a day later, when a new one starts.
- **The second step happens in the browser that did the first.** A ten-minute
  `resslab_login` cookie names the sign-in in progress: the mailed challenge,
  or the GitHub `state`. A code, or a GitHub callback URL, is useless in any
  other browser. The mailed link is the exception, on purpose: it carries its
  own 256-bit token.
- **Accounts are never merged** because two providers report the same address.
  Whoever holds an address keeps it; the second one is told to sign in with it
  and link the provider from the account page. The address is also how an
  account is found, so the email identity cannot be unlinked: GitHub can.
- **Absolute URLs** (the OAuth callback, the mailed link) are built from the
  `PUBLIC_BASE_URL` setting. They cannot come from the request: Traefik has
  already stripped `/api` and the `Host` is an internal service name.

### What `API_PASSWORD` is now

It is the machine credential, not a user password. It still guards `/upload`
and `/user`, and it is one of the two ways into `/validate` (the other being a
signed-in account). The data repository's three workflows and
`backend/Makefile` use it; nothing in the browser does.

## Setting it up

### GitHub App (once per environment)

On the App's settings page:

1. Callback URL: `https://<host>/api/auth/github/callback`. Development needs
   its own entry, e.g. `http://localhost:5173/api/auth/github/callback`.
2. Generate a client secret. That pair is `GITHUB_OAUTH_CLIENT_ID` and
   `GITHUB_OAUTH_CLIENT_SECRET`, and it is **not** the App id or private key
   already used to open pull requests.
3. Account permission "Email addresses: read", so a new account can be filled
   in with the person's verified address.

Without those two settings the GitHub button answers 503 and is simply not
offered.

### Mail

`SMTP_HOST`, `SMTP_PORT` (587), `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`.
With no `SMTP_HOST` the code and the link are written to the log instead of
being sent, which is how local development and the tests work.

Still to settle with ENAC IT: which relay the cluster's pods may use, and
whether `noreply@resslab-hub.epfl.ch` can be the sender.

### Settings

| Key | What it is |
|---|---|
| `PUBLIC_BASE_URL` | Where the app is reached, without `/api`. Every absolute URL comes from it. |
| `GITHUB_OAUTH_CLIENT_ID` / `_SECRET` | The App's OAuth pair (above). |
| `SMTP_*` | Mail (above). |
| `ADMIN_EMAILS` | Comma-separated addresses that become administrators at first sign-in, so a fresh deployment has one without a CLI. |
| `SESSION_TTL_DAYS` | 30 by default. |
| `LOGIN_CODE_TTL_MINUTES` | 10 by default. |
| `SESSION_COOKIE_SECURE` | Derived from the `PUBLIC_BASE_URL` scheme; set it only to override. |

In the deployments these go in Infisical and reach the pods through
`envFrom: secretRef`, like the existing GitHub App credentials. `CORS_ENABLED`
is gone and can be removed from the overlays.

## Signing in locally

With no SMTP configured, the code is in the backend log:

```
make dev-all              # or the worktree's own tmux session
# open http://localhost:5173/login  (the Vite port, not the backend one)
grep "Sign-in code" .wt-logs/backend.log
```

The link on the line below it works too, and skips the typing.

## Later

- **#248** roles: academic email or an invitation grants `contributor`;
  `curator` and `admin` come from the GitHub permission on `resslab-hub-data`,
  so the app and the merge gate read the same source. Admin pages for members,
  invitations and access requests.
- **#249, #250, #252** the academic identity providers of the mockup: ORCID is
  self-service; SWITCH edu-ID / eduGAIN and EPFL Entra ID each need EPFL to
  register the application, so those requests should be filed early. Each one
  is another provider in `auth_identity` and a copy of `auth/github_oauth.py`.
