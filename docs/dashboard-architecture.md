# Dashboard architecture

How a database tab works in the browser, and what the backend does to make
that cheap. Read this before touching a chart, a filter or the table; the
step-by-step for a new tab is in [adding-a-new-tab.md](adding-a-new-tab.md).

## The shape of a tab

The route renders one dashboard directly
(`components/ebf/EbfDashboard.vue`), which is a good example to read. A
dashboard is `components/commons/DashboardShell.vue` (head, toolbar, active
filter chips, and three slots: `#table`, `#charts`, `#detail`) wired to three
composables:

- `useDataset()` (`composables/useDataset.ts`): the rows and every aggregate
  over them,
- `useDashboard()` (`composables/dashboard.ts`): the filter state and its
  URL,
- `useAutoFilters()` (`composables/useAutoFilters.ts`): the filter rail.

## Loading: one fetch, then everything in the browser

A tab does not query the aggregate endpoints on every filter change. On its
first visit it drains the paginated list endpoint of the database
(`GET /eccentric-braced-frame?page=..&size=1000` and so on) with
`fetchAllPages` in `utils/backend.ts`, and keeps the rows in memory for the
life of the page. The first page gives the total, then every other page is
requested at once, so a big table costs one round-trip plus the slowest page
rather than one round-trip per page. `inferFieldTypes` in `utils/queryEngine.ts` types every
column (string, number, date, boolean) from the first non-null value.

The backend routes `/fields`, `/counts`, `/range`, `/matrix` and `/distinct`
still exist on every component router, for API users and for two things in
the app: `/distinct` feeds the sidebar badges and the home KPIs
(`stores/counts.ts`). The overview map has its own route, `/map/sites`,
which groups every database by site on the server.

## Filtering runs client side

`useDataset()` exposes `getCounts`, `getTotal`, `getRange`, `getDateRange`,
`getMatrix`, `getPage`: pure functions over the cached rows, built from
`utils/queryEngine.ts` (the predicate) and `utils/aggregate.ts` (counts,
ranges, matrices, pages). They answer in the same shape as the old
server-backed calls, so the chart composables did not change.

The query grammar is the backend's own (`__get_where_clause` in
`backend/resslab_hub/utils/common.py`), so the string that used to go to the
API now runs in the browser: clauses joined by `;`, `key:expression`, a
leading `!` negates, `,` separates a set of values, a leading `=` is an
exact match, `<<` is an inclusive range, a leading `<` or `>` a numeric
compare.

## One filter state for everything

`useDashboard()` owns the searches and derives the `query` string. It
provides it with `provide`/`inject` (`dashboardQueryKey`) rather than props,
so a filter tick does not diff the props of every chart. The query is also
mirrored into the URL with `router.replace` (not `push`: the back button
must not walk through every drag).

