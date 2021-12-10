<template>
  <v-card>
    <v-card-title>
      Connections
      <info-tooltip>Connections</info-tooltip>
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
      v-model="selectedItems"
      dense
      :headers="tableHeaders"
      :items="connections"
      :footer-props="{
        itemsPerPageOptions: [5, 10, 20, 100, 1000],
      }"
      :loading="loading"
      :options.sync="options"
      :search="search"
      :server-items-length="totalFilteredCount"
      show-select
      @click:row="onClick"
    >
      <template v-slot:top>
        <v-row class="px-4">
          <v-col v-for="header in filterHeaders" :key="header.value">
            <v-select
              v-if="header.options"
              v-model="columnSearches[header.value]"
              clearable
              hide-details
              :label="header.text"
              :multiple="header.multiple"
              :items="header.options"
            >
            </v-select>
            <div v-else v-switch="header.type">
              <v-text-field
                v-model="columnSearches[header.value]"
                v-case="'text'"
                clearable
                hide-details
                :label="header.text"
              ></v-text-field>
              <v-select
                v-model="columnSearches[header.value]"
                v-case="'boolean'"
                clearable
                hide-details
                :label="header.text"
                :items="booleanOptions"
              ></v-select>
              <v-text-field
                v-model="columnSearches[header.value]"
                v-case="'number'"
                clearable
                hide-details
                :label="header.text"
                type="number"
              ></v-text-field>
            </div>
          </v-col>
        </v-row>
      </template>
      <template v-slot:[`body.prepend`]>
        <tr>
          <td>
            <!-- select -->
          </td>
          <td v-for="header in tableHeaders" :key="header.value">
            <v-select
              v-if="header.options"
              v-model="columnSearches[header.value]"
              class="mt-0 pt-0"
              clearable
              hide-details
              :multiple="header.multiple"
              :items="header.options"
              single-line
            >
              <template
                v-if="header.value === 'connection_type'"
                v-slot:item="{ item, on, attrs }"
              >
                <v-list-item #default="{ active }" v-bind="attrs" v-on="on">
                  <v-list-item-action>
                    <v-checkbox :input-value="active"></v-checkbox>
                  </v-list-item-action>
                  <v-img
                    contain
                    max-height="128"
                    max-width="128"
                    :src="getImageSource(item)"
                  ></v-img>
                  {{ item }}
                </v-list-item>
              </template>
            </v-select>
            <div v-else v-switch="header.type">
              <v-text-field
                v-model="columnSearches[header.value]"
                v-case="'text'"
                class="mt-0 pt-0"
                clearable
                hide-details
                single-line
              ></v-text-field>
              <v-select
                v-model="columnSearches[header.value]"
                v-case="'boolean'"
                class="mt-0 pt-0"
                clearable
                hide-details
                :items="booleanOptions"
                single-line
              ></v-select>
              <v-text-field
                v-model="columnSearches[header.value]"
                v-case="'number'"
                class="mt-0 pt-0"
                clearable
                hide-details
                single-line
                type="number"
              ></v-text-field>
            </div>
          </td>
        </tr>
      </template>
      <template v-slot:expanded-item="{ headers, item }">
        <td :colspan="headers.length">
          <connection-detail :connection-id="item.id"></connection-detail>
        </td>
      </template>
      <template v-slot:[`item.t_dp_tot`]="{ item }">
        <template v-if="item.t_dp_tot">{{ item.t_dp_tot }}</template>
      </template>
    </v-data-table>
    <v-card-actions>
      <v-btn
        color="primary"
        :disabled="selectedItems.length === 0"
        text
        @click="onDownload"
      >
        <v-icon left>mdi-download</v-icon>
        Download ({{ selectedItems.length }}/{{ totalCount }})
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<style>
/* for select dropdown column search */
.v-menu__content {
  min-width: 300px !important;
}
</style>

