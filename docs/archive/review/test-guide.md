# Test guide: sign-in, accounts, roles and contributions

This guide is for the person who tests the Hub by hand before the workshop. It lists every case to try, with the steps and the result we expect. You do not need to read code. You need a browser, some mailboxes, a GitHub account and an ORCID account.

How to use it:

1. Read Part 0 once, and prepare the accounts.
2. Run the parts in order. Some parts need an account from an earlier part.
3. For each case, tick "Pass" or "Fail". When it fails, open an issue (template in Part 0) and write its number in the note.
4. "To confirm" in an expected result means we were not sure when we wrote the guide. Write what you see. It is not a fail by itself.
5. If a screen does not match the guide (other button name, other step), it is not a bug. Write it in the note, so we fix the guide.

## Part 0. Before you start

### 0.1 Where you test

| Site  | URL                                | When                         |
| ----- | ---------------------------------- | ---------------------------- |
| stage | `https://resslab-hub-test.epfl.ch` | Parts 1 to 14 and 17 to 19   |
| dev   | `https://resslab-hub-dev.epfl.ch`  | Parts 15 and 16, with Pierre |

In this guide, `<hub>` means the stage URL and `<dev>` means the dev URL. An API address like `<hub>/api/auth/me` means: type it in the address bar of the browser.

On stage, a submission opens a real pull request on the real data repository, `RESSLab-Team/resslab-hub-data`. This repository is public. Everybody on the internet can read what you submit, with your name and your address.

### 0.2 Rules

- Never merge a pull request on `RESSLab-Team/resslab-hub-data`. Never approve one.
- Use only ids that start with `DEMO-` in the data you submit.
- Write the number of each pull request you open in the cleanup list of Part 19, the same day.
- Do not start Part 12 before Pierre tells you that stage no longer sends a review request to every lab admin (`DATA_REPO_REVIEWERS`).
- Do only what a normal user can do in a browser. Do not use scripts, scanners or load tools against stage or prod.
- Never test on prod (`https://resslab-hub.epfl.ch`).
- If something looks like a security hole (you see the data of another person, you get a page you must not get), stop that part and write to Pierre directly. Do not post it anywhere public.

### 0.3 Mailboxes and accounts

Prepare these before Part 1. One Gmail inbox gives several addresses with the `+` sign: mail to `you+m2@gmail.com` arrives in `you@gmail.com`. The Hub sees each `+` address as a different address.

| Name in this guide | What                                                                                                                                                                                                              | Hub role we expect                         |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| `M1`               | Your EPFL address (Outlook, with "safe links")                                                                                                                                                                    | contributor, automatic (academic address)  |
| `M2`               | `you+m2@gmail.com`                                                                                                                                                                                                | viewer                                     |
| `M3`               | `you+m3@gmail.com`                                                                                                                                                                                                | viewer, then used for invitations          |
| `M4`               | `you+m4@gmail.com`                                                                                                                                                                                                | viewer, then used for access requests      |
| `MA`               | `you+admin@gmail.com`                                                                                                                                                                                             | administrator, given by Pierre (see below) |
| `GH`               | Your own GitHub account. Add `you+gh1@gmail.com` and `you+gh2@gmail.com` to it as verified addresses (GitHub, Settings, Emails). Do not create a second GitHub account: GitHub allows one free account per person | depends on the case                        |
| `OR`               | An ORCID account. Pierre tells you if stage uses `orcid.org` or `sandbox.orcid.org`. On the sandbox, ORCID only sends mail to `@mailinator.com` addresses                                                         | depends on the case                        |

Before Part 1, sign in once with `MA` (Part 1 shows how) and send the address to Pierre. He makes this account an administrator. You use it for Parts 8, 9 and 10.

Some cases need a second person (a colleague) with their own GitHub account. They are marked "second person".

### 0.4 Browsers

A session lives in one browser profile. To be several people at once, use several profiles:

| Name          | What                        | Signed in as                       |
| ------------- | --------------------------- | ---------------------------------- |
| Browser A     | Chrome, profile "Hub A"     | the account of the case            |
| Browser B     | Chrome, profile "Hub B"     | a second account                   |
| Browser ADMIN | Chrome, profile "Hub admin" | `MA`, all the time                 |
| Private       | A private window of Firefox | nobody, for "not signed in" checks |

Also have a phone, for Part 17.

To read cookies: open the developer tools (F12), tab "Application" in Chrome or "Storage" in Firefox, then "Cookies".

### 0.5 Test data

Pierre sends you `sample-data.zip`. Extract it. It has one folder per database. Each folder has:

- `<name>.csv`: a good batch of 15 experiments. The check passes, with range warnings on the last 3 rows.
- `<name>.invalid.csv`: the same batch with one problem per row. The check fails.
- Subfolders with one CSV per experiment: the measured curves.

| Database in the editor | Folder                       |
| ---------------------- | ---------------------------- |
| Connections            | `connections/`               |
| Columns                | `columns/`                   |
| Braces                 | `braces/`                    |
| HSS columns            | `hss_columns/`               |
| Cyclic coupons         | `material/cyclic_coupons/`   |
| Residual stresses      | `residual_stresses/`         |
| EBF links              | `eccentric_braced_frames/`   |
| Tensile coupons        | `material/tensile_coupons/`  |
| Ductile fracture       | `material/ductile_fracture/` |

All ids in these files start with `DEMO-`. Keep it that way.

### 0.6 Mail limits

The Hub sends at most 5 sign-in mails per address per hour, and at most 20 per network per hour. Your whole office counts as one network. When a limit is reached, the page still says that a code was sent, on purpose, but no mail comes.

- Plan the mail cases. Do not ask for codes you do not need.
- Keep each browser profile signed in. Sign out only when the case asks.
- If no mail comes within 2 minutes, look in the spam folder. If it is not there, you probably reached a limit. Write the time in the note and wait one hour.

### 0.7 How to report a bug

Open one issue per bug on `RESSLab-Team/resslab-hub` (private repository). Never on the data repository. Use this text:

```markdown
Case: 2.6 (test guide)
Site: stage
When: 2026-11-20 14:32
Browser: Chrome 142, profile Hub A
Account: M2 (viewer)

Steps:

1. ...
2. ...

Expected: ...
Got: ...

Screenshot: (paste it here)
```

Do not paste a sign-in code, a sign-in link or a cookie value in an issue.

## Part 1. Smoke test (5 minutes)

Run it at the start of each test day. If one case fails, tell Pierre before you go on.

#### 1.1 The home page opens

Needs: Private window.

1. Open `<hub>/`.

Expected: The home page shows the databases. No sign-in is asked. The left menu has a "Contribute" section with "New submission", and an "Account" section with "Sign in".

- [ ] Pass
- [ ] Fail, issue:

#### 1.2 A database opens without an account

Needs: Private window.

1. Click "Braces" in the left menu.

Expected: The table and the charts load. No sign-in is asked.

- [ ] Pass
- [ ] Fail, issue:

#### 1.3 Contributions are on

Needs: Private window.

1. Open `<hub>/api/features`.

Expected: The page shows `{"contributions":true}`.

- [ ] Pass
- [ ] Fail, issue:

#### 1.4 The editor asks you to sign in

Needs: Private window.

1. Open `<hub>/contribute`.

Expected: The address changes to `/login?next=/contribute/new`. The page title is "Sign in to contribute". You see "Continue with GitHub", "Continue with ORCID", and "or with your email" with an Email field.

- [ ] Pass
- [ ] Fail, issue:

#### 1.5 Sign in with a code

Needs: Browser A, mailbox `M1`.

1. Open `<hub>/login`.
2. Type `M1` in the Email field. Click "Send me a code".
3. Open the mail. Type the 6 digits in "Six-digit code". Click "Sign in".

Expected: The page says "We sent a six-digit code to `M1`..." after step 2. The mail subject is "`<code>` is your RESSLab Hub sign-in code". After step 3, you are on the home page. The left menu shows your name and the role "Contributor" under "Account".

- [ ] Pass
- [ ] Fail, issue:

#### 1.6 Sign out

Needs: Browser A, signed in.

1. Click your name in the left menu. You are on "Your account".
2. Click "Sign out".

Expected: The left menu shows "Sign in" again. Opening `<hub>/account` sends you to the sign-in page.

- [ ] Pass
- [ ] Fail, issue:

## Part 2. Sign in by email

#### 2.1 First sign-in creates an account

Needs: Browser A, mailbox `M2`, never used on the Hub.

1. Open `<hub>/login`. Type `M2`. Click "Send me a code".
2. Type the code. Click "Sign in".
3. Open "Your account".

Expected: You are signed in. The name is made from the part of the address before `@`, with a capital letter (`you+m2@gmail.com` gives "You+m2"). The address shows "confirmed". The role is "Viewer", with "Everyone starts here."

- [ ] Pass
- [ ] Fail, issue:

#### 2.2 The link in the mail, same browser

Needs: Browser A, not signed in, mailbox `M2`.

1. Open `<hub>/login`. Type `M2`. Click "Send me a code".
2. In the mail, click the link instead of typing the code. Open it in the same browser.

Expected: A page says "Signing you in..." for a moment, then you are signed in as `M2` on the home page.

- [ ] Pass
- [ ] Fail, issue:

#### 2.3 The link in another browser

Needs: Browser A and Browser B, both signed out, mailbox `M2`.

1. In Browser A, ask for a code for `M2`.
2. Copy the link from the mail. Paste it in Browser B.

Expected: Browser B is signed in as `M2`. Browser A is still on the code step, not signed in. The code of the same mail no longer works in Browser A ("That code or link is no longer valid. Ask for a new one.").

- [ ] Pass
- [ ] Fail, issue:

#### 2.4 The link through Outlook "safe links"

Needs: Browser A, signed out, mailbox `M1` (EPFL Outlook).

1. Ask for a code for `M1`.
2. In Outlook, click the link. It goes through `safelinks.protection.outlook.com` first.

Expected: You are signed in. Outlook checks the link before you, but this must not use it up. To confirm.

- [ ] Pass
- [ ] Fail, issue:

#### 2.5 A wrong code

Needs: Browser A, signed out, mailbox `M2`.

1. Ask for a code. Type `000000` (or any wrong 6 digits). Click "Sign in".

Expected: "That code is not right. Check the mail and try again." You can type again.

- [ ] Pass
- [ ] Fail, issue:

#### 2.6 Five wrong codes

Needs: Browser A, the same code step as in 2.5.

1. Type 4 more wrong codes, one by one.
2. Type the right code.
3. Click the link in the mail.

Expected: Tries 1 to 4 show "That code is not right...". The 5th wrong try shows "Too many tries. Ask for a new code." The right code then also shows "Too many tries...". The link in the mail still signs you in (to confirm: the link is a long secret, so it does not count tries).

- [ ] Pass
- [ ] Fail, issue:

#### 2.7 A code after 10 minutes

Needs: Browser A, signed out, mailbox `M2`.

1. Ask for a code. Wait 11 minutes.
2. Type the code.

Expected: "That code or link is no longer valid. Ask for a new one."

- [ ] Pass
- [ ] Fail, issue:

#### 2.8 A link after 10 minutes

Needs: The mail of 2.7.

1. Click the link of that mail.

Expected: The page shows "That code or link is no longer valid. Ask for a new one." and a button "Back to sign in".

