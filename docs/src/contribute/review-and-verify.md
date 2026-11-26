# Review and verify

This page is for the members of the lab who review the submissions. The Hub
shows each submission next to the data that it already has. You read it in
the Hub, then you approve and merge it on GitHub. [How data gets into the
Hub](index.md) shows the full path.

## Who can review

You need the `curator` role. You get it in one of two ways:

- Your GitHub account has write or maintain access on the
  [data repository][data-repo], and you linked it to your Hub account.
- An administrator of the Hub made you a curator.

[Roles and permissions](roles-and-permissions.md) explains each role and how
to get it.

Only GitHub permissions let you approve and merge, so a curator who reviews
also needs write access on the data repository. The Hub asks each
administrator of the data repository to review each new pull request, so they
get an email from GitHub.

## The review queue

Open `/curation`. The tab "To accept" lists each open pull request into
`main`, the newest first. "Refresh" reads GitHub again.

| What you see | What it is |
| --- | --- |
| A database name | A submission from the Hub, or a pull request made by hand that changes one database folder. |
| "Unrecognised" | A pull request that changes no database folder, or several. Review it on GitHub. |
| "Draft" | A draft pull request on GitHub. |
| "Fork" | A pull request from a fork. The Hub cannot push to it, so "Edit on the Hub" does not work. |

## What to check

Open a submission. The review page has these panels:

- Specimen metadata: the values of the selected experiment, grouped by
  scientific category ([variable categories](../variable-categories.md)).
- Comparison with similar experiments: the experiments of the Hub that look
  like this one, and a parallel chart. Use it to judge a value against its
  peers.
- Data preview: each curve of the submission in red, with the curves of the
  similar experiments behind it.
- Quality flags: the result of the validator for each experiment.
- Discussion: the comments of the pull request.

Before you approve, make sure that:

1. The check `validation-passed` of the data CI is green on GitHub. A failed
   validation does not block the merge today, so look at it yourself.
2. The quality flags have no error. Read each warning that the contributor
   dismissed. The pull request body lists them.
3. The values and the curves look correct next to the similar experiments.
4. The ids and the reference are correct.

## Approve, ask for changes, merge

The Hub does not approve or merge. Do it on the pull request on GitHub:

1. To ask for changes, write a comment on GitHub. The contributor edits the
   submission in the Hub, which adds a commit to the same pull request.
2. To fix a small problem yourself, click "Edit on the Hub". Your commit has
   your name, and the trailers keep the name of the contributor.
3. To accept, approve the pull request on GitHub.
4. Merge with "Squash and merge". It is the only method that the data
   repository accepts.

Some minutes after the merge, the rows are on the dashboards as "unverified".
A browser that showed the database before can need up to one hour to show
them. If they do not come, tell a maintainer
([run the data pipeline](../run-the-pipeline.md#the-data-does-not-show)).

> Note: A pull request from the test site of the Hub is a test. Close it, do
> not merge it. Branches of the sample data start with `contrib/<type>/demo-`.

## Verify the data

Accepting and verifying are two steps. To accept, you check that the
submission is correct enough to go online. To verify, you compare the values
with the publication, later.

1. Open the tab "To verify" in `/curation`. It lists the unverified
   experiments, by database and reference.
2. Open a reference. The page has the same panels as a submission. The
   ranges and the similar experiments use only the verified rows.
3. Click "Mark all as verified", or mark one experiment only. The Hub opens a
   small pull request on a branch `verify/...`. It changes only the column
   `data_curation_status`.
4. Approve it and merge it on GitHub with "Squash and merge".

The tab reads the database of the Hub. A merged verification stays in the tab
until the upload after the merge is done.

## Next step

Open `/curation` on the Hub. The developer details of these pages are in
[Curation internals](../curation.md).

[data-repo]: https://github.com/RESSLab-Team/resslab-hub-data
