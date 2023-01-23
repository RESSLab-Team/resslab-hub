<script setup lang="ts">
import {
  LocationBracesModel,
  LocationColumnsModel,
  LocationConnectionsModel,
  LocationMaterialsModel,
} from "@/backend";

import {
  PieChart,
  scaleColor,
  scaleRadius,
  typesNames,
} from "@/utils/piechart";
import { rollups, select } from "d3";
import {
  Control,
  DivIcon,
  DomUtil,
  map as LMap,
  Marker,
  MarkerClusterGroup,
  Point,
  tileLayer,
} from "leaflet";
import "leaflet.markercluster";
import "leaflet/dist/leaflet.css";
import {
  bracesApi,
  columnsApi,
  connectionsApi,
  materialsApi,
} from "@/plugins/axios";

import { createMarkers } from "@/utils/overviewmap";

import { computed, defineProps, onMounted, ref } from "vue";

const props = defineProps({
  maxHeight: {
    type: Number,
    default: 500,
  },
});

const connectionsLocations = ref<LocationConnectionsModel[]>([]);
connectionsApi
  .getConnectionsLocations()
  .then((res: { data: LocationConnectionsModel[] }) => {
    connectionsLocations.value = res.data;
    updateMap();
  });

const columnsLocations = ref<LocationColumnsModel[]>([]);
columnsApi
  .getColumnsLocations()
  .then((res: { data: LocationColumnsModel[] }) => {
    columnsLocations.value = res.data;
    updateMap();
  });

const bracesLocations = ref<LocationBracesModel[]>([]);
bracesApi.getBracesLocations().then((res: { data: LocationBracesModel[] }) => {
  bracesLocations.value = res.data;
  updateMap();
});

const materialsLocations = ref<LocationMaterialsModel[]>([]);
materialsApi
  .getMaterialsLocations()
  .then((res: { data: LocationMaterialsModel[] }) => {
    materialsLocations.value = res.data;
    updateMap();
  });

const dataLength = computed(
  () =>
    connectionsLocations.value.length +
    columnsLocations.value.length +
    bracesLocations.value.length +
    materialsLocations.value.length
);

const mapContainer = ref<HTMLDivElement>();

const map = computed(() => {
  const map = LMap(mapContainer.value as HTMLDivElement).setView([45, 0], 2);
  tileLayer(
    "https://cartodb-basemaps-1.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png"
  ).addTo(map);
  return map;
});

const prevCluster = ref<null | MarkerClusterGroup>(null);

const cluster = computed(() => {
  return new MarkerClusterGroup({
    showCoverageOnHover: false,
    iconCreateFunction: function (cluster) {
      var childCount = cluster.getChildCount();
      const radius = scaleRadius.domain([0, dataLength.value])(childCount);

      const allChilds = cluster.getAllChildMarkers();

      const counts = rollups(
        allChilds,
        (v) => v.length,
        (d) => (d.feature ? d.feature.properties.type : null)
      );

      return new DivIcon({
        html: PieChart(
          counts.map(([name, value]) => ({ name, value })),
          {
            name: (d) => d.name,
            value: (d) => d.value,
            innerRadius: Math.max(7, radius / 4),
            width: radius,
            height: radius,
          }
        ) as unknown as HTMLElement,
        className: "",
        iconSize: new Point(radius, radius),
      });
    },
  });
});

const markers = computed<Marker[]>(() => {
  return [
    createMarkers(connectionsLocations.value, "Connections"),
    createMarkers(columnsLocations.value, "Columns"),
    createMarkers(bracesLocations.value, "Braces"),
    createMarkers(materialsLocations.value, "Materials"),
  ].flat();
});

const legend = computed(() => {
  const legend = new Control({ position: "bottomright" });

  legend.onAdd = function () {
    const div = DomUtil.create("div", "legend");

    for (const type of typesNames) {
      div.innerHTML += `<input id="checkbox_${type.replace(
        /\s/g,
        ""
      )}" type='checkbox' checked /> <i style='background: ${scaleColor(
        type
      )}'> </i> ${type} <br>`;
    }

    return div;
  };
  return legend;
});

function setEventListenerLegend() {
  const div = ".legend";

  for (const type of typesNames) {
    select(div)
      .select(`#checkbox_${type.replace(/\s/g, "")}`)
      .on("change", (e) => {
        e.stopPropagation();

        const layers = markers.value.filter(({ feature }) =>
          feature ? feature.properties.type === type : false
        );
        if (e.target.checked) cluster.value.addLayers(layers);
        else cluster.value.removeLayers(layers);
      });
  }

  select(div).on("dblclick", (e) => e.stopPropagation());
}

function updateMap() {
  if (prevCluster.value)
    map.value.removeLayer(prevCluster.value as MarkerClusterGroup);
  cluster.value.clearLayers();
  cluster.value.addLayers(markers.value);
  map.value.addLayer(cluster.value);
  prevCluster.value = cluster.value;
  setEventListenerLegend();
}

onMounted(() => {
  cluster.value.addLayers(markers.value);
  map.value.addLayer(cluster.value);
  prevCluster.value = cluster.value;
  legend.value.addTo(map.value);
  setEventListenerLegend();
});
</script>

<template>
  <v-responsive aspect-ratio="1.2" :max-height="props.maxHeight">
    <div ref="mapContainer" class="mapContainer"></div>
  </v-responsive>
</template>

<style lang="scss" scoped>
.mapContainer {
  height: 500px;
  z-index: 1;
}

.mapContainer :deep(.tooltip) ul {
  list-style-type: none;
  padding-left: 0;
}

.mapContainer :deep(.tooltip) li {
  padding-bottom: 5px;
}

.mapContainer :deep(.tooltip) img {
  max-height: 130px;
  max-width: 100%;
}

.mapContainer :deep(.legend) {
  line-height: 22px;
  color: #555;
  font-size: medium;
}

.mapContainer :deep(.legend) i {
  width: 22px;
  height: 22px;
  float: left;
  margin-right: 8px;
  opacity: 0.7;
}

.mapContainer :deep(div.legend) {
  padding: 6px 8px;
  background-color: rgba(255, 255, 255, 0.8);
  box-shadow: 0 0 15px rgba(0, 0, 0, 0.2);
  border-radius: 5px;
}

.mapContainer :deep(.legend) h4 {
  margin: 0 0 5px;
  color: #777;
}
</style>
