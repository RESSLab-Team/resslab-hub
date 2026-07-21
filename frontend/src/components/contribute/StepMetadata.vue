<script setup lang="ts">
import GridEditor from '@/components/contribute/GridEditor.vue'
import { useContributionStore } from '@/stores/contribution'
import { DATABASES } from '@/utils/navigation'
import { computed } from 'vue'

const store = useContributionStore()

const databaseName = computed(
  () => DATABASES.find((entry) => entry.id === store.database)?.name ?? ''
)
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

    <GridEditor v-else />
  </div>
</template>
