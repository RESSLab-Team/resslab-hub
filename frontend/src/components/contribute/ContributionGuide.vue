<script setup lang="ts">
/**
 * The contributor guide of the selected database, rendered in the app rather
 * than linked out to GitHub.
 *
 * Two tabs. "Guide" is the data repo's per-database `README.md`, uploaded with
 * the data and served by `GET /dictionary/{database}/readme`, so each
 * deployment shows the guide that matches the data it serves. "Data dictionary"
 * is the same store the editor validates against, as a searchable list grouped
 * by scientific category. Both are the researchers' own text; this only styles
 * it.
 *
 * Two placements: `docked` fills the page's right rail (own scroll, always
 * open); otherwise it is a collapsible card above the editor.
 */
import { stripSubSup } from '@/components/commons/TextSubscript.vue'
import {
  displaySymbol,
  displayUnit,
  symbolHtml,
  useDictionaryStore,
  type DictColumn
} from '@/stores/dictionary'
import { agentGuideUrl, agentPrompt } from '@/utils/agentPrompt'
import { contributionGuideUrl, dataDictionaryUrl } from '@/utils/contribution'
import { MANAGED_COLUMNS } from '@/utils/curationStatus'
import { groupBy, type FieldGroupId } from '@/utils/fieldGroups'
import type { DatabaseId } from '@/utils/navigation'
import { downloadStarterKit, layoutEntries, layoutRoot } from '@/utils/templates'
import { timeSeriesKindsFor } from '@/utils/timeseries'
import {
  mdiCheck,
  mdiChevronRight,
  mdiContentCopy,
  mdiMagnify,
  mdiOpenInNew,
  mdiPackageVariantClosed
} from '@mdi/js'
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { computed, ref, watch } from 'vue'

const props = defineProps<{ database: DatabaseId; docked?: boolean }>()

const dictionary = useDictionaryStore()

const open = ref(false)
const tab = ref<'guide' | 'dictionary'>('guide')
const expanded = computed(() => props.docked || open.value)

watch(
  () => props.database,
  (database) => dictionary.fetchReadme(database),
  { immediate: true }
)

const readme = computed(() => dictionary.readmes[props.database])
const githubUrl = computed(() => contributionGuideUrl(props.database))
const dictionaryUrl = computed(() => dataDictionaryUrl(props.database))

/**
 * Relative links in the README (`steel_braces_data_dictionary.csv`,
 * `../README.md`) are meant for GitHub, so they are resolved against the
 * README's own folder there. Every link opens in a new tab. Done on the
 * sanitized DOM rather than through a DOMPurify hook, which would register
 * once per mounted instance.
 */
function rewriteLinks(clean: string, base: string): string {
  const doc = new DOMParser().parseFromString(clean, 'text/html')
  doc.querySelectorAll('a[href]').forEach((anchor) => {
    const href = anchor.getAttribute('href') ?? ''
    if (!/^[a-z]+:/i.test(href) && !href.startsWith('#')) {
      anchor.setAttribute('href', new URL(href, base).toString())
    }
    anchor.setAttribute('target', '_blank')
    anchor.setAttribute('rel', 'noopener noreferrer')
  })
  return doc.body.innerHTML
}

const html = computed(() => {
  if (!readme.value) return ''
  const raw = marked.parse(readme.value, { gfm: true, async: false }) as string
  const base = githubUrl.value.replace(/README\.md$/, '')
  return rewriteLinks(DOMPurify.sanitize(raw), base)
})

// --- Expected layout --------------------------------------------------------
// Rendered from the response-type table, so the hint exists even for a
// database whose README has not been written yet.

const kinds = computed(() => timeSeriesKindsFor(props.database))
const layout = computed(() => layoutEntries(props.database, kinds.value))
const root = computed(() => layoutRoot(props.database))

// --- AI agent ---------------------------------------------------------------
// A prompt for the researcher's own agent, which reads the agent guide of the
// backend (routers/agent.py) and checks its output with POST /agent/validate.

