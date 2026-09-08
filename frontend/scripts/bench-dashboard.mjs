#!/usr/bin/env node
/* eslint-env node */
/**
 * Dashboard benchmark (#354): what a database tab costs in the browser.
 *
 * Our biggest real table has 371 rows, so nobody has ever seen where the
 * exploration engine starts to hurt. This drives a real Chrome through the
 * four things a user actually does, at whatever row count the database holds,
 * and prints the numbers as a markdown table.
 *
 *   A. load        first paint, the fetch, the filter-rail profile, the charts,
 *                  the table, and when the main thread goes quiet
 *   B. filter      one categorical option ticked, then unticked
 *   C. brush       one drag across a distribution brush, frame by frame
 *   D. sort        one column header clicked, asc then desc then off
 *
 * It measures, it does not judge. Every number comes from the browser itself:
 * the paint entries, Event Timing, the long-task observer, and the `rh:` marks
 * `src/utils/perf.ts` writes inside the app.
 *
 * Needs a dev stack already running (the worktree tmux panes, or `make
 * dev-all`), and Chrome on the machine.
 *
 *   pnpm run bench:dashboard -- --url http://localhost:19006 --db braces
 *   pnpm run bench:dashboard -- --db connections --runs 5 --cpu 4
 *   pnpm run bench:dashboard -- --db braces --baseline .bench/braces-300.json
 */
