<script setup lang="ts">
import type { Searches, Value } from '@/utils/common'
import { mdiChevronLeft, mdiChevronRight, mdiClose } from '@mdi/js'
import { computed, ref, watch } from 'vue'

export interface FilterRailOption {
  label: string
  /** Search value sent to the backend (strings only; booleans as 'true'/'false'). */
  value: string
}

export interface FilterRailGroup {
  /** Search field key, e.g. ConnectionField.ConnectionType. */
  key: string
  label: string
  /** mdi icon path, shown in the collapsed icon strip. */
  icon: string
  type: 'chips' | 'range'
  /** Chip options ('chips' groups). */
  options?: (string | FilterRailOption)[]
  /** Use the red active style for this group's chips (primary dimension). */
  redChips?: boolean
  /** Data bounds for 'range' groups — drives placeholders and the track fill. */
  min?: number
  max?: number
}

const props = withDefaults(
  defineProps<{
    groups: FilterRailGroup[]
    searches: Searches
    position?: 'left' | 'right'
    collapsed?: boolean
    /** Rendered inside the narrow-viewport overlay drawer. */
    asOverlay?: boolean
  }>(),
  {
    position: 'right',
    collapsed: false,
    asOverlay: false
  }
)
const emit = defineEmits<{
  (e: 'change:searches', key: string, value?: Value): void
  (e: 'update:collapsed', value: boolean): void
  (e: 'close'): void
}>()

const openGroup = ref<string | null>(null)
watch(
  () => props.collapsed,
  () => (openGroup.value = null)
)

function normalizeOptions(group: FilterRailGroup): FilterRailOption[] {
  return (group.options ?? []).map((option) =>
    typeof option === 'string' ? { label: option, value: option } : option
  )
}

function isChipActive(group: FilterRailGroup, option: FilterRailOption): boolean {
  const current = props.searches[group.key]
  return current != null && String(current) === option.value
}

function toggleChip(group: FilterRailGroup, option: FilterRailOption): void {
  emit('change:searches', group.key, isChipActive(group, option) ? undefined : option.value)
}

/* ---- ranges (backend `min<<max` between syntax, as used by the charts) ---- */

function rangeBounds(group: FilterRailGroup): [string, string] {
  const current = props.searches[group.key]
  if (typeof current === 'string' && current.includes('<<')) {
    const [lo, hi] = current.split('<<', 2)
    return [lo, hi]
  }
  return ['', '']
}

function changeRange(group: FilterRailGroup, bound: 0 | 1, raw: string): void {
  const bounds = rangeBounds(group)
  bounds[bound] = raw.trim()
  let [lo, hi] = bounds
  if (lo === '' && hi === '') {
    emit('change:searches', group.key, undefined)
    return
  }
  // Fall back to the group's data bounds when only one input is filled.
  lo = lo === '' ? String(group.min ?? '') : lo
  hi = hi === '' ? String(group.max ?? '') : hi
  if (lo === '' || hi === '') {
    return
  }
  emit('change:searches', group.key, `${lo}<<${hi}`)
}

function rangeFill(group: FilterRailGroup): { left: string; right: string } | null {
  if (group.min == null || group.max == null) {
    return null
  }
  const [lo, hi] = rangeBounds(group)
  if (lo === '' || hi === '') {
    return null
  }
  const span = group.max - group.min
  const left = Math.max(0, Math.min(100, ((Number(lo) - group.min) / span) * 100))
  const right = Math.max(0, Math.min(100, ((group.max - Number(hi)) / span) * 100))
  return { left: `${left}%`, right: `${right}%` }
}

/* ---- head ---- */

function isGroupActive(group: FilterRailGroup): boolean {
  return props.searches[group.key] != null
}

const activeCount = computed<number>(() => props.groups.filter(isGroupActive).length)

function resetAll(): void {
  props.groups.filter(isGroupActive).forEach((group) => {
    emit('change:searches', group.key, undefined)
  })
}
</script>

