# Sign-in and accounts

How people sign in to RESSLab Hub, and what has to be set up outside the code
for it to work. Issue #247.

Browsing stays open to everyone. An account is only needed to submit data, to
review it, or to decide who can do what.

## What exists today (phase 1)

Three ways to sign in:

- **Email code.** You type an address, the backend mails a six-digit code and a
  link. Either one signs you in. The code is for when the mailbox is on another
  device, the link for when it is the same one.
- **GitHub.** OAuth through a GitHub App: in the deployments the same App that
  opens the contribution pull requests, locally a dev App. You can also link
  GitHub to an account you already have, from the account page.
- **ORCID (#250).** OAuth with a client of the ORCID public API. Same as
  GitHub: sign in, or link the iD from the account page. ORCID gives an iD
  and a name, never an address (see "ORCID and the missing address" below).

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
  or the GitHub or ORCID `state`. Each provider has its own challenge kind, so
  a GitHub `state` cannot finish on the ORCID callback. A code, or a GitHub callback URL, is useless in any
  other browser. The mailed link is the exception, on purpose: it carries its
  own 256-bit token.
- **Accounts are never merged** because two providers report the same address.
  Whoever holds an address keeps it; the second one is told to sign in with it
  and link the provider from the account page. The one exception is a bare
  account, joined only on two proofs (see "ORCID and the missing address").
- **An account can hold several addresses (#402).** Each verified address is
  an `email` row in `auth_identity`, and any of them signs in to the same
  account by code. `auth_user.email` is the main one: the contact address, and
  the one new submissions record. The person picks it on the account page.
  Migration `d3f7a1c9e5b2` added the missing row for accounts made before
  this, whose main address lived on `auth_user` only.
- **An address is added by code only, from the account page.** `POST
  /auth/emails` mails a code (no link) and `POST /auth/emails/verify` takes it,
  in the session that asked: the challenge carries `link_user_id`, and the
  sign-in endpoints refuse it. A link would let someone ask "add your address
  to my account" and have the owner of the address click it. With a code,
  only the person who reads the mailbox and holds the session can finish. An
  address that already belongs to another account is refused (409
  `email_in_use`): a person never joins two accounts alone, except from a
  bare account (below). An admin can (see "The admin page").
- **Removing an address.** `DELETE /auth/identities/{id}` removes any email
  row except the main one, and never the last way to sign in (409
  `cannot_unlink`). To drop the main address, make another one main first
  (`POST /auth/identities/{id}/main`). GitHub and ORCID can be unlinked the
  same way. Unlinking ORCID also clears the iD of the profile.
- **A submission belongs to the account that made it.** Updating an open one
  from the Hub (#321) checks the `Submitted-by` trailer on its branch's first
  Hub commit against every verified address of the account (a pull request
  opened before trailers falls back to its `contributions/*.json` record). So
  a submission sent from an address that was added or made main later is
  still yours. A curator
  can update any open one: the commit is then the curator's, and the trailers
  keep naming the person who submitted. Anyone else gets a 403. The review
  page offers "Edit on the Hub" to the owner and to curators.
- **ORCID and the missing address.** We only ask ORCID for `/authenticate`,
  and we never read an address from it: few records have a public one, and an
  address here is always proved by our own code. So a first ORCID sign-in
  makes an account with only the iD (role `viewer`), and sends the browser to
  `/account?add_email=1&next=<where it was going>`, once. The account page
  opens the add form with a line that says why. The person adds an address by
  code, or skips. Later sign-ins go straight on. `auth_user.orcid` follows the
  proved iD at each ORCID sign-in or link, so a typed iD is replaced.
- **A bare account can join another one.** A bare account has no address and
  exactly one identity, which is not an email (`users.is_bare`). It cannot own
  a submission, an access request or an invitation, since all of them need an
  address. Two places join it to another account (`users.absorb_bare_account`):
  - It adds, by code, an address that belongs to another account. The person
    proved the iD (the session) and the mailbox (the code), the same two
    proofs as "sign in by mail, then link ORCID". The iD moves to the account
    of the address, the bare account is deleted, and this browser is signed
    in to the other account.
  - Someone signed in links an ORCID iD that sits on a bare account (they
    skipped the address the first time). The iD moves the same way.

  The join is refused when the other account is disabled (403
  `account_disabled`) or already has an identity of that provider (409
  `email_in_use`, or `identity_taken` on a link). The GitHub callback does not
  join yet: a GitHub account with a private address has the same dead end.
- **Absolute URLs** (the OAuth callback, the mailed link) are built from the
  `PUBLIC_BASE_URL` setting. They cannot come from the request: Traefik has
  already stripped `/api` and the `Host` is an internal service name.

### What `API_PASSWORD` is now

It is the machine credential, not a user password. It still guards `/upload`
and `/user`, and it is one of the two ways into `/validate` (the other being a
signed-in account). The data repository's three workflows and
`backend/Makefile` use it; nothing in the browser does.

There is no default in a deployment. Laptops get `changeit` from the
`[development]` section of `settings.toml`. When `DEPLOYMENT` is set (every
k8s overlay sets it to `dev`, `stage` or `prod`), the backend refuses to start
if `API_PASSWORD` is missing, is `changeit`, or is shorter than 16 characters,
or if `POSTGRES_PASSWORD` is empty. The pod log then ends with
`DEPLOYMENT=<name>: refusing to start.` and the reason. Only the API does this
check: the upload CronJob and the migrations still run (#264).

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
default port 5173 and any other local port. It documents this for OAuth
authorization and recommends `127.0.0.1` over `localhost`. If a GitHub App ever
refuses it, register the port too. Then in `secrets/.env`:

```
GITHUB_OAUTH_CLIENT_ID=...
GITHUB_OAUTH_CLIENT_SECRET=...
PUBLIC_BASE_URL=http://127.0.0.1:5173      # the Vite port
```

and open the app at `http://127.0.0.1:<port>`, not `localhost`. Cookies ignore
the port but not the host: the `resslab_login` cookie set when you click the
button must still be there when GitHub sends the browser back. Restart the
backend after editing the file, Dynaconf only reads it at startup.

Without the two `GITHUB_OAUTH_*` settings the GitHub button is still shown,
but clicking it comes back to the login page with `?error=github_disabled`
("GitHub sign-in is not available here"), so a deployment without the pair
does not show a raw JSON error.

### ORCID

ORCID is self-service: a client of the public API is free, and EPFL has
nothing to register. The client belongs to the ORCID record that creates it.
For production, create it from a lab record, not a personal one.

1. Sign in to ORCID, open "Developer tools" and register a public API client.
   For tests and a laptop, do this on https://sandbox.orcid.org. The sandbox
   has its own accounts, and it only sends mail to `@mailinator.com`
   addresses, so make the sandbox account with one.
2. Add the redirect URI: `<PUBLIC_BASE_URL>/api/auth/orcid/callback`, one entry
   per environment. Locally, that is the Vite port, for example
   `http://127.0.0.1:5173/api/auth/orcid/callback`. Register the exact URL. The form refuses `localhost`
   (for the redirect URI and for the application URL), so use `127.0.0.1`,
   and the GitHub repository as the application URL.
3. Put the client id and secret in `secrets/.env`, with `ORCID_SANDBOX=true`
   for a sandbox client:

```
ORCID_CLIENT_ID=APP-...
ORCID_CLIENT_SECRET=...
ORCID_SANDBOX=true
PUBLIC_BASE_URL=http://127.0.0.1:5173      # the Vite port
```

Restart the backend after you edit the file. As for GitHub, open the app on
the host of `PUBLIC_BASE_URL`, or the `resslab_login` cookie is lost on the
way back.

Without the two keys the ORCID button is still shown. A click comes back to
the login page with `?error=orcid_disabled` ("ORCID sign-in is not available
here").

### Mail

With no `SMTP_HOST` the code and the link are written to the log instead of
being sent, which is how local development and the tests work.

That fallback is only for runs without `DEPLOYMENT`. The k8s ConfigMaps set
it (`dev`, `stage`, `prod`), and nothing local does. In a deployment with no
`SMTP_HOST`, the backend logs an error at startup (`SMTP_HOST is not set on
deployment ...`), and `POST /auth/email/start` answers `503` with
`mail_not_configured`. The login page then says email sign-in is not set up on
this server. Before, the code went to the backend log and the page said a mail
was on its way (#247). The pod still starts: the database must stay up for
everyone, even when the mail is broken.

The deployments use the EPFL mail relay on port 587 with STARTTLS, and a
service account of the Hub. Its password is in the secret store of the
deployment. The relay offers `AUTH GSSAPI NTLM LOGIN`; aiosmtplib knows
cram-md5, plain and login, so it picks LOGIN and no NTLM code is needed.

```env
SMTP_HOST=<relay host>
SMTP_PORT=587
SMTP_STARTTLS=true
SMTP_USER=<DOMAIN>\<service account>
SMTP_PASSWORD=<password of the service account>
SMTP_FROM=<address of the service account>
```

Two traps in that block:

- **Do not put double quotes around `SMTP_USER`.** Dynaconf reads the file
  with python-dotenv, which turns `\n` inside double quotes into a real
  newline, so a `DOMAIN\noreply-...` login becomes two broken lines. No
  quotes (as above) or single quotes both keep the backslash. Same rule in
  YAML. The `DOMAIN\account` form is the one that works with the EPFL relay.
- **The sender must be the account's own address.** Anything else comes back
  as `550 5.7.60 SMTP; Client does not have permissions to send as this
  sender`. A `+suffix` address is for the anonymous relay on port 25, not for
  a service account on 587. Staying under `epfl.ch` is also what makes SPF and
  DKIM pass; a sender on a subdomain with no DNS records of its own gets
  junked.

Mails go out as `RESSLab Hub <SMTP_FROM>`. There is no `Reply-To`: it is a
noreply mailbox, and a reply would carry a sign-in code to whoever reads it.

When the relay refuses or does not answer within 15 seconds, `POST
/auth/email/start` answers `503` with `mail_failed` and the login page says
so. The challenge is rolled back, so a broken relay does not eat the hourly
caps of the person trying to sign in. The SMTP reason is in the backend log,
on a `Mail to ... failed (host:port): <error class>: <reason>` line. The code
never is.

### Settings

| Key | What it is |
|---|---|
| `PUBLIC_BASE_URL` | Where the app is reached, without `/api`. Every absolute URL comes from it. |
| `API_USERNAME` / `API_PASSWORD` | The machine credential (Basic auth). Username defaults to `user`. |
| `GITHUB_OAUTH_CLIENT_ID` / `_SECRET` | The App's OAuth pair (above). |
| `ORCID_CLIENT_ID` / `_SECRET` | The ORCID public API client (above). |
| `ORCID_SANDBOX` | `true` talks to sandbox.orcid.org instead of orcid.org. `false` by default. |
| `SMTP_HOST` / `SMTP_PORT` | The relay. No host = log-only mode locally, `503 mail_not_configured` in a deployment (above). |
| `SMTP_STARTTLS` | On by default; the EPFL relay needs it on port 587. |
| `SMTP_USER` / `SMTP_PASSWORD` | The service account (above, mind the quoting). |
| `SMTP_FROM` | Sender address. The display name is fixed in the code. |
| `ADMIN_EMAILS` | Comma-separated addresses that are always administrators. For an admin with no GitHub account, and so a fresh deployment has one without a CLI (Roles, below). |
| `CONTRIBUTOR_DOMAINS` | Comma-separated domains that count as academic on top of the swot list ("What counts as academic", below). |
| `SESSION_TTL_DAYS` | 30 by default. |
| `LOGIN_CODE_TTL_MINUTES` | 10 by default. |
| `SESSION_COOKIE_SECURE` | Derived from the `PUBLIC_BASE_URL` scheme; set it only to override. |
| `DEPLOYMENT` | `dev`, `stage` or `prod`, set by the overlay ConfigMaps. Never set it locally. When set, a missing `SMTP_HOST` is an error. |
| `CONTRIBUTIONS_ENABLED` | `true` by default. `false` also switches sign-in and the account page off, see [contributing-data.md](contributing-data.md#settings). |

In the deployments these go in the secret store of the deployment and reach
the pods as environment variables, like the GitHub App credentials.

## Deploying the mail relay

The manifests and the secrets of the deployments live outside this repo. For
each environment, dev first:

1. Add `SMTP_HOST`, `SMTP_USER`, `SMTP_FROM` and `SMTP_PASSWORD` to the secret
   store of the deployment. Paste `DOMAIN\account` plainly, with no escaping.
2. Make sure that the backend gets the new keys, then restart the backend.
   Dynaconf reads the environment at startup only, so without a restart the
   backend still has no relay.
3. Right after startup, the backend log says `Mails go through <host>:587`,
   not `SMTP_HOST is not set`. Sign in on the deployed `/login` with a real
   address. The mail arrives from "RESSLab Hub".
4. If the keys did not arrive, the page says "Email sign-in is not set up on
   this server". If the relay refuses, the page says "The sign-in mail could
   not be sent", and the backend log has the reason on a `Mail to ... failed`
   line. If the log shows an `SMTPAuthenticationError`, read the password and
   the quoting of `SMTP_USER` again.

## Signing in locally

With no `SMTP_HOST` configured, the code is in the backend log, so no mail
server is needed to sign in locally:

```
make dev-all
# open http://127.0.0.1:5173/login  (the Vite port, not the backend one)
# then look for the "Sign-in code" line in the output of the backend
```

The link on the line below it works too, and skips the typing.

## Testing the pipeline

No second App is needed. The same App is installed on two orgs: on
RESSLab-Team for the real `resslab-hub-data`, and on EPFL-ENAC for the test
fork `resslab-hub-data-test`. An installation id is per org, so `DATA_REPO` and
`GITHUB_APP_INSTALLATION_ID` always change together. Which branch a submission
targets is `DATA_REPO_BASE_BRANCH`, and the curation queue only lists pull
requests into that branch. Every environment uses `main`, the default.

**Locally and on dev**, submissions go to the fork (two lines of settings, see
[contributing-data.md](contributing-data.md#trying-it-locally)). A merge on the
fork's `main` goes to the dev hub.
Merge or close them as you like there, and run `make data-fork-reset` when the
fork's `main` has drifted too far from the real one.

```bash
gh pr list --repo EPFL-ENAC/resslab-hub-data-test --base main
```

Roles that come from GitHub (below) are read on `DATA_REPO` too, so locally
they are your permission on the fork. `ADMIN_EMAILS` still makes you admin.

**From stage** (the test site), a submission opens a real pull request into
the real `main`, next to the real ones. **Close those, never merge them.**

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

1. A verified address of the account in `ADMIN_EMAILS` -> `admin`
   (`admin-email`).
2. Admin on `resslab-hub-data`, through the linked GitHub account -> `admin`
   (`github`).
3. A decision of an administrator, `role_override` (`override`). Changing a
   role on the admin page, approving an access request and using an
   invitation all write it.
4. Write or maintain on `resslab-hub-data` -> `curator` (`github`).
5. An academic address of the account -> `contributor` (`academic-email`,
   below).
6. Otherwise `viewer` (`default`).

The two admin sources come before the override on purpose: nobody can
demote, from the Hub, an admin that GitHub or the config made. The admin
page shows those rows as read only. To remove such an admin, change it on
GitHub or in `ADMIN_EMAILS`.

Only a **verified** address counts, but any of them does, not only the main
one: someone who signs in with GitHub and a gmail address becomes a
contributor once they add their EPFL address. Mail sign-in and an added
address verify by construction; GitHub sign-in verifies when GitHub reports
the address as verified. Removing an address works the role out again, so
`academic-email` or `admin-email` can go with it. A role from an invitation or
an administrator is an override and stays.

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

These admins are also who the Hub asks to review each pull request it opens
(#266, see [contributing-data.md](contributing-data.md#after-the-pull-request)).
The merge gate itself is a GitHub setting: the ruleset `data-contribution` on
the data repository `main` (one approving review, checks, squash only).

### What counts as academic

The list is [JetBrains swot](https://github.com/JetBrains/swot), the one
JetBrains uses to hand out student licences (#375). We read it from the
`pyswot` package, which carries a snapshot of swot inside the wheel. So
there is no network call at sign-in. The swot commit of the snapshot is on
line 2 of `pyswot/vendor/tlds.py`; `make swot-update` prints it.

`roles.py` applies the same rules as swot's own code (`Swot.kt`):

1. **The stoplist wins.** A domain on it, or under one, is refused. That is
   how swot leaves out alumni domains (`alumni.stanford.edu`) and listed
   schools that people abused (`glion.ch`).
2. **Some second-level domains are academic as a whole.** Anything under
   `edu.cn`, `ac.za`, `edu.hk`, `k12.ny.us` and about 90 more passes.
   Bare `.edu` and `.ac.uk` are not on that list: `example.edu` is refused
   if nobody added it to swot.
3. **Else the domain must be in the swot tree.** A subdomain matches its
   school: `sti.epfl.ch` matches `epfl.ch`, `cs.stanford.edu` matches
   Stanford.

Two things we do not take, on purpose:

- `pyswot.is_academic` also refuses a list of free mailboxes that swot does
  not have. That list holds real universities (`nus.edu.sg`, `unican.es`),
  so we do not call it. Gmail and the like are refused anyway: they are on
  no list.
- swot's `abused.txt` (real schools where students cheated on the licence
  form). `Swot.kt` does not read it either. For us the risk is a pull
  request that a curator reviews anyway, not a free licence.

The list is good on universities (EPFL, ETHZ, Stanford, Tokyo, Imperial,
Politecnico, TUM) and knows nothing about research institutes or industry.
Empa, NIST, AISC and Arup are all absent. That is what `CONTRIBUTOR_DOMAINS`
is for:

```env
CONTRIBUTOR_DOMAINS=empa.ch,aisc.org
```

A subdomain of a listed domain matches too, so `lab.empa.ch` passes. A bare
top-level domain never matches, so `ch` in that setting hands the role to
nobody. This setting is checked before swot, so it also wins over the
stoplist.

#### Refreshing the list

pyswot re-vendors swot every week and releases a new version. To take it:

```sh
cd backend && make swot-update   # bumps pyswot in uv.lock, prints the swot commit
```

Commit `backend/uv.lock`. The new list counts once the backend is deployed,
see "When a change shows" below.

If pyswot stops being released one day, copy its `scripts/update_vendor.py`
into `backend/data/` and commit the module it writes. The code in `roles.py`
only needs the stoplist, the academic TLDs and a domain lookup.

#### When a university is missing

Three ways, from the fastest:

- The person asks for access from the account page (see "Asking for
  access" below). An admin approves, done.
- Add the domain to `CONTRIBUTOR_DOMAINS` for a whole institution.
- Add it to swot with a pull request (rules in its README), then
  `make swot-update` once pyswot has a release with it.

### What the role gates

| | viewer | contributor | curator | admin |
|---|---|---|---|---|
| `/validate` | yes | yes | yes | yes |
| `POST /auth/access-request` | yes | | | |
| Open a submission (`POST /contributions`) | | yes | yes | yes |
| Update a submission (`PUT /contributions/{pr}`) | | own | any | any |
| Read one submission (`GET /contributions/{pr}` and below) | | own | any | any |
| The queue (`GET /contributions`) | | | yes | yes |
| Verification (`/verification/*`) | | | yes | yes |
| `/admin/*` | | | | yes |

"Own" means the `Submitted-by` trailer of the first Hub commit matches one of
the account's verified addresses. The frontend routes ask for the same roles
(`meta.auth` in `router/index.ts`): the sidebar shows the review queue to
curators only and the Administration link to admins only.

### The admin page

`/admin` (`views/AdminView.vue`, backend `routers/admin.py`) has four parts.

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
  the role is theirs as soon as an account proves that address: a sign-in
  with it, by mail or by GitHub, or adding it to an account from the account
  page. Inviting an address that already belongs to an account (main or
  added) is refused: change their role in the members list instead. A
  pending invitation can be revoked.
- **Merge two accounts.** For one person with two accounts, for example an
  EPFL one made by code and a GitHub one with a gmail (#402). `POST
  /admin/users/{keep}/merge` with `{"from_user_id": ...}` moves every
  identity of the second account to the first (addresses and GitHub), so
  they all sign in to the kept account and the submissions follow, since a
  submission belongs to its addresses. The stronger override wins, empty
  profile fields are filled, a second pending access request is declined,
  invitations and decisions point to the kept account. Then the second
  account is deleted, which signs it out everywhere. Refused: the same
  account twice (409 `same_account`), a disabled account (409
  `account_disabled`), two different GitHub accounts (409 `both_github`,
  unlink one first), and an admin merging their own account away (403
  `cannot_change_self`; merging another one into your own is fine). Nothing
  can undo a merge, so the button asks twice.

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
- A new `CONTRIBUTOR_DOMAINS` or `ADMIN_EMAILS` entry, or a new swot
  snapshot: at the person's next sign-in, or within the hour when their
  GitHub is linked. Sessions last 30 days, so tell them to sign out and
  back in.

## Backup

The `auth_*` tables are the only data that is not in the data repo. If the
database is lost, the upload job brings back the data, not the accounts. So
each deployment dumps these tables every night and keeps 30 days of dumps.
What is in the dump and how to restore it:
[backend/README.md](https://github.com/RESSLab-Team/resslab-hub/blob/dev/backend/README.md#backup-and-restore-of-a-deployed-database).

## Later

- **#249, #252** the other academic identity providers of the mockup: SWITCH
  edu-ID / eduGAIN and EPFL Entra ID each need EPFL to register the
  application, so those requests should be filed early. Each one is another
  provider in `auth_identity` and a copy of `auth/orcid_oauth.py`, with the
  shared `state` of `auth/oauth_state.py`.
- Join a bare GitHub account the same way as an ORCID one, from the GitHub
  callback.
- **#254** approve or ask for changes from the Hub.
- Academic domains edited from the admin page rather than in
  `CONTRIBUTOR_DOMAINS`, and a "my submissions" list for contributors.
