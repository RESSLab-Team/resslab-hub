<script setup lang="ts">
import { ref } from "vue";

interface MenuItem {
  text: string;
  to: string;
  children?: MenuItem[];
}

const subMenuItems: MenuItem[] = [
  {
    text: "Database",
    to: "/database",
  },
  {
    text: "Component Model",
    to: "/model",
  },
  {
    text: "Fragility Curve",
    to: "/fragility-curve",
  },
];
const menuItems: MenuItem[] = [
  {
    text: "RESSLab Hub",
    to: "/",
  },
  {
    text: "Connections",
    to: "/connections",
    children: subMenuItems,
  },
  {
    text: "Columns",
    to: "/columns",
    children: subMenuItems,
  },
  {
    text: "Braces",
    to: "/braces",
    children: subMenuItems,
  },
  {
    text: "Materials",
    to: "/materials",
    children: [
      {
        text: "Database",
        to: "/database",
      },
      {
        text: "Material Model",
        to: "/model",
      },
    ],
  },
];

const aboutDialog = ref<boolean>(false);
</script>

<template>
  <v-app>
    <v-app-bar app dense>
      <v-tabs hide-slider>
        <template v-for="item in menuItems">
          <v-menu v-if="item.children" :key="item.to" offset-y open-on-hover>
            <template #activator="{ on, attrs }">
              <v-tab :to="item.to" v-bind="attrs" v-on="on">
                {{ item.text }}
              </v-tab>
            </template>
            <v-list>
              <v-list-item v-for="subItem in item.children" :key="subItem.to">
                <v-tab
                  :to="item.to + subItem.to"
                  :class="
                    item.to + subItem.to == $route.path
                      ? 'primary--text'
                      : undefined
                  "
                >
                  {{ subItem.text }}
                </v-tab>
              </v-list-item>
            </v-list>
          </v-menu>
          <v-tab v-else :key="item.to" :to="item.to">
            <v-app-bar-title v-if="item.to === '/'">
              {{ item.text }}
            </v-app-bar-title>
            <template v-else>
              {{ item.text }}
            </template>
          </v-tab>
        </template>
        <v-spacer></v-spacer>
        <v-dialog v-model="aboutDialog">
          <template #activator="{ on, attrs }">
            <v-tab v-bind="attrs" v-on="on">
              <v-icon>mdi-information-outline</v-icon>
            </v-tab>
          </template>
          <v-card>
            <v-card-title>About</v-card-title>
            <v-card-text>
              <h2>Acknowledgements</h2>
              <p>
                <a href="https://enacit4r.epfl.ch/" target="_blank"
                  >ENAC-IT4Research</a
                >
                developed the web-based interfaces, visualisation features and
                search capabilities for the assembled databases.
              </p>
              <p>
                We would like to sincerely thank many researchers worldwide, who
                generously shared their test data for the development of the
                structural component databases for performance-based earthquake
                engineering. The database users should cite the original
                references for each test description in addition to these
                databases.
              </p>
              <p>
                An earlier version of the steel Beam-to-Column connections
                database had been assembled by
                <a
                  href="https://people.epfl.ch/dimitrios.lignos"
                  target="_blank"
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
                within the George E. Brown, Jr. Network for Earthquake
                Engineering Simulation (NEES). The project title was
                <a
                  href="https://searchworks.stanford.edu/view/yg701cw5473"
                  target="_blank"
                  >"Sidesway collapse of deteriorating structural systems under
                  seismic excitations"</a
                >. The current version of the connections database was
                significantly improved and expanded by
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
                <a
                  href="https://data.snf.ch/grants/grant/169248"
                  target="_blank"
                  >"Advanced Simulation Platform for Collapse Risk Assessment of
                  Steel Frame Buildings"</a
                >.
              </p>
              <p>
                Report technical problems to
                <a
                  href="https://people.epfl.ch/dimitrios.lignos"
                  target="_blank"
                  >Prof. Dimitrios Lignos</a
                >.
              </p>
            </v-card-text>
            <v-card-actions>
              <v-spacer></v-spacer>
              <v-btn color="primary" icon @click="aboutDialog = false">
                <v-icon>mdi-close</v-icon>
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-dialog>
      </v-tabs>
    </v-app-bar>
    <v-main>
      <router-view />
    </v-main>
  </v-app>
</template>

<style lang="scss" scoped>
.v-toolbar__title {
  overflow: unset;
  text-transform: none;
}
</style>
