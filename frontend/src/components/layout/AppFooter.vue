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
        <p class="ftr-tagline">
          Open-access databases &amp; models for design and assessment of steel structures.
        </p>
      </div>
      <div class="ftr-col">
        <h6>Databases</h6>
        <router-link v-for="db in components" :key="db.id" :to="db.to">{{ db.name }}</router-link>
      </div>
      <div class="ftr-col">
        <h6>Materials</h6>
        <router-link v-for="db in materials" :key="db.id" :to="db.to">{{ db.name }}</router-link>
      </div>
      <div class="ftr-col">
        <h6>Tools</h6>
        <router-link v-for="tool in TOOLS" :key="tool.to" :to="tool.to">
          {{ tool.name }}
        </router-link>
        <a href="https://github.com/RESSLab-Team/resslab-hub" target="_blank" rel="noreferrer">
          Documentation
        </a>
      </div>
      <div class="ftr-col">
        <h6>RESSLab</h6>
        <a href="https://www.epfl.ch/labs/resslab" target="_blank" rel="noreferrer">
          Lab homepage
        </a>
        <a href="https://www.epfl.ch/labs/resslab/people" target="_blank" rel="noreferrer">
          People
        </a>
        <a href="https://people.epfl.ch/dimitrios.lignos" target="_blank" rel="noreferrer">
          Contact
        </a>
        <router-link to="/about">About &amp; credits</router-link>
      </div>
    </div>
    <div class="ftr-bot">
      <div>
        © {{ new Date().getFullYear() }} EPFL — RESSLab Hub. Data under
        <a
          href="https://creativecommons.org/licenses/by/2.0/legalcode"
          target="_blank"
          rel="noreferrer"
          >CC-BY 2.0</a
        >
        /
        <a
          href="https://github.com/amaelkady/Steel-Columns-Test-Data/blob/main/LICENSE"
          target="_blank"
          rel="noreferrer"
          >GPL</a
        >.
      </div>
      <div>
        <a href="https://www.epfl.ch" target="_blank" rel="noreferrer">EPFL</a>
        ·
        <a href="https://enac-it4r.epfl.ch" target="_blank" rel="noreferrer">ENAC-IT4R</a>
      </div>
    </div>
  </footer>
</template>
