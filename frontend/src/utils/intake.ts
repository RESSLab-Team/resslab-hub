/**
 * Bulk intake for the contribution editor: turn whatever a contributor drops
 * (a folder, a zip, loose CSV files, or a mix) into one plan the store can
 * apply — which file is the primary CSV, which curve file belongs to which
 * experiment and response type, and what could not be placed.
 *
 * The approach follows the BIDS validator and NOMAD: nothing is refused up
 * front, everything is classified locally, and the leftovers are listed for
 * the contributor to resolve. Paths are only used to *recognise* files; the
 * archive the store builds always emits the canonical
 * `<kind.directory>/<id>.csv` layout, so a contributor's folder names never
 * reach the server.
 */

import { readCsvTable, type CsvTable } from '@/utils/csv'
import { fileStemFor, kindsMatchingHeaders, type TimeSeriesKind } from '@/utils/timeseries'

/** One file out of a drop, wherever it came from (disk, folder walk, zip). */
export interface IntakeFile {
  /** Relative path with forward slashes, e.g. `columns/moment_rotation_strong/C1.csv`. */
  path: string
  /** Basename. */
  name: string
  size: number
  text: () => Promise<string>
  /** The file on disk, when there is one (a zip member has none). */
  blob?: File
}

/** Hidden files and folders, editor and OS leftovers: skipped without a word. */
const NOISE_SEGMENT = /^(\.|~\$|__MACOSX$|Thumbs\.db$|desktop\.ini$)/i

export function isNoise(path: string): boolean {
  return path.split('/').some((segment) => NOISE_SEGMENT.test(segment))
}

export function isCsv(path: string): boolean {
  return /\.csv$/i.test(path)
}

export function isZip(path: string): boolean {
  return /\.zip$/i.test(path)
}

