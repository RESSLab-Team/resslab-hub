<script setup lang="ts">
import { publicPath } from '@/utils/common'
import { DATABASES, TOOLS } from '@/utils/navigation'

const components = DATABASES.filter((db) => db.group === 'components')
const materials = DATABASES.filter((db) => db.group === 'materials')
</script>

<template>
  <footer class="ftr">
    <div class="ftr-top">
      <div class="ftr-logo">
        <img :src="publicPath + 'logo/EPFL_Logo_184X53.svg'" alt="EPFL" />
        <p class="ftr-tagline">{{ $t('shell.footer_tagline') }}</p>
      </div>
      <div class="ftr-col">
        <h6>{{ $t('shell.databases') }}</h6>
        <router-link v-for="db in components" :key="db.id" :to="db.to">{{ db.name }}</router-link>
      </div>
      <div class="ftr-col">
        <h6>{{ $t('shell.materials') }}</h6>
        <router-link v-for="db in materials" :key="db.id" :to="db.to">{{ db.name }}</router-link>
      </div>
      <div class="ftr-col">
        <h6>{{ $t('shell.tools') }}</h6>
        <router-link v-for="tool in TOOLS" :key="tool.to" :to="tool.to">
          {{ tool.name }}
        </router-link>
        <a
          href="https://github.com/RESSLab-Team/resslab-hub"
          target="_blank"
          rel="noopener noreferrer"
        >
          {{ $t('shell.documentation') }}
        </a>
      </div>
      <div class="ftr-col">
        <h6>{{ $t('shell.resslab') }}</h6>
        <a href="https://www.epfl.ch/labs/resslab" target="_blank" rel="noopener noreferrer">
          {{ $t('shell.lab_homepage') }}
        </a>
        <a href="https://www.epfl.ch/labs/resslab/people" target="_blank" rel="noopener noreferrer">
          {{ $t('shell.people') }}
        </a>
        <a href="https://people.epfl.ch/dimitrios.lignos" target="_blank" rel="noopener noreferrer">
          {{ $t('shell.contact') }}
        </a>
        <router-link to="/about">{{ $t('shell.about_and_credits') }}</router-link>
      </div>
    </div>
    <div class="ftr-bot">
      <div>
        <i18n-t keypath="shell.copyright" tag="span" scope="global">
          <template #year>{{ new Date().getFullYear() }}</template>
          <template #pddl>
            <a
              href="https://opendatacommons.org/licenses/pddl/1-0/"
              target="_blank"
              rel="noopener noreferrer"
              >PDDL 1.0</a
            >
          </template>
          <template #agpl>
            <a
              href="https://www.gnu.org/licenses/agpl-3.0.html"
              target="_blank"
              rel="noopener noreferrer"
              >AGPL-3.0</a
            >
          </template>
        </i18n-t>
      </div>
      <div>
        <a href="https://www.epfl.ch" target="_blank" rel="noopener noreferrer">EPFL</a>
        ·
        <a href="https://enac-it4r.epfl.ch" target="_blank" rel="noopener noreferrer">ENAC-IT4R</a>
      </div>
    </div>
  </footer>
</template>