const prompt = computed(() => agentPrompt(props.database))
const agentUrl = computed(() => agentGuideUrl(props.database))
const promptBox = ref<HTMLElement | null>(null)
const copied = ref(false)
let copiedTimer: ReturnType<typeof setTimeout> | undefined

/** Copy the prompt; without clipboard access, select it for a manual copy. */
async function copyPrompt(): Promise<void> {
  try {
    await navigator.clipboard.writeText(prompt.value)
    copied.value = true
    clearTimeout(copiedTimer)
    copiedTimer = setTimeout(() => (copied.value = false), 2000)
  } catch {
    const box = promptBox.value
    const selection = window.getSelection()
    if (box && selection) selection.selectAllChildren(box)
  }
}

// --- Dictionary -----------------------------------------------------------

// Not the review status: the Hub sets it (#253), the starter kit leaves it out.
const columns = computed(() =>
  dictionary.columnsFor(props.database).filter((column) => !MANAGED_COLUMNS.has(column.name))
)
const query = ref('')

function matches(column: DictColumn, needle: string): boolean {
  return (
    column.name.toLowerCase().includes(needle) ||
    column.description.toLowerCase().includes(needle) ||
    // `dpz` finds `d<sub>pz</sub>`: search the symbol without its markup.
    stripSubSup(column.symbol).toLowerCase().includes(needle)
  )
}

const groups = computed(() => {
  const needle = query.value.trim().toLowerCase()
  const visible = needle ? columns.value.filter((column) => matches(column, needle)) : columns.value
  return groupBy(props.database, visible, (column) => column).map((group) => ({
    id: group.id,
    rows: group.items.map((column) => ({
      column,
      symbol: displaySymbol(column),
      unit: displayUnit(column)
    }))
  }))
})

const openGroups = ref<Set<FieldGroupId>>(new Set())

function toggleGroup(id: FieldGroupId): void {
  const next = new Set(openGroups.value)
  if (!next.delete(id)) next.add(id)
  openGroups.value = next
}

/** A search opens every group that still has rows; clearing it folds them. */
const groupOpen = (id: FieldGroupId): boolean =>
  query.value.trim() !== '' || openGroups.value.has(id)

/** Lets the page switch tab and open the panel from elsewhere. */
function show(which: 'guide' | 'dictionary' = 'guide'): void {
  tab.value = which
  open.value = true
}

defineExpose({ show })
</script>

