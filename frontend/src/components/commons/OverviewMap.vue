<template>
  <v-responsive aspect-ratio="1.2" :max-height="maxHeight">
    <div id="container">
      <div id="mapContainer"></div>
    </div>
  </v-responsive>
</template>

<script lang="ts">
import "leaflet/dist/leaflet.css";
import * as L from "leaflet";
import "leaflet.markercluster";

import * as d3 from "d3";
import fakeData from "@/assets/connection/fake_data_overviewmap.csv";
import {
  PieChart,
  types,
  MarkerSVG,
  scaleRadius,
  scaleColor,
} from "@/utils/piechart";
import { Component, Prop, Vue, Watch } from "vue-property-decorator";

@Component
export default class OverviewMap extends Vue {
  @Prop({ type: String, default: "" })
  private readonly title!: string;

  @Prop({ type: Number, default: 500 })
  public maxHeight!: number;

  private values: boolean[] = [];

  public createMap() {
    const map = L.map("mapContainer").setView([45, 0], 2);
    L.tileLayer(
      "https://cartodb-basemaps-1.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png"
    ).addTo(map);

    const icons = new Map(
      types.map((type) => [
        type,
        L.divIcon({
          html: MarkerSVG(scaleColor(type)),
          className: "",
          iconSize: [30, 30],
        }),
      ])
    );

    const cluster = new L.MarkerClusterGroup({
      showCoverageOnHover: false,
      iconCreateFunction: function (cluster) {
        var childCount = cluster.getChildCount();

        let radius = scaleRadius.domain([0, fakeData.length])(childCount);

        const allChilds = cluster.getAllChildMarkers();

        const counts = d3.rollups(
          allChilds,
          (v) => v.length,
          (d) => (d.feature ? d.feature.properties.type : null)
        );

        return new L.DivIcon({
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
          iconSize: new L.Point(radius, radius),
        });
      },
    });

    let markers: L.Marker[] = [];

    for (let d of fakeData) {
      let marker = L.marker([d.latitude, d.longitude], {
        icon: icons.get(d.type),
      }).bindPopup(`${d.experimental_program} ${d.date} <br> ${d.type}`);
      marker.feature = {
        type: "Feature",
        properties: d,
        geometry: { type: "Point", coordinates: [d.latitude, d.longitude] },
      };
      markers.push(marker);

      cluster.addLayer(marker);
    }

    map.addLayer(cluster);

    var legend = new L.Control({ position: "bottomright" });

    legend.onAdd = function (map) {
      var div = L.DomUtil.create("div", "legend");

      for (let type of types) {
        div.innerHTML += `<input id="checkbox_${type.replace(
          /\s/g,
          ""
        )}" type='checkbox' checked /> <i style='background: ${scaleColor(
          type
        )}'> </i> ${type} <br>`;
      }

      for (let type of types) {
        d3.select(div)
          .select(`#checkbox_${type.replace(/\s/g, "")}`)
          .on("change", (e) => {
            e.stopPropagation();

            let layers = markers.filter(({ feature }) =>
              feature ? feature.properties.type === type : false
            );
            if (e.target.checked) cluster.addLayers(layers);
            else cluster.removeLayers(layers);
          });
      }

      d3.select(div).on("dblclick", (e) => e.stopPropagation());

      return div;
    };

    legend.addTo(map);
  }

  mounted() {
    this.createMap();
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
</style>
