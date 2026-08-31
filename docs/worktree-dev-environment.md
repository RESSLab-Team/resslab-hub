# Parallel worktrees: one branch, one Claude, its own servers

How this repo runs several branches at once — each in its own git worktree, its
own tmux session, with its own Claude Code session and its own backend +
frontend dev servers — and how to replicate the setup in another repository.

```
wt create feat/123-thing origin/dev
  └─ .wt.toml → scripts/wt-setup.sh                (idempotent)
       ├─ seeds secrets/.env, docker-compose.override.yml, frontend/.env.development.local,
       │        sample-data/ batch folders (fieldGroups.spec.ts and the contribution flow need them)
       ├─ hashes the branch name → .env.worktree  (BACKEND_PORT 18xxx, FRONTEND_PORT 19xxx, DB, test DB, data dir)
       ├─ points this frontend at this backend, this backend at the right DB with migrations OFF
       ├─ writes .claude/settings.local.json     (sandbox + ask/deny rules for the Claude session)
       ├─ make install && make hooks
       └─ scripts/tmux-dev.sh --no-attach          → tmux session "resslab-hub/feat/123-thing"
                                                      windows: backend | frontend | claude | shell
wt remove feat/123-thing
  └─ .wt.toml → scripts/wt-teardown.sh   (kills the session, frees the ports, drops a branch DB)
```