<template>
  <section class="tool-card guide" :class="{ docked, expanded }">
    <header class="guide-head">
      <div class="title-row">
        <button
          v-if="!docked"
          class="toggle"
          type="button"
          :aria-expanded="open"
          @click="open = !open"
        >
          <v-icon class="caret" :class="{ open }" :icon="mdiChevronRight" size="18" />
          <span class="title">{{ $t('contribute.guide.title') }}</span>
        </button>
        <span v-else class="title">{{ $t('contribute.guide.title') }}</span>
        <a class="github" :href="githubUrl" rel="noopener noreferrer" target="_blank">
          {{ $t('contribute.guide.github') }}
          <v-icon :icon="mdiOpenInNew" size="12" />
        </a>
      </div>
      <div v-if="expanded" class="tabs" role="tablist">
        <button
          class="tab"
          :class="{ active: tab === 'guide' }"
          role="tab"
          type="button"
          :aria-selected="tab === 'guide'"
          @click="tab = 'guide'"
        >
          {{ $t('contribute.guide.tab_guide') }}
        </button>
        <button
          class="tab"
          :class="{ active: tab === 'dictionary' }"
          role="tab"
          type="button"
          :aria-selected="tab === 'dictionary'"
          @click="tab = 'dictionary'"
        >
          {{ $t('contribute.guide.tab_dictionary') }}
          <span class="count">{{ columns.length }}</span>
        </button>
      </div>
    </header>

    <div v-if="expanded && tab === 'guide'" class="body">
      <section class="layout">
        <h4>{{ $t('contribute.guide.layout_title') }}</h4>
        <p class="state">{{ $t('contribute.guide.layout_hint') }}</p>
        <ul class="tree">
          <li class="tree-root">
            <code>{{ root }}</code>
          </li>
          <li v-for="entry in layout" :key="entry.path" class="tree-entry">
            <code>{{ entry.path }}</code>
            <span v-if="!entry.kind" class="tree-desc">
              {{ $t('contribute.guide.layout_primary') }}
            </span>
            <span v-else class="tree-desc">
              <span class="tree-tag" :class="{ required: entry.kind.required }">
                {{
                  $t(
                    entry.kind.required
                      ? 'contribute.timeseries.required'
                      : 'contribute.timeseries.optional'
                  )
                }}
              </span>
              {{ $t(`contribute.timeseries.kind.${entry.kind.key}`) }} —
              <template v-for="(column, i) in entry.kind.columns" :key="column.name">
                <template v-if="i > 0">, </template><code>{{ column.name }}</code>
              </template>
            </span>
          </li>
        </ul>
        <button
          class="kit"
          type="button"
          @click="downloadStarterKit(props.database, columns, kinds)"
        >
          <v-icon :icon="mdiPackageVariantClosed" size="14" />
          {{ $t('contribute.guide.layout_kit') }}
        </button>
      </section>
      <section class="layout agent">
        <h4>{{ $t('contribute.guide.agent_title') }}</h4>
        <p class="state">{{ $t('contribute.guide.agent_hint') }}</p>
        <pre ref="promptBox" class="agent-prompt">{{ prompt }}</pre>
        <div class="agent-actions">
          <button class="kit" type="button" @click="copyPrompt">
            <v-icon :icon="copied ? mdiCheck : mdiContentCopy" size="14" />
            {{ $t(copied ? 'contribute.guide.agent_copied' : 'contribute.guide.agent_copy') }}
          </button>
          <a class="kit" :href="agentUrl" rel="noopener noreferrer" target="_blank">
            <v-icon :icon="mdiOpenInNew" size="14" />
            {{ $t('contribute.guide.agent_open') }}
          </a>
        </div>
        <p class="state agent-note">{{ $t('contribute.guide.agent_offline') }}</p>
      </section>
      <p v-if="readme === undefined" class="state">{{ $t('contribute.guide.loading') }}</p>
      <p v-else-if="readme === null" class="state">
        {{ $t('contribute.guide.missing') }}
        <a :href="githubUrl" rel="noopener noreferrer" target="_blank">{{
          $t('contribute.guide.github')
        }}</a>
      </p>
      <!-- eslint-disable-next-line vue/no-v-html -- sanitized by DOMPurify above -->
      <div v-else class="md" v-html="html" />
    </div>

    <div v-else-if="expanded" class="body dict">
      <label class="search">
        <v-icon :icon="mdiMagnify" size="16" />
        <input v-model="query" type="search" :placeholder="$t('contribute.guide.search')" />
      </label>
      <p class="state">
        {{ $t('contribute.guide.dictionary_hint', { count: columns.length }) }}
        <a class="dict-github" :href="dictionaryUrl" rel="noopener noreferrer" target="_blank">
          {{ $t('contribute.guide.dictionary_github') }}
          <v-icon :icon="mdiOpenInNew" size="12" />
        </a>
      </p>
      <p v-if="groups.length === 0" class="state">{{ $t('contribute.guide.no_match') }}</p>
      <div v-for="group in groups" :key="group.id" class="group">
        <button
          class="group-head"
          type="button"
          :aria-expanded="groupOpen(group.id)"
          @click="toggleGroup(group.id)"
        >
          <v-icon
            class="caret"
            :class="{ open: groupOpen(group.id) }"
            :icon="mdiChevronRight"
            size="15"
          />
          <span class="group-label">{{ $t(`field_group.${group.id}`) }}</span>
          <span class="count">{{ group.rows.length }}</span>
        </button>
        <ul v-if="groupOpen(group.id)" class="cols">
          <li v-for="row in group.rows" :key="row.column.name" class="col">
            <div class="col-top">
              <code class="col-name">{{ row.column.name }}</code>
              <!-- eslint-disable-next-line vue/no-v-html -- sanitised by symbolHtml -->
              <span v-if="row.symbol" class="col-symbol" v-html="symbolHtml(row.symbol)" />
              <span v-if="row.unit" class="col-unit">{{ row.unit }}</span>
              <span
                v-if="!row.column.nullable"
                class="col-required"
                :title="$t('contribute.guide.required')"
              >
                {{ $t('contribute.guide.required') }}
              </span>
            </div>
            <p class="col-desc">{{ row.column.description }}</p>
            <p class="col-meta">
              <span>{{ row.column.type }}</span>
              <span v-if="row.column.example" class="col-example">
                {{ $t('contribute.guide.example') }}: {{ row.column.example }}
              </span>
            </p>
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>