- [ ] Pass
- [ ] Fail, issue:

#### 2.9 A code used twice

Needs: Browser A, signed out, mailbox `M2`.

1. Sign in with a code. Sign out.
2. Open `<hub>/login`, go to the code step without asking a new mail (ask a code for `M2`, then type the old code from step 1).
3. Click the link of the first mail.

Expected: Step 2 shows "That code is not right..." (the new code is the one that counts). Step 3 shows "That code or link is no longer valid...".

- [ ] Pass
- [ ] Fail, issue:

#### 2.10 Two codes in a row

Needs: Browser A, signed out, mailbox `M2`.

1. Ask for a code for `M2`. Click "Use another address". Ask again for `M2`.
2. You get two mails. Type the code of the first mail.
3. Type the code of the second mail.

Expected: Step 2 shows "That code is not right..." Step 3 signs you in.

- [ ] Pass
- [ ] Fail, issue:

#### 2.11 Capitals and spaces in the address

Needs: Browser A, signed out, mailbox `M2`.

1. Type `M2` with capitals, for example `You+M2@Gmail.com`, with one space before it and one space after it. Ask for a code and sign in.

Expected: You are in the same account as in 2.1, not a new one. The address shows in lower case.

- [ ] Pass
- [ ] Fail, issue:

#### 2.12 A "+" address is another account

Needs: Browser A, signed out, a new address `you+plus@gmail.com`.

1. Sign in with this address.

Expected: A new account, separate from `M2`. Role "Viewer". This is on purpose: the Hub does not cut the part after `+`.

- [ ] Pass
- [ ] Fail, issue:

#### 2.13 An address that is not valid

Needs: Private window.

1. Type `abc`, then `a@b`, then `a b@c.org` in the Email field.

Expected: "Send me a code" stays disabled for each one.

- [ ] Pass
- [ ] Fail, issue:

#### 2.14 Paste a code with a space

Needs: Browser A, on the code step.

1. Paste the code with a space in the middle (`123 456`).

Expected: The field takes 6 characters at most, so it keeps `123 45` and "Sign in" stays disabled, with no message. This is a small bug: write it in the note, no issue needed. Also write how the code looks in the mail (with or without a space).

- [ ] Pass
- [ ] Fail, issue:

#### 2.15 You come back where you were

Needs: Private window, mailbox `M1`.

1. Open `<hub>/contribute/new`. The sign-in page opens.
2. Sign in with a code.
3. Sign out. Do steps 1 and 2 again, but click the link in the mail instead.

Expected: After step 2 and after step 3, you land on `/contribute/new`, the editor.

- [ ] Pass
- [ ] Fail, issue:

#### 2.16 You never go to another site

Needs: Private window, mailbox `M2`.

For each address below: open it, sign in with the code, look where you land. Then do it again with the link of the mail.

- `<hub>/login?next=https://example.com`
- `<hub>/login?next=//example.com`
- `<hub>/login?next=/\example.com`
- `<hub>/login?next=javascript:alert(1)`

Expected: You always land on a page of the Hub (the home page), never on `example.com`. No pop-up opens.

- [ ] Pass
- [ ] Fail, issue:

#### 2.17 The sixth mail of the hour

Needs: Browser A, signed out, mailbox `M4`, not used in the last hour.

1. Ask for a code for `M4` 6 times in a row (click "Use another address" each time). Write the time.

Expected: Mails 1 to 5 arrive. For the 6th, the page says a code was sent, but no mail comes. Any code shows "That code or link is no longer valid...". After one hour, a new code works. Write in the note how a user can know what happened.

- [ ] Pass
- [ ] Fail, issue:

#### 2.18 Sign in when you are already signed in

Needs: Browser A, signed in as `M2`, mailbox `M3`.

1. Open `<hub>/login`.
2. Sign in with `M3`.

Expected: Step 1 shows the sign-in form, with no message that you are already signed in. After step 2, the left menu shows the `M3` account, and `<hub>/api/auth/me` shows `M3`.

- [ ] Pass
- [ ] Fail, issue:

#### 2.19 Where the mail lands

Needs: The mails of this part.

1. For each mailbox (`M1`, Gmail), look where the sign-in mail landed: inbox, spam, "promotions".
2. Look at the mail itself: sender, subject, the code, the link, the logos.

Expected: The mail lands in the inbox. It shows the code in large digits, and a link. Write the sender address in the note.

- [ ] Pass
- [ ] Fail, issue:

## Part 3. Sign in with GitHub

Before this part, make sure that `GH` is not linked to any Hub account. If you are not sure, ask Pierre.

#### 3.1 First sign-in with GitHub

Needs: Browser A, signed out. In GitHub settings, set the primary address of `GH` to `you+gh1@gmail.com` (never used on the Hub).

1. Open `<hub>/login`. Click "Continue with GitHub".
2. GitHub asks you to authorize the app. Look at what it asks for. Click "Authorize".
3. Open "Your account".

Expected: At step 2, GitHub asks only to read your profile and your email addresses. After step 2, you are signed in. The name is your GitHub name (or your GitHub login if you have no name). The address is `you+gh1@gmail.com`, confirmed. "Ways to sign in" shows GitHub. "Email addresses" shows `you+gh1@gmail.com` as "Main". Role "Viewer".

- [ ] Pass
- [ ] Fail, issue:

#### 3.2 Sign in again with GitHub, then by code

Needs: The account of 3.1.

1. Sign out. Click "Continue with GitHub".
2. Sign out. Sign in by code with `you+gh1@gmail.com`.

Expected: Both times you are in the same account as in 3.1. GitHub does not ask to authorize again.

- [ ] Pass
- [ ] Fail, issue:

#### 3.3 You say no on GitHub

Needs: Browser B, signed out. In GitHub, Settings, Applications, revoke the Hub app, so GitHub asks again.

1. Click "Continue with GitHub". On GitHub, click "Cancel".

Expected: You are back on the Hub sign-in page, with "You cancelled the GitHub sign-in." Nobody is signed in.

- [ ] Pass
- [ ] Fail, issue:

#### 3.4 GitHub primary address changed after the first sign-in

Needs: The account of 3.1, signed out. In GitHub, set the primary address of `GH` to `you+gh2@gmail.com`.

1. Sign in with GitHub.
2. Open "Your account".

Expected: You are in the same account as in 3.1. The Hub keeps `you+gh1@gmail.com`. It does not add or change the address. Set the primary back to `you+gh1@gmail.com` after.

- [ ] Pass
- [ ] Fail, issue:

#### 3.5 Remove GitHub from the account

Needs: The account of 3.1, signed in.

1. On "Your account", under "Ways to sign in", click "Remove" next to GitHub.
2. Sign out. Sign in by code with `you+gh1@gmail.com`.

Expected: GitHub leaves the list. "Link GitHub" shows again. The code sign-in still works, in the same account.

- [ ] Pass
- [ ] Fail, issue:

#### 3.6 GitHub with the address of an existing Hub account

Needs: Browser A, signed out. `GH` is not linked any more (3.5). The Hub account of `you+gh1@gmail.com` exists. The GitHub primary is `you+gh1@gmail.com`.

1. Click "Continue with GitHub".

Expected: You are back on the sign-in page with "That address already has an account here. Sign in with it, then link GitHub or ORCID from your account page." No new account. Nobody is signed in.

- [ ] Pass
- [ ] Fail, issue:

#### 3.7 Link GitHub from the account page

Needs: Browser A, signed in by code as `you+gh1@gmail.com`. `GH` is not linked.

1. On "Your account", click "Link GitHub".

Expected: You come back on "Your account". GitHub is in "Ways to sign in". "Continue with GitHub" now signs you in to this account.

- [ ] Pass
- [ ] Fail, issue:

#### 3.8 GitHub with a different address than your Hub account

This is the common mistake: a person signs in by code with their university address, and another day with GitHub, whose address is a Gmail.

Needs: Browser A, signed in as `M2` (made in 2.1). First remove `GH` from the 3.1 account (like in 3.5). In GitHub, set the primary address to `you+gh2@gmail.com` (never used on the Hub).

1. Sign out. Click "Continue with GitHub".
2. Open "Your account". Write the name, address and role.
3. Sign out. Sign in by code with `M2`.

Expected: Step 1 creates a second, new account, with `you+gh2@gmail.com`. It is not the `M2` account. Step 3 opens the `M2` account, which has no GitHub. This is how the Hub works today: only an administrator can join two accounts (case 10.6). Write in the note if a user can understand what happened.

- [ ] Pass
- [ ] Fail, issue:

#### 3.9 Link a GitHub that is on another account

Needs: The account made in 3.8 has `GH`. Browser B, signed in as `M2`.

1. In Browser B, on "Your account", click "Link GitHub".

Expected: You come back on "Your account" with "That GitHub or ORCID account is already linked to another account here." `M2` still has no GitHub.

- [ ] Pass
- [ ] Fail, issue:

#### 3.10 GitHub with a private address

Needs: Browser A, signed out. In GitHub, Settings, Emails, tick "Keep my email addresses private". Remove `GH` from every Hub account first (or ask Pierre to merge the account of 3.8 later, in 10.6).

1. Click "Continue with GitHub".
2. Open "Your account".

Expected: To confirm. GitHub still gives the Hub your primary address, because the Hub asks for it. If yes, the result is the same as 3.1. If not, the account has "No confirmed address", and you must add one (Part 5) to submit. Write which one happens.

- [ ] Pass
- [ ] Fail, issue:

#### 3.11 Remove the last way to sign in

Needs: An account with only GitHub and no address. If 3.10 gave an address, skip this case and tick "Pass".

1. On "Your account", click "Remove" next to GitHub.

Expected: "This one cannot be removed. Make another address main first, and keep at least one way to sign in." GitHub stays.

- [ ] Pass
- [ ] Fail, issue:

#### 3.12 Disabled GitHub on the site

Needs: Pierre tells you if a site has no GitHub sign-in. If none, skip this case.

1. Click "Continue with GitHub".

Expected: You stay on the Hub with "GitHub sign-in is not available here. Use your email address."

- [ ] Pass
- [ ] Fail, issue:

## Part 4. Sign in with ORCID

ORCID gives the Hub your iD and your name, never your address. So a first ORCID sign-in makes an account with no address, and the Hub asks for one.

#### 4.1 First sign-in with ORCID

Needs: Browser A, signed out. `OR` never used on the Hub.

1. Open `<hub>/login`. Click "Continue with ORCID".
2. Sign in on ORCID. Click "Authorize access".

Expected: You come back on "Your account", with a box "Add an email address" open. It says that ORCID does not give us your address. It has "Send the code" and "Skip for now". The name is your ORCID name. "Ways to sign in" shows ORCID with your iD. Role "Viewer".

- [ ] Pass
- [ ] Fail, issue:

#### 4.2 Skip the address

Needs: The screen of 4.1.

1. Click "Skip for now".

Expected: The box closes. You go where you were before (the home page if you came from there). You are still signed in. On "Your account", the address line says "No confirmed address".

- [ ] Pass
- [ ] Fail, issue:

#### 4.3 An ORCID account without an address tries to contribute

Needs: The account of 4.2.

1. Open `<hub>/contribute/new`.
2. Look at the form "Ask for contributor access" on the page.

