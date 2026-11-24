# RESSLab Hub docs

The [RESSLab Hub](https://resslab-hub.epfl.ch) is a database of tests on
structural steel components (braces, columns, connections, materials,
residual stresses, HSS columns, EBF links). These docs have three parts. Go
to the part for what you want to do.

## I have data, or I review data

[Contribute data](contribute/index.md) explains how an experiment goes from
your files to the public dashboards.

- [Submit with the Hub](contribute/submit-with-the-hub.md): the form checks
  your files and opens the pull request for you.
- [Submit with a pull request](data/contributing.md): you work on the data
  repository yourself.
- [Review and verify](contribute/review-and-verify.md): for the members of
  the lab who accept the submissions and verify the data.

## I want to know what a database expects

[Databases](data/index.md) has one page for each database. Each page gives
the identifier of a specimen, the files to send, and the data dictionary with
the unit of each column. [Variable categories](variable-categories.md) lists
the scientific category of each column.

## I run or change the Hub

To run a deployment:

- [Run the data pipeline](run-the-pipeline.md): the rules of the data
  repository, the upload, the nightly rebuild, the cache.
- [Releasing](releasing.md): `dev` to `stage` to `main`, Release Please, the
  prod checklist.
- [Sign-in and accounts](auth.md): email code, GitHub and ORCID sign-in,
  roles, and the settings of a deployment.
- [SEM images](sem-images.md): the fracture images, from the TIFs in the data
  repository to the CDN.

To change the code:

- [What's new in 2.0](whats-new-in-2.0.md): the rewrite, versus the old app.
- [Dashboard architecture](dashboard-architecture.md): the dashboard engine in
  the browser, and the backend cache behind it.
- [Design system](design-system.md): the tokens, the cascade layers, and how
  to style a new page.
- [Adding a new tab](adding-a-new-tab.md): the steps for a new component
  database.
- [Contribution internals](contributing-data.md) and
  [Curation internals](curation.md): the code behind the submit and the
  review.

To run the app on your machine, read the [README][readme] of the source
repository, then the READMEs of [backend][backend] and [frontend][frontend].

The source is in [RESSLab-Team/resslab-hub][repo]. The data is in
[RESSLab-Team/resslab-hub-data][data-repo]. The Contribute and Hub pages are
built from the `docs/` folder of the source repository. The Databases pages
come from the READMEs of the data repository. The site copies them at each
deploy of the Hub.

[repo]: https://github.com/RESSLab-Team/resslab-hub
[data-repo]: https://github.com/RESSLab-Team/resslab-hub-data
[readme]: https://github.com/RESSLab-Team/resslab-hub/blob/dev/README.md
[backend]: https://github.com/RESSLab-Team/resslab-hub/blob/dev/backend/README.md
[frontend]: https://github.com/RESSLab-Team/resslab-hub/blob/dev/frontend/README.md
