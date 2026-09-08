# Dashboard architecture

How a database tab works in the browser, and what the backend does to make
that cheap. Read this before touching a chart, a filter or the table; the
step-by-step for a new tab is in [adding-a-new-tab.md](adding-a-new-tab.md).

## The shape of a tab

One view (`views/EbfView.vue`) renders one dashboard
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
life of the page. `inferFieldTypes` in `utils/queryEngine.ts` types every
column (string, number, date, boolean) from the first non-null value.

The backend routes `/fields`, `/counts`, `/range`, `/matrix` and `/distinct`
still exist on every component router, for API users and for two things in
the app: `/distinct` feeds the sidebar badges and the home KPIs
(`stores/counts.ts`), `/fields` feeds the overview map.

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
is a `ChartCell.vue`. The tooltip chrome is in `plugins/echarts-theme.ts`,
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
once per database and memoises the profile.

The list is folded by scientific category (`utils/fieldGroups.ts`, the
dictionary's `group` column first, [variable-categories.md](variable-categories.md)).
Rendered by `AutoFilterRail.vue` and `AutoFilterRow.vue`; the widgets are in
`components/commons/sliders/`: `DistributionBrush` (a histogram with a
context and focus brush, dragged through a pointer overlay rather than
ECharts' `dataZoom`), `DateDistributionBrush`, and the plain two-handle
`RangeSlider` and `DateRangeSlider`.

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

## What a new tab must implement

- A `fetchAll()` that drains its list endpoint with `fetchAllPages`, and a
  stable dataset key for `useDataset` and `useAutoFilters`.
- A dashboard built from `DashboardShell`, its charts through `useEChart` and
  `ChartCell`, the shared table, a `*Detail.vue` wrapping `CommonDetail`.
- A `group` for every column of its dictionary (or a pattern in
  `fieldGroups.ts`), else `fieldGroups.spec.ts` fails.

The rest (backend, uploader, validator, i18n, map, home) is in
[adding-a-new-tab.md](adding-a-new-tab.md).
