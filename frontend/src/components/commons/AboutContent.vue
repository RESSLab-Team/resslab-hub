<script setup lang="ts">
import { defineEmits } from "vue";

const emit = defineEmits<{
  (e: "click:close"): void;
}>();

interface Contributor {
  name: string;
  url: string;
  image?: string;
}

const contributorGroups: {
  name: string;
  url: string;
  contributors: Contributor[];
}[] = [
  {
    name: "RESSLab",
    url: "https://www.epfl.ch/labs/resslab",
    contributors: [
      {
        name: "Andronikos Skiadopoulos",
        url: "https://people.epfl.ch/andronikos.skiadopoulos",
        image: "https://people.epfl.ch/private/common/photos/links/280688.jpg",
      },
      {
        name: "Ahmed Elkady",
        url: "https://www.southampton.ac.uk/people/5xw7jd/doctor-ahmed-elkady",
        image:
          "https://www.southampton.ac.uk/sites/default/files/styles/max_1300x1300/public/2022-05/0D3350C6C313004BA012493F39365C80000D58ED.jpg",
      },
      {
        name: "Alexander Hartloper",
        url: "https://www.linkedin.com/in/alex-hartloper",
      },
      {
        name: "Selimcan Ozden",
        url: "https://people.epfl.ch/selimcan.ozden",
        image: "https://people.epfl.ch/private/common/photos/links/297594.jpg",
      },
      {
        name: "Albano Castro e Sousa",
        url: "https://people.epfl.ch/albano.sousa",
      },
      {
        name: "Subash Ghimire",
        url: "https://www.linkedin.com/in/subash-ghimire-khumbutse-629bb9ba",
      },
      {
        name: "Dimitrios Lignos",
        url: "https://people.epfl.ch/dimitrios.lignos",
        image: "https://people.epfl.ch/private/common/photos/links/265223.jpg",
      },
    ],
  },
  {
    name: "ENAC-IT4R",
    url: "https://enac-it4r.epfl.ch",
    contributors: [
      {
        name: "David Tang",
        url: "https://people.epfl.ch/david.tang",
        image: "https://people.epfl.ch/private/common/photos/links/225316.jpg",
      },
      {
        name: "Charlie Weil",
        url: "https://people.epfl.ch/charlotte.weil",
        image: "https://people.epfl.ch/private/common/photos/links/201992.jpg",
      },
      {
        name: "Pierre Guilbert",
        url: "https://people.epfl.ch/pierre.guilbert",
        image: "https://people.epfl.ch/private/common/photos/links/352707.jpg",
      },
      {
        name: "Pierre Ripoll",
        url: "https://people.epfl.ch/pierre.ripoll",
        image: "https://people.epfl.ch/private/common/photos/links/365124.jpg",
      },
    ],
  },
];
</script>

<template>
  <v-card>
    <v-card-title>Acknowledgements</v-card-title>
    <v-card-text>
      <p>
        <a href="https://enac-it4r.epfl.ch" target="_blank">ENAC-IT4Research</a>
        developed the web-based interfaces, visualisation features and search
        capabilities for the assembled databases.
      </p>
      <p>
        We would like to sincerely thank many researchers worldwide, who
        generously shared their test data for the development of the structural
        component databases for performance-based earthquake engineering. The
        database users should cite the original references for each test
        description in addition to these databases.
      </p>
      <p>
        An earlier version of the steel Beam-to-Column connections database had
        been assembled by
        <a href="https://people.epfl.ch/dimitrios.lignos" target="_blank"
          >Prof. Dimitrios Lignos</a
        >
        and the late
        <a
          href="https://en.wikipedia.org/wiki/Helmut_Krawinkler"
          target="_blank"
          >Prof. Helmut Krawinkler</a
        >
        as part of a U.S. National Science Foundation (NSF)
        <a
          href="https://www.nsf.gov/awardsearch/showAward?AWD_ID=0421551"
          target="_blank"
          >grant</a
        >
        within the George E. Brown, Jr. Network for Earthquake Engineering
        Simulation (NEES). The project title was
        <a
          href="https://searchworks.stanford.edu/view/yg701cw5473"
          target="_blank"
          >"Sidesway collapse of deteriorating structural systems under seismic
          excitations"</a
        >. The current version of the connections database was significantly
        improved and expanded by
        <a href="https://www.linkedin.com/in/andskia" target="_blank"
          >Mr. Andronikos Skiadopoulos</a
        >
        during his doctoral studies at EPFL.
      </p>
      <p>
        The steel Columns database was assembled by
        <a
          href="https://www.southampton.ac.uk/engineering/about/staff/amae1g19.page"
          target="_blank"
          >Prof. Ahmed Elkady</a
        >
        during his post-doctoral research work at EPFL and
        <a
          href="https://www.linkedin.com/in/subash-ghimire-khumbutse-629bb9ba"
          target="_blank"
          >Mr. Subash Ghimire</a
        >
        during his internship at EPFL. The work was supported by a
        <a href="https://www.snf.ch" target="_blank"
          >Swiss National Science Foundation (SNSF)</a
        >
        grant. The project title was
        <a href="https://data.snf.ch/grants/grant/169248" target="_blank"
          >"Advanced Simulation Platform for Collapse Risk Assessment of Steel
          Frame Buildings"</a
        >.
      </p>
      <p>
        Report technical problems to
        <a href="https://people.epfl.ch/dimitrios.lignos" target="_blank"
          >Prof. Dimitrios Lignos</a
        >.
      </p>
    </v-card-text>
    <v-card-text>
      <v-row>
        <v-col
          v-for="group in contributorGroups"
          :key="group.name"
          :cols="12 / contributorGroups.length"
        >
          <v-card>
            <v-card-title>
              <a :href="group.url" target="_blank">{{ group.name }}</a>
            </v-card-title>
            <v-card-text>
              <v-list>
                <v-list-item
                  v-for="item in group.contributors"
                  :key="item.name"
                  :href="item.url"
                  target="_blank"
                >
                  <v-list-item-avatar>
                    <img v-if="item.image" :alt="item.name" :src="item.image" />
                    <v-icon v-else size="48">mdi-account-circle</v-icon>
                  </v-list-item-avatar>
                  <v-list-item-content>
                    <v-list-item-title>
                      {{ item.name }}
                    </v-list-item-title>
                  </v-list-item-content>
                </v-list-item>
              </v-list>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-card-text>
    <v-card-text>
      <!-- https://www.epfl.ch/campus/services/website/legal-recommendations-for-publishing-on-the-epfl-web/use-of-google-analytics/ -->
      <a
        href="https://www.epfl.ch/about/overview/regulations-and-guidelines/disclaimer/"
        target="_blank"
      >
        Disclaimer
      </a>
      <br />
      <a href="https://go.epfl.ch/privacy-policy/" target="_blank">
        Privacy policy
      </a>
    </v-card-text>
    <v-card-actions>
      <v-spacer></v-spacer>
      <v-btn color="primary" icon @click="emit(`click:close`)">
        <v-icon>mdi-close</v-icon>
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<style lang="scss" scoped>
:deep(.v-avatar) > img {
  height: unset;
}
</style>
