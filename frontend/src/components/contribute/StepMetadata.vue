<script setup lang="ts">
import CpIcon from '@/components/contribute/CpIcon.vue'
import ExperimentCards from '@/components/contribute/ExperimentCards.vue'
import GridEditor from '@/components/contribute/GridEditor.vue'
import { useContributionStore } from '@/stores/contribution'
import { DATABASES } from '@/utils/navigation'
import { computed, ref } from 'vue'

const store = useContributionStore()

const databaseName = computed(
  () => DATABASES.find((entry) => entry.id === store.database)?.name ?? ''
)

const view = ref<'grid' | 'cards'>('grid')
</script>

<template>
  <div>
    <div class="cp-wsectionlabel">
      {{ $t('contribute.wizard.step_label', { current: 2, total: 5 }) }}
      <template v-if="databaseName"> · {{ databaseName.toUpperCase() }}</template>
    </div>
    <h2 class="cp-wh">{{ $t('contribute.metadata.title') }}</h2>
    <p class="cp-wsub">{{ $t('contribute.metadata.subtitle') }}</p>

    <p v-if="!store.database" class="cp-hint">
      {{ $t('contribute.metadata.select_database_first') }}
    </p>

    <template v-else>
      <div class="cp-viewtoggle">
        <button
          class="cp-viewtab"
          type="button"
          :class="{ active: view === 'grid' }"
          @click="view = 'grid'"
        >
          <cp-icon :size="14" name="layers" />{{ $t('contribute.metadata.view_grid') }}
        </button>
        <button
          class="cp-viewtab"
          type="button"
          :class="{ active: view === 'cards' }"
          @click="view = 'cards'"
        >
          <cp-icon :size="14" name="info" />{{ $t('contribute.metadata.view_cards') }}
        </button>
      </div>

      <GridEditor v-if="view === 'grid'" />
      <ExperimentCards v-else />
    </template>
  </div>
</template>