<style scoped>
.tool-card.guide {
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 0;
}
.guide.docked {
  max-height: inherit;
}

/* ── header ── */
.guide-head {
  flex: 0 0 auto;
  padding: 14px var(--card-pad) 0;
  border-bottom: 1px solid var(--border-subtle);
}
.title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 24px;
  padding-bottom: 12px;
}
.toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: -4px;
  padding: 0;
  border: 0;
  background: none;
  color: inherit;
  font: inherit;
  cursor: pointer;
}
.toggle:hover .title {
  color: var(--epfl-red);
}
.title {
  font-size: var(--title-panel-size);
  font-weight: var(--title-panel-weight);
  text-transform: uppercase;
  letter-spacing: var(--title-panel-tracking);
  line-height: 1;
  color: var(--fg);
}
.caret {
  flex: 0 0 auto;
  color: var(--fg-subtle);
  transition: transform var(--t-fast);
}
.caret.open {
  transform: rotate(90deg);
}
.github {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--fg-muted);
  text-decoration: none;
  white-space: nowrap;
}
.github:hover {
  color: var(--epfl-red);
}
.tabs {
  display: flex;
  gap: 18px;
}
.tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 0 10px;
  margin-bottom: -1px;
  border: 0;
  border-bottom: 2px solid transparent;
  background: none;
  color: var(--fg-muted);
  font: inherit;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.tab:hover {
  color: var(--fg);
}
.tab.active {
  color: var(--fg);
  border-bottom-color: var(--epfl-red);
}
.count {
  padding: 0 6px;
  border-radius: 999px;
  background: var(--bg-subtle);
  color: var(--fg-muted);
  font-size: 11px;
  font-weight: 600;
  line-height: 16px;
}

/* ── body ── */
.body {
  flex: 1 1 auto;
  min-height: 0;
  padding: 16px var(--card-pad) 20px;
}
.docked .body {
  overflow-y: auto;
}
.state {
  margin: 0 0 12px;
  font-size: 12.5px;
  line-height: 1.5;
  color: var(--fg-muted);
}
.state a {
  color: inherit;
}
/* The dictionary as a file in the data repository, on its own line (#241). */
.dict-github {
  display: flex;
  align-items: center;
  gap: 4px;
  width: fit-content;
  margin-top: 4px;
}
.dict-github:hover {
  color: var(--epfl-red);
}

/* Rendered README. Headings step down one level visually: the card already
   carries the title. */
