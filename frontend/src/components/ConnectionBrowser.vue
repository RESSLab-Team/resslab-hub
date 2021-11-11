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
      <template v-slot:[`item.slab`]="{ item }">
        <v-simple-checkbox v-model="item.slab" disabled></v-simple-checkbox>
      </template>
      <template v-slot:[`body.prepend`]>
        <tr>
          <td v-for="header in headers" :key="header.value">
            <div v-switch="header.type">
              <v-text-field
                v-model="header.search"
                v-case="'text'"
              ></v-text-field>
              <v-select
                v-model="header.search"
                v-case="'option'"
                clearable
                multiple
                :items="header.options"
              ></v-select>
            </div>
          </td>
        </tr>
      </template>
    </v-data-table>
  </v-card>
</template>

<style>
.v-menu__content {
  min-width: 160px !important;
}
</style>

<script lang="ts">
import { Connection } from "@/backend";
import { Component, Vue, Watch } from "vue-property-decorator";
import { DataOptions, DataTableHeader } from "vuetify";

@Component
export default class ConnectionBrowser extends Vue {
  headers: Header[] = [
    {
      text: "Experimental Program",
      value: "experimental_program",
      type: "text",
    },
    {
      text: "Specimen Designation",
      value: "specimen_designation",
      type: "text",
    },
    {
      text: "Beam-to-Column Connection Type",
      value: "beam_to_column_type",
      type: "option",
      options: ["WUF-W", "RBS", "WUF-B", "BFP", "WFP", "KBB", "BEEP"],
    },
    {
      text: "Beam Section",
      value: "beam_section",
      type: "text",
    },
    {
      text: "Column Section",
      value: "column_section",
      type: "text",
    },
    {
      text: "SLAB",
      value: "slab",
      type: "boolean",
    },
    {
      text: "North Ridge",
      value: "north_ridge",
      type: "option",
      options: ["pre", "post"],
    },
    {
      text: "Specimen Type",
      value: "specimen_type",
      type: "text",
    },
    {
      text: "Double Plate",
      value: "double_plate",
      type: "number",
    },
  ];
  connections: Connection[] = [];
  search = "";
  totalCount = -1;
  loading = true;
  options: DataOptions | null = null;

  get query(): string {
    return this.headers
      .filter((header) => header.search && header.search.length > 0)
      .map((header) => `${header.value}:${header.search}`)
      .join(";");
  }

  @Watch("options", { deep: true })
  @Watch("query")
  onTableChanged(): void {
    if (this.options) {
      this.loading = true;
      this.$connectionsApi
        .getConnectionsConnectionsGet(
          this.query,
          this.options.page,
          this.options.itemsPerPage
        )
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
}

interface Header extends DataTableHeader {
  type: "text" | "option" | "number" | "boolean";
  options?: string[];
  search?: string;
}
</script>
