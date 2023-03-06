<script setup lang="ts">
import { ConnectionField, ConnectionModel } from "@/backend";
import InfoTooltip from "@/components/commons/InfoTooltip.vue";
import SimpleTable from "@/components/commons/SimpleTable.vue";
import { connectionsApi } from "@/plugins/axios";
import { publicPath, Searches } from "@/utils/common";
import { Column, useTable } from "@/utils/table";
import {
  withDefaults,
  defineProps,
  defineEmits,
  ref,
  computed,
  toRef,
} from "vue";
import { DataOptions } from "vuetify";
import { useNotificationStore } from "@/stores/notification";
import { Page } from "@/utils/backend";

const props = withDefaults(
  defineProps<{
    query?: string;
    searches?: Searches;
    search?: string;
  }>(),
  {
    query: undefined,
    searches: () => ({}),
    search: "",
  }
);
const emit = defineEmits<{
  (e: "click:row", value: ConnectionModel): void;
  (e: "update:page", value: Page<ConnectionModel>): void;
  (e: "update:search", value: string): void;
  (e: "update:searches", value: Searches): void;
}>();

const columns: Column[] = [
  {
    value: ConnectionField.ExperimentalProgram,
    type: "text",
  },
  {
    value: ConnectionField.Date,
    type: "number",
    filterOnly: true,
  },
  {
    value: ConnectionField.SpecimenDesignation,
    type: "text",
  },
  {
    value: ConnectionField.Northridge,
    type: "option",
    options: ["pre", "post"],
    filterOnly: true,
  },
  {
    value: ConnectionField.SpecimenType,
    type: "text",
    options: ["exterior%", "interior%"],
    filterOnly: true,
  },
  {
    value: ConnectionField.Slab,
    type: "boolean",
    filterOnly: true,
  },
  {
    value: ConnectionField.ConnectionType,
    type: "option",
    options: ["WUF-W", "RBS", "WUF-B", "BFP", "WFP", "KBB", "BEEP"],
  },
  {
    value: ConnectionField.SectionB,
    type: "text",
  },
  {
    value: ConnectionField.SectionC,
    type: "text",
  },
  {
    value: ConnectionField.NDp,
    type: "number",
    options: ["0", "> 0"],
    filterOnly: true,
  },
  {
    value: ConnectionField.TDpTot,
    type: "number",
  },
];

const options = ref<DataOptions>();

const searches = computed<Searches>({
  get: () => props.searches,
  set: (value) => emit("update:searches", value),
});
const globalSearch = computed<string>({
  get: () => props.search,
  set: (value) => emit("update:search", value),
});

const notificationStore = useNotificationStore();
const { downloadFiles, items, loading, totalCount, totalFilteredCount } =
  useTable<ConnectionModel>(
    "connection",
    options,
    toRef(props, "query"),
    [
      {
        name: "beam",
        countKey: "beam_count",
        getCsv: (id) => connectionsApi.getConnectionsBeamCsv(id),
      },
      {
        name: "beam-west",
        countKey: "beam_west_count",
        getCsv: (id) => connectionsApi.getConnectionsBeamWestCsv(id),
      },
      {
        name: "global",
        countKey: "global_count",
        getCsv: (id) => connectionsApi.getConnectionsGlobalCsv(id),
      },
      {
        name: "global-west",
        countKey: "global_west_count",
        getCsv: (id) => connectionsApi.getConnectionsGlobalWestCsv(id),
      },
      {
        name: "panel-zone",
        countKey: "panel_zone_count",
        getCsv: (id) => connectionsApi.getConnectionsPanelZonesCsv(id),
      },
    ],
    () => connectionsApi.getConnectionsCounts(),
    (query, sortBy, sortDesc, page, size) =>
      connectionsApi.getConnections(query, sortBy, sortDesc, page, size),
    (ids) => connectionsApi.getConnectionsCsv(ids),
    (message) => notificationStore.notify(message),
    (page) => emit("update:page", page)
  );

function getImageSource(item: string): string {
  return publicPath + "img/connection-type/" + item.toLowerCase() + ".svg";
}
</script>

<template>
  <simple-table
    :columns="columns"
    :items="items"
    :loading="loading"
    :options.sync="options"
    prefix="connection."
    :query="query"
    :search.sync="globalSearch"
    :searches.sync="searches"
    :total-count="totalCount"
    :total-filtered-count="totalFilteredCount"
    @click:row="emit('click:row', $event)"
    @download="downloadFiles"
  >
    <template #title>
      Connections
      <info-tooltip>
        <p>
          The Connections Database presents data from early 1970s on
          beam-to-column connections under reversed cyclic and monotonic
          loading. The primary data involve the global behavior of the
          connection and the decomposed panel zone shear versus shear
          distortion, deduced beam end moment versus chord rotation, whenever
          available.
        </p>
        How to use?
        <ul>
          <li>
            Filter the table by making selections in the various plots around
            the table, or by using the filters and dropdowns above the table
            headers.
          </li>
          <li>Click on a row to see the data of a single test.</li>
          <li>
            Download specific tests results by selecting the test (left-most
            column) and click "Download" below.
          </li>
          <li>
            Share specific tests results by selecting the test (left-most
            column) and click "Share" below.
          </li>
        </ul>
      </info-tooltip>
    </template>
    <template #[`column.header.item.connection_type`]="{ item, on, attrs }">
      <v-list-item v-slot="{ active }" v-bind="attrs" v-on="on">
        <v-list-item-action>
          <v-checkbox :input-value="active" />
        </v-list-item-action>
        <v-img
          contain
          max-height="128"
          max-width="128"
          :src="getImageSource(item)"
        />
        <span class="ma-2">{{ item }}</span>
      </v-list-item>
    </template>
  </simple-table>
</template>
