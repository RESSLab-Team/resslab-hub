# Sign-in and accounts

How people sign in to RESSLab Hub, and what has to be set up outside the code
for it to work. Issue #247.

Browsing stays open to everyone. An account is only needed to submit data, to
review it, or to decide who can do what.

## What exists today (phase 1)

Two ways to sign in:

- **Email code.** You type an address, the backend mails a six-digit code and a
  link. Either one signs you in. The code is for when the mailbox is on another
  device, the link for when it is the same one.
- **GitHub.** OAuth through a GitHub App: in the deployments the same App that
  opens the contribution pull requests, locally a dev App. You can also link
  GitHub to an account you already have, from the account page.

Linking GitHub is worth doing: a submission from an account with a GitHub login
mentions that login on its pull request, so GitHub notifies the contributor of
every review comment and they can answer where the review happens.

Each account has a role (`viewer < contributor < curator < admin`), which
decides who submits, who reviews and who manages the others. See Roles below
(#248).

## How it works

- **Session.** A random token in an httpOnly `resslab_session` cookie, whose
  sha256 is a row in `auth_session`. Server side so signing out, and an admin
  disabling an account, take effect at once. Thirty days.
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
- **A submission belongs to the account that made it.** Updating an open one
  from the Hub (#321) checks the `Submitted-by` trailer on its branch's first
  Hub commit against the account's verified address (a pull request opened
  before trailers falls back to its `contributions/*.json` record). A curator
  can update any open one: the commit is then the curator's, and the trailers
  keep naming the person who submitted. Anyone else gets a 403. The review
  page offers "Edit on the Hub" to the owner and to curators.
- **Absolute URLs** (the OAuth callback, the mailed link) are built from the
  `PUBLIC_BASE_URL` setting. They cannot come from the request: Traefik has
  already stripped `/api` and the `Host` is an internal service name.

### What `API_PASSWORD` is now

It is the machine credential, not a user password. It still guards `/upload`
and `/user`, and it is one of the two ways into `/validate` (the other being a
signed-in account). The data repository's three workflows and
`backend/Makefile` use it; nothing in the browser does.

## Setting it up

### GitHub App

The OAuth pair does not have to come from the App that opens pull requests:
`GITHUB_APP_*` and `GITHUB_OAUTH_*` are separate settings. So the production
App keeps only the deployment URLs, and local development uses its own App.

**Deployments.** On the settings page of the existing App:

1. Callback URL: `https://<host>/api/auth/github/callback`, one entry per
   environment (dev, test, prod).
2. Generate a client secret. That pair is `GITHUB_OAUTH_CLIENT_ID` and
   `GITHUB_OAUTH_CLIENT_SECRET`, and it is **not** the App id or private key
   already used to open pull requests.
3. Account permission "Email addresses: read", so a new account can be filled
   in with the person's verified address.

**Local development.** Create a second App (say "RESSLab Hub dev") on your own
account. It needs no installation and no repository permission: only the
"Email addresses: read" account permission, a client secret, and one callback
URL with no port:

```
http://127.0.0.1/api/auth/github/callback
```

GitHub ignores the port on the loopback address, so that one entry serves the
main checkout on 5173 and every worktree port. It documents this for OAuth
authorization and recommends `127.0.0.1` over `localhost`. If a GitHub App ever
refuses it, register the port too. Then in `secrets/.env`:

```
GITHUB_OAUTH_CLIENT_ID=...
GITHUB_OAUTH_CLIENT_SECRET=...
PUBLIC_BASE_URL=http://127.0.0.1:5173      # or the worktree's FRONTEND_PORT
```

and open the app at `http://127.0.0.1:<port>`, not `localhost`. Cookies ignore
the port but not the host: the `resslab_login` cookie set when you click the
button must still be there when GitHub sends the browser back. Restart the
backend after editing the file, Dynaconf only reads it at startup.

Without the two `GITHUB_OAUTH_*` settings the GitHub button is still shown,
but clicking it comes back to the login page with `?error=github_disabled`
("GitHub sign-in is not available here"), so a deployment without the pair
does not show a raw JSON error.

### Mail

With no `SMTP_HOST` the code and the link are written to the log instead of
being sent, which is how local development and the tests work.

The relay is the EPFL one, documented by ENAC IT ("Sending email via epfl
infra" in the enacit4r Notion). `mail.epfl.ch:587` with STARTTLS, and the
shared service account whose password is in Infisical under `/enacit4r-email`.
The server offers `AUTH GSSAPI NTLM LOGIN`; aiosmtplib knows cram-md5, plain
and login, so it picks LOGIN and no NTLM code is needed.

```env
SMTP_HOST=mail.epfl.ch
SMTP_PORT=587
SMTP_STARTTLS=true
SMTP_USER=INTRANET\noreply-enacitdev
SMTP_PASSWORD=<Infisical /enacit4r-email>
SMTP_FROM=noreply-enacitdev@epfl.ch
```

Two traps in that block:

- **Do not put double quotes around `SMTP_USER`.** Dynaconf reads the file
  with python-dotenv, which turns `\n` inside double quotes into a real
  newline, so `"INTRANET\noreply-enacitdev"` becomes two broken lines. No
  quotes (as above) or single quotes both keep the backslash. Same rule in
  YAML. The `INTRANET\...` form is the one that works, confirmed on
  2026-09-07; the UPN form `noreply-enacitdev@epfl.ch` was never tried.
- **The sender must be the account's own address.** Tested on 2026-09-07:
  anything else comes back as `550 5.7.60 SMTP; Client does not have
  permissions to send as this sender`. So `SMTP_FROM=noreply-enacitdev@epfl.ch`
  and nothing else. The `+suffix` trick in the ENAC IT page (like
  `noreply+resslab-hub@epfl.ch`) is for the anonymous relay on port 25, not
  for a service account on 587. Staying under `epfl.ch` is also what makes SPF
  and DKIM pass; a sender on a subdomain like `resslab-hub.epfl.ch` has no DNS
  records of its own and gets junked.

  The consequence is that our mails are not distinguishable, by address, from
  any other app using the shared account. If that becomes a problem, ask the
  infra team for a group address of our own, which is the port 587 path the
  ENAC IT page mentions.

Mails go out as `RESSLab Hub <SMTP_FROM>`. There is no `Reply-To`: it is a
noreply mailbox, and a reply would carry a sign-in code to whoever reads it.

When the relay refuses or does not answer within 15 seconds, `POST
/auth/email/start` answers `503` with `mail_failed` and the login page says
so. The challenge is rolled back, so a broken relay does not eat the hourly
caps of the person trying to sign in. The SMTP reason is in the backend log,
the code never is.

### Settings

| Key | What it is |
|---|---|
| `PUBLIC_BASE_URL` | Where the app is reached, without `/api`. Every absolute URL comes from it. |
| `API_USERNAME` / `API_PASSWORD` | The machine credential (Basic auth). Username defaults to `user`. |
| `GITHUB_OAUTH_CLIENT_ID` / `_SECRET` | The App's OAuth pair (above). |
| `SMTP_HOST` / `SMTP_PORT` | The relay. No host = log-only mode (above). |
| `SMTP_STARTTLS` | On by default; the EPFL relay needs it on port 587. |
| `SMTP_USER` / `SMTP_PASSWORD` | The service account (above, mind the quoting). |
| `SMTP_FROM` | Sender address. The display name is fixed in the code. |
| `ADMIN_EMAILS` | Comma-separated addresses that are always administrators. For an admin with no GitHub account, and so a fresh deployment has one without a CLI (Roles, below). |
| `CONTRIBUTOR_DOMAINS` | Comma-separated domains that count as academic on top of the built-in list (Roles, below). |
| `SESSION_TTL_DAYS` | 30 by default. |
| `LOGIN_CODE_TTL_MINUTES` | 10 by default. |
| `SESSION_COOKIE_SECURE` | Derived from the `PUBLIC_BASE_URL` scheme; set it only to override. |
| `CONTRIBUTIONS_ENABLED` | `true` by default. `false` also switches sign-in and the account page off, see [contributing-data.md](contributing-data.md#settings). |

In the deployments these go in Infisical and reach the pods through
`envFrom: secretRef`, like the existing GitHub App credentials. `CORS_ENABLED`
is gone and can be removed from the overlays. For the mail keys, see the
runbook below.

## Deploying the mail relay

The manifests and the secrets live outside this repo, so these steps are done
by hand, once per environment (`dev`, then `staging`, then `prod`).

1. Copy the password out of the shared ENAC IT vault:
   `enac-it-secrets.epfl.ch`, path `/enacit4r-email`. That vault is the only
   source, this app never gets its own account.
2. Paste it into our own vault: project `k8s-prod-yc-rz`, path
   `/epfl-resslab/resslab-hub` (next to `API_PASSWORD`, which lands in the
   `backend-secret`), environment `dev`, `staging` or `prod`. Add the six
   `SMTP_*` keys from the block above. Values are stored as they are, no
   escaping, so paste `INTRANET\noreply-enacitdev` plainly.
   Always the vault first: the operator overwrites the k8s secret on resync,
   so a secret patched directly in the cluster silently reverts.
3. In `enack8s-app-config`, check the backend Deployment already pulls that
   secret with `envFrom: secretRef` (the GitHub App pair comes in that way,
   so usually there is nothing to add). The resync runs every 12 hours, so to
   apply it now delete the `InfisicalSecret` CR from the ArgoCD UI (ArgoCD has
   the rights for it, your own account may not) or delete the managed secret.
4. Check the cluster can reach `mail.epfl.ch:587`. The anonymous port 25 relay
   is network-restricted; the authenticated one on 587 should not be, but try
   `dev` first before touching the other two.
5. `kubectl -n epfl-resslab-resslab-hub-<env> rollout restart deployment/resslab-hub-backend-<env>`.
   Dynaconf reads the environment at startup only, so without a restart the
   pods stay in log-only mode.
6. Verify: the backend log must no longer show `Sign-in mail not sent (no
   SMTP_HOST)`. Sign in on the deployed `/login` with a real address, the mail
   arrives from "RESSLab Hub". If it fails, the page shows "The sign-in mail
   could not be sent" and `kubectl logs` has the reason on a `Sign-in mail to
   ... failed:` line.

## Signing in locally

With no `SMTP_HOST` configured, the code is in the backend log, so no mail
server is needed to sign in locally:

```
make dev-all              # or the worktree's own tmux session
# open http://127.0.0.1:5173/login  (the Vite port, not the backend one)
grep "Sign-in code" .wt-logs/backend.log
```

The link on the line below it works too, and skips the typing.

## Testing the pipeline

No second App is needed. The one installed on `resslab-hub-data` works from
anywhere. Which branch a submission targets is `DATA_REPO_BASE_BRANCH`, and the
curation queue only lists pull requests into that branch.

Every environment uses `main`, which is the setting's default, so nothing has to
be set anywhere. The data repository has no other branch: `test` and `sandbox`
both existed on paper only, and `test` was deleted after sitting untouched since
January 2022.

So a submission made from dev, from stage or from a laptop opens a real pull
request into `main`, next to the real ones. That is on purpose, it is the only
way to exercise the pipeline for real. **Close those, never merge them.**

```bash
gh pr list --repo RESSLab-Team/resslab-hub-data --base main
```

Sample-data submissions are easy to spot, their branches are named
`contrib/<type>/demo-*`.

Locally, the email code needs no setup at all (see above). GitHub sign-in
needs the dev App, only worth it to test the link flow and the @mention.

## Roles

Four roles, weakest first:

| Role | What it adds |
|---|---|
| `viewer` | Everyone signed in. Can check data with `/validate` and ask for contributor access. |
| `contributor` | Opens and updates their own submissions (`POST`/`PUT /contributions`). |
| `curator` | The review queue, every submission, and editing anyone's open one. |
| `admin` | The admin page: members, invitations and access requests. |

Browsing the databases needs no account at all.

### Where a role comes from

`auth/roles.py` works it out, first match wins, and stores the answer in
`role` with the reason in `role_source`. The account page and the admin page
both show that reason.

1. A verified address in `ADMIN_EMAILS` -> `admin` (`admin-email`).
2. Admin on `resslab-hub-data`, through the linked GitHub account -> `admin`
   (`github`).
3. A decision of an administrator, `role_override` (`override`). Changing a
   role on the admin page, approving an access request and using an
   invitation all write it.
4. Write or maintain on `resslab-hub-data` -> `curator` (`github`).
5. An academic address -> `contributor` (`academic-email`, below).
6. Otherwise `viewer` (`default`).

The two admin sources come before the override on purpose: nobody can
demote, from the Hub, an admin that GitHub or the config made. The admin
page shows those rows as read only. To remove such an admin, change it on
GitHub or in `ADMIN_EMAILS`.

Only a **verified** address counts. Mail sign-in verifies by construction;
GitHub sign-in verifies when GitHub reports the address as verified.

So the GitHub permission on the data repository is the main source: the
people who can merge there review in the Hub, the people who own it manage
it. `ADMIN_EMAILS` is only for an admin who will not link GitHub.

### The GitHub permission

It is read with the GitHub App that opens the pull requests
(`DataRepoClient.get_permission`, the collaborator permission endpoint; the
Metadata permission every App has is enough). Without that App, nothing comes
from GitHub. The value is stored in `github_role` and read again:

- at every sign-in, and when someone links GitHub;
- on any request, once the stored value is an hour old.

So someone who loses write access on GitHub loses `curator` in the Hub
within the hour, at the latest. The read gives up after 5 seconds. When it
fails, the old value stays and the next try is 5 minutes later, so a GitHub
outage does not slow every request. Unlinking GitHub clears the value.

The login is the one stored at the last GitHub sign-in or link. If the person
renames their GitHub account, GitHub no longer knows the old login, the
permission reads as `none` and the role falls back. Signing in with GitHub
once more stores the new login.

Today (October 2026) the admins of the data repository are guilbep,
ahartloper, charlottegiseleweil, pierreleripoll, AlbanoCastroSousa, dlignos,
andskia and the `RESSLab` account. Each one becomes an admin in the Hub as
soon as they link GitHub. Trim that list on GitHub if it is too long.

The merge gate itself is a GitHub setting: branch protection and a
CODEOWNERS file on the data repository `main`. They are not set yet.

### What counts as academic

The check is the `pyswot` package, which carries the domain list JetBrains
uses to hand out student licences. Free mailboxes never pass, a stoplist of
abused domains is refused, and everything else has to be on the list, where
a subdomain matches its institution (`cs.stanford.edu` matches Stanford).

It is an allowlist, not a rule about endings: `example.edu` is not academic
just because it ends in `.edu`. The list is good on universities (EPFL,
ETHZ, Stanford, Tokyo, Imperial, Politecnico, TUM are all on it) and knows
nothing about research institutes or industry. Empa, NIST, AISC and Arup
are all absent.

That is what `CONTRIBUTOR_DOMAINS` is for:

```env
CONTRIBUTOR_DOMAINS=empa.ch,aisc.org
```

A subdomain of a listed domain matches too, so `lab.empa.ch` passes. A bare
top-level domain never matches, so `ch` in that setting hands the role to
nobody.

### What the role gates

| | viewer | contributor | curator | admin |
|---|---|---|---|---|
| `/validate` | yes | yes | yes | yes |
| `POST /auth/access-request` | yes | | | |
| Open a submission (`POST /contributions`) | | yes | yes | yes |
| Update a submission (`PUT /contributions/{pr}`) | | own | any | any |
| Read one submission (`GET /contributions/{pr}` and below) | | own | any | any |
| The queue (`GET /contributions`) | | | yes | yes |
| `/admin/*` | | | | yes |

"Own" means the `Submitted-by` trailer of the first Hub commit matches the
account's verified address. The frontend routes ask for the same roles
(`meta.auth` in `router/index.ts`): the sidebar shows the review queue to
curators only and the Administration link to admins only.

### The admin page

`/admin` (`views/AdminView.vue`, backend `routers/admin.py`) has three parts.

- **Access requests.** The pending ones, with the person's message. Approve
  gives the role asked for and mails the person; decline mails nobody, the
  account page shows it and they can ask again.
- **Members.** Every account, its role and where it comes from, the GitHub
  login and permission, the last sign-in. The "Set by an administrator"
  column is the override: "Automatic" clears it, a role sets it, in both
  directions. Disable signs the person out everywhere and refuses their next
  sign-in; enable undoes it. An admin cannot change their own row, nor an
  admin from GitHub or `ADMIN_EMAILS`.
- **Invitations.** A role waiting for an address. The person gets a mail;
  the role is theirs at their first sign-in with that verified address, by
  mail or by GitHub. Inviting someone who already has an account is refused:
  change their role in the members list instead. A pending invitation can be
  revoked.

An approved request and an invitation never lower a role: approving the
request of someone who became a curator meanwhile changes nothing. But they
are saved as an override, and the override comes before GitHub write (step
3 above). So someone invited or approved as contributor stays contributor
even after they get write on the data repo. To let GitHub decide again, set
their row to "Automatic".

Every decision takes effect on the person's next request, no new sign-in
needed.

### Asking for access

A viewer with a verified address can ask for `contributor` from the account
page, or from the "not open to your account" page they land on when they try
to submit. One pending request at a time, and five tries an hour. The
admins get a mail: every address in `ADMIN_EMAILS`, plus every account whose
role is admin, has a verified address and is not disabled. Most admins come
from GitHub, so `ADMIN_EMAILS` alone would miss them.

All these mails are best effort. The decision is saved first; a relay that is
down is logged, and the admin page still shows everything. When the
invitation mail fails, the page says so and the invitation stays valid.

### When a change shows

- An admin's decision: at once.
- A GitHub permission: within the hour, or at the next sign-in.
- A new `CONTRIBUTOR_DOMAINS` or `ADMIN_EMAILS` entry: at the person's next
  sign-in. Sessions last 30 days, so tell them to sign out and back in.

## Later

- **#249, #250, #252** the academic identity providers of the mockup: ORCID is
  self-service; SWITCH edu-ID / eduGAIN and EPFL Entra ID each need EPFL to
  register the application, so those requests should be filed early. Each one
  is another provider in `auth_identity` and a copy of `auth/github_oauth.py`.
- **#254** approve or ask for changes from the Hub, and **#253** the "not
  verified" flag on a submission.
- Academic domains edited from the admin page rather than in
  `CONTRIBUTOR_DOMAINS`, and a "my submissions" list for contributors.