import { chromium } from 'playwright-core'
import { mkdir, writeFile, readFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'

const DATABASES = {
  braces: '/braces/database',
  columns: '/columns/database',
  connections: '/connections/database',
  'hss-columns': '/hss-columns/database',
  ebf: '/eccentric-braced-frames/database'
}

// Long enough that a late chart repaint lands inside the window, short enough
// that four scenarios still run in a minute.
const QUIET_MS = 600
const SETTLE_MS = 400

function parseArgs(argv) {
  const args = {
    url: 'http://localhost:19006',
    db: 'braces',
    runs: 5,
    cpu: 1,
    viewport: '1440x900',
    headless: false,
    executable: undefined,
    out: undefined,
    baseline: undefined
  }
  for (let i = 0; i < argv.length; i++) {
    // `pnpm run x -- --db braces` forwards the `--` itself, npm swallows it.
    // Skip it so the line works whichever the reader has in their fingers.
    if (argv[i] === '--') continue
    const key = argv[i].replace(/^--/, '')
    if (key === 'headless') args.headless = true
    else if (key in args) args[key] = argv[++i]
    else {
      throw new Error(
        `unknown option: ${argv[i]}\nknown: ${Object.keys(args)
          .map((name) => '--' + name)
          .join(' ')}`
      )
    }
  }
  args.runs = Number(args.runs)
  args.cpu = Number(args.cpu)
  if (!DATABASES[args.db]) {
    throw new Error(`--db must be one of ${Object.keys(DATABASES).join(', ')}`)
  }
  const [width, height] = args.viewport.split('x').map(Number)
  args.viewportSize = { width, height }
  args.out ??= `.bench/${args.db}-${new Date()
    .toISOString()
    .slice(0, 19)
    .replace(/[:T]/g, '')}.json`
  return args
}

/**
 * Runs in the page before anything else: buffered observers for everything the
 * browser reports on its own, plus a frame ticker we switch on for the drag.
 */
function installProbes() {
  const store = {
    longtasks: [],
    lcp: [],
    events: [],
    frames: [],
    recordingFrames: false
  }
  window.__bench = store
  // The resource buffer holds 250 entries by default, and Vite's dev server
  // serves hundreds of module files before the first API call. Without this
  // the page requests fall off the end and "of which network" reads empty.
  try {
    performance.setResourceTimingBufferSize(5000)
  } catch {
    // Older browsers: the column just stays empty.
  }

  const observe = (type, sink, extra = {}) => {
    try {
      new PerformanceObserver((list) =>
        sink.push(...list.getEntries().map((e) => e.toJSON()))
      ).observe({ type, buffered: true, ...extra })
    } catch {
      // An unsupported entry type just means one column of the table is empty.
    }
  }
  observe('longtask', store.longtasks)
  observe('largest-contentful-paint', store.lcp)
  // 16 ms is one frame: below that an interaction is not worth a row.
  observe('event', store.events, { durationThreshold: 16 })

  const tick = () => {
    if (!store.recordingFrames) return
    store.frames.push(performance.now())
    requestAnimationFrame(tick)
  }
  store.startFrames = () => {
    store.frames = []
    store.recordingFrames = true
    requestAnimationFrame(tick)
  }
  store.stopFrames = () => {
    store.recordingFrames = false
  }
}

/**
 * Everything the browser and the app recorded since the last reset.
 *
 * Runs in the page: the `rh:` marks with their `detail` (the entry objects
 * themselves, `toJSON` drops `detail`), the paint entries, the observers'
 * buffers, and the list-endpoint requests.
 */
const collect = (page, pattern) =>
  page.evaluate((listPattern) => {
    const ours = [
      ...performance.getEntriesByType('mark'),
      ...performance.getEntriesByType('measure')
    ]
      .filter((entry) => entry.name.startsWith('rh:'))
      .map((entry) => ({
        name: entry.name.slice(3),
        start: entry.startTime,
        duration: entry.duration || 0,
        detail: entry.detail ?? null,
        type: entry.entryType
      }))
      .sort((a, b) => a.start - b.start)

    const requests = performance
      .getEntriesByType('resource')
      .filter((entry) => new RegExp(listPattern).test(entry.name))
      .map((entry) => ({
        name: entry.name,
        start: entry.startTime,
        duration: entry.duration,
        transferSize: entry.transferSize,
        decodedBodySize: entry.decodedBodySize
      }))

    return {
      marks: ours,
      resources: requests,
      paint: performance
        .getEntriesByType('paint')
        .map((e) => ({ name: e.name, start: e.startTime })),
      lcp: window.__bench.lcp.length
        ? window.__bench.lcp[window.__bench.lcp.length - 1].startTime
        : null,
      longtasks: window.__bench.longtasks.map((t) => ({
        start: t.startTime,
        duration: t.duration
      })),
      events: window.__bench.events.map((e) => ({
        name: e.name,
        start: e.startTime,
        duration: e.duration,
        processingStart: e.processingStart,
        processingEnd: e.processingEnd
      })),
      frames: window.__bench.frames.slice(),
      now: performance.now()
    }
  }, pattern)

const resetProbes = (page) =>
  page.evaluate(() => {
    window.__bench.longtasks.length = 0
    window.__bench.events.length = 0
    window.__bench.lcp.length = 0
    window.__bench.frames.length = 0
    performance.clearMarks?.()
    performance.clearMeasures?.()
  })

/**
 * Wait until no long task has ended for `quiet` ms (or `budget` runs out).
 *
 * The floor matters: an interaction whose tail is a plain `setTimeout` never
 * produces a long task, so without it the collect would run before the last
 * mark is written and the metric would read as missing rather than as fast.
 */
async function waitForQuiet(page, quiet = QUIET_MS, budget = 60_000, floor = 0) {
  if (floor) await page.waitForTimeout(floor)
  await page.waitForFunction(
    ([quietMs]) => {
      const tasks = window.__bench.longtasks
      const last = tasks.length ? tasks[tasks.length - 1] : null
      const end = last ? last.startTime + last.duration : 0
      return performance.now() - end > quietMs
    },
    [quiet],
    { timeout: budget, polling: 100 }
  )
}

const marksNamed = (marks, name) => marks.filter((m) => m.name === name)
const firstMark = (marks, name) => marksNamed(marks, name)[0] ?? null
const lastMark = (marks, name) => marksNamed(marks, name).pop() ?? null
const measure = (marks, name) => marksNamed(marks, name).find((m) => m.type === 'measure') ?? null

const median = (xs) => {
  if (!xs.length) return null
  const s = [...xs].sort((a, b) => a - b)
  const mid = s.length >> 1
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2
}
const max = (xs) => (xs.length ? Math.max(...xs) : null)

/** Long tasks that overlap a window, and the total blocking time in it. */
function blocking(longtasks, from, to = Infinity) {
  const inside = longtasks.filter((t) => t.start + t.duration > from && t.start < to)
  return {
    count: inside.length,
    longest: max(inside.map((t) => t.duration)),
    blocking: inside.reduce((sum, t) => sum + Math.max(0, t.duration - 50), 0)
  }
}

/** The Event Timing entry for the click we just made, if the browser kept one. */
function clickTiming(events, after) {
  const hit = events.find((e) => e.start >= after - 5 && /click|pointerdown|pointerup/.test(e.name))
  if (!hit) return { inputDelay: null, handler: null, nextPaint: null }
  return {
    inputDelay: hit.processingStart - hit.start,
    handler: hit.processingEnd - hit.processingStart,
    nextPaint: hit.duration
  }
}

async function scenarioLoad(page, args) {
  const path = DATABASES[args.db]
  await page.goto(args.url + path, { waitUntil: 'commit' })
  // The table writing its rows is the first moment the page is usable.
  await page.waitForFunction(
    () => performance.getEntriesByType('mark').some((m) => m.name === 'rh:table:items'),
    undefined,
    { timeout: 120_000 }
  )
  await waitForQuiet(page)

  const data = await collect(page, `/api/${args.db.replace('-', '.')}|page=`)
  const { marks, longtasks } = data
  const fetchMeasure = measure(marks, 'dataset:fetch')
  const profileMeasure = measure(marks, 'filters:profile')
  const renders = marksNamed(marks, 'chart:render')
  const table = firstMark(marks, 'table:items')
  const fetchEnd = firstMark(marks, 'dataset:fetch:end')
  const pages = data.resources.filter((r) => /page=/.test(r.name))
  const lastTask = longtasks.length ? longtasks[longtasks.length - 1] : null

  const heap = await page.evaluate(() => performance.memory?.usedJSHeapSize ?? null)

  return {
    fcp: data.paint.find((p) => p.name === 'first-contentful-paint')?.start ?? null,
    lcp: data.lcp,
    fetch: fetchMeasure?.duration ?? null,
    rows: fetchEnd?.detail?.rows ?? null,
    pageRequests: pages.length,
    networkMs: pages.reduce((sum, r) => sum + r.duration, 0) || null,
    transferKb: pages.reduce((sum, r) => sum + (r.transferSize || 0), 0) / 1024 || null,
    decodedKb: pages.reduce((sum, r) => sum + (r.decodedBodySize || 0), 0) / 1024 || null,
    railProfile: profileMeasure?.duration ?? null,
    railFields: lastMark(marks, 'filters:profile:end')?.detail?.fields ?? null,
    firstChart: renders[0]?.start ?? null,
    lastChart: renders.length ? renders[renders.length - 1].start : null,
    chartRenders: renders.length,
    tableItems: table?.start ?? null,
    interactive:
      Math.max(lastTask ? lastTask.start + lastTask.duration : 0, table?.start ?? 0) || null,
    ...blocking(longtasks, 0),
    heapMb: heap ? heap / 1024 / 1024 : null
  }
}

/**
 * Open the rail the way a person does before filtering anything.
 *
 * Groups start folded except the identification one, and every filter row keeps
 * its body behind a `v-if` (`AutoFilterRow.vue`), so nothing is clickable until
 * the group and then the row are opened. This is setup, not measurement: it
 * runs before the probes are reset.
 */
async function openRail(page) {
  // The rail is a drawer (`.filters-overlay` in DashboardShell.vue), parked off
  // screen until the toolbar's "All filters" button opens it. Without this the
  // options are in the DOM at a negative x and nothing can be clicked.
  const trigger = page.locator('.dash-filters-trigger')
  if ((await trigger.count()) && !(await page.locator('.filters-overlay.open').count())) {
    await trigger.click()
    await page.waitForTimeout(400)
  }
  await page.evaluate(async () => {
    for (const head of document.querySelectorAll('.afr-group-head')) {
      if (!head.parentElement?.querySelector('.afr-row')) {
        head.click()
        await new Promise((resolve) => setTimeout(resolve, 30))
      }
    }
  })
  await page.waitForTimeout(200)
}

/**
 * Put the drawer back, so the charts underneath are reachable again.
 *
 * The rail's own close button, not the scrim: clicking the scrim does not close
 * this drawer, and while it is open the body cannot scroll, so the histogram's
 * brush stays below the fold and a drag lands on nothing.
 */
async function closeRail(page) {
  const close = page.locator('.dash-filters-collapse-btn').first()
  if (await close.count()) {
    await close.click()
    await page.waitForTimeout(400)
  }
}

/**
 * Open filter rows until we find the widest categorical one, then leave that one
 * open. Which field it is barely changes the cost (the pass is over the rows,
 * not the options) but the widest is the honest choice, and the report names it.
 */
async function openWidestCategorical(page, probe = 16) {
  return page.evaluate(async (limit) => {
    const rail = document.querySelector('.filters-overlay') ?? document
    const rows = [...rail.querySelectorAll('.afr-row')].slice(0, limit)
    let best = null
    for (const row of rows) {
      const head = row.querySelector('.afr-head')
      if (!head) continue
      head.click()
      await new Promise((resolve) => setTimeout(resolve, 60))
      const all = [...row.querySelectorAll('.afr-option')]
      // Skip values holding a comma: it is the query grammar's set separator,
      // so such a value round-trips as two and the option never reads back as
      // selected (see the note in docs/dashboard-architecture.md). Measuring a
      // toggle that cannot be untoggled would measure the wrong thing.
      // Skip values holding a comma: it is the query grammar's set separator,
      // so such a value round-trips as two. Two plain values are needed, one
      // per measured click.
      const plain = all
        .map((option, i) => [i, option.querySelector('.afr-option-value')?.textContent ?? ''])
        .filter(([, text]) => text && !text.includes(','))
        .map(([i]) => i)
      head.click()
      await new Promise((resolve) => setTimeout(resolve, 20))
      if (all.length >= 2 && plain.length >= 2 && (!best || all.length > best.options)) {
        best = {
          options: all.length,
          index: plain[0],
          next: plain[1],
          label: head.innerText.trim().slice(0, 40),
          row
        }
      }
    }
    if (!best) return null
    best.row.querySelector('.afr-head').click()
    await new Promise((resolve) => setTimeout(resolve, 150))
    // The rail is a tall overlay with its own scrollbar: an opened row can sit
    // well below the window, and Playwright refuses to click what it cannot see.
    best.row.querySelectorAll('.afr-option')[best.index]?.scrollIntoView({ block: 'center' })
    await new Promise((resolve) => setTimeout(resolve, 150))
    return { field: best.label, options: best.options, index: best.index, next: best.next }
  }, probe)
}

async function scenarioFilter(page) {
  await openRail(page)
  const opened = await openWidestCategorical(page)
  if (!opened) return { skipped: 'no categorical filter option in the rail' }
  const options = page.locator('.filters-overlay .afr-body .afr-option')
  const targets = [
    await options.nth(opened.index).elementHandle(),
    await options.nth(opened.next).elementHandle()
  ]
  if (!targets[0] || !targets[1]) {
    return { skipped: 'no categorical filter option in the rail' }
  }
  const values = []
  for (const handle of targets) {
    values.push(
      await handle.evaluate(
        (node) => node.querySelector('.afr-option-value')?.textContent?.trim() ?? '?'
      )
    )
  }

  // Two different values, not a tick then an untick: clicking the same option
  // again does not clear it today (the box never reads back as checked, see the
  // note in docs/dashboard-architecture.md), so the second click would measure
  // a no-op. Two values still exercise the query memo on a warm dataset.
  const clicks = []
  for (const [index, pass] of ['first value', 'second value'].entries()) {
    const target = targets[index]
    await target.evaluate((node) => node.scrollIntoView({ block: 'center' }))
    await page.waitForTimeout(100)
    await resetProbes(page)
    const before = await page.evaluate(() => performance.now())
    await target.click({ timeout: 10_000 })
    await waitForQuiet(page, QUIET_MS, 30_000, SETTLE_MS)
    const data = await collect(page, 'page=')
    const commit = firstMark(data.marks, 'query:commit')
    const renders = marksNamed(data.marks, 'chart:render')
    const table = firstMark(data.marks, 'table:items')
    const from = commit?.start ?? before
    clicks.push({
      pass,
      ...clickTiming(data.events, before),
      chartsSettled: renders.length ? renders[renders.length - 1].start - from : null,
      chartRenders: renders.length,
      tableUpdated: table ? table.start - from : null,
      ...blocking(data.longtasks, from)
    })
  }
  // Leave the page as we found it: the drawer covers the charts, and the brush
  // scenario that follows would drag the scrim instead of the histogram.
  await closeRail(page)
  return {
    field: opened.field,
    values,
    options: opened.options,
    first: clicks[0],
    second: clicks[1]
  }
}

async function scenarioBrush(page) {
  const overlay = page.locator('.dist-brush__overlay').first()
  if (!(await overlay.count())) return { skipped: 'no distribution brush in the rail' }
  await overlay.scrollIntoViewIfNeeded()
  await page.waitForTimeout(200)
  const box = await overlay.boundingBox()
  if (!box) return { skipped: 'the brush is not visible' }
  const viewport = page.viewportSize()
  if (viewport && (box.y < 0 || box.y + box.height > viewport.height)) {
    return { skipped: 'the brush is off screen even after scrolling' }
  }

  await resetProbes(page)
  const y = box.y + box.height / 2
  await page.mouse.move(box.x + box.width * 0.3, y)
  await page.evaluate(() => window.__bench.startFrames())
  await page.mouse.down()
  // 60 steps over ~1 s: a real drag, slow enough that each frame has work.
  await page.mouse.move(box.x + box.width * 0.7, y, { steps: 60 })
  const upAt = await page.evaluate(() => performance.now())
  await page.mouse.up()
  await waitForQuiet(page, QUIET_MS, 30_000, SETTLE_MS)
  await page.evaluate(() => window.__bench.stopFrames())

  const data = await collect(page, 'page=')
  const intervals = data.frames.slice(1).map((t, i) => t - data.frames[i])
  const live = marksNamed(data.marks, 'brush:live').filter((m) => m.type === 'measure')
  const renders = marksNamed(data.marks, 'chart:render')
  const settleRenders = renders.filter((r) => r.start >= upAt)
  const table = data.marks.find((m) => m.name === 'table:items' && m.start >= upAt)

  return {
    frames: data.frames.length,
    medianFrameMs: median(intervals),
    longestFrameMs: max(intervals),
    droppedFrames: intervals.filter((ms) => ms > 33).length,
    liveFrames: live.length,
    medianLiveMs: median(live.map((m) => m.duration)),
    maxLiveMs: max(live.map((m) => m.duration)),
    liveRenders: renders.filter((r) => r.start < upAt).length,
    charts: lastMark(data.marks, 'brush:live:end')?.detail?.charts ?? null,
    settleChartsMs: settleRenders.length
      ? settleRenders[settleRenders.length - 1].start - upAt
      : null,
    settleTableMs: table ? table.start - upAt : null,
    ...blocking(data.longtasks, upAt)
  }
}

async function scenarioSort(page) {
  const header = page
    .locator('th')
    .filter({ hasNot: page.locator('input') })
    .nth(1)
  if (!(await header.count())) return { skipped: 'no sortable column header' }

  const clicks = []
  for (const pass of ['asc', 'desc', 'off']) {
    await resetProbes(page)
    const before = await page.evaluate(() => performance.now())
    await header.click()
    await waitForQuiet(page, QUIET_MS, 30_000, SETTLE_MS)
    const data = await collect(page, 'page=')
    const table = firstMark(data.marks, 'table:items')
    clicks.push({
      pass,
      ...clickTiming(data.events, before),
      tableUpdated: table ? table.start - before : null,
      ...blocking(data.longtasks, before)
    })
  }
  const column = await header.textContent()
  return { column: (column ?? '').trim().slice(0, 30), clicks }
}

async function runOnce(browser, args) {
  const context = await browser.newContext({ viewport: args.viewportSize })
  const page = await context.newPage()
  await page.addInitScript(installProbes)
  if (args.cpu > 1) {
    const session = await context.newCDPSession(page)
    await session.send('Emulation.setCPUThrottlingRate', { rate: args.cpu })
  }
  try {
    const load = await scenarioLoad(page, args)
    await page.waitForTimeout(SETTLE_MS)
    const filter = await scenarioFilter(page)
    await page.waitForTimeout(SETTLE_MS)
    const brush = await scenarioBrush(page)
    await page.waitForTimeout(SETTLE_MS)
    const sort = await scenarioSort(page)
    return { load, filter, brush, sort }
  } finally {
    await context.close()
  }
}

const ROWS = [
  ['Load', 'First contentful paint', (r) => r.load.fcp],
  ['Load', 'Largest contentful paint', (r) => r.load.lcp],
  ['Load', 'Dataset fetch (10 pages)', (r) => r.load.fetch],
  ['Load', '  of which network', (r) => r.load.networkMs],
  ['Load', 'Filter rail profile', (r) => r.load.railProfile],
  ['Load', 'First chart painted', (r) => r.load.firstChart],
  ['Load', 'Last chart painted', (r) => r.load.lastChart],
  ['Load', 'Table has rows', (r) => r.load.tableItems],
  ['Load', 'Interactive (main thread quiet)', (r) => r.load.interactive],
  ['Load', 'Total blocking time', (r) => r.load.blocking],
  ['Load', 'Longest task', (r) => r.load.longest],
  ['Filter', 'Input delay', (r) => r.filter.first?.inputDelay],
  ['Filter', 'Charts settled', (r) => r.filter.first?.chartsSettled],
  ['Filter', 'Table updated', (r) => r.filter.first?.tableUpdated],
  ['Filter', 'Longest task', (r) => r.filter.first?.longest],
  ['Filter', 'Table updated, second value', (r) => r.filter.second?.tableUpdated],
  ['Brush', 'Median frame', (r) => r.brush.medianFrameMs],
  ['Brush', 'Longest frame', (r) => r.brush.longestFrameMs],
  ['Brush', 'Median live frame cost', (r) => r.brush.medianLiveMs],
  ['Brush', 'Max live frame cost', (r) => r.brush.maxLiveMs],
  ['Brush', 'Settle: charts', (r) => r.brush.settleChartsMs],
  ['Brush', 'Settle: table', (r) => r.brush.settleTableMs],
  ['Sort', 'Input delay', (r) => r.sort.clicks?.[0]?.inputDelay],
  ['Sort', 'Table sorted (asc)', (r) => r.sort.clicks?.[0]?.tableUpdated],
  ['Sort', 'Table sorted (desc)', (r) => r.sort.clicks?.[1]?.tableUpdated],
  ['Sort', 'Longest task', (r) => r.sort.clicks?.[0]?.longest]
]

const fmt = (value) =>
  value === null || value === undefined || Number.isNaN(value) ? '-' : value.toFixed(1)

function table(runs, baseline) {
  const counted = runs.length > 1 ? runs.slice(1) : runs
  const header = ['Scenario', 'Metric', 'Median ms', 'Max ms', 'Run 1 ms']
  if (baseline) header.push('Baseline ms', 'Delta')
  const lines = [`| ${header.join(' | ')} |`, `|${header.map(() => '---').join('|')}|`]
  let group = null
  for (const [scenario, label, pick] of ROWS) {
    const values = counted.map(pick).filter((v) => typeof v === 'number')
    const cells = [
      scenario === group ? '' : scenario,
      label,
      fmt(median(values)),
      fmt(max(values)),
      fmt(pick(runs[0]))
    ]
    if (baseline) {
      const base = median(
        (baseline.runs.length > 1 ? baseline.runs.slice(1) : baseline.runs)
          .map(pick)
          .filter((v) => typeof v === 'number')
      )
      const here = median(values)
      cells.push(fmt(base))
      cells.push(base && here ? `${here > base ? '+' : ''}${(here - base).toFixed(1)}` : '-')
    }
    group = scenario
    lines.push(`| ${cells.join(' | ')} |`)
  }
  return lines.join('\n')
}

async function main() {
  const args = parseArgs(process.argv.slice(2))
  const browser = await chromium.launch(
    args.executable
      ? { executablePath: args.executable, headless: args.headless }
      : { channel: 'chrome', headless: args.headless }
  )
  const runs = []
  try {
    for (let i = 0; i < args.runs; i++) {
      process.stderr.write(`run ${i + 1}/${args.runs}\n`)
      runs.push(await runOnce(browser, args))
    }
  } finally {
    await browser.close()
  }

  const baseline = args.baseline ? JSON.parse(await readFile(resolve(args.baseline), 'utf8')) : null
  const report = {
    database: args.db,
    url: args.url + DATABASES[args.db],
    rows: runs[0].load.rows,
    fields: runs[0].load.railFields,
    runs,
    options: {
      runs: args.runs,
      cpuThrottle: args.cpu,
      viewport: args.viewport,
      headless: args.headless
    },
    chrome: browser.version?.() ?? null,
    at: new Date().toISOString()
  }
  await mkdir(dirname(resolve(args.out)), { recursive: true })
  await writeFile(resolve(args.out), JSON.stringify(report, null, 2))

  console.log(`\n### ${args.db} — ${report.rows ?? '?'} rows, ${report.fields ?? '?'} filters`)
  console.log(
    `${args.runs} runs, CPU ${args.cpu}x, viewport ${args.viewport}. ` +
      `Run 1 is shown apart: the dev server's module cache is cold on it.\n`
  )
  if (runs[0].filter.field) {
    console.log(
      `Filter toggled: \`${runs[0].filter.field}\` ` +
        `(${(runs[0].filter.values ?? []).join(', ')}; ${runs[0].filter.options} options).`
    )
  }
  if (runs[0].sort.column) console.log(`Column sorted: \`${runs[0].sort.column}\`.`)
  for (const scenario of ['filter', 'brush', 'sort']) {
    if (runs[0][scenario].skipped) console.log(`${scenario} skipped: ${runs[0][scenario].skipped}`)
  }
  console.log('')
  console.log(table(runs, baseline))
  console.log(`\nRaw entries per run: ${args.out}`)
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