The open detail drawer is in the URL too, as `?specimen=<id>` (#417), so the
address bar is always a link you can share. `useDashboard()` looks the id up
in the whole dataset, not in the filtered table, so a link opens its specimen
whatever filters it carries. An unknown id shows a notice and leaves the URL.
The drawer's share button copies a link with only `specimen`, without the
filters. The map's "View experimental data" uses the same key.

During a brush drag a second path takes over, outside Vue's reactivity:
`composables/crossfilterBus.ts` is a plain publish/subscribe. The dragged
chart calls `publishLive(query)` on each frame (coalesced to one call per
animation frame), subscribers repaint imperatively, the table stays out of
it. On pointer up the chart commits once through the normal reactive path
and calls `publishSettle()`, so reactivity reconciles exactly once.
`isBrushDragging` (`composables/interactionState.ts`) is the flag every chart
reads to freeze its value axis mid-drag.

## Charts

`composables/useEChart.ts` owns the ECharts instance and exposes
`render(option)`; the option is not a reactive prop (vue-echarts would diff
it on every tick). `render` is called from a guarded `watch` for normal
changes and straight from the bus during a drag.
`composables/frameScheduler.ts` spreads a burst of updates over animation
frames, three per frame and latest wins per key, so nine charts settle over
three frames instead of one long task.

Shared chart components live in `components/commons/charts/` (`SingleChart`,
`DoubleChart`, `LegendChart`, the parallel and surface charts) and each cell
is a `ChartCell.vue`. A dashboard does not use them directly: it uses
`DatasetSingleChart`, `DatasetDoubleChart` and `DatasetParallelChart`, which
bind a chart to `useDataset()`. They take the dataset as
`:source="EBF_SOURCE"`, exported by `components/ebf/data.ts` (dataset key,
fetcher, i18n prefix, id and number fields). The tooltip chrome is in `plugins/echarts-theme.ts`,
because a tooltip is raw DOM outside the app's CSS.

### Category colours

Colours for categorical fields come from `utils/categoryColors.ts` through
`useDataset(...).colorFor(field)`: Okabe-Ito slots handed out once per
field, by frequency in the unfiltered dataset (ties alphabetical), so a value
keeps its colour when a filter reshuffles the ranking and the treemap, the
stacked histogram and the brush agree. Past eight values the palette repeats
muted toward grey. `CATEGORY_COLOR_OVERRIDES` (keyed `'<dataset key>:<field>'`)
pins a value whose colour people have learnt.

## The table

`composables/useVirtualRows.ts` windows plain `<tr>` rows of a fixed 38 px
height (`ROW_HEIGHT`), light DOM only, so the window can be re-rendered every
frame of a drag. Below 40 rows (`DISABLE_BELOW`) everything is rendered.
`composables/useColumnWidths.ts` measures the content of each column off
screen (`measureText` on a canvas), fits the columns into the container in
three regimes (everyone at its ideal width, numbers keep theirs and text
shrinks, everyone at its minimum and the table scrolls), and only ever grows
a column for the life of the component, so filtering never makes columns
jitter.

## The filter rail

`useAutoFilters()` joins the data dictionary (`GET /dictionary`: type,
symbol, unit, description per column) with the cached rows and produces a
ready-to-render list of typed filters. Adding a column to a dictionary is
enough for its filter to appear. `utils/filterProfile.ts` scans the dataset
once per database and memoises the profile. That scan is O(rows x fields),
and the rail is a closed drawer when the rows land, so it runs through
`whenIdle` (`utils/idle.ts`) once the table and the charts have painted;
until then the rail says it is loading and the active chips use their i18n
labels.

The list is folded by scientific category (`utils/fieldGroups.ts`, the
dictionary's `group` column first, [variable-categories.md](variable-categories.md)).
Rendered by `AutoFilterRail.vue` and `AutoFilterRow.vue`; the widgets are in
`components/commons/sliders/`: `DistributionBrush` (a histogram with a
context and focus brush, dragged through a pointer overlay rather than
ECharts' `dataZoom`) and `DateDistributionBrush`.

## The drawer

`components/commons/CommonDetail.vue` is the detail drawer every
`*Detail.vue` wraps. It takes `carouselItems: DetailCarouselItem[][]` (each
item: title, axis labels and bounds, and either the series or a promise of
it) and, with `databaseId` and `record`, appends every recorded property of
the specimen grouped by category (`GroupedProperties.vue`,
`PropertyItem.vue`). The ductile-fracture figures and the SEM viewer
([sem-images.md](sem-images.md)) plug in there too.

## The home page numbers

`assets/kpi-snapshot.json` is a committed snapshot of the home KPIs and the
sidebar badges (counts and distinct sources per database, universities,
users), so the first paint has numbers before the live fetch
(`stores/counts.ts`) replaces them. `pnpm run kpi:snapshot`
(`frontend/scripts/update-kpi-snapshot.mjs`) refreshes it from the `/distinct`
endpoints of production by default, and writes nothing if one call fails.
Run it by hand now and then; it is not in CI.

## The backend side

Three pieces in `backend/resslab_hub/` make "load everything once" cheap:

- **Response cache** (`utils/caching.py`, `HTTPCacheMiddleware`). Every JSON
  `GET` carries a process-wide data version as a weak ETag plus
  `Cache-Control: public, max-age=<CACHE_MAX_AGE>`; a matching
  `If-None-Match` answers `304` before touching the database. Server side the
  rendered bytes of each URL are kept in an in-process LRU (64 MiB total,
  8 MiB per entry), so only the first request per URL after a start or an
  upload pays the SQL. `bump_data_version()` (called by `/upload`)
  invalidates everything. Per process on purpose, no shared store. Paths
  under `/auth`, `/contributions`, `/analytics`, the health checks and the
  docs are excluded.
- **Warmup** (`utils/warmup.py`). At startup the app renders its hot URLs
  through its own ASGI stack (`/dictionary`, the first page of every
  database at size 1000, the two `/distinct` calls), which fills the cache
  and Postgres' buffers, then repeats every `0.8 × CACHE_MAX_AGE` before the
  entries expire, bypassing the cache lookup with a per-process header.
  `GET /readyz` answers `503` until the first pass is done, so a cold pod
  gets no traffic.
- **Pagination**: the list endpoints answer `ExtendedPage[Model]`
  (fastapi-pagination), which `fetchAllPages` drains.

`CACHE_MAX_AGE` defaults to 3600 (`config.py`). Set it to 0 locally to turn
the cache and the warmup off while you work on data.

## Measuring it at 10 000 rows

Our biggest real table has 371 rows (HSS columns), so nothing above tells you
where this design starts to hurt. `frontend/scripts/bench-dashboard.mjs` drives
a real Chrome through the four things a user does and prints the numbers. It
measures, it does not judge: read the numbers before changing anything (#354).

### Make the rows

`backend/benchmark/bootstrap_rows.py` blows a real database up to any size by
resampling its own CSV. Each column draws from its own real column, so the
distinct values, their frequencies and the share of empty cells stay real;
only the combinations are new. Numbers get a +/- 5 % jitter, else 10 000 rows
would sit on 300 distinct values and the histograms and range filters would
look cheaper than they are. Types come from the folder's
`*_data_dictionary.csv`, so it needs no database and no settings.

```bash
cd backend
make bench-rows                                  # braces, 10 000 rows
make bench-rows BENCH_DB=connections             # the wide one, 153 columns
make bench-rows BENCH_ROWS=300 BENCH_OUT=.benchmark-tmp-300   # the control
```

The real rows are kept, first and unchanged, and the synthetic ones are added
on top (294 real braces + 9706 generated). That is not politeness: the uploader
deletes every id that is not in the CSV, and a brace that still has
`brace_displacement` rows cannot be deleted, so a file of synthetic ids only
fails on the foreign key and rolls the whole upload back. Keeping the ids also
keeps the real specimens explorable, curves included.

Then load it, into **a throwaway database only** (a worktree clone;
`make db-branch` puts the real data back afterwards):

```bash
uv run python -m resslab_hub.data.uploader brace \
  .benchmark-tmp/braces/steel_braces.csv
```

The main-table uploader merges row by row: about 16 s for 10 000 braces, 32 s
for 10 000 connections. No time-series files are generated for the synthetic
rows, so their `*_count` flags stay empty and only the real specimens have
curves in the drawer.

### Run it

Needs a dev stack up (the worktree's tmux panes, or `make dev-all`) and Chrome.

```bash
cd frontend
pnpm run bench:dashboard -- --url http://localhost:19006 --db braces --runs 5
pnpm run bench:dashboard -- --db connections --runs 5 --cpu 4
pnpm run bench:dashboard -- --db braces --baseline .bench/braces-300.json
```

The `--` is optional here (pnpm forwards it, npm eats it, the script skips it
either way). `--cpu 4` throttles the CPU fourfold, roughly a laptop on battery.
`--baseline` adds a delta column, for the 300-row control and for a rerun
after a change. Raw entries land in `frontend/.bench/` (gitignored). Run 1 is
printed apart: Vite's module cache is cold on it.

The four scenarios:

- **Load** — navigate, wait for the table's rows, then for a quiet main thread.
- **Filter** — tick the first option of the rail's widest categorical filter,
  then untick it. The second click shows what the query memo buys.
- **Brush** — drag a `DistributionBrush` from 30 % to 70 % in 60 steps over
  about a second, recording every animation frame.
- **Sort** — click a numeric column header three times (asc, desc, off).

### Reading the numbers

Everything comes from the browser: the paint entries, Event Timing, the
long-task observer, and the `rh:` marks `src/utils/perf.ts` writes inside the
app (the fetch, the rail profile, each ECharts repaint, each table window,
each filter commit, each drag frame). Those marks are always on, in production
too: a `performance.mark` costs microseconds and makes a Performance panel
profile readable.

Four things are worth knowing before you blame the wrong piece:

- **The load is mostly the fetch.** `fetchAllPages` drains the list endpoint
  1000 rows at a time, the pages after the first in parallel. The table splits
  the fetch from the network span inside it.
- **The filter rail's counts are computed once**, by `profileColumns` over the
  unfiltered rows. That pass is O(rows x fields) and it is the one to watch on
  connections (153 columns). A filter toggle never redoes it, the option
  counts you see are the unfiltered ones, and it runs at idle after the table
  has painted, so it no longer sits between the data and the first rows.
- **The table is already windowed** (`useVirtualRows`), so its cost follows the
  page size, not the row count. What follows the row count is the filter and
  the sort behind it.
- **A drag never touches Vue.** The frames come off `crossfilterBus`, one per
  animation frame whatever the pointer does, so the number to read is the cost
  of one frame (`rh:brush:live`), not the number of pointer moves.

### The numbers, 2026-09-08

Linux, Chrome headless shell 1228, 1440x900, no CPU throttle, 4 runs each
(median of runs 2 to 4, run 1 excluded because Vite's module cache is cold).
Braces is 71 columns, connections 153. Milliseconds, from navigation start for
the load rows and from the click for the rest.

| | braces 300 | braces 10 000 | connections 300 | connections 10 000 |
|---|---|---|---|---|
| First contentful paint | 284 | 296 | 256 | 252 |
| Dataset fetch | 203 | 577 | 244 | 898 |
| Filter rail profile | 18 | 185 | 27 | 766 |
| Table has rows | 899 | 1436 | 1005 | 2526 |
| Interactive | 978 | 1513 | 1005 | 2526 |
| Total blocking time | 318 | 419 | 314 | 1234 |
| Longest task | 230 | 279 | 272 | **1016** |
| Filter: charts settled | 85 | 174 | 124 | 205 |
| Filter: table updated | 36 | 76 | 51 | 88 |
| Brush: median live frame | 11 | 19 | 23 | **52** |
| Brush: longest frame | 53 | 74 | 58 | **167** |
| Sort: table sorted | 32 | 32 | 37 | 24 |

What the numbers say, before anyone changes code:

- **Connections at 10 000 rows is the one that hurts.** 2.5 s before the table
  has rows, and a single 1016 ms task inside that. Braces at the same size stays
  at 1.5 s, so it is the 153 columns, not the rows alone.
- **The filter rail profile is the cost that grows fastest**: 27 ms to 766 ms on
  connections, 28 times more for 33 times the rows. It is O(rows x fields) and
  it runs once, inside the load, before any filter can be used.
- **A drag on connections drops frames.** One live frame costs 52 ms against a
  16.7 ms budget, so roughly two frames in three are lost, and the worst frame
  is 167 ms. Braces stays near the budget at 19 ms.
- **Sorting does not care about the row count at all** (24 to 37 ms
  everywhere). Neither does first paint: the shell is up in about 260 ms while
  the data is still loading.
- **A filter toggle stays usable everywhere**: input delay is about 1 ms, the
  table follows in under 90 ms, the charts in about 200 ms.

So the load is the problem, and inside it the ten sequential page requests, the
rail profile and whatever makes that one 1 s task on connections. The drag is
second. The table, the sort and the paint are fine. Nothing here is a decision
yet.

The browser numbers above come from a stub server feeding the bootstrapped rows
to the real app. Everything above the HTTP layer is the real dashboard, so the
browser time is real, but the fetch row is a floor. The backend was measured
separately, against a real Postgres holding the same 10 000 rows, in dev mode
(`CACHE_MAX_AGE=0`, so every request pays the SQL):

| | braces 10 000 | connections 10 000 |
|---|---|---|
| The 10 pages `fetchAllPages` drains | 1467 ms | 2981 ms |
| One page, 1000 rows | 147 ms | 298 ms |
| Sent over the wire, gzipped | 2195 KiB | 6364 KiB |
| One page before gzip | 1564 KiB | 3081 KiB |

So the load is worse than the browser table alone suggests: on connections the
server side is about 3 s of the wait, ahead of everything the browser then does
with it. Ten sequential requests is the shape to question first, not the SQL
behind one of them. In production the response cache serves the second visitor
from memory, but the first one still pays this.

### After the two cheap changes, same day

Two things followed straight from the table above: the pages after the first
are fetched together, and the rail profile waits for idle instead of running
between the data and the table. Same stub, same rows, connections at 10 000,
median of runs 2 to 4:

| | before | after |
|---|---|---|
| Table has rows | 2526 ms | 1336 ms |
| Interactive (main thread quiet) | 2526 ms | 2289 ms |
| Longest task | 1016 ms | 686 ms |
| Total blocking time | 1234 ms | 915 ms |
| Dataset fetch | 898 ms | 695 ms |

The table shows its rows 1.2 s sooner. The main thread goes quiet only a
little sooner, because the profile still costs its 0.7 s, just after the
rows are on screen instead of before. The fetch gain is small here because the
stub is one Node process; against the real backend and its seven replicas the
parallel pages should count for more, and that run is the one to record.

The two heavier items, one bulk endpoint per database and a shared filtered set
across charts during a drag, are parked in their own issue until a database
actually grows past a few thousand rows.

One more caveat:
- The second measured click ticks a *different* value rather than unticking the
  first. Clicking an option twice does not clear it today: the filter applies
  and the chip shows, but the box never reads back as checked, so the second
  click re-sends the same query and nothing recomputes. Seen on the braces rail
  with a real investigator name, it needs its own issue and is not a
  benchmarking artefact.

## What a new tab must implement

- A `fetchAll()` that drains its list endpoint with `fetchAllPages`, and a
  stable dataset key for `useDataset` and `useAutoFilters`.
- A dashboard built from `DashboardShell`, its charts through `useEChart` and
  `ChartCell`, the shared table, a `*Detail.vue` wrapping `CommonDetail`.
- A `group` for every column of its dictionary (or a pattern in
  `fieldGroups.ts`), else `fieldGroups.spec.ts` fails.

The rest (backend, uploader, validator, i18n, map, home) is in
[adding-a-new-tab.md](adding-a-new-tab.md).
