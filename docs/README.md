# Docs

This folder is the docs site of the RESSLab Hub, a small project of its own.
The site is served under `/docs/` of each hub, for example
<https://resslab-hub.epfl.ch/docs/>.

| Path | What |
| --- | --- |
| `src/` | The pages of the site. `src/index.md` is the home page. |
| `src/data/` | Generated from the data repository, gitignored. Never edit it. |
| `zensical.toml` | The configuration and the navigation, written by hand. |
| `scripts/` | The copy of the data repository pages, the link check, the orphan check. |
| `Dockerfile`, `nginx.conf` | The image that `deploy.yml` builds and each hub serves. |
| `archive/` | Old plans and notes. Not on the site. |
| `worktree-dev-environment.md` | The dev setup of the team with worktrees. Not on the site. |

From the root of the repository:

```bash
make docs         # strict build into docs/site/, then the link and orphan checks
make docs-serve   # preview with live reload on http://127.0.0.1:8100/docs/
```

Both read the data repository from `RESSLAB_DATA_DIR` (default
`../resslab-hub-data`), at `origin/main`.

A new page goes in `src/`, and in the `nav` of `zensical.toml`. A link that
leaves `src/` must be a full GitHub URL. The site is public: write no internal
host, no secret store path and no personal name in a page.
