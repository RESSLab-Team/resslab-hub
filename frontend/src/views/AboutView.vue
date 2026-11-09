<script setup lang="ts">
import EyebrowText from '@/components/commons/EyebrowText.vue'
import AppFooter from '@/components/layout/AppFooter.vue'
import { publicPath } from '@/utils/common'
import { reactive } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })

const EPFL_PEOPLE = 'https://people.epfl.ch'

interface Contributor {
  name: string
  /** people.epfl.ch username. The name links to the EPFL profile. */
  epfl?: string
  /**
   * Load the photo from the EPFL profile first. Only for a public profile
   * with a real photo: without one, people.epfl.ch sends a grey placeholder
   * with a 200, so the fallback to `image` never runs.
   */
  epflPhoto?: boolean
  /** Link for people with no EPFL profile. */
  url?: string
  /**
   * Our copy in public/img/people/ (192px square WebP). Used when there is
   * no EPFL photo, or when it fails to load.
   */
  image?: string
  /** Key under about.contributors.roles in the locale files. */
  role?: 'projectManager' | 'leadDev' | 'dev' | 'formerLeadDev'
}

// People are in order of how much they did for the hub.
const contributorGroups: {
  name: string
  url: string
  people: Contributor[]
}[] = [
  {
    name: 'RESSLab',
    url: 'https://www.epfl.ch/labs/resslab',
    // Photos of people who left EPFL come from their old EPFL photo (Web
    // Archive), an EPFL news article or their current university page.
    people: [
      {
        name: 'Dimitrios Lignos',
        epfl: 'dimitrios.lignos',
        epflPhoto: true,
        image: 'dimitrios-lignos.webp'
      },
      // The EPFL profile has no photo anymore. Photo from the EPFL news
      // article on his SNSF Postdoc.Mobility fellowship.
      {
        name: 'Andronikos Skiadopoulos',
        epfl: 'andronikos.skiadopoulos',
        image: 'andronikos-skiadopoulos.webp'
      },
      {
        name: 'Ahmed Elkady',
        url: 'https://www.southampton.ac.uk/people/5xw7jd/doctor-ahmed-elkady',
        image: 'ahmed-elkady.webp'
      },
      // No photo found outside LinkedIn.
      {
        name: 'Subash Ghimire',
        url: 'https://www.linkedin.com/in/subash-ghimire-khumbutse-629bb9ba'
      },
      {
        name: 'Alexander Hartloper',
        url: 'https://www.linkedin.com/in/alex-hartloper',
        image: 'alexander-hartloper.webp'
      },
      {
        name: 'Albano Castro e Sousa',
        epfl: 'albano.sousa',
        epflPhoto: true,
        image: 'albano-castro-e-sousa.webp'
      },
      // Left EPFL, the profile doesn't exist anymore.
      { name: 'Selimcan Ozden', image: 'selimcan-ozden.webp' }
    ]
  },
  {
    name: 'ENAC-IT4R',
    url: 'https://enac-it4r.epfl.ch',
    people: [
      {
        name: 'Charlie Weil',
        epfl: 'charlotte.weil',
        epflPhoto: true,
        image: 'charlie-weil.webp',
        role: 'projectManager'
      },
      {
        name: 'Pierre Ripoll',
        epfl: 'pierre.ripoll',
        epflPhoto: true,
        image: 'pierre-ripoll.webp',
        role: 'leadDev'
      },
      {
        name: 'Pierre Guilbert',
        epfl: 'pierre.guilbert',
        epflPhoto: true,
        image: 'pierre-guilbert.webp',
        role: 'dev'
      },
      // Left EPFL. Photo from his HEP Vaud staff page.
      {
        name: 'David Tang',
        url: 'https://davidtang.ch/fr',
        image: 'david-tang.webp',
        role: 'formerLeadDev'
      }
    ]
  }
]

function profileUrl(person: Contributor): string | undefined {
  return person.epfl ? `${EPFL_PEOPLE}/${person.epfl}` : person.url
}

// The photos to try, in order. `/photo` is the stable EPFL address: it
// redirects to a signed image URL that expires after a day, so never copy
// the URL it redirects to.
function photoSources(person: Contributor): string[] {
  const sources: string[] = []
  if (person.epfl && person.epflPhoto) sources.push(`${EPFL_PEOPLE}/${person.epfl}/photo`)
  if (person.image) sources.push(`${publicPath}img/people/${person.image}`)
  return sources
}

// How many photos failed to load, per person. When one fails we try the
// next source, and show the initials when there is none left.
const failedPhotos = reactive(new Map<string, number>())

function photoUrl(person: Contributor): string | undefined {
  return photoSources(person)[failedPhotos.get(person.name) ?? 0]
}

function onPhotoError(person: Contributor) {
  failedPhotos.set(person.name, (failedPhotos.get(person.name) ?? 0) + 1)
}

function linkAttrs(person: Contributor) {
  const href = profileUrl(person)
  return href ? { href, target: '_blank', rel: 'noopener noreferrer' } : {}
}

