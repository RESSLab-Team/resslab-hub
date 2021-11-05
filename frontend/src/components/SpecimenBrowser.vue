<template>
  <v-card>
    <v-card-title>
      Beams
      <v-spacer></v-spacer>
      <v-text-field
        v-model="search"
        hide-details
        single-line
        append-icon="mdi-magnify"
        label="Search"
      ></v-text-field>
    </v-card-title>
    <v-data-table :headers="headers" :items="specimens" :search="search">
      <template v-slot:item.slab="{ item }">
        <v-simple-checkbox v-model="item.slab" disabled></v-simple-checkbox>
      </template>
      <template v-slot:item.preNorthridge="{ item }">
        <v-simple-checkbox
          v-model="item.preNorthridge"
          disabled
        ></v-simple-checkbox>
      </template>
    </v-data-table>
  </v-card>
</template>

<script lang="ts">
import { Component, Vue } from "vue-property-decorator";
import { DataTableHeader } from "vuetify";

@Component
export default class SpecimenBrowser extends Vue {
  headers: DataTableHeader[] = [
    {
      text: "Experimental Program",
      value: "experimentalProgram",
    },
    {
      text: "Specimen Designation",
      value: "specimenDesignation",
    },
    {
      text: "Beam-to-Column Connection Type",
      value: "beamToColumn.type",
    },
    {
      text: "Beam Section",
      value: "beam.section",
    },
    {
      text: "Column Section",
      value: "column.section",
    },
    {
      text: "SLAB",
      value: "slab",
    },
    {
      text: "Pre-NorthRidge",
      value: "preNorthridge",
    },
    {
      text: "Specimen Type",
      value: "specimenType",
    },
    {
      text: "Double Plate",
      value: "doublePlate",
    },
  ];
  specimens: Specimen[] = [
    {
      experimentalProgram: "Del Caprio et al. (2014)",
      specimenDesignation: "RBS-A",
      beamToColumn: {
        type: "WUF-W",
      },
      beam: {
        section: "W14x26",
      },
      column: {
        section: "W12x30",
      },
      slab: true,
      preNorthridge: false,
      specimenType: "Exterior - Frame - Symmetric",
      doublePlate: 0,
    },
  ];
  search = "";
}

interface Specimen {
  experimentalProgram: string;
  specimenDesignation: string;
  beamToColumn: BeamToColumn;
  beam: Beam;
  column: Column;
  slab: boolean;
  preNorthridge: boolean;
  specimenType: string;
  doublePlate: number;
}

interface BeamToColumn {
  type: string;
}

interface Beam {
  section: string;
}

interface Column {
  section: string;
}
</script>
