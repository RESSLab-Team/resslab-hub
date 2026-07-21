<script setup lang="ts">
import CpIcon from '@/components/contribute/CpIcon.vue'
import { useContributionStore } from '@/stores/contribution'
import { CONTRIBUTION_DATABASES } from '@/utils/contribution'
import { DATABASES } from '@/utils/navigation'

const store = useContributionStore()
</script>

<template>
  <div>
    <div class="cp-wsectionlabel">
      {{ $t('contribute.wizard.step_label', { current: 1, total: 5 }) }}
    </div>
    <h2 class="cp-wh">{{ $t('contribute.database.title') }}</h2>
    <p class="cp-wsub">{{ $t('contribute.database.subtitle') }}</p>

    <div class="cp-field">
      <div class="cp-label">{{ $t('contribute.database.target') }} <span class="req">*</span></div>
      <div class="cp-chips">
        <button
          v-for="entry in DATABASES"
          :key="entry.id"
          class="cp-chip"
          :class="{ sel: store.database === entry.id }"
          type="button"
          @click="store.selectDatabase(entry.id)"
        >
          {{ entry.name }}
        </button>
      </div>
      <div
        v-if="store.database && !CONTRIBUTION_DATABASES[store.database].qualityCheckSupported"
        class="cp-hint"
      >
        {{ $t('contribute.database.no_quality_check') }}
      </div>
    </div>

    <div class="cp-fieldset" style="margin-top: 22px">
      <div class="cp-fset-h">
        {{ $t('contribute.database.source') }}
        <span class="ct">{{ $t('contribute.database.source_hint') }}</span>
      </div>
      <div class="cp-fset-body">
        <div class="cp-grid2">
          <div class="cp-field">
            <label class="cp-label" for="cp-program">
              {{ $t('contribute.database.program') }}
            </label>
            <input id="cp-program" v-model="store.program" class="cp-input" type="text" />
          </div>
          <div class="cp-field">
            <label class="cp-label" for="cp-year">{{ $t('contribute.database.year') }}</label>
            <input id="cp-year" v-model="store.year" class="cp-input" type="text" />
          </div>
        </div>
        <div class="cp-field" style="margin-bottom: 0">
          <label class="cp-label" for="cp-doi">{{ $t('contribute.database.doi') }}</label>
          <input id="cp-doi" v-model="store.doi" class="cp-input" type="text" />
          <div class="cp-hint">
            <cp-icon :size="13" name="info" />
            {{ $t('contribute.database.doi_hint') }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
