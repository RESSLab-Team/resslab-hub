<template>
  <v-row>
    <v-col cols="12">
      <v-row align="center">
        <v-col>
          <h1>Predictive Model for Steel wide Flange Columns</h1>
          <p>
            For further information refer to
            <a href="" target="_blank"> Lignos et al. (2019) </a>
          </p>
        </v-col>
        <v-col cols="auto">
          <toggle v-model="unitSystem" :items="unitItems"></toggle>
        </v-col>
      </v-row>
    </v-col>
    <v-col cols="6">
      <v-row>
        <v-col>
          <v-card>
            <v-card-title>
              Select Steel Profile
              <info-tooltip>
                Here, you may choose to either select a W-Shape from the AISC
                database or input your own dimensions using the sliders below
              </info-tooltip>
            </v-card-title>
            <v-card-text>
              <v-row>
                <v-col cols="6">
                  <v-select
                    v-model="database"
                    hide-details
                    :items="databases"
                    label="Select Database"
                    single-line
                  ></v-select>
                </v-col>
                <v-col cols="6">
                  <search-select
                    v-model="section"
                    :items="sections"
                    label="Select Section"
                  ></search-select>
                </v-col>
              </v-row>
              <v-row>
                <v-col
                  v-for="item in steelShapeDimensions"
                  :key="item.key"
                  v-bind="variableBind"
                >
                  <unit-slider
                    v-model="$data[item.key]"
                    :disabled="!!section"
                    :label="item.text"
                    :max="item.max"
                    :min="item.min"
                    :unit="item.unit"
                    :unit-system="unitSystem"
                  ></unit-slider>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-card>
            <v-card-title>
              Specify Member and Loading Properties
              <info-tooltip>
                Here you need to specify the beam full length (L), the beam
                unbraced length (L<sub>b</sub>), which is defined as the
                distance from the column face to the nearest lateral brace, the
                expected yield stress, F<sub>y</sub> of the steel material, the
                capping-to-yield ratio <sup>Mc</sup>/<sub>My</sub>, the expected
                residual strength ratio, K, and the ultimate rotation
                &theta;<sub>u</sub> of the steel component.
              </info-tooltip>
            </v-card-title>
            <v-card-text>
              <v-row>
                <v-col
                  v-for="item in memberProperties"
                  :key="item.key"
                  v-bind="variableBind"
                >
                  <unit-slider
                    v-model="$data[item.key]"
                    :label="item.text"
                    :max="item.max"
                    :min="item.min"
                    :unit="item.unit"
                    :unit-system="unitSystem"
                  ></unit-slider>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-col>
    <v-col cols="6">
      <v-img
        contain
        height="400px"
        :src="publicPath + 'img/column/component.png'"
      ></v-img>
    </v-col>
    <v-col cols="6">
      <v-row justify="center">
        <v-col cols="6">
          <v-card>
            <v-card-text>
              <unit-chart
                :option="option(backboneResult, envelopeResult)"
                :unit-system="unitSystem"
                x-unit="rad"
                y-unit="kN⋅mm"
              ></unit-chart>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-col>
    <v-col cols="6">
      <v-card>
        <v-card-title>
          Predictive model for columns
          <info-tooltip>
            Provided that the steel member is in double curvature
          </info-tooltip>
        </v-card-title>
        <v-card-text>
          <v-simple-table dense>
            <template #default>
              <thead>
                <tr>
                  <th class="text-center">Parameter</th>
                  <th class="text-center">Unit</th>
                  <th class="text-center">Monotonic Backbone</th>
                  <th class="text-center">First Cycle Envelope</th>
                </tr>
              </thead>
              <tbody>
                <unit-table-row
                  v-for="item in rows"
                  :key="item.key"
                  :field="item.key"
                  :text="item.text"
                  :unit="item.unit"
                  :fraction-digit="item.fractionDigit"
                  :columns="[backboneResult, envelopeResult]"
                  :unit-system="unitSystem"
                ></unit-table-row>
              </tbody>
            </template>
          </v-simple-table>
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import aiscSections from "@/assets/connection/aisc-sections.csv";
import europeanSections from "@/assets/connection/european-sections.csv";
import japaneseSections from "@/assets/connection/japanese-sections.csv";
import UnitChart from "@/components/commons/charts/UnitChart.vue";
import InfoTooltip from "@/components/commons/InfoTooltip.vue";
import SearchSelect from "@/components/commons/SearchSelect.vue";
import UnitSlider, {
  Variable,
} from "@/components/commons/sliders/UnitSlider.vue";
import Toggle, { unitItems } from "@/components/commons/Toggle.vue";
import UnitTableRow, {
  UnitTableRowData,
} from "@/components/commons/UnitTableRow.vue";
import { publicPath, Section } from "@/utils/common";
import { variableBind } from "@/utils/model";
import { UnitSystem } from "@/utils/unit";
import { primaryColor, secondaryColor, SelectItem } from "@/utils/vuetify";
import { EChartsOption } from "echarts";
import { clamp } from "lodash";
import { Component, Vue, Watch } from "vue-property-decorator";

