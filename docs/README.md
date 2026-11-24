# RESSLab Hub docs

The [RESSLab Hub](https://resslab-hub.epfl.ch) is a database of tests on
structural steel components (braces, columns, connections, materials,
residual stresses, HSS columns, EBF links). These docs explain how data gets
into it, and how the app works for the people who maintain it.

The source is in [RESSLab-Team/resslab-hub][repo]. The data is in
[RESSLab-Team/resslab-hub-data][data-repo]. These pages are built from the
`docs/` folder of the source repository.

## Data pipeline

Start with [How data gets into the Hub](data-pipeline/index.md), then read
the page for your role:

- [Submit data](data-pipeline/submit-data.md): for researchers who share their
  experiments.
- [Review data](data-pipeline/review-data.md): for the members of the lab who
  review and verify the submissions.
- [Run the pipeline](data-pipeline/run-the-pipeline.md): for the maintainers
  of the data repository and of the deployments.
- [Contribution internals](contributing-data.md) and
  [Curation internals](curation.md): the code behind the submit and the
  review.
- [Variable categories](variable-categories.md): the scientific category of
  each column, for each database.

## For maintainers

- [What's new in 2.0](whats-new-in-2.0.md): the rewrite, versus the old app.
- [Releasing](releasing.md): `dev` to `stage` to `main`, Release Please, the
  prod checklist.
- [Sign-in and accounts](auth.md): email code, GitHub and ORCID sign-in,
  roles, and the settings of a deployment.
- [Dashboard architecture](dashboard-architecture.md): the dashboard engine in
  the browser, and the backend cache behind it.
- [Design system](design-system.md): the tokens, the cascade layers, and how
  to style a new page.
- [SEM images](sem-images.md): the fracture images, from the TIFs in the data
  repository to the CDN.
- [Adding a new tab](adding-a-new-tab.md): the steps for a new component
  database.

To run the app on your machine, read the [README][readme] of the source
repository, then the READMEs of [backend][backend] and [frontend][frontend].

[repo]: https://github.com/RESSLab-Team/resslab-hub
[data-repo]: https://github.com/RESSLab-Team/resslab-hub-data
[readme]: https://github.com/RESSLab-Team/resslab-hub/blob/dev/README.md
[backend]: https://github.com/RESSLab-Team/resslab-hub/blob/dev/backend/README.md
[frontend]: https://github.com/RESSLab-Team/resslab-hub/blob/dev/frontend/README.md
