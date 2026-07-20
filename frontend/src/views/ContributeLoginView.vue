<script setup lang="ts">
import CpIcon from '@/components/contribute/CpIcon.vue'
import { useAuthStore, type SignInMethod } from '@/stores/auth'
import { useCountsStore } from '@/stores/counts'
import { publicPath } from '@/utils/common'
import { DATABASES } from '@/utils/navigation'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import '@/assets/styles/contribution.css'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const countsStore = useCountsStore()
onMounted(() => countsStore.fetch())

const email = ref('')

// Client-side domain shaping only — with no identity provider behind this,
// it demonstrates the intended eduGAIN check rather than enforcing anything.
const ACADEMIC = /@([\w-]+\.)*(edu|ac\.[a-z]{2}|[a-z-]+\.[a-z]{2})$/i
const PERSONAL = /@(gmail|yahoo|hotmail|outlook|icloud|proton|protonmail)\./i

const isPersonal = computed(() => PERSONAL.test(email.value))
const isValid = computed(() => ACADEMIC.test(email.value) && !isPersonal.value)
const showError = computed(() => email.value.length > 3 && !isValid.value)

const stats = computed(() => [
  { value: countsStore.total?.toLocaleString() ?? '—', label: 'contribute.gate.stat_tests' },
  { value: String(DATABASES.length), label: 'contribute.gate.stat_databases' }
])

function signIn(method: SignInMethod): void {
  authStore.signIn(method, method === 'email' ? email.value : '')
  const redirect = route.query.redirect
  router.push(typeof redirect === 'string' ? redirect : '/contribute/new')
}
</script>

<template>
  <div class="cp cp-gate">
    <aside class="cp-gate-aside">
      <router-link class="cp-logo" to="/">
        <img :src="publicPath + 'logo/EPFL_Logo_184X53.svg'" alt="EPFL" />
        <span class="div" />
        <span class="sitename">{{ $t('shell.brand_name') }}</span>
      </router-link>

      <div class="lead">
        {{ $t('contribute.gate.lead_before') }}<em>{{ $t('contribute.gate.lead_em') }}</em
        >{{ $t('contribute.gate.lead_after') }}
      </div>
      <p class="sub">{{ $t('contribute.gate.blurb') }}</p>

      <div class="gate-stats">
        <div v-for="stat in stats" :key="stat.label" class="gs">
          <b>{{ stat.value }}</b>
          <span>{{ $t(stat.label) }}</span>
        </div>
      </div>
    </aside>

    <div class="cp-gate-main">
      <div class="cp-authcard">
        <h2>{{ $t('contribute.gate.title') }}</h2>
        <p class="ah-sub">{{ $t('contribute.gate.subtitle') }}</p>

        <div class="cp-sso">
          <button class="cp-ssobtn" type="button" @click="signIn('tequila')">
            <span class="lg epfl">E</span>
            {{ $t('contribute.gate.sso_tequila') }}
            <span class="arr"><cp-icon name="chevronRight" /></span>
          </button>
          <button class="cp-ssobtn" type="button" @click="signIn('edugain')">
            <span class="lg edu"><cp-icon :size="14" name="shield" /></span>
            {{ $t('contribute.gate.sso_edugain') }}
            <span class="arr"><cp-icon name="chevronRight" /></span>
          </button>
          <button class="cp-ssobtn" type="button" @click="signIn('orcid')">
            <span class="lg orcid">iD</span>
            {{ $t('contribute.gate.sso_orcid') }}
            <span class="arr"><cp-icon name="chevronRight" /></span>
          </button>
        </div>

        <div class="cp-or">{{ $t('contribute.gate.or') }}</div>

        <div class="cp-field" :class="{ 'is-err': showError, 'is-ok': isValid }">
          <label class="cp-label" for="cp-email">
            {{ $t('contribute.gate.email_label') }} <span class="req">*</span>
          </label>
          <input
            id="cp-email"
            v-model="email"
            class="cp-input"
            :placeholder="$t('contribute.gate.email_placeholder')"
            type="email"
            @keydown.enter="isValid && signIn('email')"
          />
          <div v-if="showError" class="cp-hint err">
            <cp-icon :size="13" name="alert" />
            {{
              isPersonal
                ? $t('contribute.gate.email_error_personal')
                : $t('contribute.gate.email_error_domain')
            }}
          </div>
          <div v-else-if="isValid" class="cp-hint ok">
            <cp-icon :size="13" name="check" />
            {{ $t('contribute.gate.email_ok') }}
          </div>
        </div>

        <button
          class="cp-btn primary lg"
          :disabled="!isValid"
          style="width: 100%; justify-content: center"
          type="button"
          @click="signIn('email')"
        >
          {{ $t('contribute.gate.magic_link') }}
        </button>

        <div class="cp-eduflag">
          <cp-icon :size="15" name="lock" />
          <span>{{ $t('contribute.gate.prototype_notice') }}</span>
        </div>

        <div class="cp-gatehelp">
          {{ $t('contribute.gate.help') }} <a>{{ $t('contribute.gate.help_link') }}</a>
        </div>
      </div>
    </div>
  </div>
</template>
