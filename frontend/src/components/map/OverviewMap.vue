<script setup lang="ts">
import 'leaflet/dist/leaflet.css'

import {
  bracesApi,
  columnsApi,
  connectionsApi,
  ductileFractureApi,
  ebfApi,
  hssApi,
  materialsApi,
  residualsApi,
  tensileCouponApi
} from '@/plugins/axios'
import { typesNames } from '@/utils/backend'
import {
  createMarkers,
  hasCoordinates,
  locationBraceFields,
  locationColumnFields,
  locationConnectionFields,
  locationDuctileFractureFields,
  locationEbfFields,
  locationHSSColumnFields,
  locationMaterialFields,
  locationResidualStressFields,
  locationTensileCouponFields,
  type LocationHSSColumn,
  type LocationEbf,
  type LocationBrace,
  type LocationColumn,
  type LocationConnection,
  type LocationDuctileFracture,
  type LocationMaterial,
  type LocationResidualStress,
  type LocationTensileCoupon
} from '@/utils/overviewmap'
import { PieChart, scaleColor, scaleRadius } from '@/utils/piechart'
import { rollups, select } from 'd3'
import {
  Control,
  DivIcon,
  DomUtil,
  map as LMap,
  Marker,
  MarkerClusterGroup,
  Point,
  tileLayer
} from 'leaflet'
import 'leaflet.markercluster'
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

// Maps an English category identifier (used for logic/comparison) to its
// translated display label. The identifier itself is never translated.
const categoryLabelKeys: Record<string, string> = {
  Connections: 'map.category_connections',
  Columns: 'map.category_columns',
  Braces: 'map.category_braces',
  'Cyclic Coupons': 'map.category_cyclic_coupons',
  'Residual Stresses': 'map.category_residual_stresses',
  'HSS Columns': 'map.category_hss_columns',
  'EBF Links': 'map.category_ebf_links',
  'Tensile Coupons': 'map.category_tensile_coupons',
  'Ductile Fracture': 'map.category_ductile_fracture'
}

function categoryLabel(type: string): string {
  const key = categoryLabelKeys[type]
  return key ? t(key) : type
}

// Reactive references to store various locations from API calls
const connectionsLocations = ref<LocationConnection[]>([])
connectionsApi.getConnectionsFields([...locationConnectionFields]).then((res) => {
  connectionsLocations.value = (res.data as LocationConnection[]).filter(hasCoordinates)
  updateMap()
})

const columnsLocations = ref<LocationColumn[]>([])
columnsApi.getColumnsFields(locationColumnFields).then((res) => {
  columnsLocations.value = (res.data as LocationColumn[]).filter(hasCoordinates)
  updateMap()
})

const bracesLocations = ref<LocationBrace[]>([])
bracesApi.getBracesFields(locationBraceFields).then((res) => {
  bracesLocations.value = (res.data as LocationBrace[]).filter(hasCoordinates)
  updateMap()
})

const materialsLocations = ref<LocationMaterial[]>([])
materialsApi.getMaterialsFields(locationMaterialFields).then((res) => {
  materialsLocations.value = (res.data as LocationMaterial[]).filter(hasCoordinates)
  updateMap()
})

const residualStressesLocations = ref<LocationResidualStress[]>([])
residualsApi.getResidualStressesFields(locationResidualStressFields).then((res) => {
  residualStressesLocations.value = (res.data as LocationResidualStress[]).filter(hasCoordinates)
  updateMap()
})

const hssColumnsLocations = ref<LocationHSSColumn[]>([])
hssApi.getHssColumnsFields(locationHSSColumnFields).then((res) => {
  hssColumnsLocations.value = (res.data as LocationHSSColumn[]).filter(hasCoordinates)
  updateMap()
})

const ebfLocations = ref<LocationEbf[]>([])
ebfApi.getEccentricBracedFramesFields(locationEbfFields).then((res) => {
  ebfLocations.value = (res.data as LocationEbf[]).filter(hasCoordinates)
  updateMap()
})

const tensileCouponLocations = ref<LocationTensileCoupon[]>([])
tensileCouponApi.getTensileCouponsFields(locationTensileCouponFields).then((res) => {
  tensileCouponLocations.value = (res.data as LocationTensileCoupon[]).filter(hasCoordinates)
  updateMap()
})

const ductileFractureLocations = ref<LocationDuctileFracture[]>([])
ductileFractureApi.getDuctileFracturesFields(locationDuctileFractureFields).then((res) => {
  ductileFractureLocations.value = (res.data as LocationDuctileFracture[]).filter(hasCoordinates)
  updateMap()
})

// Computed property to get the total number of markers
const dataLength = computed(
  () =>
    connectionsLocations.value.length +
    columnsLocations.value.length +
    bracesLocations.value.length +
    materialsLocations.value.length +
    residualStressesLocations.value.length +
    hssColumnsLocations.value.length +
    ebfLocations.value.length +
    tensileCouponLocations.value.length +
    ductileFractureLocations.value.length
)

