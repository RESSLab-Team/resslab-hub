<script setup lang="ts">
import { categoryFor, colorFor } from '@/utils/mapCategories'
import { treemap } from '@/utils/mapGlyph'
import { formatCount, mixOf, sumCounts, type Counts } from '@/utils/mapSites'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

/**
 * The category mix of a site or a cluster: a thin strip or a treemap on top,
 * then one bar per category, biggest first. Used by the tooltip, the panel
 * and the sheet.
 */
const props = withDefaults(
  defineProps<{
    counts: Counts
    /** what sits above the bars */
    lead?: 'strip' | 'tree'
    /** treemap height in viewBox units (the width is 332) */
    treeHeight?: number
    /** bar rows before "+ N more categories" */
    max?: number
  }>(),
  { lead: 'strip', treeHeight: 132, max: 9 }
)

const { t } = useI18n({ useScope: 'global' })

const TREE_WIDTH = 332

const items = computed(() => mixOf(props.counts))
const total = computed(() => sumCounts(props.counts))
const top = computed(() => items.value[0]?.n ?? 1)
const shown = computed(() => items.value.slice(0, props.max))
const rest = computed(() => items.value.length - shown.value.length)

const label = (id: Parameters<typeof categoryFor>[0]) => t(categoryFor(id).labelKey)

const cells = computed(() =>
  treemap(props.counts, 0, 0, TREE_WIDTH, props.treeHeight).map((cell) => ({
    ...cell,
    w: Math.max(0.5, cell.w - 2),
    h: Math.max(0.5, cell.h - 2),
    // Name and share when the cell is big enough, the bare count when it is small.
    text: cell.w > 78 && cell.h > 32 ? 'full' : cell.w > 26 && cell.h > 16 ? 'count' : 'none',
    share: total.value > 0 ? Math.round((cell.n / total.value) * 100) : 0
  }))
)
</script>

<template>
  <div class="mm">
    <div v-if="lead === 'strip'" class="mm-strip">
      <span
        v-for="item in items"
        :key="item.id"
        :style="{ flexGrow: item.n, background: colorFor(item.id) }"
      ></span>
    </div>
    <svg
      v-else
      class="mm-tree"
      :viewBox="`0 0 ${TREE_WIDTH} ${treeHeight}`"
      :style="{ aspectRatio: `${TREE_WIDTH} / ${treeHeight}` }"
      role="img"
      :aria-label="items.map((item) => `${label(item.id)} ${item.n}`).join(', ')"
    >
      <g v-for="cell in cells" :key="cell.id">
        <rect :x="cell.x" :y="cell.y" :width="cell.w" :height="cell.h" :fill="colorFor(cell.id)">
          <title>{{ label(cell.id) }} · {{ formatCount(cell.n) }}</title>
        </rect>
        <template v-if="cell.text === 'full'">
          <text class="mm-tree-l" :x="cell.x + 7" :y="cell.y + 16">{{ label(cell.id) }}</text>
          <text class="mm-tree-n" :x="cell.x + 7" :y="cell.y + 29">
            {{ formatCount(cell.n) }} · {{ cell.share }}%
          </text>
        </template>
        <text
          v-else-if="cell.text === 'count'"
          class="mm-tree-n mm-tree-s"
          :x="cell.x + 5"
          :y="cell.y + 13"
        >
          {{ cell.n }}
        </text>
      </g>
    </svg>
    <div class="mm-bars">
      <div v-for="item in shown" :key="item.id" class="mm-bar">
        <span class="mm-sq" :style="{ background: colorFor(item.id) }"></span>
        <span class="mm-bar-l">{{ label(item.id) }}</span>
        <span class="mm-bar-t">
          <span
            :style="{ width: `${(item.n / top) * 100}%`, background: colorFor(item.id) }"
          ></span>
        </span>
        <span class="mm-bar-n">{{ formatCount(item.n) }}</span>
      </div>
      <div v-if="rest > 0" class="mm-more">{{ t('map.more_categories', rest) }}</div>
    </div>
  </div>
</template>

<style scoped>
.mm-strip {
  display: flex;
  height: 4px;
  gap: 1px;
  margin-bottom: 10px;
}
.mm-strip span {
  display: block;
  min-width: 1px;
}
.mm-tree {
  display: block;
  width: 100%;
  margin-bottom: 12px;
}
.mm-tree text {
  fill: var(--on-primary);
  pointer-events: none;
}
.mm-tree-l {
  font-family: var(--font-sans);
  font-size: 11px;
  font-weight: 700;
}
.mm-tree-n {
  font-family: var(--font-mono);
  font-size: 10.5px;
  font-feature-settings: 'tnum';
  opacity: 0.9;
}
.mm-tree-s {
  font-size: 9.5px;
}
.mm-bars {
  display: grid;
  gap: 5px;
}
.mm-bar {
  display: grid;
  grid-template-columns: 11px 104px minmax(0, 1fr) 38px;
  align-items: center;
  gap: 8px;
  font-size: 11.5px;
}
.mm-sq {
  width: 11px;
  height: 11px;
}
.mm-bar-l {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.mm-bar-t {
  position: relative;
  height: 2px;
  background: var(--border);
}
.mm-bar-t span {
  position: absolute;
  left: 0;
  top: -1px;
  height: 4px;
}
.mm-bar-n {
  font-family: var(--font-mono);
  font-size: 11px;
  font-feature-settings: 'tnum';
  text-align: right;
}
.mm-more {
  padding-left: 19px;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--fg-subtle);
}
</style>
