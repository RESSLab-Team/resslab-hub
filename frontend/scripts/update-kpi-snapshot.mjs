#!/usr/bin/env node
/* eslint-env node */
/**
 * Refreshes src/assets/kpi-snapshot.json from the live API.
 *
 * The snapshot seeds the homepage KPIs (and sidebar badges) so they render
 * instantly on a cold visit; the live fetch then overwrites them in place.
 * Run occasionally when the numbers feel stale:
 *
 *   npm run kpi:snapshot                             # against production
 *   KPI_API_BASE=http://127.0.0.1:8000 npm run kpi:snapshot   # against local dev
 *
 * Any database endpoint failure aborts without writing (a partial snapshot is
 * worse than a stale one); only the Google-Analytics-backed user count falls
 * back to the previous snapshot's value.
 */
import { readFile, writeFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const BASE = process.env.KPI_API_BASE ?? 'https://resslab-hub.epfl.ch/api'
const OUT = join(dirname(fileURLToPath(import.meta.url)), '../src/assets/kpi-snapshot.json')

// Mirrors fetcherFor / sourcesFetcherFor in src/stores/counts.ts.
const DATABASES = {
  connections: { path: 'connections', sourceField: 'experimental_program' },
  columns: { path: 'columns', sourceField: 'experimental_program' },
  braces: { path: 'braces', sourceField: 'investigator' },
  hss: { path: 'hss-column', sourceField: 'reference' },
  ebf: { path: 'eccentric-braced-frame', sourceField: 'investigator' },
  cyclic: { path: 'materials', sourceField: 'experimental_program' },
  tensile: { path: 'tensile-coupon', sourceField: 'experimental_program' },
  'ductile-fracture': { path: 'ductile-fracture', sourceField: 'experimental_program' },
  residuals: { path: 'residual-stress', sourceField: 'experimental_program' }
}

// Mirrors the university count in src/views/HomeView.vue (6 databases only).
const UNIVERSITY_PATHS = [
  'braces',
  'columns',
  'connections',
  'materials',
  'residual-stress',
  'hss-column'
]

async function get(path) {
  const res = await fetch(BASE + path)
  if (!res.ok) throw new Error(`GET ${path} -> ${res.status}`)
  return res.json()
}

const entries = Object.entries(DATABASES)
const [countValues, sourceValues, universityResponses, usersRaw, previous] = await Promise.all([
  Promise.all(entries.map(([, db]) => get(`/${db.path}/distinct`))),
  Promise.all(entries.map(([, db]) => get(`/${db.path}/distinct?fields=${db.sourceField}`))),
  Promise.all(
    UNIVERSITY_PATHS.map((path) => get(`/${path}/counts?fields=latitude&fields=longitude`))
  ),
  get('/analytics/users').catch(() => -1),
  readFile(OUT, 'utf8')
    .then(JSON.parse)
    .catch(() => ({ users: null }))
])

const snapshot = {
  generatedAt: new Date().toISOString().slice(0, 10),
  counts: Object.fromEntries(entries.map(([id], index) => [id, countValues[index]])),
  sources: Object.fromEntries(entries.map(([id], index) => [id, sourceValues[index]])),
  universities: new Set(universityResponses.flatMap((rows) => rows.map((row) => row.names))).size,
  // -1 means Google Analytics is unavailable — keep the last known value.
  users: usersRaw >= 0 ? usersRaw : previous.users ?? null
}

await writeFile(OUT, JSON.stringify(snapshot, null, 2) + '\n')
console.log(`Wrote ${OUT}`)
console.log(JSON.stringify(snapshot, null, 2))
