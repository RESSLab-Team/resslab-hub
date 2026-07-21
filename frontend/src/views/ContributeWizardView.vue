<script setup lang="ts">
import CpIcon from '@/components/contribute/CpIcon.vue'
import StepDatabase from '@/components/contribute/StepDatabase.vue'
import StepFiles from '@/components/contribute/StepFiles.vue'
import StepMetadata from '@/components/contribute/StepMetadata.vue'
import StepQuality from '@/components/contribute/StepQuality.vue'
import StepReview from '@/components/contribute/StepReview.vue'
import { useContributionStore } from '@/stores/contribution'
import { publicPath } from '@/utils/common'
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import '@/assets/styles/contribution.css'

const router = useRouter()
const store = useContributionStore()

const STEPS = [
  { key: 'database', component: StepDatabase },
  { key: 'metadata', component: StepMetadata },
  { key: 'files', component: StepFiles },
  { key: 'quality', component: StepQuality },
  { key: 'review', component: StepReview }
] as const

const isLastStep = computed(() => store.currentStep === STEPS.length - 1)

/** Step 1 is the only hard gate: every later step needs a target schema. */
const canContinue = computed(() => store.currentStep > 0 || store.database !== null)

function goTo(index: number): void {
  // Forward jumps stay blocked until a database is chosen, but stepping back is
  // always allowed so a mistake on step 1 is cheap to fix.
  if (index > store.currentStep && !canContinue.value) return
  store.currentStep = Math.min(Math.max(index, 0), STEPS.length - 1)
}

function back(): void {
  if (store.currentStep === 0) {
    router.push('/')
    return
  }
  goTo(store.currentStep - 1)
}
</script>

<template>
  <div class="cp cp-wizard">
    <aside class="cp-wside">
      <router-link class="cp-logo" to="/">
        <img :src="publicPath + 'logo/EPFL_Logo_184X53.svg'" alt="EPFL" />
        <span class="div" />
        <span class="sitename">{{ $t('shell.brand_name') }}</span>
      </router-link>
      <div class="wedition">{{ $t('contribute.wizard.draft') }}</div>

      <div class="cp-steps">
        <button
          v-for="(step, index) in STEPS"
          :key="step.key"
          class="cp-step"
          :class="
            index < store.currentStep ? 'done' : index === store.currentStep ? 'active' : 'todo'
          "
          type="button"
          @click="goTo(index)"
        >
          <span class="num">
            <cp-icon v-if="index < store.currentStep" :size="13" :width="2.6" name="check" />
            <template v-else>{{ index + 1 }}</template>
          </span>
          <span>
            <span class="lbl">{{ $t(`contribute.steps.${step.key}`) }}</span>
            <span class="sub">{{ $t(`contribute.steps.${step.key}_sub`) }}</span>
          </span>
        </button>
      </div>

      <div class="cp-wsave">
        <cp-icon :size="13" name="save" />
        {{ $t('contribute.wizard.autosave') }}
      </div>
    </aside>

    <div class="cp-wmain">
      <div class="cp-wbody">
        <component :is="STEPS[store.currentStep].component" />
      </div>

      <div class="cp-wfoot">
        <button class="cp-btn ghost" type="button" @click="back">
          <cp-icon :size="15" name="arrowLeft" />
          {{
            store.currentStep === 0 ? $t('contribute.wizard.cancel') : $t('contribute.wizard.back')
          }}
        </button>
        <div class="left">
          {{
            $t('contribute.wizard.step_of', { current: store.currentStep + 1, total: STEPS.length })
          }}
        </div>
        <button
          v-if="!isLastStep"
          class="cp-btn primary"
          :disabled="!canContinue"
          type="button"
          @click="goTo(store.currentStep + 1)"
        >
          {{ $t('contribute.wizard.continue') }}
          <cp-icon :size="15" name="arrowRight" />
        </button>
        <button v-else class="cp-btn primary" disabled type="button">
          <cp-icon :size="15" name="send" />
          {{ $t('contribute.review.submit') }}
        </button>
      </div>
    </div>
  </div>
</template>
