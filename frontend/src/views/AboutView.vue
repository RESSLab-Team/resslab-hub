<script setup lang="ts">
import EyebrowText from '@/components/commons/EyebrowText.vue'
import AppFooter from '@/components/layout/AppFooter.vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })

interface Contributor {
  name: string
  url: string
  image?: string
}

const contributorGroups: {
  name: string
  url: string
  contributors: Contributor[]
}[] = [
  {
    name: 'RESSLab',
    url: 'https://www.epfl.ch/labs/resslab',
    contributors: [
      {
        name: 'Andronikos Skiadopoulos',
        url: 'https://people.epfl.ch/andronikos.skiadopoulos',
        image: 'https://people.epfl.ch/private/common/photos/links/280688.jpg'
      },
      {
        name: 'Ahmed Elkady',
        url: 'https://www.southampton.ac.uk/people/5xw7jd/doctor-ahmed-elkady',
        image:
          'https://www.southampton.ac.uk/sites/default/files/styles/max_1300x1300/public/2022-05/0D3350C6C313004BA012493F39365C80000D58ED.jpg'
      },
      {
        name: 'Alexander Hartloper',
        url: 'https://www.linkedin.com/in/alex-hartloper'
      },
      {
        name: 'Selimcan Ozden',
        url: 'https://people.epfl.ch/selimcan.ozden',
        image: 'https://people.epfl.ch/private/common/photos/links/297594.jpg'
      },
      {
        name: 'Albano Castro e Sousa',
        url: 'https://people.epfl.ch/albano.sousa'
      },
      {
        name: 'Subash Ghimire',
        url: 'https://www.linkedin.com/in/subash-ghimire-khumbutse-629bb9ba'
      },
      {
        name: 'Dimitrios Lignos',
        url: 'https://people.epfl.ch/dimitrios.lignos',
        image: 'https://people.epfl.ch/private/common/photos/links/265223.jpg'
      }
    ]
  },
  {
    name: 'ENAC-IT4R',
    url: 'https://enac-it4r.epfl.ch',
    contributors: [
      {
        name: 'David Tang',
        url: 'https://people.epfl.ch/david.tang',
        image: 'https://people.epfl.ch/private/common/photos/links/225316.jpg'
      },
      {
        name: 'Charlie Weil',
        url: 'https://people.epfl.ch/charlotte.weil',
        image: 'https://people.epfl.ch/private/common/photos/links/201992.jpg'
      },
      {
        name: 'Pierre Guilbert',
        url: 'https://people.epfl.ch/pierre.guilbert',
        image: 'https://people.epfl.ch/private/common/photos/links/352707.jpg'
      },
      {
        name: 'Pierre Ripoll',
        url: 'https://people.epfl.ch/pierre.ripoll',
        image: 'https://people.epfl.ch/private/common/photos/links/365124.jpg'
      }
    ]
  }
]

function initials(name: string): string {
  return name
    .split(' ')
    .map((part) => part[0])
    .slice(0, 2)
    .join('')
}
</script>

