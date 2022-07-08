<template>
  <v-container class="text-justify">
    <h1>About this Site</h1>

    <h2>Disclaimer</h2>
    <p>
      The databases in RESSLab-hub were assembled as a service to the research
      and practice communities in earthquake engineering. The assembled data,
      which have been fully digitized from various experimental reports, are
      shared under the
      <a
        href="https://creativecommons.org/licenses/by/2.0/legalcode"
        target="_blank"
        >Creative Commons Attribution 2.0 Generic</a
      >
      and the
      <a
        href="https://github.com/amaelkady/Steel-Columns-Test-Data/blob/main/LICENSE"
        target="_blank"
        >GNU General Public</a
      >
      licences. EPFL, and the researchers who performed the experiments make no
      warranties to the accuracy of the information that has been collected and
      provided in this website. If you have any questions, comments or
      suggestions, please contact
      <a href="https://people.epfl.ch/dimitrios.lignos" target="_blank"
        >Prof. Dimitrios Lignos</a
      >
      at <a href="https://www.epfl.ch" target="_blank">EPFL</a>.
    </p>

    <h2>Acknowledgements</h2>
    <p>
      <a
        href="https://www.epfl.ch/schools/enac/about/data-services-en/"
        target="_blank"
        >ENAC-IT4Research</a
      >
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
      <a href="https://en.wikipedia.org/wiki/Helmut_Krawinkler" target="_blank"
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
    <br />
    <v-row>
      <v-col v-for="(logo, index) in logos" :key="index">
        <a :href="logo.url" target="_blank">
          <v-img contain :src="logo.src" max-height="128"></v-img>
        </a>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
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
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { publicPath } from "@/utils/common";
import { Component, Vue } from "vue-property-decorator";

@Component
export default class About extends Vue {
  readonly logos: Logo[] = [
    {
      src: publicPath + "logo/resslab_logo_v1.svg",
      url: "https://www.epfl.ch/labs/resslab",
    },
    {
      src: publicPath + "logo/EPFL_Logo_184X53.svg",
      url: "https://www.epfl.ch",
    },
    {
      src: publicPath + "logo/SNF_logo_standard_web_color_pos_e.svg",
      url: "https://www.snf.ch",
    },
  ];
}

interface Logo {
  src: string;
  url: string;
}
</script>