/**
 * Computations from https://github.com/RESSLab-Team/resslab-hub-scripts/tree/main/steel_columns
 */
@Component({
  components: {
    InfoTooltip,
    SearchSelect,
    Toggle,
    UnitChart,
    UnitSlider,
    UnitTableRow,
  },
})
export default class ColumnComponent extends Vue {
  readonly unitItems = unitItems;
  readonly publicPath = publicPath;
  readonly variableBind = variableBind;

  readonly databases: Database[] = ["aisc", "european", "japanese"];
  readonly chartBind = {
    cols: "12",
    sm: "6",
    lg: "3",
    xl: "2",
  };
  readonly steelShapeDimensions: Variable[] = [
    {
      key: "bf",
      text: "b<sub>f</sub>",
      unit: "mm",
      min: 100,
      max: 500,
    },
    { key: "d", text: "d", unit: "mm", min: 100, max: 2000 },
    {
      key: "tf",
      text: "t<sub>f</sub>",
      unit: "mm",
      min: 5,
      max: 100,
    },
    {
      key: "tw",
      text: "t<sub>w</sub>",
      unit: "mm",
      min: 5,
      max: 100,
    },
  ];

  readonly memberProperties: Variable[] = [
    {
      key: "pgPye",
      text: "P<sub>g</sub>/P<sub>ye</sub>",
      min: 0,
      max: 1,
    },
    {
      key: "l",
      text: "L",
      unit: "mm",
      min: 1000,
      max: 12000,
    },
    {
      key: "lb",
      text: "L<sub>b</sub>",
      unit: "mm",
      min: 1000,
      max: 12000,
    },
    {
      key: "fy",
      text: "F<sub>y</sub>",
      unit: "MPa",
      min: 250,
      max: 500,
    },
  ];

  readonly rows: UnitTableRowData[] = [
    {
      key: "ke",
      text: "K<sub>e</sub>",
      unit: "<sup>kN⋅mm</sup>/<sub>rad</sub>",
      fractionDigit: 0,
    },
    {
      key: "my",
      text: "M<sub>y</sub>",
      unit: "kN⋅mm",
      fractionDigit: 0,
    },
    {
      key: "mc",
      text: "M<sub>c</sub>",
      unit: "kN⋅mm",
      fractionDigit: 0,
    },
    {
      key: "mRes",
      text: "M<sub>r</sub>",
      unit: "kN⋅mm",
      fractionDigit: 0,
    },
    {
      key: "thetaP",
      text: "&theta;<sub>p</sub>",
      unit: "rad",
      fractionDigit: 3,
    },
    {
      key: "thetaPc",
      text: "&theta;<sub>pc</sub>",
      unit: "rad",
      fractionDigit: 3,
    },
    {
      key: "thetaUlt",
      text: "&theta;<sub>u</sub>",
      unit: "rad",
      fractionDigit: 3,
    },
    {
      key: "lamdba",
      text: "&Lambda;",
      unit: "rad",
      fractionDigit: 3,
    },
  ];

  unitSystem: UnitSystem = "metric";
  database: Database = "aisc";
  section: Section | null = null;