<template>
  <div>
    <section class="section about-hero">
      <div class="eyebrow" style="margin-bottom: 10px">
        <eyebrow-text :text="t('about.eyebrow')" />
      </div>
      <h1 class="about-title">{{ t('about.title') }}</h1>
      <p class="about-lede">
        <i18n-t keypath="about.lede" tag="span" scope="global">
          <template #dataLicence>
            <a href="https://opendatacommons.org/licenses/pddl/1-0/" target="_blank">{{
              t('about.dataLicence')
            }}</a>
          </template>
          <template #codeLicence>
            <a href="https://www.gnu.org/licenses/agpl-3.0.html" target="_blank">{{
              t('about.codeLicence')
            }}</a>
          </template>
        </i18n-t>
      </p>
    </section>

    <section class="section section-bg-subtle">
      <div class="section-eyebrow"><eyebrow-text :text="t('about.contributors.eyebrow')" /></div>
      <h2 class="section-title" style="margin-bottom: 36px">{{ t('about.contributors.title') }}</h2>
      <div class="split-2">
        <div v-for="group in contributorGroups" :key="group.name" class="surface surface-pad">
          <h3 class="about-group-name">
            <a :href="group.url" target="_blank">{{ group.name }}</a>
          </h3>
          <div class="about-people">
            <a
              v-for="contributor in group.contributors"
              :key="contributor.name"
              class="about-person"
              :href="contributor.url"
              target="_blank"
              rel="noreferrer"
            >
              <img v-if="contributor.image" :src="contributor.image" :alt="contributor.name" />
              <span v-else class="about-person-initials">{{ initials(contributor.name) }}</span>
              <span>{{ contributor.name }}</span>
            </a>
          </div>
        </div>
      </div>
      <p class="section-sub" style="max-width: 760px">
        <i18n-t keypath="about.contributors.credits" tag="span" scope="global">
          <template #enac>
            <a href="https://enac-it4r.epfl.ch" target="_blank">ENAC-IT4Research</a>
          </template>
        </i18n-t>
      </p>
    </section>

    <section class="section">
      <div class="split-2">
        <div>
          <div class="section-eyebrow"><eyebrow-text :text="t('about.citation.eyebrow')" /></div>
          <h2 class="section-title about-subtitle">{{ t('about.citation.title') }}</h2>
          <p class="about-note">{{ t('about.citation.note') }}</p>
          <div class="about-citation">
            Lignos, D.G. et al. RESSLab Hub: Open-access databases<br />
            and models for design and assessment of steel structures.<br />
            EPFL. https://resslab-hub.epfl.ch
          </div>
        </div>
        <div>
          <div class="section-eyebrow"><eyebrow-text :text="t('about.funding.eyebrow')" /></div>
          <h2 class="section-title about-subtitle">{{ t('about.funding.supportedBy') }}</h2>
          <div class="about-funding">
            <a href="https://www.snf.ch" target="_blank" rel="noreferrer">
              Swiss National Science Foundation
            </a>
            <a href="https://www.epfl.ch/schools/enac/" target="_blank" rel="noreferrer">
              EPFL ENAC
            </a>
            <a
              href="https://www.nsf.gov/awardsearch/showAward?AWD_ID=0421551"
              target="_blank"
              rel="noreferrer"
            >
              U.S. NSF (NEES)
            </a>
            <a href="https://www.epfl.ch/labs/resslab" target="_blank" rel="noreferrer">
              EPFL RESSLab
            </a>
          </div>
          <p class="about-note" style="margin-top: 18px">
            <i18n-t keypath="about.funding.historyConnections" tag="span" scope="global">
              <template #lignos>
                <a href="https://people.epfl.ch/dimitrios.lignos" target="_blank"
                  >Prof. Dimitrios Lignos</a
                >
              </template>
              <template #krawinkler>
                <a href="https://en.wikipedia.org/wiki/Helmut_Krawinkler" target="_blank"
                  >Prof. Helmut Krawinkler</a
                >
              </template>
              <template #neesProject>
                <a href="https://searchworks.stanford.edu/view/yg701cw5473" target="_blank"
                  >“Sidesway collapse of deteriorating structural systems under seismic
                  excitations”</a
                >
              </template>
              <template #snsfProject>
                <a href="https://data.snf.ch/grants/grant/169248" target="_blank"
                  >“Advanced Simulation Platform for Collapse Risk Assessment of Steel Frame
                  Buildings”</a
                >
              </template>
            </i18n-t>
          </p>
          <p class="about-note">
            <i18n-t keypath="about.funding.support" tag="span" scope="global">
              <template #lignos>
                <a href="https://people.epfl.ch/dimitrios.lignos" target="_blank"
                  >Prof. Dimitrios Lignos</a
                >
              </template>
              <template #disclaimer>
                <a
                  href="https://www.epfl.ch/about/overview/regulations-and-guidelines/disclaimer/"
                  target="_blank"
                  >{{ t('about.funding.disclaimer') }}</a
                >
              </template>
              <template #privacy>
                <a href="https://go.epfl.ch/privacy-policy/" target="_blank">{{
                  t('about.funding.privacyPolicy')
                }}</a>
              </template>
            </i18n-t>
          </p>
        </div>
      </div>
    </section>

    <app-footer />
  </div>
</template>

<style scoped>
.about-hero {
  padding-top: 56px;
  padding-bottom: 32px;
}
.about-title {
  font-size: 48px;
  font-weight: 700;
  line-height: 1.05;
  letter-spacing: -0.01em;
  margin: 0 0 24px;
  max-width: 880px;
}
.about-lede {
  font-size: 18px;
  line-height: 1.55;
  color: var(--fg-muted);
  max-width: 760px;
  margin: 0;
}
.about-group-name {
  margin: 0 0 18px;
  font-size: 22px;
  font-weight: 700;
}
.about-group-name a {
  color: inherit;
  text-decoration: none;
}
.about-group-name a:hover {
  color: var(--epfl-red);
}
.about-people {
  display: grid;
  grid-template-columns: 1fr 1fr;
  row-gap: 10px;
  column-gap: 18px;
}
.about-person {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: var(--fg);
  text-decoration: none;
}
.about-person:hover {
  color: var(--epfl-red);
}
.about-person img,
.about-person-initials {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid var(--border);
  object-fit: cover;
  flex: 0 0 32px;
}
.about-person-initials {
  background: var(--bg-subtle);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  color: var(--fg-muted);
  font-size: 11px;
}
.about-subtitle {
  margin-bottom: 18px;
  font-size: 28px;
}
.about-note {
  font-size: 14px;
  color: var(--fg-muted);
  line-height: 1.55;
  margin: 0 0 16px;
}
.about-citation {
  background: var(--bg-subtle);
  border: 1px solid var(--border);
  padding: 18px;
  font-family: var(--font-sans);
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--fg);
}
.about-funding {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1px;
  background: var(--border);
  border: 1px solid var(--border);
}
.about-funding a {
  background: var(--bg);
  padding: 18px 20px;
  font-weight: 600;
  font-size: 14px;
  color: var(--fg);
  text-decoration: none;
}
.about-funding a:hover {
  color: var(--epfl-red);
}
@media (max-width: 767px) {
  .about-title {
    font-size: 32px;
  }
  .about-people {
    grid-template-columns: 1fr;
  }
}
</style>
