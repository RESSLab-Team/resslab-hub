<template>
  <v-responsive aspect-ratio="1.2" :max-height="maxHeight">
    <div id="mapContainer"></div>
  </v-responsive>
</template>

<script lang="ts">
import "leaflet/dist/leaflet.css";
import { specimenTypeImageSrc } from "@/utils/connections";

import {
  map as LMap,
  tileLayer,
  divIcon,
  MarkerClusterGroup,
  DivIcon,
  Point,
  Marker,
  Control,
  DomUtil,
} from "leaflet";
import "leaflet.markercluster";

import { rollups, select } from "d3";
import {
  PieChart,
  typesNames,
  MarkerSVG,
  scaleRadius,
  scaleColor,
} from "@/utils/piechart";
import { Component, Prop, Vue, Watch } from "vue-property-decorator";
import { LocationModel } from "@/backend";

@Component
export default class OverviewMap extends Vue {
  @Prop({ type: Number, default: 500 })
  public maxHeight!: number;

  private icons = new Map(
    typesNames.map((type) => [
      type,
      divIcon({
        html: MarkerSVG(scaleColor(type)),
        className: "",
        iconSize: [30, 30],
        iconAnchor: [15, 30],
      }),
    ])
  );

  private connectionsLocations: LocationModel[] = [];

  // should return this.connectionsLocations.length + this.steelMaterialsLocations.length etc... when endpoint finished
  get dataLength(): number {
    return this.connectionsLocations.length;
  }

  @Watch("connectionsLocations")
  onConnectionsChanged() {
    this.updateMap();
  }

  private get map() {
    const map = LMap("mapContainer").setView([45, 0], 2);
    tileLayer(
      "https://cartodb-basemaps-1.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png"
    ).addTo(map);
    return map;
  }

  private get cluster() {
    const dataLength = this.dataLength;
    return new MarkerClusterGroup({
      showCoverageOnHover: false,
      iconCreateFunction: function (cluster) {
        var childCount = cluster.getChildCount();

        const radius = scaleRadius.domain([0, dataLength])(childCount);

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
  }

  createTooltipConnections(d: LocationModel) {
    return `<div class="tooltip">
      <h3><a href="${d.link}">${d.experimental_program} (${d.date})</a></h3>
      <br>
      <ul>
        <li>${d.specimen_type}</li >
        <li>${d.connection_type}, Beam: ${d.section_b} Col: ${d.section_c}</li>
        <li>
          <img alt="${d.specimen_type}" src="${specimenTypeImageSrc(
      d.specimen_type
    )}"></img>
        </li>
        <li><a href=''>View experimental data</a></li>
      </ul>
      </div>`;
  }

  getCreateTooltip(type: string) {
    switch (type) {
      case "Connections":
        return this.createTooltipConnections;
    }
    return (d: LocationModel) =>
      `<h3>No tooltip constructor found for ${d} type is ${type}</h3>`;
  }

  createMarkers(data: LocationModel[], type: string) {
    const createTooltip = this.getCreateTooltip(type);
    return data.map((d) => {
      const marker = new Marker([d.latitude, d.longitude], {
        icon: this.icons.get(type),
      }).bindPopup(createTooltip(d));
      marker.feature = {
        type: "Feature",
        properties: Object.assign(d, { type }),
        geometry: {
          type: "Point",
          coordinates: [d.latitude, d.longitude],
        },
      };
      return marker;
    });
  }

  private get markers() {
    return this.createMarkers(this.connectionsLocations, "Connections");
  }
  private get legend() {
    const legend = new Control({ position: "bottomright" });

    legend.onAdd = function () {
      var div = DomUtil.create("div", "legend");

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
  }

  setEventListenerLegend() {
    const div = ".legend";

    for (const type of typesNames) {
      select(div)
        .select(`#checkbox_${type.replace(/\s/g, "")}`)
        .on("change", (e) => {
          e.stopPropagation();

          const layers = this.markers.filter(({ feature }) =>
            feature ? feature.properties.type === type : false
          );
          if (e.target.checked) this.cluster.addLayers(layers);
          else this.cluster.removeLayers(layers);
        });
    }

    select(div).on("dblclick", (e) => e.stopPropagation());
  }

  public setupMap() {
    this.cluster.addLayers(this.markers);
    this.map.addLayer(this.cluster);
    this.legend.addTo(this.map);
    this.setEventListenerLegend();
  }

  public updateMap() {
    this.cluster.addLayers(this.markers);
    this.map.addLayer(this.cluster);
    this.setEventListenerLegend();
  }

  mounted() {
    this.setupMap();
  }
  public created() {
    this.$connectionsApi
      .getConnectionsLocations()
      .then((res) => (this.connectionsLocations = res.data));
  }
}
</script>

<style>
.legend {
  line-height: 22px;
  color: #555;
  font-size: medium;
}

#mapContainer {
  height: 500px;
}

.legend i {
  width: 22px;
  height: 22px;
  float: left;
  margin-right: 8px;
  opacity: 0.7;
}

div.legend {
  padding: 6px 8px;
  background-color: rgba(255, 255, 255, 0.8);
  box-shadow: 0 0 15px rgba(0, 0, 0, 0.2);
  border-radius: 5px;
}

.legend h4 {
  margin: 0 0 5px;
  color: #777;
}

.tooltip ul {
  list-style-type: none;
  padding-left: 0;
}

.tooltip li {
  padding-bottom: 5px;
}

.tooltip img {
  max-height: 130px;
  max-width: 100%;
}
</style>
