<script setup lang="ts">
import CpIcon from '@/components/contribute/CpIcon.vue'
</script>

<template>
  <div>
    <div class="cp-wsectionlabel">
      {{ $t('contribute.wizard.step_label', { current: 3, total: 5 }) }}
    </div>
    <h2 class="cp-wh">{{ $t('contribute.files.title') }}</h2>
    <p class="cp-wsub">{{ $t('contribute.files.subtitle') }}</p>

    <div class="cp-fieldset">
      <div class="cp-fset-h">
        {{ $t('contribute.files.timeseries') }}
        <span class="ct">{{ $t('contribute.files.optional_stub') }}</span>
      </div>
      <div class="cp-fset-body">
        <div class="cp-drop is-disabled">
          <cp-icon class="ic" :size="34" :width="1.5" name="upload" />
          <div class="big">{{ $t('contribute.files.timeseries_soon') }}</div>
          <div class="small">{{ $t('contribute.files.timeseries_kinds') }}</div>
        </div>
        <div class="cp-metanote">
          <cp-icon :size="15" name="info" />
          <span>{{ $t('contribute.files.note') }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
