<script setup lang="ts">
import ContributionGuide from '@/components/contribute/ContributionGuide.vue'
import ExperimentCards from '@/components/contribute/ExperimentCards.vue'
import FailureDetails from '@/components/contribute/FailureDetails.vue'
import { useContributionStore, type CardIssue } from '@/stores/contribution'
import { useDictionaryStore } from '@/stores/dictionary'
import { CONTRIBUTION_DATABASES, fieldLabel } from '@/utils/contribution'
import { DATABASES, type DatabaseId } from '@/utils/navigation'
import { loadContributor, saveContributor } from '@/utils/submission'
import {
  mdiAlertOutline,
  mdiArrowRight,
  mdiBellOffOutline,
  mdiCheck,
  mdiCheckCircleOutline,
  mdiChevronRight,
  mdiClose,
  mdiOpenInNew,
  mdiSend,
  mdiShieldCheckOutline
} from '@mdi/js'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })
const store = useContributionStore()
const dictionary = useDictionaryStore()

onMounted(() => dictionary.fetch())

const supported = (id: DatabaseId) => CONTRIBUTION_DATABASES[id].qualityCheckSupported

// Switching database clears the batch, so when there is work to lose the first
// click only arms the button and the second one confirms.
const pending = ref<DatabaseId | null>(null)
const atRisk = computed(() => (store.hasAnyId ? store.experimentCount : 0))

/** Name of the picked database, echoed next to the section title. */
const selectedName = computed(
  () => DATABASES.find((entry) => entry.id === store.database)?.name ?? ''
)

function pick(id: DatabaseId): void {
  if (store.database === id) return
  if (atRisk.value > 0 && pending.value !== id) {
    pending.value = id
    return
  }
  pending.value = null
  store.selectDatabase(id)
}

/**
 * One line summarizing the automatic server check. Client-side warnings (a
 * blank required field, no test data) count with the server's, so a pass with
 * something left to look at reads as a warning.
 */
const statusText = computed(() => {
  switch (store.status) {
    case 'running':
      return t('contribute.status.running')
    case 'pass':
    case 'warn':
      // A client-side error (a bad id, a wrong type) blocks the batch even
      // when the last server round trip passed.
      if (store.activeErrorCount > 0) {
        return t('contribute.status.fail', { count: store.activeErrorCount })
      }
      if (store.activeWarningCount > 0) {
        return t('contribute.status.warn', { count: store.activeWarningCount })
      }
      return t(
        store.status === 'warn' ? 'contribute.status.warn_dismissed' : 'contribute.status.pass'
      )
    case 'fail':
      return t('contribute.status.fail', { count: store.activeErrorCount })
    case 'unsupported':
      return t('contribute.status.unsupported')
    case 'error':
      // The details block under the bar carries the message and the report.
      return store.checkFailure
        ? t('contribute.status.error_short')
        : `${t('contribute.status.error')} ${store.errorMessage}`
    default:
      return store.hasAnyId ? t('contribute.status.pending') : t('contribute.status.idle')
  }
})

/** Once every warning is dismissed the bar reads as a pass, and vice versa. */
const statusClass = computed(() => {
  if (store.status !== 'pass' && store.status !== 'warn') return store.status
  if (store.activeErrorCount > 0) return 'fail'
  return store.activeWarningCount > 0 ? 'warn' : 'pass'
})

// --- Problem summary --------------------------------------------------------
// Errors and unresolved warnings, batch-wide, folded under the status line;
// unfolded, one row per experiment that jumps to (and opens) its card.

const cards = ref<InstanceType<typeof ExperimentCards> | null>(null)
const showProblems = ref(false)
const hasProblems = computed(() => store.activeErrorCount > 0 || store.activeWarningCount > 0)

function reveal(uid: number): void {
  cards.value?.reveal(uid)
}

function revealIssue(uid: number, issue: CardIssue): void {
  cards.value?.revealIssue(uid, issue)
}