.md {
  font-size: 13.5px;
  line-height: 1.55;
  max-width: 78ch;
}
.md :deep(h1) {
  margin: 0 0 6px;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: -0.01em;
  line-height: 1.25;
}
.md :deep(h1 + p) {
  color: var(--fg-muted);
}
.md :deep(h2) {
  margin: 24px 0 8px;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--border);
  font-size: 11.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--fg-muted);
}
.md :deep(h3) {
  margin: 16px 0 6px;
  font-size: 13.5px;
  font-weight: 700;
}
.md :deep(p) {
  margin: 0 0 10px;
}
.md :deep(ul),
.md :deep(ol) {
  margin: 0 0 10px;
  padding-left: 20px;
}
.md :deep(li) {
  margin: 3px 0;
}
.md :deep(a) {
  color: var(--epfl-red);
}
.md :deep(code) {
  padding: 1px 5px;
  border-radius: 3px;
  background: var(--bg-subtle);
  font-size: 12px;
}
.md :deep(pre) {
  margin: 0 0 12px;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg-subtle);
  overflow-x: auto;
  font-size: 12px;
}
.md :deep(pre code) {
  padding: 0;
  background: none;
}
.md :deep(table) {
  display: block;
  max-width: 100%;
  margin: 0 0 14px;
  overflow-x: auto;
  border-collapse: collapse;
  font-size: 12.5px;
}
.md :deep(th),
.md :deep(td) {
  padding: 5px 9px;
  border: 1px solid var(--border);
  text-align: left;
  vertical-align: top;
}
.md :deep(th) {
  background: var(--bg-subtle);
  font-weight: 600;
  white-space: nowrap;
}

/* ── dictionary ── */
.search {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  padding: 6px 10px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius);
  background: var(--bg);
  color: var(--fg-muted);
}
.search:focus-within {
  border-color: var(--epfl-red);
}
.search input {
  flex: 1;
  min-width: 0;
  border: 0;
  background: none;
  color: var(--fg);
  font: inherit;
  font-size: 13px;
  outline: none;
}
.group {
  border-top: 1px solid var(--border-subtle);
}
.group:last-child {
  border-bottom: 1px solid var(--border-subtle);
}
.group-head {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 9px 0;
  border: 0;
  background: none;
  color: var(--fg);
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.group-head:hover .group-label {
  color: var(--epfl-red);
}
.group-label {
  flex: 1;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.cols {
  list-style: none;
  margin: 0;
  padding: 0 0 8px;
}
.col {
  padding: 8px 0 8px 23px;
  border-top: 1px dashed var(--border-subtle);
}
.col-top {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 8px;
}
.col-symbol {
  font-style: italic;
  font-size: 13px;
}
.col-unit {
  font-size: 12px;
  color: var(--fg-muted);
}
.col-required {
  margin-left: auto;
  font-size: 10.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--epfl-red);
}
.col-desc {
  margin: 3px 0 0;
  font-size: 13px;
  line-height: 1.45;
}
.col-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin: 3px 0 0;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--fg-subtle);
}
.col-example {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

/* Expected layout — a small tree above the README. */
.layout {
  margin-bottom: 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--border-subtle);
}
.layout h4 {
  margin: 0 0 4px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--fg-muted);
}
.tree {
  margin: 8px 0;
  padding: 0;
  list-style: none;
  font-size: 12.5px;
  line-height: 1.5;
}
.tree code {
  font-size: 12px;
}
.tree-entry {
  padding-left: 16px;
}
.tree-desc {
  display: block;
  padding-left: 12px;
  color: var(--fg-muted);
}
.tree-tag {
  display: inline-block;
  margin-right: 4px;
  padding: 0 5px;
  border: 1px solid var(--border);
  border-radius: 999px;
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}
.tree-tag.required {
  border-color: var(--epfl-red);
  color: var(--epfl-red);
}
.agent-prompt {
  margin: 8px 0 10px;
  padding: 10px 12px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-subtle);
  font-family: var(--font-mono);
  font-size: 11.5px;
  line-height: 1.5;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.agent-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}
.agent-note {
  margin: 10px 0 0;
}
.kit {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0;
  border: 0;
  background: none;
  color: var(--fg);
  font: inherit;
  font-size: 12.5px;
  font-weight: 600;
  text-decoration: underline;
  cursor: pointer;
}
</style>