function hostOf(url: string): string {
  return new URL(url).hostname.replace(/^www\./, '')
}

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
      <div class="section-eyebrow"><eyebrow-text :text="t('about.eyebrow')" /></div>
      <h1 class="about-title">{{ t('about.title') }}</h1>
      <p class="about-lede about-prose">
        <i18n-t keypath="about.lede" tag="span" scope="global">
          <template #dataLicence>
            <a
              href="https://opendatacommons.org/licenses/pddl/1-0/"
              target="_blank"
              rel="noopener noreferrer"
              >{{ t('about.dataLicence') }}</a
            >
          </template>
          <template #codeLicence>
            <a
              href="https://www.gnu.org/licenses/agpl-3.0.html"
              target="_blank"
              rel="noopener noreferrer"
              >{{ t('about.codeLicence') }}</a
            >
          </template>
        </i18n-t>
      </p>
    </section>

    <section class="section section-bg-subtle">
      <div class="section-eyebrow"><eyebrow-text :text="t('about.contributors.eyebrow')" /></div>
      <h2 class="section-title about-section-title">{{ t('about.contributors.title') }}</h2>

      <div v-for="group in contributorGroups" :key="group.name" class="about-group">
        <h3 class="about-group-name">
          <a :href="group.url" target="_blank" rel="noopener noreferrer">{{ group.name }}</a>
        </h3>
        <ul class="about-people">
          <li v-for="person in group.people" :key="person.name">
            <component
              :is="profileUrl(person) ? 'a' : 'div'"
              class="about-person"
              v-bind="linkAttrs(person)"
            >
              <!-- The name sits right next to the photo, so the photo is decorative. -->
              <img
                v-if="photoUrl(person)"
                class="about-portrait"
                :src="photoUrl(person)"
                alt=""
                loading="lazy"
                @error="onPhotoError(person)"
              />
              <span v-else class="about-portrait about-initials" aria-hidden="true">{{
                initials(person.name)
              }}</span>
              <span class="about-person-text">
                <span class="about-person-name">{{ person.name }}</span>
                <!-- The role replaces the site name: one short line is enough. -->
                <span v-if="person.role" class="about-person-link">{{
                  t(`about.contributors.roles.${person.role}`)
                }}</span>
                <span v-else-if="profileUrl(person)" class="about-person-link">{{
                  hostOf(profileUrl(person)!)
                }}</span>
              </span>
            </component>
          </li>
        </ul>
      </div>

      <p class="section-sub about-credits about-prose">
        <i18n-t keypath="about.contributors.credits" tag="span" scope="global">
          <template #enac>
            <a href="https://enac-it4r.epfl.ch" target="_blank" rel="noopener noreferrer"
              >ENAC-IT4Research</a
            >
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
          <p class="about-citation">
            Lignos, D.G. et al. RESSLab Hub: Open-access databases and models for design and
            assessment of steel structures. EPFL. https://resslab-hub.epfl.ch
          </p>
        </div>
        <div>
          <div class="section-eyebrow"><eyebrow-text :text="t('about.funding.eyebrow')" /></div>
          <h2 class="section-title about-subtitle">{{ t('about.funding.supportedBy') }}</h2>
          <div class="about-funding">
            <a href="https://www.snf.ch" target="_blank" rel="noopener noreferrer">
              Swiss National Science Foundation
            </a>
            <a href="https://www.epfl.ch/schools/enac/" target="_blank" rel="noopener noreferrer">
              EPFL ENAC
            </a>
            <a
              href="https://www.nsf.gov/awardsearch/showAward?AWD_ID=0421551"
              target="_blank"
              rel="noopener noreferrer"
            >
              U.S. NSF (NEES)
            </a>
            <a href="https://www.epfl.ch/labs/resslab" target="_blank" rel="noopener noreferrer">
              EPFL RESSLab
            </a>
          </div>
          <p class="about-note about-prose about-history">
            <i18n-t keypath="about.funding.historyConnections" tag="span" scope="global">
              <template #lignos>
                <a
                  href="https://people.epfl.ch/dimitrios.lignos"
                  target="_blank"
                  rel="noopener noreferrer"
                  >Prof. Dimitrios Lignos</a
                >
              </template>
              <template #krawinkler>
                <a
                  href="https://en.wikipedia.org/wiki/Helmut_Krawinkler"
                  target="_blank"
                  rel="noopener noreferrer"
                  >Prof. Helmut Krawinkler</a
                >
              </template>
              <template #neesProject>
                <a
                  href="https://searchworks.stanford.edu/view/yg701cw5473"
                  target="_blank"
                  rel="noopener noreferrer"
                  >“Sidesway collapse of deteriorating structural systems under seismic
                  excitations”</a
                >
              </template>
              <template #snsfProject>
                <a
                  href="https://data.snf.ch/grants/grant/169248"
                  target="_blank"
                  rel="noopener noreferrer"
                  >“Advanced Simulation Platform for Collapse Risk Assessment of Steel Frame
                  Buildings”</a
                >
              </template>
            </i18n-t>
          </p>
          <p class="about-note about-prose">
            <i18n-t keypath="about.funding.support" tag="span" scope="global">
              <template #lignos>
                <a
                  href="https://people.epfl.ch/dimitrios.lignos"
                  target="_blank"
                  rel="noopener noreferrer"
                  >Prof. Dimitrios Lignos</a
                >
              </template>
              <template #disclaimer>
                <a
                  href="https://www.epfl.ch/about/overview/regulations-and-guidelines/disclaimer/"
                  target="_blank"
                  rel="noopener noreferrer"
                  >{{ t('about.funding.disclaimer') }}</a
                >
              </template>
              <template #privacy>
                <a
                  href="https://go.epfl.ch/privacy-policy/"
                  target="_blank"
                  rel="noopener noreferrer"
                  >{{ t('about.funding.privacyPolicy') }}</a
                >
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
  padding-top: 3.5rem;
  padding-bottom: 2rem;
}
.about-title {
  font-size: var(--fs-h1);
  font-weight: var(--w-bold);
  line-height: var(--lh-tight);
  letter-spacing: -0.01em;
  margin: 0 0 1.5rem;
  max-width: 55rem;
}
.about-lede {
  font-size: var(--fs-lead);
  line-height: 1.55;
  color: var(--fg-muted);
  max-width: 47.5rem;
  margin: 0;
}

