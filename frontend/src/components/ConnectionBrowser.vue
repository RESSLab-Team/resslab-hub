<template>
  <v-card>
    <v-card-title>
      Connections
      <v-spacer></v-spacer>
      <v-text-field
        v-model="search"
        hide-details
        single-line
        append-icon="mdi-magnify"
        label="Search"
      ></v-text-field>
    </v-card-title>
    <v-data-table
      :headers="headers"
      :items="connections"
      :loading="loading"
      :options.sync="options"
      :search="search"
      :server-items-length="totalCount"
    >
      <template v-slot:item.slab="{ item }">
        <v-simple-checkbox v-model="item.slab" disabled></v-simple-checkbox>
      </template>
      <template v-slot:item.pre_north_ridge="{ item }">
        <v-simple-checkbox
          v-model="item.preNorthridge"
          disabled
        ></v-simple-checkbox>
      </template>
    </v-data-table>
  </v-card>
</template>

<script lang="ts">
import { Connection } from "@/backend";
import { Component, Vue, Watch } from "vue-property-decorator";
import { DataOptions, DataTableHeader } from "vuetify";

@Component
export default class ConnectionBrowser extends Vue {
  headers: DataTableHeader[] = [
    {
      text: "Experimental Program",
      value: "experimental_program",
    },
    {
      text: "Specimen Designation",
      value: "specimen_designation",
    },
    {
      text: "Beam-to-Column Connection Type",
      value: "beam_to_column_type",
    },
    {
      text: "Beam Section",
      value: "beam_section",
    },
    {
      text: "Column Section",
      value: "column_section",
    },
    {
      text: "SLAB",
      value: "slab",
    },
    {
      text: "Pre-NorthRidge",
      value: "pre_north_ridge",
    },
    {
      text: "Specimen Type",
      value: "specimen_type",
    },
    {
      text: "Double Plate",
      value: "double_plate",
    },
  ];
  connections: Connection[] = [];
  search = "";
  totalCount = -1;
  loading = true;
  options: DataOptions | null = null;

  @Watch("options", { deep: true })
  onOptionsChanged(options: DataOptions): void {
    this.loading = true;
    this.$connectionsApi
      .getConnectionsConnectionsGet(options.page, options.itemsPerPage)
      .then((response) => response.data)
      .then((connections) => {
        this.connections = connections.items;
        this.totalCount = connections.total;
      })
      .finally(() => {
        this.loading = false;
      });
  }
}
</script>
