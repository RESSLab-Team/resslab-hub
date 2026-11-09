<script setup lang="ts">
/**
 * The warning at the top of a specimen drawer when the row is still
 * unverified (#253). A curator also gets the button that opens the
 * verification pull request, or a link to the one already open.
 */
import { useAuthStore } from '@/stores/auth'
import { errorDetail, useVerificationStore } from '@/stores/verification'
import { CONTRIBUTION_DATABASES } from '@/utils/contribution'
import type { DatabaseId } from '@/utils/navigation'
import { mdiOpenInNew } from '@mdi/js'
import { computed, onMounted, ref } from 'vue'

const props = defineProps<{
  databaseId: DatabaseId
  rowId: string
}>()

const auth = useAuthStore()
const verification = useVerificationStore()

const curator = computed(() => auth.hasRole('curator'))
const type = computed(() => CONTRIBUTION_DATABASES[props.databaseId].type)
const pending = computed(() => verification.pendingFor(type.value, props.rowId))

const busy = ref(false)
const failed = ref(false)
const failure = ref<string | undefined>()

onMounted(() => {
  // The list says which rows already have a pull request open.
  if (curator.value) verification.fetchList()
})

async function verify(): Promise<void> {
  busy.value = true
  failed.value = false
  failure.value = undefined
  try {
    await verification.verify(type.value, [props.rowId])
  } catch (caught) {
    failed.value = true
    failure.value = errorDetail(caught)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="unverified-notice" role="note">
    <div class="un-head">
      <span class="un-tag">{{ $t('commons.unverified.tag') }}</span>
      <span class="un-text">{{ $t('commons.unverified.notice') }}</span>
    </div>
    <div v-if="curator" class="un-actions">
      <a
        v-if="pending"
        class="un-link"
        :href="pending.pr_url"
        target="_blank"
        rel="noopener noreferrer"
      >
        {{ $t('commons.unverified.pending', { number: pending.pr_number }) }}
        <v-icon :icon="mdiOpenInNew" size="11" />
      </a>
      <button
        v-else
        class="btn btn-secondary btn-sm"
        type="button"
        :disabled="busy"
        @click="verify"
      >
        {{ busy ? $t('commons.unverified.opening') : $t('commons.unverified.verify') }}
      </button>
      <span v-if="!pending" class="un-hint">{{ $t('commons.unverified.verify_hint') }}</span>
    </div>
    <div v-if="failed" class="un-error" role="alert">
      {{ $t('commons.unverified.failed') }}
      <span v-if="failure" class="un-detail">{{ failure }}</span>
    </div>
  </div>
</template>

<style scoped>
/* A hairline box with an orange rule on the left: orange is too light for
   text, so the words stay in --fg (see --warning in epfl-tokens.css). */
.unverified-notice {
  border: 1px solid var(--border);
  border-left: 3px solid var(--warning);
  padding: 12px 14px;
  margin-bottom: 18px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.un-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
}
.un-tag {
  font-size: var(--title-panel-size);
  text-transform: uppercase;
  letter-spacing: var(--title-panel-tracking);
  font-weight: var(--title-panel-weight);
  color: var(--fg);
  flex: 0 0 auto;
}
.un-text {
  font-size: 13px;
  line-height: 1.45;
  color: var(--fg);
}
.un-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.un-hint {
  font-size: 12px;
  color: var(--fg-muted);
}
.un-link {
  font-size: 13px;
  color: var(--fg);
  text-decoration: none;
  border-bottom: 1px solid var(--border);
}
.un-link:hover {
  color: var(--link-hover);
  border-bottom-color: var(--link-hover);
}
.un-error {
  font-size: 12px;
  color: var(--fg);
}
.un-detail {
  display: block;
  color: var(--fg-muted);
  margin-top: 2px;
}
</style>
