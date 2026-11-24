# Submit data

This page is for researchers who want to add their experiments to the
RESSLab Hub. It tells you what you need, how the Hub checks your files, and
what happens after you submit. [How data gets into the Hub](index.md) shows
the full path.

## What you need

- An account on the Hub. Sign in at `/login` with an email code, GitHub or
  ORCID.
- The `contributor` role. An address of a university or a research institute
  gets it at sign-in. With a different address, ask for access from your
  account page. An administrator of the lab then decides.
- A name and a confirmed email address on the account. The Hub writes both on
  the pull request. Without them, the submit is refused.
- Your files: one CSV with one row for each experiment, and one curve file for
  each experiment and each type of test data. The README of each database
  folder in the [data repository][data-repo] gives the column names, the units
  and the file names. The editor shows the same README and the data
  dictionary next to your data.

> Note: What you submit becomes public, because the data repository is
> public. The pull request and its commit show your name and your email
> address. They also show your institution, your ORCID iD and your GitHub
> login, when the account has them.

## Fill the editor

1. Open `/contribute` and select the database.
2. Drop your files on the page: a folder, a zip file or loose files. The
   editor sorts them into the main CSV and the curve files. It tells you what
   it did with each file.
3. Fix the problems that the editor shows on each experiment card.
4. Click "Submit for review".

The editor checks your data at each pause in your work. It sends the files to
the same validator that the server uses. The checks cover the headers, the
types, the empty required cells, the curve files and the rules of the README.

- An error blocks the submit. Fix it in the card or in your files.
- A warning does not block the submit. A frequent warning is a value far
  outside the range of the data that the Hub already has. If the value is
  correct, dismiss the warning. The curator sees the list of the warnings you
  dismissed.
- An id that already exists in the Hub or in the data repository is an error.

## After you submit

The Hub opens a pull request (in the Hub: a "review request") on the data
repository, then shows its number. Nothing changes on the dashboards yet.

1. The data CI of the data repository checks the files again.
2. A curator of the lab reviews the submission and approves it on GitHub.
3. The curator merges it. Some minutes later, your experiments are on the
   dashboards, marked as not verified yet.
4. Later, a curator compares the values with the publication and marks the
   rows as verified.

The page of your submission stays at `/contribute/edit/<number>`. To change
something, edit it there and submit again. This adds a commit to the same pull
request, and the checks run again. Do not start a second submission for the
same data. You can also follow the review at `/curation/<number>`, which shows
the comments of the curator.

## Limits

| Limit | Value |
| --- | --- |
| New submissions | 5 for each hour |
| Updates of a submission | 10 for each hour |
| Size of one submission | 50 MB once compressed, 2000 files |
| Open submissions in the queue | 25. If the queue is full, the Hub asks you to try again later. |

## Without the Hub

You can also open a pull request on the data repository yourself. Fork it,
add your rows and files on a branch, and open the pull request into `main`.
The README of the data repository gives the steps. The curators see this pull
request in the same queue. The Hub can show only the rows that it adds to the
main CSV.

## Next step

Open `/contribute` on the Hub, or read the README of your database folder in
the [data repository][data-repo] first.

[data-repo]: https://github.com/RESSLab-Team/resslab-hub-data