Expected: The page "Not open to your account" opens. It says that the page needs the Contributor role. The access form says that you must confirm an email address first. Write the exact text in the note: today it may say "sign out, then sign in once with your email", which is wrong for ORCID (you can add an address on your account page).

- [ ] Pass
- [ ] Fail, issue:

#### 4.4 Add a new address to the ORCID account

Needs: The account of 4.2, signed in. Address `you+orcid@gmail.com`, never used on the Hub.

1. On "Your account", click "Add an email address".
2. Type the address. Click "Send the code".
3. Type the code from the mail (subject "`<code>` confirms your address on RESSLab Hub"). Click "Add the address".

Expected: The mail has a code and no link. After step 3, the page says the address is now on your account. It shows in "Email addresses" as "Main", and at the top of the page with "confirmed". Still the same account (same ORCID).

- [ ] Pass
- [ ] Fail, issue:

#### 4.5 ORCID, then the address of an existing account: the two join

Needs: Browser A, signed in to the account of 4.4. Browser B, signed out. The address `M3` has a Hub account (sign in once with it if not).

1. In Browser A, on "Your account", click "Remove" next to ORCID. The account keeps `you+orcid@gmail.com`. `OR` is free again.
2. In Browser B, click "Continue with ORCID". You land on "Your account" with the "Add an email address" box. This is a new account with only ORCID.
3. Type `M3`. Send the code. Type it. Click "Add the address".

Expected: The page says that `M3` already had an account, that your ORCID iD is on that account now, and that you are signed in to it. The left menu shows the `M3` account. "Ways to sign in" of `M3` shows ORCID. The empty ORCID account is gone.

- [ ] Pass
- [ ] Fail, issue:

#### 4.6 Link ORCID from an existing account

Needs: Browser B, signed in as `M3` with `OR` (end of 4.5). Browser A, signed in as `M2`.

1. In Browser B, on "Your account", click "Remove" next to ORCID.
2. In Browser A, on "Your account", click "Link ORCID".

Expected: You come back on "Your account". ORCID is in "Ways to sign in", with your iD. "Continue with ORCID" now signs you in to the `M2` account.

- [ ] Pass
- [ ] Fail, issue:

#### 4.7 Link an ORCID that is on another account

Needs: `OR` linked to `M2` (4.6). Browser B, signed in as `M3`, without ORCID.

1. On "Your account", click "Link ORCID".

Expected: "That GitHub or ORCID account is already linked to another account here." `M3` has no ORCID.

- [ ] Pass
- [ ] Fail, issue:

#### 4.8 Link ORCID when the ORCID account is empty

Needs: Browser A, signed in as `M2` with `OR` (4.6). Browser B, signed in as `M3`.

1. In Browser A, click "Remove" next to ORCID.
2. In Browser B, sign out. Click "Continue with ORCID", then "Skip for now". This is a new account with only ORCID.
3. In Browser A, click "Link ORCID".

Expected: The link works. ORCID moves to `M2`. The empty ORCID account is gone: Browser B is signed out at its next page load.

- [ ] Pass
- [ ] Fail, issue:

#### 4.9 You say no on ORCID

Needs: Browser B, signed out.

1. Click "Continue with ORCID". On ORCID, click "Deny access".

Expected: Back on the sign-in page with "You cancelled the ORCID sign-in."

- [ ] Pass
- [ ] Fail, issue:

#### 4.10 Remove ORCID

Needs: `M2` with ORCID (4.6 or 4.8).

1. On "Your account", click "Remove" next to ORCID.

Expected: ORCID leaves the list. "Link ORCID" shows again. Sign-in by code still works.

- [ ] Pass
- [ ] Fail, issue:

#### 4.11 ORCID sign-in comes back with a broken link

Needs: Browser A, signed out.

1. Click "Continue with ORCID". When you are on the ORCID page, copy its address.
2. Sign in on ORCID in Browser B with that copied address (another browser).

Expected: Browser B comes back to the Hub sign-in page with "ORCID sign-in did not finish. Please try again." Nobody is signed in in Browser B. Do the same with GitHub: "GitHub sign-in did not finish. Please try again."

- [ ] Pass
- [ ] Fail, issue:

#### 4.12 The account of the address already has another ORCID

Needs: A second ORCID account `OR2` (on the sandbox, make one with another `@mailinator.com` address). If you have only one, skip. `M2` with `OR`: if 4.10 removed it, link it again from `M2`. Browser B, signed out.

1. In Browser B, click "Continue with ORCID" and sign in with `OR2`. You land on "Your account" with the "Add an email address" box.
2. Type `M2`. Send the code. Type it. Click "Add the address".

Expected: "That address belongs to another account here. Sign in with it to use that account." Browser B stays on the `OR2` account, with no address. `M2` still has `OR`, not `OR2`. An account has one ORCID iD.

- [ ] Pass
- [ ] Fail, issue:

#### 4.13 The account of the address is disabled

Needs: Browser ADMIN. Browser B, signed out. `OR` free: remove it from `M2` first.

1. In Browser ADMIN, disable `M3` on the admin page.
2. In Browser B, click "Continue with ORCID" and sign in with `OR`. You land on "Your account" with the "Add an email address" box.
3. Type `M3`. Send the code. Type it. Click "Add the address".
4. In Browser ADMIN, enable `M3` again.

Expected: Step 3 says "This account is disabled. Ask an administrator of the lab if you think it is a mistake." Browser B stays on the ORCID account. `M3` has no ORCID.

- [ ] Pass
- [ ] Fail, issue:

#### 4.14 Disabled ORCID on the site

Needs: Pierre tells you if a site has no ORCID sign-in. If none, skip.

1. Click "Continue with ORCID".

Expected: "ORCID sign-in is not available here. Use your email address."

- [ ] Pass
- [ ] Fail, issue:

## Part 5. Several addresses on one account

An account can have several addresses. Each one signs in to the same account, and each one counts for the role. The "Main" address gets the mails and signs new submissions.

#### 5.1 Add a second address

Needs: Browser A, signed in as `M2`. Address `you+m5@gmail.com`, never used on the Hub.

1. On "Your account", click "Add an email address".
2. Type `you+m5@gmail.com`. Click "Send the code".
3. Type the code from the mail. Click "Add the address".

Expected: The mail subject is "`<code>` confirms your address on RESSLab Hub". The mail has a code and no link. After step 3, the page says "`you+m5@gmail.com` is now on your account." The address is in "Email addresses", with "Make main" and "Remove" next to it. `M2` stays "Main".

- [ ] Pass
- [ ] Fail, issue:

#### 5.2 A wrong code when you add an address

Needs: Browser A, signed in as `M2`. Address `you+m6@gmail.com`.

1. Ask for a code for `you+m6@gmail.com`. Type a wrong code. Click "Add the address".
2. Type 4 more wrong codes. Then type the right code.

Expected: Step 1 shows "That code is not right. Check the mail and try again." After the 5th wrong code, "Too many tries. Ask for a new code." The right code then shows the same message. The address is not added.

- [ ] Pass
- [ ] Fail, issue:

#### 5.3 Add an address that is already yours

Needs: Browser A, signed in as `M2`.

1. Click "Add an email address". Type `M2`. Click "Send the code".

Expected: "That address is already on your account." No mail is sent.

- [ ] Pass
- [ ] Fail, issue:

#### 5.4 Add the address of another account

Needs: Browser A, signed in as `M2`. `M3` has its own account.

1. Click "Add an email address". Type `M3`. Click "Send the code".
2. Type the code from the mail. Click "Add the address".

Expected: The code is sent (the Hub checks that you own the address first). After step 2: "That address belongs to another account here. Sign in with it to use that account." `M3` is not added. The `M3` account does not change.

- [ ] Pass
- [ ] Fail, issue:

#### 5.5 Sign in with the second address

Needs: The account of 5.1.

1. Sign out. Sign in by code with `you+m5@gmail.com`.

Expected: You are in the `M2` account (same name, both addresses listed).

- [ ] Pass
- [ ] Fail, issue:

#### 5.6 Make another address the main one

Needs: The account of 5.1, signed in.

1. Next to `you+m5@gmail.com`, click "Make main".

Expected: `you+m5@gmail.com` shows "Main". `M2` shows "Make main". Click "Make main" on `M2` to put it back.

- [ ] Pass
- [ ] Fail, issue:

#### 5.7 Remove the main address

Needs: The account of 5.1, `M2` is "Main".

1. Look for "Remove" next to `M2`. If there is one, click it.

Expected: Either there is no "Remove" next to the main address, or you get "This one cannot be removed. Make another address main first, and keep at least one way to sign in." `M2` stays.

- [ ] Pass
- [ ] Fail, issue:

#### 5.8 Remove a second address

Needs: The account of 5.1.

1. Click "Remove" next to `you+m5@gmail.com`.
2. Sign out. Sign in by code with `you+m5@gmail.com`.

Expected: Step 1 removes the address. Step 2 creates a new, separate account, role "Viewer". The address is free again, so this is normal.

- [ ] Pass
- [ ] Fail, issue:

#### 5.9 The role follows the academic address

Needs: Browser A, signed in as `M1` (Contributor). Address `you+m7@gmail.com`.

1. Add `you+m7@gmail.com` to the account (like 5.1). Look at the role.
2. Click "Make main" next to `you+m7@gmail.com`. Then click "Remove" next to `M1`. Reload the page. Look at the role.
3. Add `M1` again (like 5.1, with the code). Reload. Look at the role.
4. Click "Make main" next to `M1`.

Expected: After step 1, the role is still "Contributor", "Granted from your academic email address." After step 2, the role is "Viewer", "Everyone starts here." After step 3, it is "Contributor" again. The left menu shows the same role as the account page.

- [ ] Pass
- [ ] Fail, issue:

## Part 6. Sessions

#### 6.1 You stay signed in after a restart

Needs: Browser A, signed in as `M1`.

1. Close Chrome completely (all windows). Open it again with the same profile. Open `<hub>/account`.

Expected: You are still signed in.

- [ ] Pass
- [ ] Fail, issue:

#### 6.2 The cookies

Needs: Browser A.

1. Signed out, open `<hub>/login` and ask for a code for `M1`. Open the developer tools, then the cookies of the Hub.
2. Sign in. Look at the cookies again.

Expected: At step 1 there is a cookie `resslab_login`. At step 2 there is a cookie `resslab_session`. Each one has: "HttpOnly" ticked, "Secure" ticked, "SameSite" set to "Lax", path `/`. `resslab_login` ends about 10 minutes after it was made. `resslab_session` ends about 30 days later. Write in the note if `resslab_login` is still there after the sign-in.

- [ ] Pass
- [ ] Fail, issue:

#### 6.3 Sign out in one browser only

Needs: Browser A and Browser B, both signed in as `M2`.

1. In Browser A, sign out.
2. In Browser B, reload the page.

Expected: Browser B is still signed in. A sign-out ends only the session of that browser.

- [ ] Pass
- [ ] Fail, issue:

#### 6.4 Two tabs, sign out in one

Needs: Browser A, signed in as `M2`, two tabs on `<hub>/account`.

1. In tab 1, sign out.
2. In tab 2, do not reload. Click "Add an email address" and try to send a code. Then reload.

Expected: Step 2 does not work (an error, or the sign-in page). After the reload, tab 2 shows that you are signed out. Write what tab 2 shows before the reload.

- [ ] Pass
- [ ] Fail, issue:

#### 6.5 The back button after sign-out

Needs: Browser A, signed in as `M2`, on `<hub>/account`.

1. Sign out. Click the "Back" button of the browser.

Expected: You do not see the account page with its data. You are sent to the sign-in page, or the page is empty. To confirm.

- [ ] Pass
- [ ] Fail, issue:

#### 6.6 An old session cookie no longer works (optional)

Needs: Browser A, signed in as `M2`. Developer tools.

1. In the cookies, copy the value of `resslab_session` into a private note on your computer. Never paste it in an issue.
2. Sign out.
3. In the developer tools, add a cookie `resslab_session` with the old value. Reload `<hub>/account`.
4. Delete the private note.

Expected: You are not signed in. The server ended the session at sign-out.

- [ ] Pass
- [ ] Fail, issue:

#### 6.7 A disabled account

Needs: Browser B, signed in as `M4`. Browser ADMIN.

1. In Browser ADMIN, open `<hub>/admin`. In "Members", find `M4`. Click "Disable" and confirm.
2. In Browser B, reload the page.
3. In Browser B, try to sign in by code with `M4`.
4. In Browser ADMIN, click "Enable" for `M4`. In Browser B, sign in again.

Expected: After step 1, `M4` shows "Disabled". After step 2, Browser B is signed out. Step 3 shows "This account is disabled. Ask an administrator of the lab if you think it is a mistake." Step 4 works.

- [ ] Pass
- [ ] Fail, issue:

## Part 7. Roles

You check what each role can open. Do 7.1 first. The rows with `<n>` and `<m>` need the pull requests of Part 12: come back to them after Part 12.

- `<n>`: the number of the pull request that `M1` opened in Part 12.
- `<m>`: the number of the pull request that `MA` opened in Part 12.

#### 7.1 Prepare one account per role

Needs: Browser ADMIN.

1. On `<hub>/admin`, in "Members", set the role of `M3` to "curator" (column "Set by an administrator").
2. Sign in:
   - Private window: nobody.
   - Browser B: `M2` (Viewer).
   - Browser A: `M1` (Contributor).
   - A new Chrome profile "Hub curator": `M3` (Curator).
   - Browser ADMIN: `MA` (Administrator).

Expected: Each account page shows the expected role. `M3` shows "Curator", "Set by an administrator."

- [ ] Pass
- [ ] Fail, issue:

#### 7.2 Pages

Needs: The five browsers of 7.1.

For each page, open the address in each browser. Write a cross in the table when the result is not the expected one.

- "Open": the page shows.
- "Sign-in": the sign-in page opens, and after the sign-in you come back to the page.
- "Forbidden (role)": the page "Not open to your account" says that the page needs this role.

| Page                                                                                           | Nobody                                                                           | Viewer                    | Contributor                                                                              | Curator                   | Admin      |
| ---------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- | ------------------------- | ---------------------------------------------------------------------------------------- | ------------------------- | ---------- |
| `/`                                                                                            | Open                                                                             | Open                      | Open                                                                                     | Open                      | Open       |
| `/about`                                                                                       | Open                                                                             | Open                      | Open                                                                                     | Open                      | Open       |
| `/braces/database`                                                                             | Open                                                                             | Open                      | Open                                                                                     | Open                      | Open       |
| `/materials/ductile-fracture`                                                                  | Open                                                                             | Open                      | Open                                                                                     | Open                      | Open       |
| Every other tab of the left menu (each database, model and fragility curve)                    | Open                                                                             | Open                      | Open                                                                                     | Open                      | Open       |
| `/login`                                                                                       | Open                                                                             | see 2.18                  | see 2.18                                                                                 | see 2.18                  | see 2.18   |
| `/account`                                                                                     | Sign-in                                                                          | Open                      | Open                                                                                     | Open                      | Open       |
| `/contribute`                                                                                  | Sign-in                                                                          | Forbidden (Contributor)   | Open, as `/contribute/new`                                                               | Open                      | Open       |
| `/contribute/new`                                                                              | Sign-in                                                                          | Forbidden (Contributor)   | Open                                                                                     | Open                      | Open       |
| `/contribute/edit/<n>`                                                                         | Sign-in                                                                          | Forbidden (Contributor)   | Open                                                                                     | Open                      | Open       |
| `/contribute/edit/<m>`                                                                         | Sign-in                                                                          | Forbidden (Contributor)   | Error "could not be loaded" (see the note)                                               | Open                      | Open       |
| `/curation`                                                                                    | Sign-in                                                                          | Forbidden (Curator)       | Forbidden (Curator)                                                                      | Open                      | Open       |
| `/curation/<n>`                                                                                | Sign-in                                                                          | Forbidden (Contributor)   | Open                                                                                     | Open                      | Open       |
| `/curation/<m>`                                                                                | Sign-in                                                                          | Forbidden (Contributor)   | Forbidden, "This submission is not yours. Only its author and the curators can open it." | Open                      | Open       |
| `/curation/verify/<type>` (open it from the "To verify" tab as curator, then copy the address) | Sign-in                                                                          | Forbidden (Curator)       | Forbidden (Curator)                                                                      | Open                      | Open       |
| `/admin`                                                                                       | Sign-in                                                                          | Forbidden (Administrator) | Forbidden (Administrator)                                                                | Forbidden (Administrator) | Open       |
| `/login/verify` (no link)                                                                      | "That code or link is no longer valid. Ask for a new one." and "Back to sign in" | same                      | same                                                                                     | same                      | same       |
| `/forbidden`                                                                                   | "Your account cannot open this page."                                            | same                      | same                                                                                     | same                      | same       |
| `/curation/abc`                                                                                | Empty page                                                                       | Empty page                | Empty page                                                                               | Empty page                | Empty page |

Expected: Every cell matches.

Note on two cells. The editor of someone else's submission shows "The submission could not be loaded. Check your connection and try again." The text is wrong (it is not a connection problem), but the access is refused, which is what counts here. Write it in the note. The app has no "page not found": an unknown address shows the menu and an empty page. Write it in the note too.

- [ ] Pass
- [ ] Fail, issue:

#### 7.3 The left menu

Needs: The five browsers of 7.1.

Expected:

| Menu entry         | Nobody | Viewer | Contributor | Curator | Admin |
| ------------------ | ------ | ------ | ----------- | ------- | ----- |
| "New submission"   | yes    | yes    | yes         | yes     | yes   |
| "Review queue"     | no     | no     | no          | yes     | yes   |
| "Administration"   | no     | no     | no          | no      | yes   |
| "Sign in"          | yes    | no     | no          | no      | no    |
| Your name and role | no     | yes    | yes         | yes     | yes   |

- [ ] Pass
- [ ] Fail, issue:

#### 7.4 The API, in the address bar

Needs: The five browsers of 7.1.

The browser shows the raw answer of the server. Look at the start of the text. In Chrome, tick "Pretty-print" if you see it.

- 200: you see data.
- 401: `{"detail":"Sign in to continue"}`.
- 403: `{"detail":"This action needs the ... role."}`, or for a submission, "Only curators and the person who made this submission can see it."
- 404 on the row `files?path=x`: `{"detail":"This file is not part of the submission."}`. It means the role was accepted.
- 422: a parameter is missing. It means the role was accepted.

| Address                                    | Nobody          | Viewer       | Contributor  | Curator        | Admin          |
| ------------------------------------------ | --------------- | ------------ | ------------ | -------------- | -------------- |
| `<hub>/api/features`                       | 200             | 200          | 200          | 200            | 200            |
| `<hub>/api/auth/me`                        | `{"user":null}` | your account | your account | your account   | your account   |
| `<hub>/api/auth/identities`                | 401             | 200          | 200          | 200            | 200            |
| `<hub>/api/contributions`                  | 401             | 403          | 403          | 200            | 200            |
| `<hub>/api/contributions/<n>`              | 401             | 403          | 200          | 200            | 200            |
| `<hub>/api/contributions/<m>`              | 401             | 403          | 403          | 200            | 200            |
| `<hub>/api/contributions/<m>/validation`   | 401             | 403          | 403          | 200            | 200            |
| `<hub>/api/contributions/<m>/comments`     | 401             | 403          | 403          | 200            | 200            |
| `<hub>/api/contributions/<m>/files?path=x` | 401             | 403          | 403          | 404            | 404            |
| `<hub>/api/contributions/<m>/curves`       | 401             | 403          | 403          | 200            | 200            |
| `<hub>/api/verification`                   | 401             | 403          | 403          | 200            | 200            |
| `<hub>/api/verification/<type>/batch`      | 401             | 403          | 403          | not 401 or 403 | not 401 or 403 |
| `<hub>/api/verification/<type>/validation` | 401             | 403          | 403          | not 401 or 403 | not 401 or 403 |
| `<hub>/api/verification/<type>/files`      | 401             | 403          | 403          | 422            | 422            |
| `<hub>/api/admin/users`                    | 401             | 403          | 403          | 403            | 200            |
| `<hub>/api/admin/invitations`              | 401             | 403          | 403          | 403            | 200            |
| `<hub>/api/admin/access-requests`          | 401             | 403          | 403          | 403            | 200            |
| `<hub>/api/user`                           | 401             | 401          | 401          | 401            | 401            |
| `<hub>/api/dictionary`                     | 200             | 200          | 200          | 200            | 200            |
| `<hub>/api/map/sites`                      | 200             | 200          | 200          | 200            | 200            |
| `<hub>/api/analytics/users`                | 200             | 200          | 200          | 200            | 200            |

For `<type>`, open the "To verify" tab as the curator, open one line, and copy the word after `/curation/verify/` in the address.

Expected: Every cell matches. No browser shows a password pop-up, also not for `/api/user`. If a pop-up opens, click "Cancel" and write the address in the note. The answer of `/api/auth/me` shows only your own account.

The routes that change something (sign in, submit, set a role) are not in this table: the address bar can only read. Part 7.5 tests them through the pages, and package 03 of the review tests each one with each role.

- [ ] Pass
- [ ] Fail, issue:

#### 7.5 What each role can do

Needs: The five browsers of 7.1. Do it during Parts 8 to 15, and tick here.

| Action                              | Viewer | Contributor         | Curator | Admin | Case       |
| ----------------------------------- | ------ | ------------------- | ------- | ----- | ---------- |
| Ask for contributor access          | yes    | no (already has it) | no      | no    | 8.1, 8.7   |
| Submit a batch                      | no     | yes                 | yes     | yes   | 12.2       |
| Edit their own submission           | no     | yes                 | yes     | yes   | 13.1       |
| Edit the submission of someone else | no     | no                  | yes     | yes   | 13.5, 13.6 |
| See the review queue                | no     | no                  | yes     | yes   | 14.1       |
| Mark a batch as verified            | no     | no                  | yes     | yes   | 15.3       |
| Change roles, invite, merge         | no     | no                  | no      | yes   | Part 10    |

- [ ] Pass
- [ ] Fail, issue:

#### 7.6 The page "Not open to your account"

Needs: Browser B (Viewer) and Browser A (Contributor).

1. In Browser B, open `<hub>/contribute/new`.
2. In Browser A, open `<hub>/curation`.
3. In Browser B, open `<hub>/admin`.
4. On each page, click "Back to the databases".