/** What a problem is about, the way the card labels it: the field, or the file kind. */
function issueSubject(issue: CardIssue): string {
  if (issue.column) return fieldLabel(store.database!, issue.column)
  if (issue.kindKey) return t(`contribute.timeseries.kind.${issue.kindKey}`)
  return ''
}

// --- Submission dialog ----------------------------------------------------

const dialogOpen = ref(false)
const contributor = ref(loadContributor())

const contributorValid = computed(
  () =>
    contributor.value.name.trim().length > 0 &&
    /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contributor.value.email.trim())
)

const curveCount = computed(() => Object.keys(store.timeSeries).length)

function openDialog(): void {
  contributor.value = loadContributor()
  dialogOpen.value = true
}

// --- Guide ----------------------------------------------------------------

const guide = ref<InstanceType<typeof ContributionGuide> | null>(null)

// On wide screens the guide is docked in a sticky right rail; below that it is
// a collapsible card above the editor. Same breakpoint as the CSS below, and it
// counts in the 260px app sidebar: docking any earlier leaves the editor around
// 520px, which is too narrow for the field grid.
const wideQuery = window.matchMedia('(min-width: 1400px)')
const wide = ref(wideQuery.matches)
const onWide = (event: MediaQueryListEvent) => (wide.value = event.matches)
onMounted(() => wideQuery.addEventListener('change', onWide))
onBeforeUnmount(() => wideQuery.removeEventListener('change', onWide))

