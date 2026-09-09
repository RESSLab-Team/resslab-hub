# resslab-hub frontend

Vue 3 single page app: Vuetify 3 for the components, Vite 6 for the build,
TypeScript 5.9 in strict mode, Pinia for the stores, vue-router, vue-i18n
(English and French), ECharts for the charts, Vitest 4 for the tests.
Package manager is pnpm (`npm install -g pnpm`).

## IDE

VS Code with the "Vue (Official)" extension (the old Volar and TypeScript Vue
Plugin pair is folded into it). `.vscode/` at the repo root has the launch
configurations.

## Scripts

Run them from `frontend/`, or through the root `Makefile` (`make help`).

| Command                  | What it does                                                                                                                                                                                        |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pnpm install`           | dependencies (`make install` at the root does it too)                                                                                                                                               |
| `pnpm run dev`           | Vite dev server on http://127.0.0.1:5173 (`FRONTEND_PORT` in a worktree). It proxies `/api` to the backend, open the app here and not on the backend port, or the session cookie is not first-party |
| `pnpm run build`         | type-check + production build, in parallel                                                                                                                                                          |
| `pnpm run type-check`    | `vue-tsc`, no emit                                                                                                                                                                                  |
| `pnpm run lint`          | ESLint (Vue 3 + TS + Prettier rules) with auto-fix                                                                                                                                                  |
| `pnpm run format`        | Prettier on the whole `frontend/` folder (minus `.prettierignore`), README included                                                                                                                 |
| `pnpm run format:check`  | same, read-only. CI runs it, so run it before pushing                                                                                                                                               |
| `pnpm run test:unit`     | Vitest in watch mode. One run: `pnpm run test:unit run` (what `make test` does)                                                                                                                     |
| `pnpm run test:coverage` | Vitest with coverage, report in `coverage/`                                                                                                                                                         |
| `pnpm run api`           | regenerate `src/backend/` from `../openapi.json` (use `make api` at the root, it regenerates the spec first)                                                                                        |
| `pnpm run kpi:snapshot`  | refresh `src/assets/kpi-snapshot.json`, the home page numbers shown before the live fetch (hits production by default)                                                                              |

Node 24 is the safe choice for the tests: Node 26 with the current jsdom kills
the specs that import i18n.

## Layout of `src/`

| Folder         | Content                                                                                                                                                                                                                                                                |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `views/`       | one component per page. Per database: `{Type}View.vue` (dashboard), `{Type}Database.vue` (table), `{Type}ModelView.vue` (model curves), `{Type}FragilityCurve.vue` where it exists. Plus the pages: home, about, login, account, contribute, curation queue and review |
| `components/`  | by domain (`braces/`, `columns/`, ..., `contribute/`, `curation/`, `map/`, `home/`, `layout/`) and `commons/` for what every dashboard shares (shell, filter rail, charts, sliders, the detail drawer)                                                                 |
| `composables/` | the dashboard engine: dataset cache, crossfilter bus, auto filters, virtual rows, ECharts binding. See [docs/dashboard-architecture.md](../docs/dashboard-architecture.md)                                                                                             |
| `stores/`      | Pinia: auth, contribution, curation, counts, dictionary, notification, unit                                                                                                                                                                                            |
| `utils/`       | pure functions: query engine, aggregates, field groups, category colours, submission archive, validation reports                                                                                                                                                       |
| `locales/`     | `en.json` and `fr.json`. Every key exists in both, French keeps its accents                                                                                                                                                                                            |
| `backend/`     | the generated API client. Never edit by hand, run `make api`                                                                                                                                                                                                           |
| `assets/`      | styles (EPFL tokens, Suisse font faces, `app.css`, all pulled by `styles/index.css` - see [design-system.md](../docs/design-system.md)), the section CSVs used by the component selectors, the KPI snapshot                                                            |
| `plugins/`     | axios, i18n, vuetify, the ECharts theme, gtag                                                                                                                                                                                                                          |

## Environment files

- `.env.development`: `VITE_APP_BACKEND_URL=/api` (keep it relative, see above)
  and `VITE_SEM_CDN_BASE_URL=/sem` for the local SEM images (symlink
  `public/sem`, see [docs/sem-images.md](../docs/sem-images.md)).
- `.env.production`: the real CDN base URL.
- `.env.development.local` (gitignored): per-checkout overrides. Worktrees
  get theirs from `scripts/wt-setup.sh`.

## Adding a database tab

[docs/adding-a-new-tab.md](../docs/adding-a-new-tab.md), end to end.

## Video optimization

The home page video is `public/video/steel-mrf-front-page.mp4`.

```bash
# Crop video if necessary
ffmpeg -i input.mp4 -filter:v "crop=1620:1080:150:0" -y cropped.mp4

# Optimize video
ffmpeg -y -i cropped.mp4 -c:v libx264 -b:v 2500k -profile:v high -pix_fmt yuv420p -color_primaries 1 -color_trc 1 -colorspace 1 -movflags +faststart -an output.mp4
```