<template>
  <!-- Collapsed: icon strip with red-dot badges; click an icon for a popover. -->
  <aside
    v-if="collapsed && !asOverlay"
    class="dash-filters dash-filters-collapsed"
    :class="{ 'dash-filters-right': position === 'right' }"
  >
    <button
      class="dash-filters-collapse-btn"
      :title="$t('commons.expand_filters')"
      :aria-label="$t('commons.expand_filters')"
      @click="emit('update:collapsed', false)"
    >
      <v-icon :icon="position === 'right' ? mdiChevronLeft : mdiChevronRight" size="14" />
    </button>
    <div class="dash-filters-collapsed-list">
      <div
        v-for="group in groups"
        :key="group.key"
        class="dash-filter-icon-row"
        :class="{ 'is-open': openGroup === group.key }"
      >
        <button
          class="dash-filter-icon"
          :class="{ 'is-active': isGroupActive(group) }"
          :title="group.label"
          :aria-label="group.label"
          @click="openGroup = openGroup === group.key ? null : group.key"
        >
          <v-icon :icon="group.icon" size="16" />
          <span v-if="isGroupActive(group)" class="dash-filter-icon-dot" />
        </button>
        <div
          v-if="openGroup === group.key"
          class="dash-filter-popover"
          :class="position === 'right' ? 'dash-filter-popover-left' : 'dash-filter-popover-right'"
        >
          <div class="dash-filter-popover-head">
            <span>{{ group.label }}</span>
            <button
              class="dash-filter-popover-x"
              :aria-label="$t('commons.close')"
              @click="openGroup = null"
            >
              <v-icon :icon="mdiClose" size="12" />
            </button>
          </div>
          <div class="dash-filter-popover-body">
            <div v-if="group.type === 'chips'" class="filter-chips">
              <button
                v-for="option in normalizeOptions(group)"
                :key="option.value"
                class="chip"
                :class="{
                  on: isChipActive(group, option) && !group.redChips,
                  'on-red': isChipActive(group, option) && group.redChips
                }"
                @click="toggleChip(group, option)"
              >
                {{ option.label }}
              </button>
            </div>
            <template v-else>
              <div v-if="rangeFill(group)" class="range-track">
                <div class="range-fill" :style="rangeFill(group)!" />
              </div>
              <div class="range-row">
                <input
                  type="number"
                  :placeholder="group.min != null ? String(group.min) : $t('commons.range_min')"
                  :value="rangeBounds(group)[0]"
                  @change="changeRange(group, 0, ($event.target as HTMLInputElement).value)"
                />
                <input
                  type="number"
                  :placeholder="group.max != null ? String(group.max) : $t('commons.range_max')"
                  :value="rangeBounds(group)[1]"
                  @change="changeRange(group, 1, ($event.target as HTMLInputElement).value)"
                />
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>
    <button
      v-if="activeCount > 0"
      class="dash-filters-collapsed-reset"
      :title="$t('commons.reset_all_filters')"
      @click="resetAll"
    >
      <v-icon :icon="mdiClose" size="11" />
    </button>
  </aside>

  <!-- Expanded: full rail. The overlay variant shows a close button instead. -->
  <aside
    v-else
    class="dash-filters"
    :class="{
      'dash-filters-right': position === 'right' && !asOverlay,
      'dash-filters-overlay': asOverlay
    }"
  >
    <div class="dash-filters-head">
      <div class="dash-filters-head-l">
        <h6>{{ $t('commons.filters') }}</h6>
        <span v-if="activeCount > 0" class="dash-filters-active-count">{{ activeCount }}</span>
      </div>
      <div class="dash-filters-head-r">
        <button class="reset" @click="resetAll">{{ $t('commons.reset_all') }}</button>
        <button
          v-if="asOverlay"
          class="dash-filters-collapse-btn"
          :title="$t('commons.close_filters')"
          :aria-label="$t('commons.close_filters')"
          @click="emit('close')"
        >
          <v-icon :icon="mdiClose" size="14" />
        </button>
        <button
          v-else
          class="dash-filters-collapse-btn"
          :title="$t('commons.collapse_filters')"
          :aria-label="$t('commons.collapse_filters')"
          @click="emit('update:collapsed', true)"
        >
          <v-icon :icon="position === 'right' ? mdiChevronRight : mdiChevronLeft" size="14" />
        </button>
      </div>
    </div>

    <div v-for="group in groups" :key="group.key" class="filter-group">
      <div class="filter-group-head">
        {{ group.label }}
        <span v-if="group.type === 'chips'" class="count">
          {{ normalizeOptions(group).length }}
        </span>
      </div>
      <div v-if="group.type === 'chips'" class="filter-chips">
        <button
          v-for="option in normalizeOptions(group)"
          :key="option.value"
          class="chip"
          :class="{
            on: isChipActive(group, option) && !group.redChips,
            'on-red': isChipActive(group, option) && group.redChips
          }"
          @click="toggleChip(group, option)"
        >
          {{ option.label }}
        </button>
      </div>
      <template v-else>
        <div v-if="rangeFill(group)" class="range-track">
          <div class="range-fill" :style="rangeFill(group)!" />
        </div>
        <div class="range-row">
          <input
            type="number"
            :placeholder="group.min != null ? String(group.min) : $t('commons.range_min')"
            :value="rangeBounds(group)[0]"
            @change="changeRange(group, 0, ($event.target as HTMLInputElement).value)"
          />
          <input
            type="number"
            :placeholder="group.max != null ? String(group.max) : $t('commons.range_max')"
            :value="rangeBounds(group)[1]"
            @change="changeRange(group, 1, ($event.target as HTMLInputElement).value)"
          />
        </div>
      </template>
    </div>
  </aside>
</template>