function openGuide(which: 'guide' | 'dictionary' = 'guide'): void {
  guide.value?.show(which)
  if (!wide.value) guide.value?.$el?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

async function confirmSubmit(): Promise<void> {
  if (!contributorValid.value) return
  const details = {
    name: contributor.value.name.trim(),
    email: contributor.value.email.trim(),
    institution: contributor.value.institution.trim(),
    orcid: contributor.value.orcid.trim()
  }
  saveContributor(details)
  dialogOpen.value = false
  await store.submit(details)
}
</script>

<template>
  <div class="tool-page contribute-page">
    <!-- Same page head as the curation pages (their `.phead`): full-bleed, the
         eyebrow qualified by what you are looking at, one rule under it. -->
    <div class="phead">
      <p class="eyebrow">
        <span class="red">{{ $t('contribute.eyebrow') }}</span>
        <span v-if="selectedName" class="mut"> · {{ selectedName }}</span>
      </p>
      <div class="prow">
        <h1 class="ptitle">{{ $t('contribute.title') }}</h1>
      </div>
      <p class="pdesc">{{ $t('contribute.description') }}</p>
    </div>

    <div class="pbody layout" :class="{ 'with-rail': store.database && dictionary.ready }">
      <div class="main">
        <section class="block setup">
          <div class="block-bar">
            <h2 class="block-h">{{ $t('contribute.setup.title') }}</h2>
          </div>
          <div class="db-grid">
            <button
              v-for="entry in DATABASES"
              :key="entry.id"
              class="db"
              :class="{ active: store.database === entry.id, pending: pending === entry.id }"
              type="button"
              @click="pick(entry.id)"
            >
              <span class="db-top">
                <v-icon :icon="entry.icon" size="17" />
                <span class="db-name">{{ entry.name }}</span>
              </span>
              <span v-if="pending === entry.id" class="db-warn">
                {{ $t('contribute.setup.switch_confirm', { count: atRisk }) }}
              </span>
              <span v-else-if="!supported(entry.id)" class="db-flag">
                {{ $t('contribute.setup.no_check_badge') }}
              </span>
            </button>
          </div>
          <p v-if="store.config && !store.config.qualityCheckSupported" class="note">
            <v-icon :icon="mdiAlertOutline" size="14" />
            {{ $t('contribute.setup.no_quality_check') }}
          </p>
        </section>

        <template v-if="store.database">
          <p
            v-if="dictionary.state === 'loading' || dictionary.state === 'idle'"
            class="dict-state"
          >
            {{ $t('contribute.dictionary_loading') }}
          </p>
          <p v-else-if="dictionary.state === 'error'" class="dict-state">
            {{ $t('contribute.dictionary_error') }}
            <button class="btn btn-secondary btn-sm" type="button" @click="dictionary.fetch()">
              {{ $t('contribute.retry') }}
            </button>
          </p>
          <experiment-cards v-else ref="cards" @open-guide="openGuide" />

          <div v-if="store.globalIssues.length" class="global-issues">
            <p class="global-issues-title">{{ $t('contribute.global_issues') }}</p>
            <p
              v-for="(entry, index) in store.globalIssues"
              :key="index"
              class="global-issue"
              :class="entry.severity"
            >
              <v-icon :icon="mdiAlertOutline" size="14" />
              {{ entry.issue.message }}
            </p>
          </div>
        </template>

        <footer
          v-if="store.database && dictionary.ready && store.submitStatus === 'submitted'"
          class="status-bar submitted-bar"
        >
          <span class="status pass">
            <v-icon :icon="mdiCheckCircleOutline" size="16" />
            {{ $t('contribute.submitted.title', { number: store.pullRequestNumber }) }}
          </span>
          <span class="submitted-note">{{ $t('contribute.submitted.next') }}</span>
          <div class="bar-actions">
            <a class="btn btn-secondary btn-sm" :href="store.pullRequestUrl" target="_blank">
              <v-icon :icon="mdiOpenInNew" size="14" />{{ $t('contribute.submitted.view_pr') }}
            </a>
            <button class="btn btn-primary btn-sm" type="button" @click="store.reset()">
              {{ $t('contribute.submitted.new') }}
            </button>
          </div>
        </footer>

        <footer v-else-if="store.database && dictionary.ready" class="status-bar">
          <span class="status" :class="statusClass">
            <v-icon
              :icon="
                statusClass === 'pass'
                  ? mdiCheck
                  : statusClass === 'running'
                  ? mdiShieldCheckOutline
                  : mdiAlertOutline
              "
              size="15"
            />
            {{ statusText }}
          </span>
          <button
            v-if="hasProblems"
            class="problems-toggle"
            type="button"
            :aria-expanded="showProblems"
            @click="showProblems = !showProblems"
          >
            <v-icon
              class="chevron"
              :class="{ open: showProblems }"
              :icon="mdiChevronRight"
              size="14"
            />
            <span v-if="store.activeErrorCount" class="err">
              {{ $t('contribute.status.problems_errors', { count: store.activeErrorCount }) }}
            </span>
            <span v-if="store.activeWarningCount" class="wrn">
              {{ $t('contribute.status.problems_warnings', { count: store.activeWarningCount }) }}
            </span>
            <span class="toggle-label">
              {{
                $t(
                  showProblems
                    ? 'contribute.status.hide_problems'
                    : 'contribute.status.show_problems'
                )
              }}
            </span>
          </button>
          <span v-if="store.dismissedCount" class="dismissed">
            <v-icon :icon="mdiBellOffOutline" size="14" />
            {{ $t('contribute.status.dismissed', { count: store.dismissedCount }) }}
            <button class="link" type="button" @click="store.restoreDismissed()">
              {{ $t('contribute.editor.restore_all') }}
            </button>
          </span>
          <div class="bar-actions">
            <button
              class="btn btn-secondary btn-sm"
              :disabled="
                !store.hasAnyId ||
                store.status === 'running' ||
                !store.config?.qualityCheckSupported
              "
              type="button"
              @click="store.runQualityCheck()"
            >
              {{ $t('contribute.status.check_now') }}
            </button>
            <button
              class="btn btn-primary btn-sm"
              :disabled="!store.canSubmit"
              type="button"
              @click="openDialog()"
            >
              <v-icon :icon="mdiSend" size="14" />
              {{
                store.submitStatus === 'submitting'
                  ? $t('contribute.submitting')
                  : $t('contribute.submit')
              }}
            </button>
          </div>
          <div v-if="hasProblems && showProblems" class="problems">
            <p class="problems-hint">{{ $t('contribute.status.problems_hint') }}</p>
            <div v-for="entry in store.problemSummary" :key="entry.uid" class="problem-row">
              <span class="problem-id">
                {{ entry.id || $t('contribute.editor.untitled', { n: entry.index + 1 }) }}
              </span>
              <!-- A lone problem is shown, and dismissable, right here; more than
                   one is summarised and handed to the card. -->
              <template v-if="entry.issues.length === 1">
                <button
                  class="problem-issue"
                  :class="entry.issues[0].level"
                  type="button"
                  :title="entry.issues[0].message"
                  @click="revealIssue(entry.uid, entry.issues[0])"
                >
                  <v-icon :icon="mdiAlertOutline" size="14" />
                  <span class="problem-msg">
                    <template v-if="issueSubject(entry.issues[0])"
                      >{{ issueSubject(entry.issues[0]) }}:
                    </template>
                    {{ entry.issues[0].message }}
                  </span>
                </button>
                <button
                  v-if="entry.issues[0].level === 'warn'"
                  class="problem-dismiss"
                  type="button"
                  :title="$t('contribute.editor.dismiss_hint')"
                  @click="store.dismissIssue(entry.issues[0].key)"
                >
                  <v-icon :icon="mdiClose" size="14" />
                  <span class="sr-only">{{ $t('contribute.editor.dismiss') }}</span>
                </button>
              </template>
              <template v-else>
                <span class="problem-counts">
                  <span v-if="entry.errors" class="problem-count err">
                    {{ $t('contribute.status.problems_errors', { count: entry.errors }) }}
                  </span>
                  <span v-if="entry.warnings" class="problem-count wrn">
                    {{ $t('contribute.status.problems_warnings', { count: entry.warnings }) }}
                  </span>
                </span>
                <button class="problem-more" type="button" @click="reveal(entry.uid)">
                  {{ $t('contribute.status.see_all_issues', { count: entry.issues.length }) }}
                  <v-icon :icon="mdiArrowRight" size="14" />
                </button>
              </template>
            </div>
          </div>
          <failure-details
            v-if="store.submitStatus === 'error' && store.submitFailure"
            class="submit-error"
            :report="store.submitFailure"
            :label="$t('contribute.submit_failed')"
          />
          <failure-details
            v-else-if="store.status === 'error' && store.checkFailure"
            class="submit-error"
            :report="store.checkFailure"
            :label="$t('contribute.status.error')"
          />
          <p class="draft-note">{{ $t('contribute.draft_notice') }}</p>
        </footer>
      </div>

      <aside v-if="store.database && dictionary.ready" class="guide-rail">
        <contribution-guide ref="guide" :database="store.database" :docked="wide" />
      </aside>
    </div>

    <div v-if="dialogOpen" class="dialog-backdrop" @click.self="dialogOpen = false">
      <div class="dialog tool-card" role="dialog" aria-modal="true">
        <div class="tool-card-h">{{ $t('contribute.dialog.title') }}</div>
        <p class="dialog-recap">
          {{
            $t('contribute.dialog.recap', {
              experiments: store.experimentCount,
              files: curveCount
            })
          }}
          <template v-if="store.withoutTestDataCount">
            {{ $t('contribute.dialog.recap_no_data', { count: store.withoutTestDataCount }) }}
          </template>
          <template v-if="store.dismissedWarningMessages.length">
            {{
              $t('contribute.dialog.recap_dismissed', {
                count: store.dismissedWarningMessages.length
              })
            }}
          </template>
        </p>
        <div class="dialog-grid">
          <label class="dialog-field">
            <span>{{ $t('contribute.dialog.name') }} *</span>
            <input v-model="contributor.name" type="text" autocomplete="name" />
          </label>
          <label class="dialog-field">
            <span>{{ $t('contribute.dialog.email') }} *</span>
            <input v-model="contributor.email" type="email" autocomplete="email" />
          </label>
          <label class="dialog-field">
            <span>{{ $t('contribute.dialog.institution') }}</span>
            <input v-model="contributor.institution" type="text" autocomplete="organization" />
          </label>
          <label class="dialog-field">
            <span>{{ $t('contribute.dialog.orcid') }}</span>
            <input v-model="contributor.orcid" type="text" placeholder="0000-0000-0000-0000" />
          </label>
        </div>
        <p class="dialog-note">{{ $t('contribute.dialog.note') }}</p>
        <div class="dialog-actions">
          <button class="btn btn-secondary btn-sm" type="button" @click="dialogOpen = false">
            {{ $t('contribute.dialog.cancel') }}
          </button>
          <button
            class="btn btn-primary btn-sm"
            :disabled="!contributorValid"
            type="button"
            @click="confirmSubmit()"
          >
            <v-icon :icon="mdiSend" size="14" />{{ $t('contribute.dialog.confirm') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* The page is a single scroll: a stack of flush sections on the left, all
   sharing one left edge, and the contribution guide docked in a sticky rail
   once the viewport can afford a second column.

   Head and body are full-bleed and share one horizontal inset, the same one the
   curation pages use — this is the third page of that family, and it should read
   as such. */
.contribute-page {
  --stack: 24px;
  --edge: clamp(20px, 3vw, 56px);
  min-height: 100%;
  background: var(--bg);
}
@media (min-height: 900px) {
  .contribute-page {
    --stack: 28px;
  }
}

/* ── page head (matches CurationQueueView's .phead) ── */
.phead {
  padding: 30px var(--edge) 22px;
  border-bottom: 1px solid var(--fg);
}
.eyebrow {
  margin: 0 0 14px;
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.eyebrow .red {
  color: var(--epfl-red);
}
.eyebrow .mut {
  color: var(--fg-subtle);
}
.prow {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
}
.ptitle {
  margin: 0;
  font-size: 40px;
  font-weight: 300;
  line-height: 1;
  letter-spacing: -0.02em;
}
.pdesc {
  margin: 16px 0 0;
  max-width: 74ch;
  font-size: 14px;
  line-height: 1.5;
  color: var(--fg-muted);
}
@media (max-width: 700px) {
  .ptitle {
    font-size: 30px;
  }
}

.pbody {
  padding: 26px var(--edge) 120px;
}
.layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: var(--stack);
  align-items: start;
}
.main {
  display: flex;
  flex-direction: column;
  gap: var(--stack);
  min-width: 0;
}

/* Narrow (phones, portrait tablets): the guide leads the page as a collapsed
   bar. `.guide-rail` deliberately avoids the name `.rail`, which tool-pages.css
   turns into an off-canvas drawer below 900px. */
.guide-rail {
  order: -1;
  min-width: 0;
}
@media (min-width: 1400px) {
  .layout.with-rail {
    grid-template-columns: minmax(0, 1fr) clamp(330px, 24vw, 430px);
    gap: clamp(24px, 2.4vw, 40px);
  }
  .guide-rail {
    order: 1;
    position: sticky;
    /* No top bar at this width — the sidebar is the chrome — so the rail only
       clears the body's own top padding. */
    top: 20px;
    max-height: calc(100vh - 40px);
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .guide-rail > * {
    max-height: inherit;
  }
}
@media (min-width: 1800px) {
  .layout.with-rail {
    grid-template-columns: minmax(0, 1fr) clamp(400px, 24vw, 520px);
  }
}

/* ── section chrome, shared with ExperimentCards ── */
.block {
  min-width: 0;
}
.block-bar {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  padding-bottom: 10px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--border);
}
.block-h {
  margin: 0;
  font-size: var(--title-panel-size);
  font-weight: var(--title-panel-weight);
  text-transform: uppercase;
  letter-spacing: var(--title-panel-tracking);
  color: var(--fg);
}
/* ── database picker ── */
/* A tile grid rather than wrapped pills: the names differ in length, and only
   fixed tracks keep the columns and the badges aligned across rows. */
.db-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: 10px;
}
.db {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
  min-height: 62px;
  padding: 10px 14px;
  border: 1px solid var(--border-strong);
  background: var(--bg);
  color: var(--fg);
  font: inherit;
  text-align: left;
  cursor: pointer;
  border-radius: var(--radius);
  transition: border-color var(--t-fast), background var(--t-fast);
}
.db-top {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.db-name {
  font-size: 13.5px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.db:hover {
  background: var(--bg-subtle);
  border-color: var(--fg-muted);
}
.db.active {
  border-color: var(--epfl-red);
  background: var(--epfl-red);
  color: #fff;
}
.db.active .db-name {
  font-weight: 600;
}
.db.pending {
  border-color: var(--epfl-orange);
}
.db-flag,
.db-warn {
  font-size: 11px;
  line-height: 1.3;
  color: var(--epfl-orange);
}
.db.active .db-flag {
  color: #fff;
}
.db-warn {
  font-weight: 600;
}
.note {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin: 14px 0 0;
  font-size: 13px;
  line-height: 1.5;
  color: var(--epfl-orange);
}
.dict-state {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0;
  font-size: 14px;
  color: var(--fg-muted);
}

.global-issues {
  padding: 12px 16px;
  border: 1px solid var(--border);
  border-left: 3px solid var(--epfl-red);
  background: var(--bg);
}
.global-issues-title {
  margin: 0 0 6px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--fg-muted);
}
.global-issue {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin: 3px 0;
  font-size: 13px;
}
.global-issue.error {
  color: var(--epfl-red);
}
.global-issue.warning {
  color: var(--epfl-orange);
}

/* ── status bar ──
   Two rows on one line where there is room: the verdict on the left, the
   actions right; the notes always sit on their own row underneath. */
.status-bar {
  position: sticky;
  bottom: 0;
  z-index: 3;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 6px 16px;
  margin-top: auto;
  padding: 12px 16px;
  border: 1px solid var(--border);
  background: var(--bg);
  box-shadow: 0 -4px 16px rgba(0, 0, 0, 0.06);
}
.status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
}
.status.pass {
  color: var(--epfl-green-text);
}
.status.warn {
  color: var(--epfl-orange);
}
.status.fail,
.status.error {
  color: var(--epfl-red);
}
.bar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  grid-column: 2;
  grid-row: 1;
  justify-content: flex-end;
}
.problems-toggle,
.dismissed,
.submitted-note {
  grid-column: 1;
  font-size: 13px;
}
/* The fold: counts in their severity colours, the verb underlined like a link. */
.problems-toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  justify-self: start;
  padding: 0;
  border: none;
  background: transparent;
  font: inherit;
  font-size: 13px;
  color: var(--fg-muted);
  text-align: left;
  cursor: pointer;
}
.problems-toggle .chevron {
  transition: transform 0.15s ease;
}
.problems-toggle .chevron.open {
  transform: rotate(90deg);
}
.problems-toggle .err,
.problem-count.err {
  color: var(--epfl-red);
  font-weight: 600;
}
.problems-toggle .wrn,
.problem-count.wrn {
  color: var(--epfl-orange);
  font-weight: 600;
}
.problems-toggle .toggle-label {
  text-decoration: underline;
}
.problems-toggle:hover .toggle-label {
  color: var(--fg);
}
/* One row per experiment, capped so a long batch scrolls inside the bar. */
.problems {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-height: 40vh;
  overflow-y: auto;
  padding-top: 8px;
  border-top: 1px solid var(--border-subtle);
}
.problems-hint {
  margin: 0 0 4px;
  font-size: 12px;
  color: var(--fg-muted);
}
.problem-row {
  display: grid;
  grid-template-columns: minmax(0, 240px) minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  padding: 4px 8px;
  border-radius: var(--radius);
  font-size: 13px;
}
.problem-row:hover {
  background: var(--bg-subtle);
}
.problem-id {
  overflow: hidden;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.problem-counts {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
/* The lone problem: same look as a card's issue line, one line, ellipsised. */
.problem-issue {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  padding: 2px 0;
  border: none;
  background: transparent;
  font: inherit;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
}
.problem-issue.error {
  color: var(--epfl-red);
}
.problem-issue.warn {
  color: var(--epfl-orange);
}
.problem-issue .v-icon {
  flex: none;
}
.problem-msg {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.problem-issue:hover .problem-msg,
.problem-issue:focus-visible .problem-msg {
  text-decoration: underline;
}
.problem-dismiss,
.problem-more {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  justify-self: end;
  border: none;
  background: transparent;
  font: inherit;
  font-size: 13px;
  color: var(--fg-muted);
  cursor: pointer;
}
.problem-dismiss {
  padding: 3px;
  border-radius: var(--radius);
}
.problem-dismiss:hover,
.problem-dismiss:focus-visible {
  background: var(--bg-subtle);
  color: var(--fg);
}
.problem-more {
  padding: 0;
  text-decoration: underline;
  white-space: nowrap;
}
.problem-more:hover,
.problem-more:focus-visible {
  color: var(--fg);
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}
@media (max-width: 700px) {
  .problem-row {
    grid-template-columns: minmax(0, 1fr) auto;
  }
  .problem-id {
    grid-column: 1 / -1;
  }
}

.submitted-note,
.dismissed {
  color: var(--fg-muted);
}
.dismissed {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.dismissed .link {
  border: none;
  background: transparent;
  color: inherit;
  font: inherit;
  text-decoration: underline;
  cursor: pointer;
}
.dismissed .link:hover {
  color: var(--fg);
}
.draft-note,
.submit-error {
  grid-column: 1 / -1;
  margin: 0;
  font-size: 12px;
  color: var(--fg-muted);
}
.submit-error {
  font-size: 13px;
  color: var(--epfl-red);
}
.submitted-bar {
  border-color: var(--epfl-green-text);
}
.submitted-bar .btn {
  text-decoration: none;
}
/* Below ~700px the two columns cannot hold both the verdict and the buttons. */
@media (max-width: 700px) {
  .status-bar {
    grid-template-columns: minmax(0, 1fr);
  }
  .bar-actions {
    grid-column: 1;
    grid-row: auto;
    justify-content: flex-start;
    flex-wrap: wrap;
  }
}

.dialog-backdrop {
  position: fixed;
  inset: 0;
  z-index: 40;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(0, 0, 0, 0.45);
}
.dialog {
  width: min(560px, 100%);
  max-height: 90vh;
  overflow-y: auto;
  background: var(--bg);
}
.dialog-recap {
  margin: 0 0 16px;
  font-size: 13.5px;
  line-height: 1.5;
  color: var(--fg-muted);
}
.dialog-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px 16px;
}
.dialog-field {
  display: block;
  min-width: 0;
}
.dialog-field span {
  display: block;
  margin-bottom: 4px;
  font-size: 12.5px;
  font-weight: 600;
}
.dialog-field input {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid var(--border-strong);
  background: var(--bg);
  color: var(--fg);
  font: inherit;
  font-size: 13.5px;
  border-radius: var(--radius);
}
.dialog-field input:focus {
  outline: 2px solid var(--epfl-red);
  outline-offset: -1px;
}
.dialog-note {
  margin: 14px 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--fg-muted);
}
.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