// Reference to the map container element
const mapContainer = ref<HTMLDivElement>()

// Initialize the Leaflet map using the container reference
const map = computed(() => {
  const map = LMap(mapContainer.value as HTMLDivElement, {
    minZoom: 1,
    zoomSnap: 0.25
  })
    .setView([45, 0], 2)
    .setMaxBounds([
      [-120, -200],
      [120, 200]
    ])
  tileLayer('https://cartodb-basemaps-1.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png').addTo(map)
  return map
})

const prevCluster = ref<null | MarkerClusterGroup>(null)

const cluster = computed(() => {
  return new MarkerClusterGroup({
    showCoverageOnHover: false,
    zoomToBoundsOnClick: false,
    iconCreateFunction: function (cluster) {
      const childCount = cluster.getChildCount()
      const radius = scaleRadius.domain([0, dataLength.value])(childCount)

      const allChilds = cluster.getAllChildMarkers()

      // Use D3 rollups to count the distribution of marker types within the cluster
      const counts = rollups(
        allChilds,
        (v) => v.length,
        (d) => (d.feature ? d.feature.properties.type : null)
      )

      return new DivIcon({
        html: PieChart(
          counts.map(([name, value]) => ({ name, value })),
          {
            name: (d) => d.name,
            value: (d) => d.value,
            innerRadius: Math.max(7, radius / 4),
            width: radius,
            height: radius
          }
        ) as unknown as HTMLElement,
        className: '',
        iconSize: new Point(radius, radius)
      })
    }
  })
})

// Compute markers from the fetched locations
const markers = computed<Marker[]>(() => {
  return [
    createMarkers(connectionsLocations.value, 'Connections'),
    createMarkers(columnsLocations.value, 'Columns'),
    createMarkers(bracesLocations.value, 'Braces'),
    createMarkers(materialsLocations.value, 'Cyclic Coupons'),
    createMarkers(residualStressesLocations.value, 'Residual Stresses'),
    createMarkers(hssColumnsLocations.value, 'HSS Columns'),
    createMarkers(ebfLocations.value, 'EBF Links'),
    createMarkers(tensileCouponLocations.value, 'Tensile Coupons'),
    createMarkers(ductileFractureLocations.value, 'Ductile Fracture')
  ].flat()
})

// Create a legend control for filtering markers by type
const legend = computed(() => {
  const legend = new Control({ position: 'bottomleft' })

  legend.onAdd = function () {
    const div = DomUtil.create('div', 'legend')

    for (const type of typesNames) {
      div.innerHTML += `<input id="checkbox_${type.replace(
        /\s/g,
        ''
      )}" type='checkbox' checked /> <i style='background: ${scaleColor(
        type
      )}'> </i> ${categoryLabel(type)} <br>`
    }

    return div
  }
  return legend
})

function setEventListenerLegend() {
  const div = '.legend'

  for (const type of typesNames) {
    select(div)
      .select(`#checkbox_${type.replace(/\s/g, '')}`)
      .on('change', (e) => {
        e.stopPropagation()

        const layers = markers.value.filter(({ feature }) =>
          feature ? feature.properties.type === type : false
        )
        if (e.target.checked) cluster.value.addLayers(layers)
        else cluster.value.removeLayers(layers)
      })
  }

  select(div).on('dblclick', (e) => e.stopPropagation())
}

function updateMap() {
  if (prevCluster.value) map.value.removeLayer(prevCluster.value as MarkerClusterGroup)
  cluster.value.clearLayers()
  cluster.value.addLayers(markers.value)

  map.value.addLayer(cluster.value)
  prevCluster.value = cluster.value
  map.value.fitBounds(cluster.value.getBounds())
  setEventListenerLegend()
}

const mapWidth = computed(() => mapContainer.value?.clientWidth || 0)
const mapHeight = computed(() => mapContainer.value?.clientHeight || 0)

onMounted(() => {
  cluster.value.addLayers(markers.value)
  map.value.addLayer(cluster.value)
  prevCluster.value = cluster.value
  legend.value.addTo(map.value)
  cluster.value.on('clusterclick', function (a) {
    a.layer.zoomToBounds({ padding: [mapWidth.value * 0.2, mapHeight.value * 0.1] })
  })
  setEventListenerLegend()
})
</script>

<template>
  <div class="fill-height">
    <div ref="mapContainer" class="fill-height mapContainer" color="secondary"></div>
    <div
      class="cluster-table"
      :style="{ width: `${mapWidth / 5}px`, height: `${mapHeight / 5}px` }"
    />
  </div>
</template>

<style lang="scss" scoped>
.cluster-table {
  position: relative;
  z-index: 10;
  background-color: blue;
}

.mapContainer {
  z-index: 1;
}

.mapContainer :deep(a) {
  color: black;
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