Expected: Step 1 says "This page needs the Contributor role. Ask an administrator of the lab for it." It also says that the contributor role comes from academic addresses, and it shows the form "Ask for contributor access". Step 2 says the page needs the Curator role, and that curators are the people with write access on the data repository on GitHub. No access form. Step 3 says the page needs the Administrator role. Step 4 goes to the home page.

- [ ] Pass
- [ ] Fail, issue:

#### 7.7 A role changes while you are signed in

Needs: The curator browser (`M3`) on `<hub>/curation`. Browser ADMIN.

1. In Browser ADMIN, set the role of `M3` to "Automatic".
2. In the curator browser, reload the page.
3. In Browser ADMIN, set the role of `M3` back to "curator".

Expected: After step 2, `M3` sees "Not open to your account" (Curator). The left menu shows "Viewer" and no "Review queue". After step 3 and a reload, the queue opens again.

- [ ] Pass
- [ ] Fail, issue:

#### 7.8 A role from GitHub (Pierre)

Needs: Pierre. His GitHub account has admin access on the data repository.

1. Pierre signs in with GitHub on stage. He opens "Your account".

Expected: Role "Administrator". The reason is "From your permission on the data repository." or "Listed as an administrator of this deployment.", when his address is in the deployment config.

- [ ] Pass
- [ ] Fail, issue:

## Part 8. Access requests

A viewer asks to become a contributor. An administrator says yes or no.

#### 8.1 A viewer asks for access

Needs: Browser B, signed in as `M4` (Viewer). Browser ADMIN.

1. Open `<hub>/contribute/new`. The page "Not open to your account" opens.
2. In "Ask for contributor access", write: `Test of the access form, please ignore.` Click "Send the request".

Expected: The form is replaced by "Your request was sent on `<date>`. An administrator will look at it." `MA` gets a mail that says `M4` asks for the contributor role, with the message. Pierre gets it too. Write in the note how long the mail takes.

- [ ] Pass
- [ ] Fail, issue:

#### 8.2 Ask twice

Needs: Browser B after 8.1.

1. Reload the page. Look at the form.
2. Open a second tab on `<hub>/account`. If the form shows, send it again.

Expected: Step 1 shows the request as waiting, with no form. If step 2 can send, the answer is "Your request is already waiting for an administrator."

- [ ] Pass
- [ ] Fail, issue:

#### 8.3 The admin approves

Needs: Browser ADMIN. Browser B as `M4`.

1. In Browser ADMIN, open `<hub>/admin`. Look at "Access requests".
2. Click "Approve" for `M4`.
3. In Browser B, reload `<hub>/contribute/new`.

Expected: Step 1 shows `M4`, "asks for the contributor role", and the message. After step 2, the request goes to "Decided requests (1)" with "Approved by `<admin name>`". `M4` gets a mail. After step 3, the editor opens. "Your account" of `M4` shows "Contributor", "Set by an administrator."

- [ ] Pass
- [ ] Fail, issue:

#### 8.4 The admin declines

Needs: Browser B, signed in as `you+plus@gmail.com` (the account of 2.12, Viewer). Browser ADMIN.

1. In Browser B, ask for access (like 8.1).
2. In Browser ADMIN, click "Decline".
3. In Browser B, reload `<hub>/contribute/new`.

Expected: Step 3 shows "Your last request was declined. You can ask again, maybe with a few words on your data." and the form. Write in the note if a mail came (we expect none, to confirm).

- [ ] Pass
- [ ] Fail, issue:

#### 8.5 Ask again after a decline

Needs: Browser B after 8.4.

1. Send the form again.

Expected: The request is waiting again. It shows again in "Access requests" on the admin page. Decline it again to clean up.

- [ ] Pass
- [ ] Fail, issue:

#### 8.6 Two admins answer at the same time

Needs: A waiting request (ask one with `you+plus@gmail.com` again). Browser ADMIN with two tabs on `<hub>/admin`.

1. In tab 1, click "Approve".
2. In tab 2, without a reload, click "Decline".

Expected: Tab 2 shows "Another administrator already answered this request." The request stays approved.

- [ ] Pass
- [ ] Fail, issue:

#### 8.7 A contributor does not see the form

Needs: Browser A as `M1` (Contributor).

1. Open "Your account".

Expected: No form "Ask for contributor access". If the form shows and you send it, the answer is "You already have this access."

- [ ] Pass
- [ ] Fail, issue:

#### 8.8 Odd text in the message

Needs: A viewer account (sign in with a new address `you+odd@gmail.com`). Browser ADMIN.

1. Ask for access with this message: `<b>bold</b> <img src=x onerror=alert(1)> @RESSLab-Team https://example.com`
2. In Browser ADMIN, look at the request. Look at the mail to the admins.
3. Decline it.

Expected: The admin page and the mail show the text as it was typed. No bold text, no image, no pop-up.

- [ ] Pass
- [ ] Fail, issue:

## Part 9. Invitations

An administrator gives a role to an address that has no account yet. The role comes at the first sign-in with that address.

#### 9.1 Invite a new address

Needs: Browser ADMIN. Address `you+inv1@gmail.com`, never used.

1. On `<hub>/admin`, in "Invitations", type `you+inv1@gmail.com`. Choose the role "contributor". Click "Invite".

Expected: "Invitation mailed to `you+inv1@gmail.com`." The list shows it as "Waiting". The mail arrives. It says who invited you and tells you to sign in with this address. Write the text and the sender in the note.

- [ ] Pass
- [ ] Fail, issue:

#### 9.2 Sign in with the invited address

Needs: Browser B, signed out. The invitation of 9.1.

1. Sign in by code with `you+inv1@gmail.com`.
2. In Browser ADMIN, reload the admin page.

Expected: The account is "Contributor", "Set by an administrator." The invitation shows "Used".

- [ ] Pass
- [ ] Fail, issue:

#### 9.3 Invite an address that has an account

Needs: Browser ADMIN.

1. Invite `M2`.
2. Invite `you+m7@gmail.com` (an added address of the `M1` account, from 5.9).

Expected: Both show "This address already has an account. Change its role in the members list."

- [ ] Pass
- [ ] Fail, issue:

#### 9.4 Invite the same address twice

Needs: Browser ADMIN. Address `you+inv2@gmail.com`.

1. Invite `you+inv2@gmail.com` as contributor.
2. Invite it again.

Expected: Step 2 shows "This address already has an invitation waiting."

- [ ] Pass
- [ ] Fail, issue:

#### 9.5 Revoke an invitation

Needs: The invitation of 9.4. Browser B.

1. In Browser ADMIN, click "Revoke" next to `you+inv2@gmail.com`.
2. In Browser B, sign in by code with `you+inv2@gmail.com`.

Expected: The invitation shows "Revoked". The new account is "Viewer".

- [ ] Pass
- [ ] Fail, issue:

#### 9.6 Revoke twice

Needs: Browser ADMIN, two tabs on `<hub>/admin`. A new invitation for `you+inv3@gmail.com`.

1. In tab 1, revoke it.
2. In tab 2, without a reload, revoke it.

Expected: Tab 2 shows "It is gone. Reload the page."

- [ ] Pass
- [ ] Fail, issue:

#### 9.7 An invitation used by a GitHub sign-in

Needs: Browser ADMIN. Browser B, signed out. `GH` is not linked to any Hub account: if it is, sign in with GitHub and remove it first (Part 3.5). Address `you+gh3@gmail.com`, added to `GH` and verified on GitHub.

1. In Browser ADMIN, invite `you+gh3@gmail.com` as "curator".
2. On GitHub, make `you+gh3@gmail.com` the primary address.
3. In Browser B, click "Continue with GitHub".

Expected: A new account with `you+gh3@gmail.com`, role "Curator", "Set by an administrator." The invitation shows "Used". Put the GitHub primary address back after.

- [ ] Pass
- [ ] Fail, issue:

#### 9.8 An invitation used when you add an address

Needs: Browser ADMIN. Browser B, signed in as `M2` (Viewer). Address `you+inv4@gmail.com`.

1. In Browser ADMIN, invite `you+inv4@gmail.com` as contributor.
2. In Browser B, add `you+inv4@gmail.com` to the `M2` account (Part 5.1). Reload.

Expected: `M2` is now "Contributor", "Set by an administrator." The invitation shows "Used". Then, in Browser ADMIN, set `M2` back to "Automatic", and remove the address from `M2`.

- [ ] Pass
- [ ] Fail, issue:

#### 9.9 Capitals in the invited address

Needs: Browser ADMIN. Address `you+inv5@gmail.com`.

1. Invite `You+INV5@Gmail.com` as contributor.
2. Sign in by code with `you+inv5@gmail.com` (lower case).

Expected: The list shows the address in lower case. The account is "Contributor".

- [ ] Pass
- [ ] Fail, issue:

## Part 10. The admin page

#### 10.1 The page

Needs: Browser ADMIN.

1. Open `<hub>/admin`.

Expected: The title is "Who can do what". You see "Access requests", "Members", "Invitations" and "Merge two accounts". The members list has every account from your tests, with the role, where the role comes from ("Default", "Academic address", "Set here", "GitHub", "Deployment config") and the last sign-in. An account with several addresses shows "Also ..." with the other addresses. Your own row shows "You".

- [ ] Pass
- [ ] Fail, issue:

#### 10.2 Give a role and take it back

Needs: Browser ADMIN. Browser B as `M2` (Viewer).

1. Set the role of `M2` to "curator".
2. In Browser B, reload "Your account".
3. Set the role of `M2` back to "Automatic". Reload Browser B.

Expected: After step 2, `M2` is "Curator", "Set by an administrator." After step 3, `M2` is "Viewer", "Everyone starts here."

- [ ] Pass
- [ ] Fail, issue:

#### 10.3 Lower an academic account

Needs: Browser ADMIN. Browser A as `M1` (Contributor, academic).

1. Set the role of `M1` to "viewer". Reload Browser A.
2. Set it back to "Automatic". Reload Browser A.

Expected: After step 1, `M1` is "Viewer", "Set by an administrator.": the choice of the admin wins over the academic address. After step 2, `M1` is "Contributor" again.

- [ ] Pass
- [ ] Fail, issue:

#### 10.4 Change your own account

Needs: Browser ADMIN.

1. In your own row ("You"), try to change the role, or click "Disable".

Expected: The controls are off, or you get "You cannot change your own account. Ask another administrator."

- [ ] Pass
- [ ] Fail, issue:

#### 10.5 An admin from the config or from GitHub

Needs: Browser ADMIN. Pierre's row (he signed in once on stage, see 7.8).

1. Find Pierre's row. Try to change its role, or click "Disable".

Expected: The row shows "In the deployment config" or "Admin on GitHub". The controls are off, or you get "This administrator comes from GitHub or from the deployment config. Change it there."

- [ ] Pass
- [ ] Fail, issue:

#### 10.6 Merge two accounts of one person

This is the fix for case 3.8: one person, two accounts.

Needs: Browser ADMIN. The GitHub account of 9.7 (`you+gh3@gmail.com`, Curator), signed in in Browser B. `M2`, with no GitHub.

1. In "Merge two accounts", pick `M2` as "Account to keep". Pick the `you+gh3@gmail.com` account as "Account to merge into it". Click "Merge", then "Click again to merge".
2. In Browser B, reload.
3. In Browser B, click "Continue with GitHub". Open "Your account".
4. Sign out. Sign in by code with `you+gh3@gmail.com`.