  get sections(): SelectItem[] {
    let sections: Section[];
    switch (this.database) {
      case "aisc":
        sections = aiscSections;
        break;
      case "european":
        sections = europeanSections;
        break;
      case "japanese":
        sections = japaneseSections;
        break;
      default:
        return [];
    }
    return sections.map((section) => ({
      text: section.id,
      value: section,
    }));
  }

  @Watch("database")
  onDatabaseChanged(): void {
    this.section = null;
  }

  @Watch("section")
  onSectionChanged(): void {
    if (this.section) {
      this.bf = this.section.bf;
      this.d = this.section.d;
      this.tf = this.section.tf;
      this.tw = this.section.tw;
    }
  }

  readonly e = 205;

  bf = 100;
  d = 100;
  tf = 5;
  tw = 5;
  pgPye = 0.2;
  l = 5000;
  lb = 5000;
  fy = 380;

  private get h(): number {
    if (this.section) {
      return this.section.h;
    }
    return this.d - 2 * this.tf;
  }

  private get ix(): number {
    if (this.section) {
      return this.section.ix;
    }
    return (
      (Math.pow(this.d - 2 * this.tf, 3) * this.tw) / 12 +
      2 *
        this.bf *
        this.tf *
        (Math.pow(this.tf, 2) / 12 + Math.pow((this.d - this.tf) / 2, 2))
    );
  }

  private get ry(): number {
    if (this.section) {
      return this.section.ry;
    }
    const a = 2 * this.tf * this.bf + (this.d - 2 * this.tf) * this.tw;
    const iy =
      (this.tf * Math.pow(this.bf, 3)) / 12 +
      ((this.d - 2 * this.tf) * Math.pow(this.tw, 3)) / 12;
    return Math.sqrt(iy / a);
  }

  get ke(): number {
    return (6 * this.e * this.ix) / this.l;
  }

  get zx(): number {
    if (this.section) {
      return this.section.zx;
    }
    return (
      2 *
      (this.bf * this.tf * ((this.d - this.tf) / 2) +
        (Math.pow(this.d - 2 * this.tf, 2) * this.tw) / 4)
    );
  }

  get my(): number {
    return this.pgPye < 0.2
      ? 1.15 * this.zx * (this.fy / 1000) * (1 - this.pgPye / 2)
      : 1.15 * this.zx * (this.fy / 1000) * (9 / 8) * (1 - this.pgPye);
  }

  get backbone(): Backbone {
    const a = clamp(
      12.5 *
        Math.pow(this.h / this.tw, -0.2) *
        Math.pow(this.lb / this.ry, -0.4) *
        Math.pow(1 - this.pgPye, 0.4),
      1,
      1.3
    );
    const mc = a * this.my;
    const res = 0.5 - 0.4 * this.pgPye;
    const mRes = res * this.my;
    const thetaY = this.my / this.ke;
    const thetaP = Math.min(
      0.2,
      294 *
        Math.pow(this.h / this.tw, -1.7) *
        Math.pow(this.lb / this.ry, -0.7) *
        Math.pow(1 - this.pgPye, 1.6)
    );
    const thetaPc = Math.min(
      0.3,
      90 *
        Math.pow(this.h / this.tw, -0.8) *
        Math.pow(this.lb / this.ry, -0.8) *
        Math.pow(1 - this.pgPye, 2.5)
    );
    const thetaUlt = 0.15;
    const alpha = (mc - this.my) / thetaP / this.ke;
    const alphaPc = -mc / (this.ke * thetaPc);
    const lambda =
      this.pgPye <= 0.35
        ? Math.min(
            3.0,
            25000 *
              Math.pow(this.h / this.tw, -2.14) *
              Math.pow(this.lb / this.ry, -0.53) *
              Math.pow(1 - this.pgPye, 4.92)
          )
        : Math.min(
            3.0,
            268000 *
              Math.pow(this.h / this.tw, -2.3) *
              Math.pow(this.lb / this.ry, -1.3) *
              Math.pow(1 - this.pgPye, 1.19)
          );
    return {
      thetaY,
      a,
      mc,
      thetaP,
      thetaPc,
      res,
      mRes,
      thetaUlt,
      alpha,
      alphaPc,
      lambda,
    };
  }

