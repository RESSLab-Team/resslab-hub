<script setup lang="ts">
import CpIcon from '@/components/contribute/CpIcon.vue'
import { useContributionStore } from '@/stores/contribution'
import { DATABASES } from '@/utils/navigation'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })
const store = useContributionStore()

const notSet = t('contribute.review.not_set')

const qualitySummary = computed(() => {
  const response = store.response
  switch (store.status) {
    case 'pass':
      return t('contribute.quality.passed')
    case 'warn':
    case 'fail':
      return `${response?.error_count ?? 0} ${t('contribute.quality.failed').toLowerCase()}`
    case 'unsupported':
      return t('contribute.database.no_quality_check')
    case 'error':
      return t('contribute.quality.error')
    default:
      return t('contribute.review.quality_not_run')
  }
})

const rows = computed(() => [
  {
    key: t('contribute.review.database'),
    value: DATABASES.find((entry) => entry.id === store.database)?.name ?? notSet
  },
  {
    key: t('contribute.review.experiments'),
    value: store.experimentCount
      ? t('contribute.review.experiments_value', {
          count: store.experimentCount,
          withId: store.specimenIds.length
        })
      : notSet
  },
  { key: t('contribute.review.program'), value: store.program || notSet },
  { key: t('contribute.review.year'), value: store.year || notSet },
  { key: t('contribute.review.doi'), value: store.doi || notSet },
  {
    key: t('contribute.review.fields_filled'),
    value: store.config
      ? t('contribute.review.fields_filled_value', {
          filled: store.filledCount,
          total: store.config.columns.length * store.experimentCount
        })
      : notSet
  },
  { key: t('contribute.review.quality'), value: qualitySummary.value }
])
</script>

<template>
  <div>
    <div class="cp-wsectionlabel">
      {{ $t('contribute.wizard.step_label', { current: 5, total: 5 }) }}
    </div>
    <h2 class="cp-wh">{{ $t('contribute.review.title') }}</h2>
    <p class="cp-wsub">{{ $t('contribute.review.subtitle') }}</p>

    <div class="cp-fieldset">
      <div class="cp-fset-h">{{ $t('contribute.review.summary') }}</div>
      <div class="cp-fset-body" style="padding: 8px 22px">
        <div v-for="row in rows" :key="row.key" class="cp-prop">
          <span class="pk">{{ row.key }}</span>
          <span class="pv">{{ row.value }}</span>
        </div>
      </div>
    </div>

    <div class="cp-eduflag" style="border-left-color: var(--epfl-orange)">
      <cp-icon :size="15" name="alert" />
      <span>{{ $t('contribute.review.draft_notice') }}</span>
    </div>
  </div>
</template>
