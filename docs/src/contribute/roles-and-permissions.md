# Roles and permissions

This page is for the researchers and the curators who use the Hub. It tells
you what each role lets you do, where your role comes from, and how to get a
higher one. You do not need an account to look at the data. You need one to
send data or to review it.

## The four roles

Each account has one role. The roles go from the weakest to the strongest,
and each role can do all that the roles before it can do:

1. Viewer: each account that is signed in.
2. Contributor: sends test data to the databases.
3. Curator: a member of the lab who reviews the submissions.
4. Administrator: manages the accounts of the Hub.

Your account page (`/account`) shows your role and the reason for it, for
example "Granted from your academic email address". A submission is a set of
test data that you send from the Hub. The Hub makes it into a pull request
on the public [data repository][data-repo].

## Who can do what

| Action | No account | Viewer | Contributor | Curator | Administrator |
|---|---|---|---|---|---|
| Look at, filter and download the data (CSV and curves) | yes | yes | yes | yes | yes |
| Check your files against the rules of a database | | yes | yes | yes | yes |
| Ask for the contributor role | | yes | | | |
| Send a new submission | | | yes | yes | yes |
| Open and change an open submission | | | own | all | all |
| Open the review queue | | | | yes | yes |
| Mark records as verified | | | | yes | yes |
| Use the admin page | | | | | yes |

"Own" means a submission that you sent. The Hub knows it is yours when the
email address on the submission is one of the confirmed addresses of your
account. A contributor cannot see the submissions of other people.

The admin page lets an administrator do these tasks:

- Approve or decline the requests for the contributor role.
- Change the role of an account, or disable an account.
- Invite a person who has no account yet.
- Merge two accounts of the same person.

## What the Hub does not decide

The Hub does not approve, reject or merge a submission. A curator reads the
submission in the Hub, then approves and merges the pull request on GitHub.
Only the permissions on the data repository on GitHub allow that step. Thus
a curator who reviews also needs write access on the data repository.
[Review and verify](review-and-verify.md) explains the review.

## Where your role comes from

The Hub calculates your role each time that one of its sources changes. It
reads the sources in this order and keeps the first one that applies:

1. Your address is on the list of administrators of the deployment: you are
   an administrator.
2. Your GitHub account is an admin of the data repository: you are an
   administrator.
3. An administrator of the Hub set your role: you have that role.
4. Your GitHub account has write or maintain access on the data repository:
   you are a curator.
5. One of your addresses is academic: you are a contributor.
6. If none of these applies, you are a viewer.

The GitHub sources count only after you link GitHub to your account. Each
confirmed address of your account counts, not only the main one. An
academic address is the address of a university or of a known research
institute. The Hub uses a public list of university domains, and the people
who run the Hub can add other institutes. [Sign-in and
accounts](../auth.md#what-counts-as-academic) gives the full rule.

A role that an administrator set comes before GitHub write access. If an
administrator made you a contributor, write access on GitHub does not make
you a curator. Ask an administrator to set your role back to "Automatic".

## Get a higher role

To become a contributor, do one of these steps:

1. Sign in with your academic address, or add it to your account on the
   account page. The role comes at once.
2. If you have no academic address, ask for access on your account page. You
   must first confirm an email address. You can add a short message about
   your data. An administrator reads the request, and you get an email when
   it is approved.
3. An administrator can invite your address. The role comes at your first
   sign-in with that address.

You can have only one open request at a time. If an administrator declines
it, the account page tells you, and you can ask again.

To become a curator, link your GitHub account on the account page. Your
GitHub account must have write access on the data repository. If it does
not, ask an administrator of the lab. The same applies to the administrator
role, which comes from admin access on the data repository.

An approved request or an invitation never lowers your role.

## When a change shows

- A decision of an administrator: at your next action in the Hub. You do not
  have to sign in again.
- A change of your access on GitHub: in one hour at the latest, or at your
  next sign-in.
- A new academic domain: at your next sign-in. A session lasts 30 days, so
  sign out and sign in again.

If the Hub still shows the wrong role, read the reason on your account page.
Then ask an administrator of the lab.

[data-repo]: https://github.com/RESSLab-Team/resslab-hub-data