  get envelope(): Envelope {
    const a = clamp(
      9.5 *
        Math.pow(this.h / this.tw, -0.4) *
        Math.pow(this.lb / this.ry, -0.16) *
        Math.pow(1 - this.pgPye, 0.2),
      1,
      1.3
    );
    const mc = a * this.my;
    const res = 0.4 - 0.4 * this.pgPye;
    const mRes = res * this.my;
    const thetaY = this.my / this.ke;
    const thetaP = Math.min(
      0.1,
      15 *
        Math.pow(this.h / this.tw, -1.6) *
        Math.pow(this.lb / this.ry, -0.3) *
        Math.pow(1 - this.pgPye, 2.3)
    );
    const thetaPc = Math.min(
      0.1,
      14 *
        Math.pow(this.h / this.tw, -0.8) *
        Math.pow(this.lb / this.ry, -0.5) *
        Math.pow(1 - this.pgPye, 3.2)
    );
    const thetaUlt = 0.08 * (1 - 0.6 * this.pgPye);
    const alpha = (mc - this.my) / thetaP / this.ke;
    const alphaPc = -mc / (this.ke * thetaPc);
    return {
      thetaY,
      mc,
      thetaP,
      thetaPc,
      res,
      mRes,
      thetaUlt,
      alpha,
      alphaPc,
    };
  }

  private getPoints(output: Envelope | Backbone): Point[] {
    const p1: Point = [0, 0];
    const p2: Point = [output.thetaY, this.my];
    const p3: Point = [p2[0] + output.thetaP, output.mc];
    const p4: Point = [
      p3[0] + (output.mc - output.mRes) / (-output.alphaPc * this.ke),
      output.mRes,
    ];
    if (p4[0] < output.thetaUlt) {
      const p5: Point = [output.thetaUlt, output.mRes];
      const p6: Point = [p5[0], 0];
      return [p1, p2, p3, p4, p5, p6];
    } else if (p3[0] < output.thetaUlt) {
      // && output.thetaUlt <= p4[0]
      const p5: Point = [
        output.thetaUlt,
        output.mc +
          output.alphaPc * this.ke * Math.abs(output.thetaPc - output.thetaUlt),
      ];
      const p6: Point = [p5[0], 0];
      return [p1, p2, p3, p5, p6];
    } else if (p2[0] < output.thetaUlt) {
      // && output.thetaUlt <= p3[0]
      const p5: Point = [
        output.thetaUlt,
        this.my + output.alpha * this.ke * (output.thetaUlt - output.thetaY),
      ];
      const p6: Point = [p5[0], 0];
      return [p1, p2, p5, p6];
    } else {
      const p5: Point = [output.thetaUlt, this.ke * output.thetaUlt];
      const p6: Point = [p5[0], 0];
      return [p1, p5, p6];
    }
  }

  private getResult(output: Envelope | Backbone): Result {
    return {
      ke: this.ke,
      my: this.my,
      lamdba: (output as Backbone).lambda,
      ...output,
      points: this.getPoints(output),
    };
  }

  get backboneResult(): Result {
    return this.getResult(this.backbone);
  }

  get envelopeResult(): Result {
    return this.getResult(this.envelope);
  }

  option(backbone: Result, envelope: Result): EChartsOption {
    return {
      xAxis: {
        name: "Chord Rotation, θ",
      },
      yAxis: {
        name: "Moment, M",
      },
      series: [
        {
          type: "line",
          name: "Monotonic Backbone",
          data: backbone.points,
          color: primaryColor.base,
        },
        {
          type: "line",
          name: "First-Cycle Envelope",
          data: envelope.points,
          color: secondaryColor.base,
        },
      ],
    };
  }
}

interface Result {
  ke: number;
  my: number;
  mc: number;
  mRes: number;
  thetaP: number;
  thetaPc: number;
  thetaUlt: number;
  lamdba?: number;
  points: Point[];
}

interface Envelope {
  thetaY: number;
  mc: number;
  thetaP: number;
  thetaPc: number;
  res: number;
  mRes: number;
  thetaUlt: number;
  alpha: number;
  alphaPc: number;
}

interface Backbone extends Envelope {
  a: number;
  lambda: number;
}

type Point = [number, number];

type Database = "aisc" | "european" | "japanese";
</script>