Expected: Step 1 shows "`you+gh3@gmail.com` is now part of `M2`." (or the names of the accounts). The merged account leaves the members list. After step 2, Browser B is signed out. Step 3 opens the `M2` account, with GitHub in "Ways to sign in" and both addresses. The role is "Curator" (the stronger role of the two moves over). Step 4 opens the `M2` account too. After the case, set `M2` to "Automatic" and remove GitHub from it.

- [ ] Pass
- [ ] Fail, issue:

#### 10.7 Merge refused

Needs: Browser ADMIN.

1. Pick the same account twice, and click "Merge".
2. Disable `you+plus@gmail.com`. Try to merge it into `M2`. Enable it again after.
3. Try to merge your own account (`MA`) into another one, or another one into yours.
4. Second person, optional: two accounts that each have a different GitHub. Try to merge them.

Expected: Step 1: "Pick two different accounts.", or the page does not let you pick it. Step 2: "One of the two accounts is disabled. Enable it first." Step 3: write what happens (to confirm). Step 4: "The two accounts use different GitHub accounts. Unlink one first."

- [ ] Pass
- [ ] Fail, issue:

#### 10.8 An account that is gone

Needs: Browser ADMIN, two tabs on `<hub>/admin`. A spare account (sign in with `you+gone@gmail.com`).

1. In tab 1, merge the spare account into `you+plus@gmail.com`.
2. In tab 2, without a reload, change the role of the spare account.

Expected: Tab 2 shows "It is gone. Reload the page."

- [ ] Pass
- [ ] Fail, issue:

## Part 11. The editor

You prepare batches in the editor. Nothing in this part opens a pull request: you never click "Submit for review" here. The automatic check (the Hub reads your batch and lists its problems) runs a few seconds after each change.

Use Browser A, signed in as `M1` (Contributor), on `<hub>/contribute/new`.

#### 11.1 The editor page

1. Open `<hub>/contribute/new`.
2. Open the list of databases.
3. Pick "Braces". Open the tabs "Guide" and "Data dictionary" of the contribution guide.

Expected: The page is "New submission". The list has the 9 databases of Part 0.5. The guide shows the text for braces (how to build the id, which files to give). The dictionary shows a table of columns, with a filter box. The status line says "Add at least one experiment with an identifier to enable the automatic check."

- [ ] Pass
- [ ] Fail, issue:

#### 11.2 The downloads

1. On "Braces", download "Template CSV", "Dictionary CSV" and "Starter kit".
2. Open each file.

Expected: The template CSV opens in a spreadsheet, with one header row. The dictionary CSV lists the same columns. The starter kit is a zip with the template, one example file per response type, and a README. No file is empty.

- [ ] Pass
- [ ] Fail, issue:

#### 11.3 A good batch, for each database

For each database, do these steps:

1. Pick the database.
2. Drop its folder from `sample-data` on the drop zone (or click "Choose a folder").
3. Wait for the check.
4. Click "Show details".

Expected: The page says "15 experiment(s) added, 0 updated." and lists the attached files. The check says "Checks passed with 3 warning(s)". The 3 warnings are on the last 3 experiments. No experiment shows "Test data to attach".

| Database          | 15 added | Files attached | 3 warnings, no error | Pass |
| ----------------- | -------- | -------------- | -------------------- | ---- |
| Connections       |          |                |                      |      |
| Columns           |          |                |                      |      |
| Braces            |          |                |                      |      |
| HSS columns       |          |                |                      |      |
| Cyclic coupons    |          |                |                      |      |
| Residual stresses |          |                |                      |      |
| EBF links         |          |                |                      |      |
| Tensile coupons   |          |                |                      |      |
| Ductile fracture  |          |                |                      |      |

- [ ] Pass
- [ ] Fail, issue:

#### 11.4 A bad batch

1. Pick "Braces". Drop `braces.invalid.csv` alone.
2. Click "Show details". Click one experiment.
3. Click "Go to the first one".

Expected: The check says "`<count>` error(s) block this contribution." Each experiment shows its own problem, on the field that is wrong. The "Submit for review" button is off. Do the same with 2 other databases of your choice.

- [ ] Pass
- [ ] Fail, issue:

#### 11.5 A zip of the folder

1. Make a zip of `sample-data/braces/` with your computer.
2. Pick "Braces". Drop the zip.

Expected: Same result as 11.3.

- [ ] Pass
- [ ] Fail, issue:

#### 11.6 Loose files, without their folders

1. Pick "Columns". Click "Choose files".
2. Select `columns.csv` and, from 2 different subfolders, the files of one experiment (they have the same name).

Expected: The experiments load. For the files with the same name and no folder, the page says that their type is not clear, and lets you pick the type of each file. After you pick the types, the files are attached.

- [ ] Pass
- [ ] Fail, issue:

#### 11.7 Files that do not fit

1. Pick "Braces". Drop the folder of 11.3.
2. Drop these files on the drop zone:
   - a copy of one curve file, renamed `DEMO-NOBODY.csv`;
   - a photo (`.jpg`);
   - `columns.csv` from the columns folder.

Expected: The photo is "Not CSV, skipped". `DEMO-NOBODY.csv` "match no experiment": you can pick an experiment or ignore it. `columns.csv` "look like another database's experiments CSV". "Ignore all remaining" removes the list.

- [ ] Pass
- [ ] Fail, issue:

#### 11.8 Add an experiment by hand

1. Pick "Braces", with no batch. Click "Add an experiment manually".
2. Type an id `DEMO-HAND-1`. Fill 2 or 3 fields. Leave the others empty.
3. On the card, attach one curve file from the braces folder.
4. Click "Duplicate" on the card. Then "Remove" on the copy.

Expected: The card shows "`<count>` still to fill in" for the required fields. The check runs when you stop typing, and shows errors for the empty required fields. The file is attached to the card. "Duplicate" makes a second card, "Remove" deletes it.

- [ ] Pass
- [ ] Fail, issue:

#### 11.9 Dismiss a warning

1. Load the good braces batch (11.3). Open one of the last 3 experiments.
2. Click "Dismiss this warning" on its warning.
3. Change the value of that field, then put it back.
4. Dismiss it again. Then click "Restore".

Expected: After step 2, the check says that warnings were dismissed, and the count goes down. After step 3, the warning comes back. "Restore" brings it back too.

- [ ] Pass
- [ ] Fail, issue:

#### 11.10 Change the database with work in it

1. Load the good braces batch. Pick "Columns".
2. Pick "Columns" again.

Expected: Step 1 asks first: "Click again to replace 15 experiment(s)". Step 2 empties the editor and switches to columns.

- [ ] Pass
- [ ] Fail, issue:

#### 11.11 An id that already exists in the database

1. Open `<hub>/braces/database` in another tab. Copy the id of one real experiment.
2. In the editor, add an experiment by hand with this id. Fill the required fields.

Expected: The check shows an error on the id: it already exists in the database. Do not submit. If the check passes, it is a fail: do not submit, write it.

- [ ] Pass
- [ ] Fail, issue:

#### 11.12 Odd ids

1. Add an experiment by hand with the id `DEMO-A/B`.
2. Add a second one with the id `DEMO-HAND-1`, twice (two cards with the same id).

Expected: Step 1 gives an error: the id cannot be used as a file name. Step 2 gives an error: the id is twice in the batch.

- [ ] Pass
- [ ] Fail, issue:

#### 11.13 Odd text in the cells

1. Load the good braces batch. Open the first experiment. In a free text field (a comment or a reference), type each value below, one at a time, and wait for the check:
   - `=1+1`
   - `<b>bold</b><img src=x onerror=alert(1)>`
   - `@RESSLab-Team please look`
   - `Zürich, École, ñ, 東京`
   - a text of about 2000 characters (copy a long paragraph several times)

Expected: The text shows as you typed it. No bold, no image, no pop-up. The check works. Write in the note what the check says about the long text.

- [ ] Pass
- [ ] Fail, issue:

#### 11.14 A batch that is too big

Needs: `big.zip` from Pierre (about 60 MB).

1. Pick the database Pierre says. Drop `big.zip`.

Expected: The editor or the check says that the batch is too large ("The contribution is too large to validate in one request." or another clear text). Write the exact text. A raw HTML page or a frozen browser is a fail.

- [ ] Pass
- [ ] Fail, issue:

#### 11.15 A reload loses the work

1. Load the good braces batch. Dismiss one warning.
2. Reload the page.

Expected today: The editor is empty again, and the browser does not warn before the reload. This is a known gap. Tick "Pass" if it behaves like this, and write in the note if anything was kept.

- [ ] Pass
- [ ] Fail, issue:

#### 11.16 The check on a phone

1. On the phone, sign in as `M1`. Open `<hub>/contribute/new`. Pick "Braces".
2. Use "Choose files" to pick `braces.csv` (send it to the phone first).

Expected: The page is usable. The experiments load and the check runs. Write what is hard to use.

- [ ] Pass
- [ ] Fail, issue:

## Part 12. Submit

Each submission opens a real pull request on the public repository `RESSLab-Team/resslab-hub-data`. Wait for Pierre's go (Part 0.2). Write the number of each pull request in the cleanup list of Part 19 at once.

The sample data uses only `DEMO-` ids. Do not change them.

#### 12.1 The submit dialog

Needs: Browser A as `M1`. `GH` free (no Hub account has it): link it to `M1` with "Link GitHub" on the account page.

1. Pick "Braces". Drop the good braces folder. Dismiss one of the 3 warnings.
2. Click "Submit for review".
3. Read the dialog. Click "Cancel".

Expected: The dialog says "You are submitting 15 experiment(s) and `<count>` test-data file(s)." and "1 dismissed warning(s) will be listed for the curator." "Submitting as" shows the name of `M1`, its main address and `@<your GitHub login>`. The note says that the name and address appear in a public pull request on GitHub. "Cancel" closes the dialog and keeps the batch.

- [ ] Pass
- [ ] Fail, issue:

#### 12.2 Submit

Needs: The batch of 12.1.

1. Click "Submit for review", then "Submit". Click only once.
2. Wait. Note the time it takes.

Expected: The page shows "Sending ... files to GitHub", then "Submitted. Review request #`<n>` is open." There are buttons "View review request" and "Start a new contribution". Write `<n>` here: `____`. Write the time in the note. Only one pull request is opened.

- [ ] Pass
- [ ] Fail, issue:

#### 12.3 The pull request on GitHub

Needs: Pull request `<n>`. Open it with "View review request".

Expected:

| What                        | Expected                                                                                                                                                                     | OK  |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --- |
| Title                       | `data(<database>): add 15 experiments (DEMO-...…)`                                                                                                                           |     |
| Opened by                   | the Hub's GitHub App (a bot), not a person                                                                                                                                   |     |
| Branch                      | starts with `contrib/`, then the database, then the first id in lower case, then 8 random characters                                                                         |     |
| Body                        | "Automated submission from the RESSLab-Hub contribution editor.", then Database, Experiments (15), Time-series files, Contributor (name and address), GitHub (`@your-login`) |     |
| Dismissed warning           | listed in the body, as code (grey box)                                                                                                                                       |     |
| "To update this submission" | at the end of the body, with a link to the CSV on the branch                                                                                                                 |     |
| Files                       | the main CSV of the database (15 rows added at the end), and one curve file per experiment and response type                                                                 |     |
| New rows                    | the column `data_curation_status` is `unverified` on each new row                                                                                                            |     |
| Commit                      | author: the name and address of `M1`. Committer: the bot                                                                                                                     |     |
| Commit message              | ends with lines like `Submitted-by: ...`, `GitHub: ...`, `Dismissed-Warning: ...`                                                                                            |     |
| Checks                      | the data validation workflow runs and passes                                                                                                                                 |     |
| Reviewers                   | only the person Pierre set, not every lab admin                                                                                                                              |     |
| You                         | GitHub sends you a notification (you are mentioned)                                                                                                                          |     |