function fromFile(file: File, path: string): IntakeFile {
  return {
    path: path.replace(/\\/g, '/').replace(/^\.?\//, ''),
    name: file.name,
    size: file.size,
    text: () => file.text(),
    blob: file
  }
}

// --- Collecting ------------------------------------------------------------

/** Files picked through an `<input type="file">`, `webkitdirectory` or not. */
export function collectFromFileList(files: FileList | File[]): IntakeFile[] {
  return Array.from(files).map((file) => fromFile(file, file.webkitRelativePath || file.name))
}

function readAllEntries(reader: FileSystemDirectoryReader): Promise<FileSystemEntry[]> {
  // Chromium hands back at most 100 entries per call; loop until empty.
  return new Promise((resolve, reject) => {
    const all: FileSystemEntry[] = []
    const step = () =>
      reader.readEntries((batch) => {
        if (batch.length === 0) resolve(all)
        else {
          all.push(...batch)
          step()
        }
      }, reject)
    step()
  })
}

function entryFile(entry: FileSystemFileEntry): Promise<File> {
  return new Promise((resolve, reject) => entry.file(resolve, reject))
}

async function walkEntry(entry: FileSystemEntry, prefix: string, out: IntakeFile[]): Promise<void> {
  const path = prefix ? `${prefix}/${entry.name}` : entry.name
  if (entry.isFile) {
    const file = await entryFile(entry as FileSystemFileEntry)
    out.push(fromFile(file, path))
  } else if (entry.isDirectory) {
    const entries = await readAllEntries((entry as FileSystemDirectoryEntry).createReader())
    for (const child of entries) await walkEntry(child, path, out)
  }
}

/**
 * Files dropped on an element, folders walked recursively. The entries have to
 * be taken from `dataTransfer.items` synchronously — they vanish after the
 * drop event — hence the two phases.
 */
export async function collectFromDataTransfer(transfer: DataTransfer): Promise<IntakeFile[]> {
  const entries: FileSystemEntry[] = []
  const items = Array.from(transfer.items ?? [])
  for (const item of items) {
    if (item.kind !== 'file') continue
    const entry = typeof item.webkitGetAsEntry === 'function' ? item.webkitGetAsEntry() : null
    if (entry) entries.push(entry)
  }
  if (entries.length === 0) return collectFromFileList(transfer.files)
  const out: IntakeFile[] = []
  for (const entry of entries) await walkEntry(entry, '', out)
  return out
}

/** Replace every zip in the list by its members (folders inside kept as paths). */
export async function expandArchives(files: IntakeFile[]): Promise<IntakeFile[]> {
  const out: IntakeFile[] = []
  for (const file of files) {
    if (!isZip(file.path) || !file.blob) {
      out.push(file)
      continue
    }
    // Lazy: jszip is ~100 kB and only needed when an archive is dropped.
    const { default: JSZip } = await import('jszip')
    const zip = await JSZip.loadAsync(await file.blob.arrayBuffer())
    zip.forEach((path, entry) => {
      if (entry.dir) return
      out.push({
        path: path.replace(/^\.?\//, ''),
        name: path.slice(path.lastIndexOf('/') + 1),
        size: 0,
        text: () => entry.async('string')
      })
    })
  }
  return out
}

// --- Classifying -----------------------------------------------------------

/** A curve file placed on an experiment and a response type. */
export interface IntakeMatch {
  file: IntakeFile
  kind: TimeSeriesKind
  /** Specimen id, as written in the primary CSV (the row may be new). */
  id: string
  text: string
  /**
   * Placed by a guess: no folder name told the type, the headers fit several
   * types, and the file went to the only required one (strong axis rather
   * than weak axis). The drop report says so.
   */
  assumed?: boolean
}

/** A curve file the classifier could not place; the contributor decides. */
export interface IntakePending {
  /** Client-only, keys the list. */
  id: number
  file: IntakeFile
  text: string
  /**
   * `orphan`: the response type is known, no experiment has this name;
   * `ambiguous`: several response types share these headers;
   * `unknown`: the headers match no response type of this database;
   * `foreign`: it has an `id` column but not this database's fields — a
   *   primary CSV for another database, most likely.
   */
  reason: 'orphan' | 'ambiguous' | 'unknown' | 'foreign'
  /** The response types still possible (one for an orphan, none for `foreign`). */
  kinds: TimeSeriesKind[]
}

export interface IntakePlan {
  /** The primary CSV, when exactly one was recognised. */
  primary: { file: IntakeFile; table: CsvTable } | null
  /** Several files looked like a primary CSV: none is imported, all are named. */
  primaryCandidates: IntakeFile[]
  matched: IntakeMatch[]
  pending: IntakePending[]
  /** Files that are not CSV (Excel workbooks, MATLAB figures…). */
  skipped: IntakeFile[]
  /** Hidden and system files dropped silently. */
  noise: number
}

let pendingCounter = 0

function stem(name: string): string {
  return name.replace(/\.csv$/i, '').trim()
}

function leafOf(path: string): string {
  return path.slice(path.lastIndexOf('/') + 1).toLowerCase()
}

/** The folder a file sits in, lowercased; empty for a loose file. */
function parentLeaf(path: string): string {
  const parts = path.split('/')
  return parts.length > 1 ? parts[parts.length - 2].toLowerCase() : ''
}

function firstLine(text: string): string {
  const end = text.search(/\r?\n/)
  return end === -1 ? text : text.slice(0, end)
}

export interface ClassifyOptions {
  /** Every dictionary column of the database, to recognise the primary CSV. */
  columns: string[]
  /** Basename of the database's primary CSV, to pick between candidates. */
  primaryName: string
  kinds: TimeSeriesKind[]
  /** Ids already in the batch. */
  ids: string[]
  /** Extra folder names a response type may go by (its translated label). */
  aliases?: (kind: TimeSeriesKind) => string[]
}

/**
 * A primary CSV is recognised by its headers, never by its name: it carries
 * `id` and at least two other dictionary columns, which no curve file does.
 */
function readPrimary(text: string, columns: string[]): { table: CsvTable | null; hasId: boolean } {
  try {
    const table = readCsvTable(text, columns)
    const hasId = table.matched.includes('id')
    return { table: hasId && table.matched.length >= 3 ? table : null, hasId }
  } catch {
    return { table: null, hasId: false }
  }
}

function kindsByFolder(kinds: TimeSeriesKind[], folder: string, options: ClassifyOptions) {
  if (!folder) return []
  return kinds.filter((kind) => {
    const names = [leafOf(kind.directory), kind.key.toLowerCase()]
    for (const alias of options.aliases?.(kind) ?? []) names.push(alias.toLowerCase())
    return names.includes(folder)
  })
}

/** The only required kind among several candidates, or undefined. */
function soleRequired(kinds: TimeSeriesKind[]): TimeSeriesKind | undefined {
  const required = kinds.filter((kind) => kind.required)
  return required.length === 1 ? required[0] : undefined
}

/** Key of a file stem and its candidate types, to find two files that compete. */
function rivalKey(fileStem: string, kinds: TimeSeriesKind[]): string {
  return `${fileStem.toLowerCase()}|${kinds.map((kind) => kind.key).join('|')}`
}

/**
 * Place every file. Order of the rules for a curve file:
 *  1. its folder is named after a response type (the repository's directory,
 *     the kind key, or its label) — the only way to tell F1 from F2;
 *  2. otherwise its headers, when they single out one response type. When
 *     they fit several types and only one of them is required, a file alone
 *     for its experiment goes to the required one, flagged `assumed` (a drop
 *     that lost its folder names: strong and weak axis share their headers);
 *  3. its stem is a specimen id (case-insensitive), through the kind's naming
 *     rule (`id74` for EBF).
 * Ids from a primary CSV in the same drop count, so a whole folder lands in one go.
 */
export async function classifyIntake(
  files: IntakeFile[],
  options: ClassifyOptions
): Promise<IntakePlan> {
  const plan: IntakePlan = {
    primary: null,
    primaryCandidates: [],
    matched: [],
    pending: [],
    skipped: [],
    noise: 0
  }
  const curves: Array<{ file: IntakeFile; text: string }> = []
  const primaries: Array<{ file: IntakeFile; table: CsvTable }> = []

  for (const file of files) {
    if (isNoise(file.path)) {
      plan.noise++
      continue
    }
    if (!isCsv(file.path)) {
      plan.skipped.push(file)
      continue
    }
    const text = await file.text()
    const { table, hasId } = readPrimary(text, options.columns)
    if (table) primaries.push({ file, table })
    else if (hasId) {
      plan.pending.push({ id: pendingCounter++, file, text, reason: 'foreign', kinds: [] })
    } else curves.push({ file, text })
  }

  if (primaries.length === 1) plan.primary = primaries[0]
  else if (primaries.length > 1) {
    // The one carrying the repository's own name wins (`steel_braces.csv`
    // next to `steel_braces.invalid.csv`); otherwise the contributor picks.
    const named = primaries.filter(
      (entry) => entry.file.name.toLowerCase() === options.primaryName.toLowerCase()
    )
    if (named.length === 1) {
      plan.primary = named[0]
      plan.primaryCandidates = primaries.filter((entry) => entry !== named[0]).map((e) => e.file)
    } else plan.primaryCandidates = primaries.map((entry) => entry.file)
  }

  const ids = [...options.ids]
  for (const row of plan.primary?.table.rows ?? []) {
    const id = (row.id ?? '').trim()
    if (id && !ids.includes(id)) ids.push(id)
  }

  const placed = curves.map(({ file, text }) => {
    let kinds = kindsByFolder(options.kinds, parentLeaf(file.path), options)
    if (kinds.length !== 1) kinds = kindsMatchingHeaders(options.kinds, firstLine(text))
    return { file, text, kinds }
  })
  // Files that could be the same experiment's same slot: none of them is guessed.
  const rivals = new Map<string, number>()
  for (const { file, kinds } of placed) {
    if (kinds.length < 2) continue
    const key = rivalKey(stem(file.name), kinds)
    rivals.set(key, (rivals.get(key) ?? 0) + 1)
  }

  for (const { file, text, kinds: candidates } of placed) {
    let kinds = candidates
    let assumed = false
    if (kinds.length > 1) {
      const required = soleRequired(kinds)
      if (required && rivals.get(rivalKey(stem(file.name), kinds)) === 1) {
        kinds = [required]
        assumed = true
      }
    }
    if (kinds.length === 0) {
      plan.pending.push({
        id: pendingCounter++,
        file,
        text,
        reason: 'unknown',
        kinds: options.kinds
      })
      continue
    }
    if (kinds.length > 1) {
      plan.pending.push({ id: pendingCounter++, file, text, reason: 'ambiguous', kinds })
      continue
    }
    const kind = kinds[0]
    const id = matchId(kind, stem(file.name), ids)
    if (id === undefined) {
      // A guessed type is no more than a guess: the contributor still picks among all.
      const left = assumed ? candidates : [kind]
      plan.pending.push({ id: pendingCounter++, file, text, reason: 'orphan', kinds: left })
      continue
    }
    plan.matched.push(assumed ? { file, kind, id, text, assumed } : { file, kind, id, text })
  }
  return plan
}

/** The specimen whose file this is: an exact stem first, then case-insensitive. */
export function matchId(kind: TimeSeriesKind, fileStem: string, ids: string[]): string | undefined {
  const exact = ids.find((id) => fileStemFor(kind, id) === fileStem)
  if (exact !== undefined) return exact
  const lower = fileStem.toLowerCase()
  return ids.find((id) => fileStemFor(kind, id).toLowerCase() === lower)
}
