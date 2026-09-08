# Docs

One line per guide. Start with the root [README](../README.md) to run the app.

## Run it

- [Root README](../README.md): prerequisites, dev servers, populate the database, deploy targets
- [backend/README.md](../backend/README.md): migrations, model generation, uploads (local and in-cluster)
- [frontend/README.md](../frontend/README.md): scripts, layout of `src/`, env files
- [worktree-dev-environment.md](worktree-dev-environment.md): one branch, its own servers, database and Claude session
- [releasing.md](releasing.md): dev -> stage -> main, Release Please, the token, the prod checklist

## How it works

- [whats-new-in-2.0.md](whats-new-in-2.0.md): the refactor, section by section, versus the old app on `main`
- [auth.md](auth.md): sign-in by email code or GitHub, sessions, roles, the settings a deployment needs
- [contributing-data.md](contributing-data.md): from a dropped folder to a pull request on the data repo, and editing it
- [curation.md](curation.md): the review queue and the review page
- [dashboard-architecture.md](dashboard-architecture.md): the client-side dashboard engine, and the backend cache behind it
- [variable-categories.md](variable-categories.md): the scientific category of every column, per database

## Maintain it

- [adding-a-new-tab.md](adding-a-new-tab.md): the end-to-end playbook for a new component database
- [modernization-followups.md](modernization-followups.md): toolchain upgrades done and still open, upload perf notes
- [design/](design/): the brand exploration and the sign-in mail brief and handoff

`CLAUDE.md` at the root is the map of the repo for coding agents. It repeats
the facts above in short form and is kept in step with them.