- [ ] Pass
- [ ] Fail, issue:

#### 12.4 A second submission, by the admin

Needs: Browser ADMIN as `MA`.

1. Pick "Columns". Drop the good columns folder.
2. Open the first experiment. In a free text field, type `=1+1`. Dismiss one warning.
3. Submit.

Expected: "Submitted. Review request #`<m>` is open." Write `<m>` here: `____`. On GitHub, the cell shows `'=1+1` (with a quote in front, so a spreadsheet does not run it). The body has no `GitHub:` line (no GitHub on `MA`), and the dialog said so before you submitted ("Link GitHub on your account page...").

- [ ] Pass
- [ ] Fail, issue:

Now go back to Part 7 and fill the rows with `<n>` and `<m>`.

#### 12.5 "Start a new contribution"

Needs: Browser A after 12.2.

1. Click "Start a new contribution".

Expected: The editor is empty. The database choice is back.

- [ ] Pass
- [ ] Fail, issue:

#### 12.6 "Edit" in the dialog

Needs: Browser A as `M1`.

1. Load the good braces batch. Click "Submit for review". Click "Edit" next to "Submitting as".
2. Click "Back" in the browser.

Expected: Step 1 opens "Your account". Write in the note if the batch is still in the editor after step 2. If it is gone, it is the gap of 11.15: note it, it is not a fail.

- [ ] Pass
- [ ] Fail, issue:

#### 12.7 A contributor with no address

Needs: Browser B, signed in with `OR` only (a new ORCID account with no address, see 4.2). Browser ADMIN.

1. In Browser ADMIN, set the role of the ORCID account to "contributor".
2. In Browser B, open the editor. Load the good braces batch. Click "Submit for review".
3. In Browser ADMIN, set the role back to "Automatic".

Expected: The dialog says "This account has no confirmed email address. Sign in with your email address to submit." The "Submit" button is off. No pull request is opened.

- [ ] Pass
- [ ] Fail, issue:

#### 12.8 The same batch twice

Needs: Browser A as `M1`. Pull request `<n>` is open. Pierre's go for one more pull request.

1. Drop the good braces folder again. Wait for the check.
2. Submit.

Expected today: The check passes and a second pull request opens with the same ids. The Hub checks the ids of the database and of the data repository, not the ids of open submissions. This is a known gap: tick "Pass" if it behaves like this. Write the new number in Part 19.

- [ ] Pass
- [ ] Fail, issue:

## Part 13. Edit a submission

#### 13.1 Edit your own submission

Needs: Browser A as `M1`. Pull request `<n>`.

1. Open `<hub>/contribute/edit/<n>`.
2. Change one value of the first experiment. Click "Submit the update", then "Update".

Expected: Step 1 shows "You are editing submission #`<n>`." with the 15 experiments and their files. After step 2: "Updated. Review request #`<n>` now has your changes." On GitHub, the same pull request has a second commit, on the same branch. No new pull request.

- [ ] Pass
- [ ] Fail, issue:

#### 13.2 Edit from the review page

Needs: Browser A as `M1`.

1. Open `<hub>/curation/<n>`. Click "Edit on the Hub".

Expected: The editor of 13.1 opens.

- [ ] Pass
- [ ] Fail, issue:

#### 13.3 Two edits at the same time

Needs: Browser A as `M1`, two tabs on `<hub>/contribute/edit/<n>`.

1. In tab 1, change a value and submit the update.
2. In tab 2, without a reload, change another value and submit the update.
3. Reload tab 2.

Expected: Step 2 shows "This submission changed on GitHub after you opened it. Reload the page to get the latest version, then make your changes again." Nothing is written. After step 3, tab 2 shows the change of tab 1.

- [ ] Pass
- [ ] Fail, issue:

#### 13.4 Edit on GitHub, then on the Hub

Needs: Browser A as `M1`, on `<hub>/contribute/edit/<n>`. Your GitHub account can edit the branch only if you have write access: if not, ask Pierre to do step 1.

1. On GitHub, edit the CSV of the branch (the link "Edit the CSV on GitHub", or the link in the body). Change one cell and commit.
2. In the Hub tab, without a reload, change a value and submit the update.

Expected: The same message as in 13.3.

- [ ] Pass
- [ ] Fail, issue:

#### 13.5 A contributor cannot edit the submission of someone else

Needs: Browser A as `M1`. Pull request `<m>` (by `MA`).

1. Open `<hub>/contribute/edit/<m>`.

Expected: The editor does not open. The page shows an error (see the note of 7.2). Nothing is written.

- [ ] Pass
- [ ] Fail, issue:

#### 13.6 A curator edits the submission of someone else

Needs: The curator browser (`M3`, Curator). Pull request `<n>` (by `M1`).

1. Open `<hub>/contribute/edit/<n>`. Change one value. Submit the update.

Expected: The update works. On GitHub, the new commit has `M3` as author. The pull request still says that `M1` made the submission. Write what the commit message says.

- [ ] Pass
- [ ] Fail, issue:

#### 13.7 A closed submission

Needs: Pull request `<m>`. Ask Pierre to close it on GitHub, or close it yourself if you can.

1. In Browser ADMIN, open `<hub>/contribute/edit/<m>`.
2. Open `<hub>/curation/<m>`.

Expected: Step 1 shows "This submission does not exist, or it is no longer open." Step 2 shows "This submission does not exist or is no longer open."

- [ ] Pass
- [ ] Fail, issue:

#### 13.8 A number that does not exist

1. In Browser ADMIN, open `<hub>/contribute/edit/999999` and `<hub>/curation/999999`.

Expected: The same messages as in 13.7. No error page with code.

- [ ] Pass
- [ ] Fail, issue:

## Part 14. Curation

The review queue lists the open pull requests of the data repository. Approve, reject and merge happen on GitHub, not in the Hub. Never merge or approve on `RESSLab-Team/resslab-hub-data`.

Use the curator browser (`M3`).

#### 14.1 The queue

1. Open `<hub>/curation`.
2. Click "Refresh".

Expected: Two tabs, "To accept" and "To verify". "To accept" lists the open pull requests, with PR number, database, title, contributor, number of experiments and the date. Your `<n>` is in the list. The contributor column shows names, not mail addresses. A pull request that was not made with the Hub shows "Opened on GitHub" or "Unrecognised". A draft shows "Draft", one from a fork shows "Fork".

- [ ] Pass
- [ ] Fail, issue:

#### 14.2 The review page

1. In the queue, click "Review" on `<n>`.

Expected: The page "Submission #`<n>`" shows "Submitted by `<name of M1>`", the list of experiments, "Specimen metadata", "Data preview" with the curves, "Quality flags" with the result of the checks and the dismissed warning ("Dismissed by the contributor"), and "Discussion". The buttons "Approve", "Reject" and "Request changes" are off. Hover one: it says that decisions happen on GitHub. The mail address of `M1` is not on the page.

- [ ] Pass
- [ ] Fail, issue:

#### 14.3 Compare with the database

1. On the review page, pick one experiment. Look at "Comparison with similar experiments".
2. Add a specimen from the cohort to the curves.

Expected: The chart shows the new experiment in red and the similar ones in light lines. The added specimen shows on the curve chart.

- [ ] Pass
- [ ] Fail, issue:

#### 14.4 The discussion

1. On GitHub, on pull request `<n>`, write a comment: `Test comment **bold** <img src=x onerror=alert(1)> @RESSLab-Team`.
2. On the review page, click "Refresh the discussion".

Expected: The comment shows with its author and date. "bold" is bold. No image box with a broken link that runs code, no pop-up. If a pop-up shows, stop and write to Pierre directly (Part 0.2). Delete the comment on GitHub after.

- [ ] Pass
- [ ] Fail, issue:

#### 14.5 The contributor's own review page

Needs: Browser A as `M1`.

1. Open `<hub>/curation/<n>`.

Expected: The page opens, like for the curator. `M1` has no "Review queue" in the menu.

- [ ] Pass
- [ ] Fail, issue:

#### 14.6 Old texts

1. Read the description of the queue and of the "Discussion" box.

Expected: They say that decisions happen on GitHub "until curator roles are in place". Curator roles exist now, so this text is old. Write it in the note. It is not a fail.

- [ ] Pass
- [ ] Fail, issue:

## Part 15. Verification, on dev

A merged submission goes live as "unverified". A curator checks it against the publication, then marks it as verified. This opens a second pull request that only changes the status column.

This part runs on `<dev>`, not on stage. Dev writes to the test fork `EPFL-ENAC/resslab-hub-data-test`, where a pull request can be merged. Never merge on `RESSLab-Team/resslab-hub-data`.

Do this part with Pierre. You need an account on `<dev>` with the curator role, and write access on the test fork (or Pierre merges for you).

#### 15.1 Submit on dev

1. On `<dev>`, sign in as a contributor. Pick "Braces". Drop the good braces folder. Submit.
2. Open the pull request.

Expected: The pull request opens on `EPFL-ENAC/resslab-hub-data-test`, not on `RESSLab-Team/resslab-hub-data`. If it opens on the real repository, stop and tell Pierre at once. Write the number here: `____`.

- [ ] Pass
- [ ] Fail, issue:

#### 15.2 Merge and upload

1. On GitHub, merge the pull request of 15.1 with "Squash and merge".
2. Open the "Actions" tab of the fork. Wait for the upload workflow to finish.
3. Ask Pierre to restart the dev backend (the Hub keeps its answers for up to one hour).
4. On `<dev>/braces/database`, search for `DEMO-`.

Expected: The 15 experiments are on the dashboard. Each one has the tag "Unverified". The detail of one experiment says "This experiment has not yet been reviewed by our team. Use it with care." The filter "Verified only" hides them.

- [ ] Pass
- [ ] Fail, issue:

#### 15.3 Mark as verified

Needs: The curator account on `<dev>`.

1. Open `<dev>/curation`, tab "To verify".
2. Find the braces line with the reference of the sample data. Open it.
3. Click "Mark all 15 as verified".
4. Open the new pull request.

Expected: Step 1 lists the unverified experiments by database and reference. Step 3 opens a pull request on the fork. On GitHub, the pull request changes only the column `data_curation_status` of the 15 rows. The "To verify" page now says that they are in a verification pull request.

- [ ] Pass
- [ ] Fail, issue:

#### 15.4 After the merge

1. Merge the pull request of 15.3 with "Squash and merge". Wait for the upload. Ask Pierre to restart the backend.
2. Open the dashboard and the "To verify" tab again.

Expected: The tag "Unverified" is gone from the 15 experiments. The "To verify" tab no longer lists them. Before the upload, the tab still lists them: "The list comes from the database, so a merged verification stays here until the next upload." That is normal.