<script lang="ts">
import { ConnectionModel } from "@/backend";
import { Component, Prop, PropSync, Vue, Watch } from "vue-property-decorator";
import { DataOptions, DataTableHeader } from "vuetify";
import { booleanOptions } from "@/utils/vuetify";
import { publicPath, Searches } from "@/utils/common";
import InfoTooltip from "@/components/commons/InfoTooltip.vue";

@Component({
  components: {
    InfoTooltip,
  },
})
export default class ConnectionTable extends Vue {
  readonly booleanOptions = booleanOptions;

  readonly headers: Header[] = [
    {
      value: "experimental_program",
      type: "text",
    },
    {
      value: "date",
      type: "number",
      filterOnly: true,
    },
    {
      value: "specimen_designation",
      type: "text",
    },
    {
      value: "northridge",
      type: "option",
      options: ["pre", "post"],
      filterOnly: true,
    },
    {
      value: "specimen_type",
      type: "text",
      options: ["exterior%", "interior%"],
      filterOnly: true,
    },
    {
      value: "slab",
      type: "boolean",
      filterOnly: true,
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
      filterOnly: true,
    },
    {
      value: "t_dp_tot",
      type: "number",
    },
  ];

  @PropSync("searches", { type: Object as () => Searches, default: () => ({}) })
  columnSearches!: Searches;
  @PropSync("search", { type: String, default: () => "" })
  globalSearch!: string;
  @Prop({ default: "" })
  readonly query!: string;

  connections: ConnectionModel[] = [];
  totalFilteredCount = -1;
  loading = true;
  options: DataOptions | null = null;
  selectedItems: ConnectionModel[] = [];
  totalCount = -1;

  get tableHeaders(): TableHeader[] {
    return this.headers
      .filter((header) => !header.filterOnly)
      .map(this.mapHeader);
  }

  get filterHeaders(): TableHeader[] {
    return this.headers
      .filter((header) => header.filterOnly)
      .map(this.mapHeader);
  }

  get hasFilters(): boolean {
    return (
      this.globalSearch.length > 0 ||
      Object.keys(this.columnSearches).length > 0
    );
  }

  created(): void {
    this.$connectionsApi
      .getCounts()
      .then((response) => response.data)
      .then((counts) => {
        this.totalCount = counts[0].value;
      });
  }

  @Watch("options", { deep: true })
  @Watch("query")
  onTableChanged(): void {
    if (this.options) {
      this.loading = true;
      this.$connectionsApi
        .getConnections(
          this.query,
          this.options.sortBy,
          this.options.sortDesc,
          this.options.page,
          this.options.itemsPerPage
        )
        .then((response) => response.data)
        .then((connections) => {
          this.connections = connections.items;
          this.totalFilteredCount = connections.total;
        })
        .finally(() => {
          this.loading = false;
        });
    }
  }

  getImageSource(item: string): string {
    return publicPath + "img/connection-type/" + item.toLowerCase() + ".png";
  }

  mapHeader(header: Header): TableHeader {
    return {
      value: header.value,
      text: this.$t("connection." + header.value).toString(),
      type: header.type,
      options: header.options?.sort(),
      multiple: header.options ? header.options.length > 2 : false,
    };
  }

  onResetFilters(): void {
    this.globalSearch = "";
    this.columnSearches = {};
  }

  onDownload(): void {
    this.selectedItems
      .map((item) => item.id)
      .map((id) => {
        this.$connectionsApi
          .getDownload(id)
          .then((response) => response.data)
          .then((data) => {
            window.open(data.global_csv);
            window.open(data.panel_zone_csv);
          });
      });
  }

  onClick(connection: ConnectionModel): void {
    this.$emit("click", connection);
  }
}

type HeaderType = "text" | "option" | "number" | "boolean";

interface Header {
  value: string;
  type: HeaderType;
  options?: string[];
  filterOnly?: boolean;
}

interface TableHeader extends DataTableHeader {
  type: HeaderType;
  options?: string[];
  multiple?: boolean;
}
</script>
