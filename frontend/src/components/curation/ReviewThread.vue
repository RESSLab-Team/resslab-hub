<script setup lang="ts">
/**
 * The submission's discussion, read-only: the pull request body (the summary
 * the contributor wrote) followed by every comment on the PR.
 *
 * Replying, requesting changes and approving still happen on GitHub — the hub
 * has no per-user identity to sign a decision with until #247, so this panel
 * shows the conversation and links into it rather than pretending to own it.
 */
import type { CurationComment } from '@/backend'
import { useCurationStore } from '@/stores/curation'
import { formatAge } from '@/utils/curation'
import { mdiAlertOutline, mdiOpenInNew, mdiRefresh } from '@mdi/js'
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{
  prNumber: number
  prUrl: string
}>()

const { locale } = useI18n({ useScope: 'global' })
const store = useCurationStore()

const items = ref<CurationComment[]>([])
const state = ref<'loading' | 'ready' | 'error'>('loading')

async function load(force = false): Promise<void> {
  state.value = 'loading'
  try {
    items.value = await store.fetchComments(props.prNumber, force)
    state.value = 'ready'
  } catch {
    state.value = 'error'
  }
}

watch(
  () => props.prNumber,
  () => load(),
  { immediate: true }
)

/** Comment bodies are GitHub markdown from a third party — sanitize, always. */
function bodyHtml(body: string): string {
  if (!body.trim()) return ''
  return DOMPurify.sanitize(marked.parse(body, { gfm: true, async: false }) as string)
}
</script>

<template>
  <div class="thread">
    <div class="thread-head">
      <p class="sech">{{ $t('curation.notes.title') }}</p>
      <button
        class="icon-btn"
        :disabled="state === 'loading'"
        type="button"
        :title="$t('curation.notes.refresh')"
        @click="load(true)"
      >
        <v-icon :icon="mdiRefresh" size="15" />
      </button>
    </div>

    <p v-if="state === 'loading'" class="state">{{ $t('curation.notes.loading') }}</p>
    <p v-else-if="state === 'error'" class="state">
      <v-icon :icon="mdiAlertOutline" size="14" />
      {{ $t('curation.notes.error') }}
      <button class="linkish" type="button" @click="load(true)">
        {{ $t('curation.retry') }}
      </button>
    </p>
    <p v-else-if="!items.length" class="state">{{ $t('curation.notes.empty') }}</p>

    <ol v-else class="msgs">
      <li v-for="item in items" :key="item.id" class="msg" :class="{ body: item.is_body }">
        <div class="msg-head">
          <span class="who">{{ item.author || $t('curation.notes.unknown_author') }}</span>
          <span v-if="item.author_type === 'Bot'" class="tag">{{ $t('curation.notes.bot') }}</span>
          <span v-if="item.is_body" class="tag">{{ $t('curation.notes.summary') }}</span>
          <span class="when">{{ formatAge(item.created_at, locale) }}</span>
          <a
            class="jump"
            :href="item.html_url"
            target="_blank"
            rel="noreferrer"
            :title="$t('curation.notes.open_discussion')"
          >
            <v-icon :icon="mdiOpenInNew" size="13" />
          </a>
        </div>
        <!-- eslint-disable-next-line vue/no-v-html -- sanitized by DOMPurify above -->
        <div v-if="item.body.trim()" class="md" v-html="bodyHtml(item.body)" />
        <p v-else class="state">{{ $t('curation.notes.no_body') }}</p>
      </li>
    </ol>

    <p class="notes-text">{{ $t('curation.notes.on_github') }}</p>
    <a class="notes-link" :href="prUrl" target="_blank" rel="noreferrer">
      {{ $t('curation.notes.open_discussion') }} →
    </a>
  </div>
</template>

<style scoped>
.thread {
  margin-top: 28px;
}
.thread-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
}
.sech {
  flex: 1;
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-weight: 700;
  margin: 0 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}
.icon-btn {
  border: 0;
  background: none;
  color: var(--fg-subtle);
  cursor: pointer;
  padding: 0 0 8px;
}
.icon-btn:hover:not([disabled]) {
  color: var(--epfl-red);
}
.icon-btn[disabled] {
  opacity: 0.4;
  cursor: default;
}
.state {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0 0 12px;
  font-size: 12.5px;
  color: var(--fg-muted);
}
.linkish {
  border: 0;
  background: none;
  padding: 0;
  font-size: 12.5px;
  font-weight: 500;
  color: var(--epfl-red);
  cursor: pointer;
}

/* ── messages ── */
.msgs {
  list-style: none;
  margin: 0 0 16px;
  padding: 0;
}
.msg {
  padding: 12px 0;
  border-top: 1px solid var(--border-subtle);
}
.msg:first-child {
  border-top: 0;
  padding-top: 0;
}
/* The PR body is the submission summary, not a reply — set it on the subtle
   ground so the conversation proper reads as everything below it. */
.msg.body {
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-left: 2px solid var(--fg);
  background: var(--bg-subtle);
}
.msg-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 7px;
  margin-bottom: 6px;
}
.who {
  font-size: 12.5px;
  font-weight: 600;
}
.tag {
  font-family: var(--font-mono);
  font-size: 9.5px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 2px 5px;
  border: 1px solid var(--border-strong);
  color: var(--fg-subtle);
}
.when {
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: 10.5px;
  color: var(--fg-subtle);
}
.jump {
  color: var(--fg-subtle);
  line-height: 1;
}
.jump:hover {
  color: var(--epfl-red);
}

.notes-text {
  font-size: 13px;
  color: var(--fg-muted);
  line-height: 1.55;
  margin: 0 0 8px;
}
.notes-link {
  font-size: 13px;
  font-weight: 500;
  color: var(--epfl-red);
  text-decoration: none;
}

/* Rendered comment markdown — the compact subset of the README renderer. */
.md {
  font-size: 13px;
  line-height: 1.55;
  overflow-wrap: anywhere;
}
.md :deep(h1),
.md :deep(h2),
.md :deep(h3) {
  margin: 12px 0 6px;
  font-size: 13px;
  font-weight: 700;
}
.md :deep(p) {
  margin: 0 0 8px;
}
.md :deep(p:last-child) {
  margin-bottom: 0;
}
.md :deep(ul),
.md :deep(ol) {
  margin: 0 0 8px;
  padding-left: 18px;
}
.md :deep(li) {
  margin: 2px 0;
}
.md :deep(a) {
  color: var(--epfl-red);
}
.md :deep(code) {
  padding: 1px 4px;
  border-radius: 3px;
  background: var(--bg-subtle);
  font-size: 11.5px;
}
.md :deep(pre) {
  margin: 0 0 8px;
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg-subtle);
  overflow-x: auto;
  font-size: 11.5px;
}
.md :deep(pre code) {
  padding: 0;
  background: none;
}
.md :deep(blockquote) {
  margin: 0 0 8px;
  padding-left: 10px;
  border-left: 2px solid var(--border-strong);
  color: var(--fg-muted);
}
.md :deep(img) {
  max-width: 100%;
}
.md :deep(table) {
  display: block;
  max-width: 100%;
  overflow-x: auto;
  font-size: 11.5px;
}
</style>
