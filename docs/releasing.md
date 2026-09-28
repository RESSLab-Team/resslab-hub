# Releasing

Three branches, one direction: `dev` -> `stage` -> `main`.

| Branch | Deploys to | How |
|---|---|---|
| `dev` | https://resslab-hub-dev.epfl.ch | every push |
| `stage` | https://resslab-hub-test.epfl.ch | every push |
| `main` | nothing by itself | Release Please tags it, the tag deploys prod |
| tag `v*.*.*` | https://resslab-hub.epfl.ch | `deploy.yml` on the tag push |

## Rule: promotion PRs use a merge commit, never squash

Feature PRs into `dev` are squashed, that is fine. But `dev -> stage` and
`stage -> main` must be merged with a **merge commit**. A squash turns 200
commits into one `chore:` commit, and Release Please then sees nothing to
release, so the changelog would be empty and the version would not move.

## Steps

1. **dev -> stage**

   ```bash
   gh pr create --base stage --head dev --title "chore: promote dev to stage"
   ```

   Merge it with a merge commit. Wait for the stage deploy, then check
   https://resslab-hub-test.epfl.ch.

   If someone edited a file directly on `stage` (it happens), the PR conflicts.
   Resolve by taking `dev`'s version, then push the fix to `dev` too so the two
   branches do not drift again.

2. **stage -> main**

   ```bash
   gh pr create --base main --head stage --title "chore: promote stage to main"
   ```

   Merge commit again.

3. **Release Please opens the release PR** on `main` a minute later, titled
   `chore(main): release <version>`. Its body becomes the changelog entry, so
   read it and trim it if it is noisy. Merging it:

   - writes `CHANGELOG.md`,
   - bumps `package.json`, `frontend/package.json` and `backend/pyproject.toml`,
   - creates the tag `v<version>` and the GitHub release.

4. **Check the prod deploy ran** on the tag:

   ```bash
   gh run list --workflow=deploy.yml
   ```

   If no run appeared for the tag, the token lacks rights (see below). Deploy by
   hand:

   ```bash
   gh workflow run deploy.yml --ref v<version>
   ```

5. **Bring the release commit back down**, or the branches diverge again:

   ```bash
   git push origin main:stage
   git push origin main:dev
   ```

   Both are fast-forwards if nothing landed in between. Otherwise open a
   `main -> dev` PR and merge it with a merge commit.

## Choosing the version

Release Please computes it from the commits: `fix:` bumps the patch, `feat:` the
minor, a `!` or a `BREAKING CHANGE:` footer the major. To force a version, put
this footer in any commit that will end up on `main`:

```bash
git commit --allow-empty -m "chore: release 2.0.0" -m "Release-As: 2.0.0"
```

The footer only applies to the next release, nothing to clean up after.

## Tag names

`release-please-config.json` sets `include-component-in-tag: false`. Without it
release-please defaults to `true` and would tag `resslab-hub-v2.0.0`, which does
not match the `v*.*.*` pattern in `deploy.yml`, so prod would not deploy. It
would also fail to find the previous `v1.1.0` tag and rebuild the whole
changelog. Leave that option alone.

## The token

`release-please.yml` uses `secrets.RELEASE_PLEASE_TOKEN`, not the default
`GITHUB_TOKEN`. Reason: a tag created by `GITHUB_TOKEN` does not trigger other
workflows, so `deploy.yml` would never fire and prod would stay on the old
version. The secret is a fine-grained PAT on this repo with **Contents: read and
write**, **Pull requests: read and write** and **Issues: read and write** (that
last one is what lets it put labels on the release PR). When it expires, release
PRs stop appearing, with no other warning. Put a reminder in the calendar for the
expiry date.

## First deploy of a big change to prod

A tag deploys prod straight away. Before tagging a release that changes the
database schema or the deployment, do the boring checks: dump the prod database
(`make backup-dump DEST_FOLDER=...`), confirm the prod secrets are in place, and
confirm the Alembic migrations that ran on stage are the same ones prod will get.
The backend caches responses for an hour per process, so restart the prod pods if
new data must show right away.

### Keeping the contribution pipeline off in prod

Submit, curation, sign-in and account can ship to prod switched off, and be
switched on later without a new release. The switch is `CONTRIBUTIONS_ENABLED`
([contributing-data.md](contributing-data.md#settings)). Dev and stage set
nothing and keep the default, `true`.

Before the first tag that carries the pipeline, add this line to
`overlays/prod/kustomization.yaml` in `enack8s-app-config/epfl-resslab/resslab-hub`,
under `configMapGenerator` > `name: resslab-hub-backend` > `literals:`
(the indentation is the one of the other literals):

```yaml
      - CONTRIBUTIONS_ENABLED=false
```

Kustomize puts a hash of the content in the generated ConfigMap name, so ArgoCD
rolls the backend pods when it syncs the change. If they did not roll, restart
them by hand, the setting is read at startup:

```bash
kubectl -n epfl-resslab-resslab-hub-prod rollout restart deployment/resslab-hub-backend-prod
```

Check it with `curl https://resslab-hub.epfl.ch/api/features`, which must say
`{"contributions":false}`. The frontend needs nothing: it reads that endpoint on
each page load. To switch the pipeline on, remove the line (or set it to `true`).
With it on, prod also needs the GitHub App, OAuth and mail secrets of
[auth.md](auth.md), or `/features` stays `false`.
