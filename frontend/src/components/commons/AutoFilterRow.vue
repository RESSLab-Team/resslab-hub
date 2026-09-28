<script setup lang="ts">
/**
 * One auto-generated filter: a collapsed summary row that expands into the
 * input its column's type calls for ({@link FilterInput}).
 *
 * The expanded body is behind `v-if`, so a rail of sixty filters mounts sixty
 * buttons and nothing else — the ECharts brushes exist only for the rows the
 * user actually opens.
 */
import FilterInput from '@/components/commons/FilterInput.vue'
import TextSubscript from '@/components/commons/TextSubscript.vue'
import type { LabeledFilter } from '@/composables/useAutoFilters'
import { formatFilterValue, type Value } from '@/utils/common'
import { mdiChevronDown, mdiClose } from '@mdi/js'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{
  filter: LabeledFilter
  value?: Value
  open: boolean
}>()
const emit = defineEmits<{
  (e: 'update', value?: Value): void
  (e: 'update:open', value: boolean): void
}>()

const { t } = useI18n({ useScope: 'global' })

const active = computed<boolean>(() => props.value != null && props.value !== '')

/* ---- collapsed summary ---- */

const summary = computed<string>(() =>
  props.value == null ? '' : formatFilterValue(props.value, t)
)
</script>

<template>
  <div class="afr-row" :class="{ 'is-open': open, 'is-active': active }">
    <button class="afr-head" :aria-expanded="open" @click="emit('update:open', !open)">
      <v-icon class="afr-caret" :icon="mdiChevronDown" size="14" />
      <span class="afr-label">
        {{ filter.label }}
        <span v-if="filter.unit" class="afr-unit">[{{ filter.unit }}]</span>
        <span v-else-if="filter.symbol" class="afr-unit">
          <text-subscript :text="filter.symbol" />
        </span>
      </span>
      <span v-if="active" class="afr-summary">{{ summary }}</span>
      <span
        v-if="active"
        class="afr-clear"
        role="button"
        :aria-label="$t('commons.reset_filters')"
        @click.stop="emit('update', undefined)"
      >
        <v-icon :icon="mdiClose" size="11" />
      </span>
    </button>

    <div v-if="open" class="afr-body">
      <filter-input :filter="filter" :value="value" @update="emit('update', $event)" />
    </div>
  </div>
</template>
