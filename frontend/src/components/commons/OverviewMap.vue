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

import * as d3 from "d3-array";
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
      iconCreateFunction: function (cluster) {
        var childCount = cluster.getChildCount();

        let radius = scaleRadius(childCount);

        const allChilds = cluster.getAllChildMarkers();

        const counts = d3.rollups(
          allChilds,
          (v) => v.length,
          (d) => (d.feature ? d.feature.properties.type : null)
        );
        console.log(childCount, radius, cluster, allChilds);
        console.log(counts);

        return new L.DivIcon({
          html: PieChart(
            counts.map(([name, value]) => ({ name, value })),
            {
              name: (d) => d.name,
              value: (d) => d.value,
              width: radius,
              height: radius,
            }
          ) as unknown as HTMLElement,
          className: "",
          iconSize: new L.Point(radius, radius),
        });
      },
    });

    for (let d of fakeData) {
      let marker = L.marker([d.latitude, d.longitude], {
        icon: icons.get(d.type),
      }).bindPopup(`${d.experimental_program} ${d.date} <br> ${d.type}`);
      marker.feature = {
        type: "Feature",
        properties: d,
        geometry: { type: "Point", coordinates: [d.latitude, d.longitude] },
      };
      cluster.addLayer(marker);
    }

    map.addLayer(cluster);

    var legend = new L.Control({ position: "bottomright" });

    legend.onAdd = function () {
      var div = L.DomUtil.create("div", "legend");

      for (let type of types) {
        div.innerHTML +=
          '<i style="background:' +
          scaleColor(type) +
          '"></i> ' +
          type +
          "<br>";
      }

      return div;
    };

    legend.addTo(map);

    console.log(map);
  }

  mounted() {
    this.createMap();
  }
}
</script>

<style>
.legend {
  line-height: 18px;
  color: #555;
}

#mapContainer {
  height: 500px;
}

.legend i {
  width: 18px;
  height: 18px;
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