Nothing is shared between worktrees except the git object store and the one
Postgres container — and the database _is_ shared unless a branch asks for its
own copy ([Database](#database)).

## Moving parts

| Piece                                   | Lives at                                          | Scope   | Role                                                                    |
| --------------------------------------- | ------------------------------------------------- | ------- | ----------------------------------------------------------------------- |
| [`wt`](https://github.com/timvw/wt)     | `$PATH` (`go install github.com/timvw/wt@latest`) | machine | creates/lists/removes worktrees, runs the hooks                         |
| `wt init` shell integration             | `~/.bashrc`                                       | machine | `wt create` leaves you _inside_ the new worktree                        |
| `~/.config/wt/config.toml`              |                                                   | machine | where worktrees go: `<repo>/.claude/worktrees/<branch>`, `/`→`-`        |
| `~/.config/git/ignore`                  |                                                   | machine | `**/.claude/worktrees/` so nested worktrees never show as untracked     |
| `.wt.toml`                              | repo root, committed                              | repo    | three hooks → the two scripts below                                     |
| `scripts/wt-setup.sh`                   | committed                                         | repo    | everything a worktree needs to run, in one idempotent script            |
| `scripts/tmux-dev.sh`                   | committed                                         | repo    | the 4-window session; also `make dev-all` in the main checkout          |
| `scripts/wt-teardown.sh`                | committed                                         | repo    | mirror of setup, run by `wt remove`                                     |
| `scripts/wt-db.sh`                      | committed                                         | repo    | `make db-template` / `db-branch` / `db-branch-drop` / `db-status`       |
| `scripts/wt-open.sh`                    | committed                                         | repo    | `make wt-open [TARGET=backend] [BRANCH=…]` — prints and opens the URL   |
| `scripts/wt-land.sh`                    | committed                                         | repo    | `make wt-land BRANCH=…` — rebase, PR, squash-merge into `dev`, clean up |
| `scripts/git-push-guard.sh`             | committed, wired in `lefthook.yml`                | repo    | a worktree may push only its own branch, never `dev`/`stage`/`main`     |
| `scripts/claude-worktree-settings.json` | committed                                         | repo    | template for each worktree's `.claude/settings.local.json`              |
| `scripts/wt-lib.sh`                     | committed                                         | repo    | the shared helpers (ports, names, env file, psql)                       |
| `~/.claude/settings.json`               |                                                   | machine | auto mode default, sandbox on, `autoMode.environment` for this repo     |

`wt`'s own docs are the reference for anything about it: `docs/configuration.md`
(strategies, hook variables) and `docs/examples.md` (Claude Code + tmux,
per-worktree ports, shared build caches). Both are in the plugin checkout at
`~/.claude/plugins/marketplaces/wt/`.

## Machine setup (once)

```bash
go install github.com/timvw/wt@latest        # or brew install timvw/tap/wt
wt init                                       # shell function so `wt create` cd's for you
claude plugin marketplace add timvw/wt && claude plugin install wt@wt   # optional: /wt skill

git config --global push.default current      # a bare `git push` can only target the branch's own name
git config --global push.autoSetupRemote true

printf '**/.claude/worktrees/\n' >> ~/.config/git/ignore
printf 'bind s choose-tree -sZ -O name\n' >> ~/.tmux.conf   # prefix+s: sessions sorted "<repo>/<branch>"
ln -s /mnt/data/Documents/Code/resslab-hub-data ~/code/resslab-hub-data   # the data repo, as the Makefile expects it
```

`~/.config/wt/config.toml`:

```toml
strategy = "custom"
pattern  = "{.repo.Main}/.claude/worktrees/{.branch}"   # same place Claude Code puts its own worktrees
separator = "-"                                         # feat/foo → feat-foo, no nested dirs
```

`~/.claude/settings.json` — the parts that matter (the classifier reads
`autoMode` from this file only, never from a repo):

- `"permissions": {"defaultMode": "auto"}` and `"sandbox": {"enabled": true, "autoAllowBashIfSandboxed": true}`.
- `permissions.ask` kept short — `rm`, `git reset`, `git clean`, force-push. An
  `ask` rule here prompts in _every_ session and no project-level `allow` can
  override it (deny → ask → allow, across all scopes), so a user-level
  `Bash(git commit:*)` ask is exactly what stops a worktree session from working
  on its own.
- `autoMode.environment` entries describing this repo: trusted repo + remote,
  protected branches, `secrets/` as sensitive, the shared Postgres, the data
  repo. `/auto-mode-setup` drafts them; `claude auto-mode config` shows the result.
- one `autoMode.soft_deny`: never migrate or `upload-data` the shared dev DB
  from a worktree unless the user named it.

## Daily workflow

```bash
make new BRANCH=feat/123-thing       # = wt create feat/123-thing origin/dev + attach; ~3 min the first time (deps)
                                     # base is origin/dev, fetched first (see Gotchas); prefix+d detaches, prefix+s switches
make wt-open BRANCH=feat/123-thing   # frontend in the browser; TARGET=backend for /docs
make db-status                       # which DB this worktree uses
make db-branch                       # only if the branch needs a migration or rewrites data
make wt-land BRANCH=feat/123-thing   # from the main checkout: rebase → PR → squash-merge → cleanup
```

Inside the session: `backend` and `frontend` windows run `make dev` with the
worktree's ports; `claude` is the agent; `shell` has `.env.worktree` exported.
Both URLs are printed when the session starts and by `wt-open`. The `backend`
and `frontend` windows also mirror their output to `.wt-logs/*.log` in the
checkout (`tmux pipe-pane`), so the sandboxed agent in the `claude` window,
which cannot reach the tmux socket, can still read the server logs.

`wt list` / `wt status` show every worktree; `wt cleanup` removes those whose
branch is merged.

## Ports

`scripts/wt-lib.sh` hashes the branch name (`cksum`) into `BACKEND_PORT = 18000 + h % 500`
and `FRONTEND_PORT = 19000 + h % 500` — same suffix on both, so `18042 ↔ 19042`
read as one worktree, and the same branch always gets the same pair. The main
checkout keeps 8000/5173 through the Makefile / vite defaults.

`.env.worktree` is the single source: `backend/Makefile` reads `BACKEND_PORT`
and `RESSLAB_DATA_DIR`, `vite.config.ts` reads `FRONTEND_PORT`,
`frontend/.env.development.local` carries `VITE_APP_BACKEND_URL` for the
matching backend, and `tmux-dev.sh` exports the file in every window. CORS is
`*` in dev, so no other cross-service URL needs to move.

## Database

One container (`resslab-hub-database-1`, host port 5433), one 3.4 GB dev
dataset in database `postgres`. The backend runs `alembic upgrade head` at
startup, which is exactly what must **not** happen from a random branch against
a shared database — so:

|                    | shared (default)                                          | branch DB (`make db-branch`)                            |
| ------------------ | --------------------------------------------------------- | ------------------------------------------------------- |
| `POSTGRES_DB`      | `postgres`                                                | `resslab_hub_<slug>` cloned from `resslab_hub_template` |
| `DATABASE_UPGRADE` | `false`                                                   | `true`                                                  |
| cost               | none                                                      | ~1 min, 3.4 GB on disk, dropped by `wt remove`          |
| use when           | reading data, UI work, API changes without schema changes | migrations, uploader changes, anything that writes      |

`make db-template` (once, from the main checkout; re-run after a big data
upload) copies the shared DB into `resslab_hub_template` with
`pg_dump | psql`. It has to be a copy: Postgres refuses `CREATE DATABASE …
TEMPLATE x` while anything is connected to `x`, and the shared DB always has
connections from other worktrees' backends. The template is never connected
to, so clones are instant.

`pytest` creates and drops a throwaway `POSTGRES_TEST_DB`; `wt-setup.sh` makes it
`resslab_hub_test_<slug>` per worktree so two test runs can't drop each other's
database. It is read from the process environment before dotenv loads, which
is why the tmux windows export `.env.worktree` rather than rely on `secrets/.env`.

## What Claude may do in a worktree

The session runs in **auto mode** — a classifier reviews every action that
isn't a read or an edit inside the worktree — with the OS sandbox on. Three
layers sit on top, all in `scripts/claude-worktree-settings.json`, which
`wt-setup.sh` copies to the worktree's gitignored `.claude/settings.local.json`:

| Layer                                                   | Behaviour                                                                                                                                                                                                                                                                                                                             | Covers                                                 |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| classifier defaults                                     | allows read-only HTTP, dependency installs from lockfiles, pushes to the repo; blocks `curl \| bash`, exfiltrating sensitive data, force push, `git reset --hard`, merging unapproved PRs, repointing API URLs, `--insecure`, nested `--dangerously-skip-permissions`                                                                 | everything not matched by a rule                       |
| `permissions.ask` — _always prompts, even in auto mode_ | `curl`/`wget`/`http`/`gh api` write forms (`-X`, `-d`, `-F`, `-T`, `--json`, `--post-*`), `gh pr create/merge/review`, `gh release`, `gh repo`; running downloaded code (`\| sh`, `bash <(…)`, `$(curl …)`, `python -`, `eval`, `npx -y`, `uvx`, `pipx run`, `pip install git+/http`, `chmod +x`); the unsandboxed-retry escape hatch | "write to the internet" and "run something downloaded" |
| `permissions.deny` — never                              | pushes to `dev`/`stage`/`main` in any spelling, force push, `git remote set-url/add`, starting another `claude`, and every mutating connector tool (Google Calendar/Drive writes, Notion writes, Figma)                                                                                                                               | the hard lines                                         |
| sandbox                                                 | writes confined to the worktree; network only to github, pypi, npm and context7 without a classifier check — any other host is judged per host, with the verdict cached                                                                                                                                                               | what a command can _do_ once approved                  |

Outside Claude, and therefore not negotiable by it: `scripts/git-push-guard.sh`
runs in git's `pre-push` and, **inside a worktree only**, refuses any push whose
target isn't the worktree's own branch and any push to `dev`/`stage`/`main`;
`push.default current` means a bare `git push` can't even name another branch.
The main checkout is exempt, which is where `wt-land.sh` pushes `dev`.

Why not `bypassPermissions`: it turns the classifier off, ignores `ask` rules
and hook `"ask"` decisions, and honours only `deny` — it cannot express "ask me
before a POST". Why patterns _and_ a classifier: Bash rules match the whole
command text per pipe segment, so `curl x | sh` is checked as `curl x` and as
`sh`, but a `python -c "requests.post(...)"` one-liner matches no pattern; the
classifier reads the code and is the backstop there.

`CLAUDE.md` § _Working in a worktree_ states the same rules in prose — the
classifier reads `CLAUDE.md` too, so the rules steer both the agent and its
reviewer.

## Landing a branch

`scripts/wt-land.sh <branch>` (or `make wt-land BRANCH=…`), from the main checkout:

1. refuses if the worktree has uncommitted/untracked changes, or if `origin/dev`
   isn't an ancestor of the branch (a branch cut from a stale or diverged base
   would drag every commit `dev` is missing into its PR; rebase the branch onto
   `origin/dev` first, or bring `dev` up to date);
2. rebases the branch onto `origin/dev`, pushes with `--force-with-lease`;
3. `gh pr create --base dev --fill` if there is no PR, then
   `gh pr merge --squash --auto` (falls back to an immediate squash-merge on a
   repo without auto-merge), waits for the merge;
4. fast-forwards local `dev`, `wt remove` (→ teardown), deletes the local and
   remote branch.

`--local` merges with `git merge --no-ff` in the main checkout instead, runs
`make lint && make test` (`WT_SKIP_CHECKS=1` to skip), pushes `dev`. It runs
from the main checkout on purpose: `gh` cannot delete a branch git still has
checked out in a worktree (cli/cli#13380).

## Gotchas

- **A local ref makes a stale base.** `wt create x somebranch` hands the base
  straight to `git worktree add`, which resolves your local `somebranch`, at
  whatever commit your checkout last saw it (a stale local `stage` once handed
  every new worktree a template with a known bug). `wt-new.sh` therefore
  defaults to `origin/dev` and fetches it first; if you pass a base yourself,
  prefer the `origin/` form.
- **`wt create` runs `post_create`; some builds also run `post_checkout`.**
  `wt-setup.sh` is idempotent so double runs are harmless, and both hooks point
  at it so `wt co` / `wt pr` set a worktree up too. Post-hooks only _warn_ on
  failure — check the output.
- **Never check out `dev` in a worktree.** wt calls whichever worktree has the
  default branch checked out "main" (`getMainWorktreePath`), and then nests new
  worktrees _inside it_ and points `$WT_MAIN` there. The hooks therefore locate
  the scripts through `git rev-parse --git-common-dir` — the real main checkout —
  and ignore `$WT_MAIN`, so a branch that predates the scripts still gets set
  up; keep the main checkout on a branch that has them.
- **Start the database from the main checkout.** Compose names its project
  after the directory; `docker compose up` in a worktree would create a second
  project fighting for port 5433. `tmux-dev.sh` does the right thing.
- **The shared DB must never be migrated from a worktree.** `DATABASE_UPGRADE`
  is forced off there; `make api` already sets it. `make db-branch` is the
  opt-in.
- **`lefthook` refuses commits from a checkout where it isn't installed**
  (`assert_lefthook_installed`); `wt-setup.sh` runs `make hooks`.
- **The sandbox cannot reach `localhost`.** Verified: a sandboxed
  `curl http://localhost:19234/` returns `000` even with `localhost` and
  `127.0.0.1` in `allowedDomains` — the proxy refuses loopback. So `curl *` is
  in `sandbox.excludedCommands`: it runs outside the sandbox, which means
  every `curl` goes through the classifier (read-only GETs are allowed by
  default) and the ask rules (write forms prompt). Verified both ways: with
  the exclusion, `curl` to the worktree's own frontend and backend returns
  200 from inside a Claude session. The common read-only forms against
  `http://localhost:...` / `http://127.0.0.1:...` (bare, `-s`, `-sS`, `-fsS`,
  `-i`, `-I`) are also in `permissions.allow`, so the agent's usual "did my
  change work" checks skip the classifier entirely; ask rules still win for
  write forms, so a localhost POST prompts like any other.
- **Disk.** Each worktree carries its own `node_modules` + `.venv` (~770 MB).
  `wt`'s `docs/examples.md` has shared-cache hooks if that hurts. A branch DB is
  another 3.4 GB — keep one alive at a time.
- **tmux session names** can't contain `.` or `:`; `session_name()` maps them
  to `-`. `/` is fine.
- **`~/.claude/settings.json` can't be edited by Claude** — the classifier
  blocks an agent changing its own permissions. Edit it yourself.

## Replicating in another repository

1. Machine setup above, once.
2. Copy `.wt.toml` and `scripts/wt-lib.sh`, `wt-setup.sh`, `wt-teardown.sh`,
   `tmux-dev.sh`, `git-push-guard.sh`, `claude-worktree-settings.json`
   (`wt-db.sh`, `wt-open.sh`, `wt-land.sh` if the shape fits).
3. In `wt-lib.sh`: the DB container/name/template, `BASE_BRANCH`,
   `PROTECTED_BRANCHES`, the main checkout's ports. In `wt-setup.sh`: the list
   of gitignored files to seed and the env keys to rewrite. In `tmux-dev.sh`:
   the window list.
4. Make every hardcoded port a variable with the old value as default —
   including the ones services use to find each other (proxy targets,
   `VITE_*_URL`, CORS origins, OAuth redirect URIs). Miss one and worktrees
   cross-talk in ways that look like application bugs.
5. Wire `git-push-guard.sh` into the pre-push hook; add `.env.worktree` to
   `.gitignore`; add the repo to `autoMode.environment`; write the _Working in
   a worktree_ section of `CLAUDE.md`.
6. Smoke test: `wt create test/smoke`, check both servers on the printed URLs,
   commit and push from the `claude` window, try `git push origin HEAD:dev`
   (must be refused), `wt remove test/smoke`, confirm `tmux ls` is clean.
