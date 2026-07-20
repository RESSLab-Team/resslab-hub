<script setup lang="ts">
import CpIcon from '@/components/contribute/CpIcon.vue'
import { useContributionStore } from '@/stores/contribution'
import { fieldLabel } from '@/utils/contribution'
import { DATABASES } from '@/utils/navigation'
import { computed } from 'vue'

const store = useContributionStore()

const databaseName = computed(
  () => DATABASES.find((entry) => entry.id === store.database)?.name ?? ''
)
const columns = computed(() => store.config?.columns ?? [])
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
      <div class="cp-metasum">
        <cp-icon :size="15" name="layers" />
        <b>{{ $t('contribute.metadata.summary_fields', { count: columns.length }) }}</b>
        <span>·</span>
        <span class="mut">{{ $t('contribute.metadata.summary_blank') }}</span>
      </div>

      <div class="cp-fieldset">
        <div class="cp-fset-h">
          {{ $t('contribute.metadata.fields') }}
          <span class="ct">{{ store.filledCount }} / {{ columns.length }}</span>
        </div>
        <div class="cp-fset-body">
          <div class="cp-grid2">
            <div v-for="column in columns" :key="column" class="cp-field">
              <label class="cp-label" :for="`cp-f-${column}`">
                {{ fieldLabel(store.database, column) }}
                <span v-if="column === 'id'" class="req">*</span>
              </label>
              <input
                :id="`cp-f-${column}`"
                v-model="store.values[column]"
                class="cp-input"
                type="text"
              />
            </div>
          </div>

          <div class="cp-metanote">
            <cp-icon :size="15" name="info" />
            <span>{{ $t('contribute.metadata.id_required') }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
