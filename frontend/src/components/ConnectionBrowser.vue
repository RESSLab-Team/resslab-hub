<template>
  <v-card>
    <v-card-title>
      Connections
      <v-spacer></v-spacer>
      <v-text-field
        v-model="search"
        clearable
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
      show-expand
    >
      <template v-slot:[`body.prepend`]>
        <tr>
          <td>
            <!-- expand -->
          </td>
          <td v-for="header in headers" :key="header.value">
            <div v-switch="header.type">
              <div v-case="'text'">
                <v-select
                  v-if="header.options"
                  v-model="header.search"
                  clearable
                  :items="header.options"
                ></v-select>
                <v-text-field
                  v-else
                  v-model="header.search"
                  clearable
                ></v-text-field>
              </div>
              <v-select
                v-model="header.search"
                v-case="'option'"
                clearable
                :multiple="isMultiple(header)"
                :items="header.options"
              ></v-select>
              <v-select
                v-model="header.search"
                v-case="'boolean'"
                clearable
                :items="booleanOptions"
              ></v-select>
              <div v-case="'number'">
                <v-select
                  v-if="header.options"
                  v-model="header.search"
                  clearable
                  :items="header.options"
                ></v-select>
                <v-text-field
                  v-else
                  v-model="header.search"
                  clearable
                  type="number"
                ></v-text-field>
              </div>
            </div>
          </td>
        </tr>
      </template>
      <template v-slot:expanded-item="{ headers, item }">
        <td :colspan="headers.length">
          <connection-detail :connection-id="item.id"></connection-detail>
        </td>
      </template>
    </v-data-table>
  </v-card>
</template>

<style lang="scss" scoped>
.v-data-table__expanded {
  td {
    padding: 16px !important;
  }
}
</style>
<style>
.v-menu__content {
  min-width: 160px !important;
}
</style>

<script lang="ts">
import { ConnectionModel } from "@/backend";
import { Component, Vue, Watch } from "vue-property-decorator";
import { DataOptions, DataTableHeader } from "vuetify";
import { booleanOptions } from "@/utils/vuetify";
import ConnectionDetail from "@/components/ConnectionDetail.vue";

@Component({
  components: {
    ConnectionDetail,
  },
})
export default class ConnectionBrowser extends Vue {
  booleanOptions = booleanOptions;

  headers: Header[] = [
    {
      text: "Experimental Program",
      value: "experimental_program",
      type: "text",
    },
    {
      text: "Date",
      value: "date",
      type: "number",
    },
    {
      text: "Specimen Designation",
      value: "specimen_designation",
      type: "text",
    },
    {
      text: "North Ridge",
      value: "northridge",
      type: "option",
      options: ["pre", "post"],
    },
    {
      text: "Specimen Type",
      value: "specimen_type",
      type: "text",
      options: ["exterior", "interior"],
    },
    {
      text: "SLAB",
      value: "slab",
      type: "boolean",
    },
    {
      text: "Connection Type",
      value: "connection_type",
      type: "option",
      options: ["WUF-W", "RBS", "WUF-B", "BFP", "WFP", "KBB", "BEEP"],
    },
    {
      text: "Beam Section",
      value: "section_b",
      type: "text",
    },
    {
      text: "Column Section",
      value: "section_c",
      type: "text",
    },
    {
      text: "Double Plate",
      value: "n_dp",
      type: "number",
      options: ["0", "> 0"],
    },
  ];
  connections: ConnectionModel[] = [];
  search = "";
  totalCount = -1;
  loading = true;
  options: DataOptions | null = null;

  get query(): string {
    const queries = this.headers
      .filter(
        (header) =>
          header.search != undefined &&
          (typeof header.search == "boolean" || header.search.length > 0)
      )
      .map((header) => {
        switch (header.type) {
          case "text":
            return `${header.value}:~%${header.search}%`;
          default:
            return `${header.value}:${header.search}`;
        }
      });
    if (this.search && this.search.length > 0) {
      queries.push(`%${this.search}%`);
    }
    return queries.join(";");
  }

  @Watch("options", { deep: true })
  @Watch("query")
  onTableChanged(): void {
    if (this.options) {
      this.loading = true;
      this.$connectionsApi
        .getConnectionsConnectionsGet(
          this.query,
          this.options.sortBy,
          this.options.sortDesc,
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

  isMultiple(header: Header): boolean {
    if (header.options) {
      return header.options.length > 2;
    } else {
      return false;
    }
  }
}

interface Header extends DataTableHeader {
  type: "text" | "option" | "number" | "boolean";
  options?: string[];
  search?: string;
}
</script>
