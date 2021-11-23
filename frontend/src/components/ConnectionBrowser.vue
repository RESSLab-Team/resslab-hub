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
      :headers="tableHeaders"
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
          <td v-for="(header, index) in tableHeaders" :key="header.value">
            <div v-switch="header.type">
              <div v-case="'text'">
                <v-select
                  v-if="header.options"
                  v-model="searches[index]"
                  clearable
                  :items="header.options"
                ></v-select>
                <v-text-field
                  v-else
                  v-model="searches[index]"
                  clearable
                ></v-text-field>
              </div>
              <v-select
                v-model="searches[index]"
                v-case="'option'"
                clearable
                :multiple="header.multiple"
                :items="header.options"
              ></v-select>
              <v-select
                v-model="searches[index]"
                v-case="'boolean'"
                clearable
                :items="booleanOptions"
              ></v-select>
              <div v-case="'number'">
                <v-select
                  v-if="header.options"
                  v-model="searches[index]"
                  clearable
                  :items="header.options"
                ></v-select>
                <v-text-field
                  v-else
                  v-model="searches[index]"
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
      value: "experimental_program",
      type: "text",
    },
    {
      value: "date",
      type: "number",
    },
    {
      value: "specimen_designation",
      type: "text",
    },
    {
      value: "northridge",
      type: "option",
      options: ["pre", "post"],
    },
    {
      value: "specimen_type",
      type: "text",
      options: ["exterior", "interior"],
    },
    {
      value: "slab",
      type: "boolean",
    },
    {
      value: "connection_type",
      type: "option",
      options: ["WUF-W", "RBS", "WUF-B", "BFP", "WFP", "KBB", "BEEP"],
    },
    {
      value: "section_b",
      type: "text",
    },
    {
      value: "section_c",
      type: "text",
    },
    {
      value: "n_dp",
      type: "number",
      options: ["0", "> 0"],
    },
  ];
  connections: ConnectionModel[] = [];
  search = "";
  searches: string[] = [];
  totalCount = -1;
  loading = true;
  options: DataOptions | null = null;

  get tableHeaders(): TableHeader[] {
    return this.headers.map((header) => {
      return {
        value: header.value,
        text: this.$t(header.value).toString(),
        type: header.type,
        options: header.options,
        multiple: header.options ? header.options.length > 2 : false,
      };
    });
  }

  get query(): string {
    const queries = this.tableHeaders
      .map((header, index) => {
        const search = this.searches[index];
        if (
          search != undefined &&
          (typeof search == "boolean" || search.length > 0)
        ) {
          switch (header.type) {
            case "text":
              return `${header.value}:~%${search}%`;
            default:
              return `${header.value}:${search}`;
          }
        } else {
          return undefined;
        }
      })
      .filter((query) => query);
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
}

type HeaderType = "text" | "option" | "number" | "boolean";

interface Header {
  value: string;
  type: HeaderType;
  options?: string[];
}

interface TableHeader extends DataTableHeader {
  type: HeaderType;
  options?: string[];
  multiple?: boolean;
}
</script>