- [ ] Pass
- [ ] Fail, issue:

#### 15.5 Mark one experiment from the dashboard

Needs: One more unverified experiment on `<dev>` (submit, merge and upload 1 experiment, as in 15.1 and 15.2).

1. As the curator, open the experiment on the dashboard.
2. Click "Mark as verified" in the notice.
3. Open it again as a contributor, in Browser B.

Expected: Step 2 shows "Verification pending: PR #`<number>`". The contributor sees the notice, without the button.

- [ ] Pass
- [ ] Fail, issue:

#### 15.6 A curator verifies their own submission

1. As the curator, submit 1 experiment on `<dev>`. Merge and upload it.
2. As the same curator, mark it as verified.

Expected: To confirm. Write if the Hub lets the curator verify their own data. Pierre decides if it is a problem.

- [ ] Pass
- [ ] Fail, issue:

## Part 16. Contributions switched off

Prod ran with contributions off until now. When the flag is off, the Hub must look like a plain database: no sign-in, no editor, no queue.

Pierre runs this part on `<dev>`. He sets `CONTRIBUTIONS_ENABLED=false` on the dev backend and restarts it. Ask him before you start, and tell him when you are done, so he switches it back on.

#### 16.1 What the Hub says

1. Open `<dev>/api/features`.

Expected: The answer says that contributions are off (`"contributions": false`).

- [ ] Pass
- [ ] Fail, issue:

#### 16.2 The pages

1. In a private window, open the home page. Look at the menu.
2. Open each page: `/login`, `/login/verify`, `/account`, `/contribute/new`, `/contribute/edit/1`, `/curation`, `/curation/1`, `/curation/verify/braces`, `/admin`.

Expected: No "Sign in" in the menu. Each page of step 2 goes to the home page. The database pages work as usual.

- [ ] Pass
- [ ] Fail, issue:

#### 16.3 Someone who was signed in

1. Before Pierre switches the flag off, sign in on `<dev>` in Browser A.
2. After the switch, reload. Open `/account`.

Expected: The menu shows no account. `/account` goes to the home page. No error page.

- [ ] Pass
- [ ] Fail, issue:

#### 16.4 The API

1. Open these addresses in the browser:
   - `<dev>/api/auth/me`
   - `<dev>/api/auth/github/start`
   - `<dev>/api/contributions`
   - `<dev>/api/verification`
   - `<dev>/api/admin/users`

Expected: `/api/auth/me` answers `{"user":null}` in a private window. In a browser that was signed in before the switch, write what it answers. The others answer 404 with "Contributions are not enabled on this deployment." No answer shows data.

- [ ] Pass
- [ ] Fail, issue:

#### 16.5 The unverified notice

1. Open an unverified experiment (from Part 15) on the dashboard.

Expected: The notice "This experiment has not yet been reviewed by our team." is still there. There is no "Mark as verified" button.

- [ ] Pass
- [ ] Fail, issue:

#### 16.6 When the Hub does not answer about the flag

Needs: Chrome DevTools.

1. Open DevTools, tab "Network". Right-click any request and pick "Block request URL". Change the blocked address to `*/api/features`.
2. Reload the home page. Open `/contribute/new`.
3. Remove the block.

Expected: To confirm. Write what the menu shows and where `/contribute/new` goes. If the Hub shows "Sign in" or the editor while the flag is off, write it: the page would offer a feature that the backend refuses.

- [ ] Pass
- [ ] Fail, issue:

#### 16.7 Switched on again

1. When Pierre switched the flag back on, reload `<dev>`. Sign in.

Expected: Everything works as before. A session from before the switch still works.

- [ ] Pass
- [ ] Fail, issue:

## Part 17. Across the app

Do these cases on `<hub>`, with `M1` (Contributor) and the admin account.

#### 17.1 French

1. Switch the language to French.
2. Go through: the sign-in page, a sign-in by mail (the mail too), "Your account", the editor with the bad braces batch, the submit dialog (then "Cancel"), the review queue, a review page, the admin page, the Forbidden page.

Expected: Every text is in French, with its accents (é, è, à, ç). No English text left, no key name like `contribute.dialog.title`. Write each English text or wrong text with the page where you saw it.

- [ ] Pass
- [ ] Fail, issue:

#### 17.2 Phone width

1. On a phone (or Chrome DevTools, device "iPhone SE"), open each page of 17.1.

Expected: Each page fits the width. No text is cut. Every button can be reached and clicked. The review queue table scrolls, or shows the rows in another way. Write the pages that are hard to use.

- [ ] Pass
- [ ] Fail, issue:

#### 17.3 Dark theme

1. Switch the Hub to the dark theme (the button in the menu).
2. Open each page of 17.1.

Expected: Every text can be read. No white box with white text. The charts of the review page can be read.

- [ ] Pass
- [ ] Fail, issue:

#### 17.4 Firefox and Safari

Do these steps in Firefox, then in Safari (on a Mac or an iPhone).

1. Sign in with a mail code. Sign out. Sign in with GitHub.
2. In the editor, pick "Braces" and drop the good braces folder. Then try "Choose a folder".
3. Open the submit dialog. Click "Cancel".
4. Open the review page of `<n>`.

Expected: Everything works as in Chrome. Write the steps that do not.

| Step                              | Firefox | Safari |
| --------------------------------- | ------- | ------ |
| 1. Sign in (mail, GitHub)         |         |        |
| 2. Drop a folder, choose a folder |         |        |
| 3. Submit dialog                  |         |        |
| 4. Review page                    |         |        |

- [ ] Pass
- [ ] Fail, issue:

#### 17.5 Slow network

1. In Chrome DevTools, tab "Network", pick "Slow 4G".
2. Sign in with a mail code. Click "Send me a code" twice fast.
3. In the editor, drop the good braces folder. Wait for the check.
4. Open the review page of `<n>`.

Expected: Each slow step shows that it is working (a spinner or a text). A double click sends one mail, not two. Nothing breaks. Write the steps that look frozen.

- [ ] Pass
- [ ] Fail, issue:

#### 17.6 The session ends while you edit

Needs: Browser A as `M1`, and a second tab.

1. In tab 1, load the good braces batch. Do not submit.
2. In tab 2, sign out.
3. In tab 1, click "Submit for review", then "Submit".

Expected: The Hub says that you must sign in again. No pull request opens. Write if the batch is still there after you sign in again (probably not, see 11.15).

- [ ] Pass
- [ ] Fail, issue:

#### 17.7 The browser buttons

1. Sign in with a mail code from `/contribute/new` (you are sent to sign in first).
2. After you land on the editor, click "Back" in the browser twice.

Expected: Step 1 lands on the editor. Step 2 does not show the code form again with an error, and does not sign you out.

- [ ] Pass
- [ ] Fail, issue:

#### 17.8 The keyboard only

1. On the sign-in page, use only the keyboard (Tab, Enter) to send a code and type it.
2. In the editor, open the submit dialog with the keyboard. Close it with Escape.

Expected: You can do everything with the keyboard. You can always see which element has the focus.

- [ ] Pass
- [ ] Fail, issue:

## Part 18. Checks from the browser

These checks look for data that should not be visible. Open the addresses in the browser, nothing else. Do not change a request, do not use a tool to send many requests.

#### 18.1 The API documentation

1. Open `<hub>/api/docs`.

Expected: To confirm. Write if the page opens and if it lists the sign-in, admin and contribution routes. Pierre decides if it must stay public.

- [ ] Pass
- [ ] Fail, issue:

#### 18.2 No mail address on the public pages

1. In a private window (not signed in), open the home page, each database page, the detail of 3 experiments, the map and the "About" page.
2. On each page, search for `@` (Ctrl+F). Then open the page source (Ctrl+U) and search for `@` again.

Expected: No mail address of a person. The addresses of the lab or of EPFL on the "About" page are fine.

- [ ] Pass
- [ ] Fail, issue:

#### 18.3 No mail address on the review page

1. As `M3` (Curator), open the review page of `<n>`. Search for the address of `M1` in the page and in the "Discussion".
2. Open DevTools, tab "Network". Reload. Search for the address of `M1` in the answers (the search box of the "Network" tab, Ctrl+F).

Expected: The address of `M1` is in no page and in no answer. The pull request on GitHub has it (that is known, the contributor agreed to it in the dialog).

- [ ] Pass
- [ ] Fail, issue:

#### 18.4 Answers that must not be kept

1. Signed in as `M1`, open DevTools, tab "Network". Open "Your account".
2. Click the request `auth/me`. Look at the "Response headers".

Expected: `Cache-Control` says `private` or `no-store`. Write the value.

- [ ] Pass
- [ ] Fail, issue:

#### 18.5 After sign-out

1. Signed in as `M1`, open "Your account".
2. Sign out. Click "Back" in the browser.

Expected: The account page does not show your addresses again. If it shows them, reload: they must go away.

- [ ] Pass
- [ ] Fail, issue:

#### 18.6 Cookies and analytics

1. In a private window, open `<hub>`. Do not answer the cookie banner.
2. In DevTools, tab "Network", search for `google`.
3. Click "OK" on the banner. Reload. Search again.

Expected: Before "OK", no request to Google Analytics. After "OK", the requests start.

- [ ] Pass
- [ ] Fail, issue:

## Part 19. Cleanup

Do this at the end of each day, not only at the end of the test.

#### 19.1 The pull requests

Close every pull request that you opened on `RESSLab-Team/resslab-hub-data`, with the comment "Test of the Hub, closed." Then click "Delete branch". Never merge one.

| Pull request | Case | Opened by | Closed | Branch deleted |
| ------------ | ---- | --------- | ------ | -------------- |
| `<n>`        | 12.2 | `M1`      |        |                |
| `<m>`        | 12.4 | `MA`      |        |                |
|              | 12.8 | `M1`      |        |                |
|              |      |           |        |                |
|              |      |           |        |                |

The pull requests of Part 15 are on the test fork. Leave them: Pierre cleans the fork.

#### 19.2 GitHub comments

Delete the comment of 14.4. Delete any other comment you wrote on the data repository.

#### 19.3 Accounts and roles

1. In Browser ADMIN, open the admin page.
2. Set back to "Automatic" every role that you changed.
3. Revoke the invitations that are still open.
4. Disable the test accounts, except the ones that Pierre wants to keep. The Hub cannot delete an account.
5. On GitHub, in "Settings", "Applications", revoke the Hub's access for `gh1` and `gh2` if you do not need them again. On ORCID, do the same in "Trusted parties".

#### 19.4 The report

1. Send Pierre this guide with the boxes ticked, and the list of issues you opened.
2. Write how long each part took.

## Error messages that you cannot reach by hand

Some messages show only when a server breaks or is badly set up, or when the page hides the button that causes them. Automated tests cover them, so this guide has no case for them:

| Message key                       | When it shows                                                                                                |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `auth.errors.generic`             | an unknown error during sign-in                                                                              |
| `auth.errors.mail_failed`         | the mail server refuses the mail                                                                             |
| `auth.errors.mail_not_configured` | the deployment has no mail server                                                                            |
| `auth.errors.email_required`      | an account with no confirmed address sends an access request. The page hides the form in this case (see 4.3) |
| `admin.errors.generic`            | an unknown error on the admin page                                                                           |

If you see one of them during the test, write it as a bug, with the time.