/* Links inside running text. The app never underlines links, but here they
   sit in grey prose, and colour alone doesn't show a link (WCAG 1.4.1). So
   they opt back in with a thin red underline, like `.section-link`. */
.about-prose a {
  color: var(--link);
  text-decoration: underline;
  text-decoration-color: var(--primary);
  text-decoration-thickness: 0.0625rem;
  text-underline-offset: 0.2em;
  transition: color var(--t-fast);
}
.about-prose a:hover {
  color: var(--link-hover);
}

/* EPFL focus: 2px solid outline, 2px offset, same hue as the hover. */
a:focus-visible,
.about-person:focus-visible {
  outline: 0.125rem solid var(--primary-hover);
  outline-offset: 0.125rem;
}

.about-section-title {
  margin-bottom: 2.25rem;
}
.about-group + .about-group {
  margin-top: 2.5rem;
}
.about-group-name {
  margin: 0 0 1rem;
  font-size: var(--fs-h5);
  font-weight: var(--w-bold);
}
.about-group-name a {
  color: var(--fg);
  transition: color var(--t-fast);
}
.about-group-name a:hover {
  color: var(--link-hover);
}
.about-people {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  /* At most four columns (7 people make 4 + 3, not 6 + 1), fewer when a
     tile would get narrower than 16rem. */
  grid-template-columns: repeat(auto-fill, minmax(max(16rem, calc((100% - 2.25rem) / 4)), 1fr));
  gap: 0.75rem;
}
.about-person {
  display: flex;
  align-items: center;
  gap: 1rem;
  height: 100%;
  padding: 0.75rem;
  background: var(--bg);
  border: 1px solid var(--border);
  color: var(--fg);
  transition: border-color var(--t-fast), color var(--t-fast);
}
a.about-person:hover {
  border-color: var(--border-strong);
}
a.about-person:hover .about-person-name {
  color: var(--link-hover);
}
.about-portrait {
  flex: none;
  width: 3.5rem;
  height: 3.5rem;
  object-fit: cover;
  /* Faces sit in the top half of most portraits. */
  object-position: center 25%;
  background: var(--bg-muted);
}
.about-initials {
  display: grid;
  place-items: center;
  font-size: var(--fs-sm);
  font-weight: var(--w-semibold);
  letter-spacing: 0.02em;
  color: var(--fg-muted);
}
.about-person-text {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  min-width: 0;
}
.about-person-name {
  font-size: 0.9375rem;
  font-weight: var(--w-medium);
  line-height: var(--lh-normal);
  transition: color var(--t-fast);
}
.about-person-link {
  font-size: var(--fs-xs);
  color: var(--fg-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.about-credits {
  max-width: 47.5rem;
  margin-top: 2rem;
}

.about-subtitle {
  margin-bottom: 1.125rem;
  font-size: var(--fs-h3);
}
.about-note {
  font-size: var(--fs-sm);
  color: var(--fg-muted);
  line-height: 1.55;
  margin: 0 0 1rem;
}
.about-history {
  margin-top: 1.125rem;
}
.about-citation {
  margin: 0;
  background: var(--bg-subtle);
  border: 1px solid var(--border);
  padding: 1.125rem;
  font-size: var(--fs-sm);
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
  padding: 1.125rem 1.25rem;
  font-weight: var(--w-semibold);
  font-size: var(--fs-sm);
  color: var(--fg);
  transition: background-color var(--t-fast), color var(--t-fast);
}
.about-funding a:hover {
  background: var(--bg-subtle);
  color: var(--link-hover);
}
@media (max-width: 767px) {
  .about-title {
    font-size: var(--fs-h2);
  }
  .about-funding {
    grid-template-columns: 1fr;
  }
}
</style>
