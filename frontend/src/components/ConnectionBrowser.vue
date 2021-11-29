<template>
  <v-card>
    <v-card-title>
      Connections
      <v-spacer></v-spacer>
      <v-text-field
        v-model="globalSearch"
        clearable
        hide-details
        single-line
        append-icon="mdi-magnify"
        label="Search"
      ></v-text-field>
      <v-btn
        color="primary"
        :disabled="!hasFilters"
        text
        @click="onResetFilters"
      >
        Reset filters
      </v-btn>
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
          <td v-for="header in tableHeaders" :key="header.value">
            <div v-switch="header.type">
              <div v-case="'text'">
                <v-select
                  v-if="header.options"
                  v-model="columnSearches[header.value]"
                  clearable
                  :items="header.options"
                ></v-select>
                <v-text-field
                  v-else
                  v-model="columnSearches[header.value]"
                  clearable
                ></v-text-field>
              </div>
              <v-select
                v-model="columnSearches[header.value]"
                v-case="'option'"
                clearable
                :multiple="header.multiple"
                :items="header.options"
              ></v-select>
              <v-select
                v-model="columnSearches[header.value]"
                v-case="'boolean'"
                clearable
                :items="booleanOptions"
              ></v-select>
              <div v-case="'number'">
                <v-select
                  v-if="header.options"
                  v-model="columnSearches[header.value]"
                  clearable
                  :items="header.options"
                ></v-select>
                <v-text-field
                  v-else
                  v-model="columnSearches[header.value]"
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
import { Component, Prop, PropSync, Vue, Watch } from "vue-property-decorator";
import { DataOptions, DataTableHeader } from "vuetify";
import { booleanOptions } from "@/utils/vuetify";
import ConnectionDetail from "@/components/ConnectionDetail.vue";
import { Searches } from "@/utils/common";

@Component({
  components: {
    ConnectionDetail,
  },
})
export default class ConnectionBrowser extends Vue {
  readonly booleanOptions = booleanOptions;

  @PropSync("searches", { type: Object as () => Searches, default: () => ({}) })
  columnSearches!: Searches;
  @PropSync("search", { type: String, default: () => "" })
  globalSearch!: string;
  @Prop({ default: "" })
  readonly query!: string;

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
      options: ["exterior%", "interior%"],
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
    {
      value: "t_dp_tot",
      type: "number",
    },
  ];
  connections: ConnectionModel[] = [];
  totalCount = -1;
  loading = true;
  options: DataOptions | null = null;

  get tableHeaders(): TableHeader[] {
    return this.headers.map((header) => {
      return {
        value: header.value,
        text: this.$t("connection." + header.value).toString(),
        type: header.type,
        options: header.options,
        multiple: header.options ? header.options.length > 2 : false,
      };
    });
  }

  get hasFilters(): boolean {
    return (
      this.globalSearch.length > 0 ||
      Object.keys(this.columnSearches).length > 0
    );
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

  onResetFilters(): void {
    this.globalSearch = "";
    this.columnSearches = {};
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
