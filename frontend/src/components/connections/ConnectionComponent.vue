<template>
  <v-row>
    <v-col cols="12">
      <v-row align="center">
        <v-col>
          <h1>Backbone Curve Plotter for Steel Components</h1>
          <p>
            Construct the backbone curve of beams with RBS and beams
            other-than-RBS. For further information refer to
            <a
              href="http://ascelibrary.org/doi/abs/10.1061/(ASCE)ST.1943-541X.0000376"
              target="_blank"
            >
              Lignos and Krawinkler (2011)
            </a>
          </p>
        </v-col>
        <v-col cols="auto">
          <toggle v-model="unitSystem" :items="unitSystems"></toggle>
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
                    :step="item.step"
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
              Specify Member Properties
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
                    :step="item.step"
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
        height="200px"
        :src="publicPath + 'img/connection/component-1.png'"
      ></v-img>
      <v-img
        contain
        height="200px"
        :src="publicPath + 'img/connection/component-2.png'"
      ></v-img>
    </v-col>
    <v-col cols="6">
      <v-row>
        <v-col cols="6">
          <v-card>
            <v-card-title>Beams with RBS</v-card-title>
            <v-card-text>
              <unit-chart
                :option="option(backboneWithRbs, envelopeWithRbs)"
                :unit-system="unitSystem"
                x-unit="rad"
                y-unit="kN⋅mm"
              ></unit-chart>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="6">
          <v-card>
            <v-card-title>Beams without RBS</v-card-title>
            <v-card-text>
              <unit-chart
                :option="option(backboneWithoutRbs, envelopeWithoutRbs)"
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
          Component Models
          <info-tooltip>
            Provided that the steel member is in double curvature
          </info-tooltip>
        </v-card-title>
        <v-card-text>
          <v-simple-table dense>
            <template #default>
              <thead>
                <tr>
                  <th rowspan="2">Parameter</th>
                  <th rowspan="2">Unit</th>
                  <th colspan="2">Beams with RBS</th>
                  <th colspan="2">Beams without RBS</th>
                </tr>
                <tr>
                  <th>Monotonic Backbone</th>
                  <th>First Cycle Envelope</th>
                  <th>Monotonic Backbone</th>
                  <th>First Cycle Envelope</th>
                </tr>
              </thead>
              <tbody>
                <unit-table-row
                  v-for="item in rows"
                  :key="item.key"
                  :field="item.key"
                  :text="item.text"
                  :unit="item.unit"
                  :columns="[
                    backboneWithRbs,
                    envelopeWithRbs,
                    backboneWithoutRbs,
                    envelopeWithoutRbs,
                  ]"
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
import UnitSlider from "@/components/commons/sliders/UnitSlider.vue";
import Toggle from "@/components/commons/Toggle.vue";
import UnitTableRow, {
  UnitTableRowData,
} from "@/components/commons/UnitTableRow.vue";
import { publicPath, Section } from "@/utils/common";
import { UnitSystem, unitSystems } from "@/utils/unit";
import { primaryColor, secondaryColor, SelectItem } from "@/utils/vuetify";
import { EChartsOption } from "echarts/types/dist/shared";
import { clamp } from "lodash";
import { Component, Vue, Watch } from "vue-property-decorator";

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
export default class ConnectionComponent extends Vue {
  readonly unitSystems = unitSystems;
  readonly publicPath = publicPath;
  readonly databases: Database[] = ["aisc", "european", "japanese"];

  readonly variableBind = {
    cols: "12",
    md: "6",
    xl: "3",
  };
  readonly chartBind = {
    cols: "12",
    sm: "6",
    lg: "3",
    xl: "2",
  };
  readonly steelShapeDimensions: Variable[] = [
    new Variable({
      key: "bf",
      text: "b<sub>f</sub>",
      unit: "mm",
      min: 100,
      max: 500,
    }),
    new Variable({ key: "h", text: "h", unit: "mm", min: 100, max: 1000 }),
    new Variable({
      key: "tf",
      text: "t<sub>f</sub>",
      unit: "mm",
      min: 5,
      max: 100,
    }),
    new Variable({
      key: "tw",
      text: "t<sub>w</sub>",
      unit: "mm",
      min: 5,
      max: 100,
    }),
  ];

  readonly memberProperties: Variable[] = [
    new Variable({
      key: "rbsReduction",
      text: "RBS flange reduction",
      min: 0,
      max: 0.5,
    }),
    new Variable({
      key: "l",
      text: "L",
      unit: "mm",
      min: 1000,
      max: 12000,
    }),
    new Variable({
      key: "lb",
      text: "L<sub>b</sub>",
      unit: "mm",
      min: 1000,
      max: 12000,
    }),
    new Variable({
      key: "fy",
      text: "F<sub>y</sub>",
      unit: "MPa",
      min: 250,
      max: 500,
    }),
  ];

  readonly rows: UnitTableRowData[] = [
    {
      key: "ke",
      text: "K<sub>e</sub>",
      unit: "<sup>kN⋅mm</sup>/<sub>rad</sub>",
    },
    {
      key: "my",
      text: "M<sub>y</sub>",
      unit: "kN⋅mm",
    },
    {
      key: "mc",
      text: "M<sub>c</sub>",
      unit: "kN⋅mm",
    },
    {
      key: "mRes",
      text: "M<sub>r</sub>",
      unit: "kN⋅mm",
    },
    {
      key: "thetaP",
      text: "&theta;<sub>p</sub>",
      unit: "rad",
    },
    {
      key: "thetaPc",
      text: "&theta;<sub>pc</sub>",
      unit: "rad",
    },
    {
      key: "thetaUlt",
      text: "&theta;<sub>u</sub>",
      unit: "rad",
    },
    {
      key: "lamdba",
      text: "&Lambda;",
      unit: "rad",
    },
    {
      key: "k",
      text: "K (residual strength ratio)",
      unit: "",
    },
    {
      key: "ix",
      text: "Ix",
      unit: "mm<sup>4</sup>",
    },
    {
      key: "zx",
      text: "Zx",
      unit: "mm<sup>3</sup>",
    },
    {
      key: "ry",
      text: "ry",
      unit: "mm",
    },
    {
      key: "d",
      text: "d",
      unit: "mm",
    },
    {
      key: "thetaY",
      text: "&theta;<sub>y</sub>",
      unit: "rad",
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
      this.h = this.section.h;
      this.tf = this.section.tf;
      this.tw = this.section.tw;
    }
  }

  readonly e = 205;

  bf = 100;
  h = 100;
  tf = 5;
  tw = 5;
  rbsReduction = 0.5; // 0
  l = 8000; // 1000
  lb = 4000; // 1000
  fy = 380; // 250

  private get ix(): number {
    if (this.section) {
      return this.section.ix;
    }
    // FIXME
    return (
      (this.bf * Math.pow(this.d, 3) -
        Math.pow(this.h, 3) * (this.bf - this.tw)) /
      12
    );
  }

  private get zx(): number {
    if (this.section) {
      return this.section.zx;
    }
    // FIXME
    return (
      this.bf * this.tf * (this.d - this.tf) +
      0.25 * this.tw * Math.pow(this.d - 2 * this.tf, 2)
    );
  }

  private get ry(): number {
    if (this.section) {
      return this.section.ry;
    }
    // FIXME
    return Math.sqrt(this.iy / this.a);
  }

  private get d(): number {
    if (this.section) {
      return this.section.d;
    }
    // FIXME
    return this.h + 2 * this.tf;
  }

  private get iy(): number {
    return (this.tf * Math.pow(this.bf, 3) + this.h * Math.pow(this.tw, 3)) / 6;
  }

  private get a(): number {
    return this.bf * this.d - this.h * (this.bf - this.tw);
  }

  private rbs(): {
    lRbs: number;
    lCanti: number;
    k: number;
    my: number;
  } {
    const _a = 0.625 * this.bf;
    const _b = 0.75 * this.d;
    const _c = this.rbsReduction * this.bf;
    const lRbs = _a + 0.5 * _b;
    const zRbs = this.zx - _c * this.tf * (this.d - this.tf);

    const lCanti = this.l / 2;

    const k = (6 * this.e * this.ix) / this.l;
    const my = 1.06 * zRbs * (this.fy / 1000);
    return {
      lRbs,
      lCanti,
      k,
      my,
    };
  }

  private getBackboneRbs(): Backbone {
    const { lRbs, lCanti, k, my } = this.rbs();

    const a = 1.09;
    const mc = a * my;
    const res = 0.4;
    const mRes = res * my;

    const thetaY = my / k;
    const thetaP =
      0.19 *
      Math.pow(this.h / this.tw, -0.314) *
      Math.pow(this.bf / 2 / this.tf, -0.1) *
      Math.pow(this.lb / this.ry, -0.185) *
      Math.pow((lCanti - lRbs) / this.d, 0.113) *
      Math.pow(this.d / 533, -0.76) *
      Math.pow(this.fy / 355, -0.07);
    const thetaPc =
      9.52 *
      Math.pow(this.h / this.tw, -0.513) *
      Math.pow(this.bf / 2 / this.tf, -0.863) *
      Math.pow(this.lb / this.ry, -0.108) *
      Math.pow(this.fy / 355, -0.36);
    const thetaUlt = 0.2;
    const alpha = ((mc - my) / thetaP / k) * (lCanti / (lCanti - lRbs));
    const alphaPc = (-mc / (k * thetaPc)) * (lCanti / (lCanti - lRbs));
    const lambda = clamp(
      585 *
        Math.pow(this.h / this.tw, -1.14) *
        Math.pow(this.bf / 2 / this.tf, -0.632) *
        Math.pow(this.lb / this.ry, -0.205) *
        Math.pow(this.fy / 355, -0.391),
      3.0
    );
    return {
      k,
      my,
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
      lRbs,
      lambda,
    };
  }

  private getEnvelopeRbs(): Envelope {
    const { lRbs, lCanti, k, my } = this.rbs();

    const res = 0.3;
    const mRes = res * my;

    const thetaY = my / k;
    const thetaP =
      0.25 *
      Math.pow(this.h / this.tw, -0.5) *
      Math.pow(this.bf / 2 / this.tf, -0.7) *
      Math.pow(this.lb / this.ry, -0.5) *
      Math.pow((lCanti - lRbs) / this.d, 0.8) *
      Math.pow(this.e / this.fy, 0.23);
    const thetaPc = clamp(
      2.5 *
        Math.pow(this.h / this.tw, -1.1) *
        Math.pow(this.bf / 2 / this.tf, -0.1) *
        Math.pow(this.lb / this.ry, -0.1) *
        Math.pow(this.e / this.fy, 0.09),
      0.05
    );
    const thetaUlt = 0.08;
    const alpha = 0.03;
    const mc = my + alpha * k * thetaP;

    const alphaPc = (-mc / (k * thetaPc)) * (lCanti / (lCanti - lRbs));
    return {
      k,
      my,
      thetaY,
      mc,
      thetaP,
      thetaPc,
      res,
      mRes,
      thetaUlt,
      alpha,
      alphaPc,
      lRbs,
    };
  }

  private nonRbs(): {
    lCanti: number;
    k: number;
    my: number;
  } {
    const lCanti = this.l / 2;
    const k = (6 * this.e * this.ix) / this.l;
    const my = 1.17 * this.zx * (this.fy / 1000);
    return {
      lCanti,
      k,
      my,
    };
  }

  private getBackboneNonRbs(): Backbone {
    const { lCanti, k, my } = this.nonRbs();

    const a = 1.11;
    const mc = a * my;
    const res = 0.4;
    const mRes = res * my;

    const thetaY = my / k;

    let thetaP;
    let thetaPc;
    let lambda;
    if (this.d <= 533) {
      thetaP =
        0.0865 *
        Math.pow(this.h / this.tw, -0.365) *
        Math.pow(this.bf / 2 / this.tf, -0.14) *
        Math.pow(lCanti / this.d, 0.34) *
        Math.pow(this.d / 533, -0.721) *
        Math.pow(this.fy / 355, -0.23);
      thetaPc =
        5.63 *
        Math.pow(this.h / this.tw, -0.565) *
        Math.pow(this.bf / 2 / this.tf, -0.8) *
        Math.pow(this.d / 533, -0.28) *
        Math.pow(this.fy / 355, -0.43);
      lambda = clamp(
        536 *
          Math.pow(this.h / this.tw, -1.26) *
          Math.pow(this.bf / 2 / this.tf, -0.525) *
          Math.pow(this.lb / this.ry, -0.13) *
          Math.pow(this.fy / 355, -0.291),
        3.0
      );
    } else {
      thetaP =
        0.318 *
        Math.pow(this.h / this.tw, -0.55) *
        Math.pow(this.bf / 2 / this.tf, -0.345) *
        Math.pow(this.lb / this.ry, -0.023) *
        Math.pow(lCanti / this.d, 0.09) *
        Math.pow(this.d / 533, -0.33) *
        Math.pow(this.fy / 355, -0.13);

      thetaPc =
        7.5 *
        Math.pow(this.h / this.tw, -0.61) *
        Math.pow(this.bf / 2 / this.tf, -0.71) *
        Math.pow(this.lb / this.ry, -0.11) *
        Math.pow(this.d / 533, -0.161) *
        Math.pow(this.fy / 355, -0.32);
      lambda = clamp(
        585 *
          Math.pow(this.h / this.tw, -1.14) *
          Math.pow(this.bf / 2 / this.tf, -0.632) *
          Math.pow(this.lb / this.ry, -0.205) *
          Math.pow(this.fy / 355, -0.391),
        3.0
      );
    }
    const thetaUlt = 0.2;
    const alpha = (mc - my) / thetaP / k;
    const alphaPc = -mc / (k * thetaPc);
    return {
      k,
      my,
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

  private getEnvelopeNonRbs(): Envelope {
    const { lCanti, k, my } = this.nonRbs();
    const res = 0.3;
    const mRes = res * my;
    const thetaY = my / k;

    const thetaP =
      0.5 *
      Math.pow(this.h / this.tw, -0.9) *
      Math.pow(this.bf / 2 / this.tf, -1.1) *
      Math.pow(this.lb / this.ry, -0.2) *
      Math.pow(lCanti / this.d, 1.1) *
      Math.pow(this.e / this.fy, 0.2);
    const thetaPc = clamp(
      6.4 *
        Math.pow(this.h / this.tw, -0.9) *
        Math.pow(this.bf / 2 / this.tf, -0.2) *
        Math.pow(this.lb / this.ry, -0.5) *
        Math.pow(this.e / this.fy, 0.1),
      0.05
    );
    const thetaUlt = 0.08;
    const alpha = 0.03;
    const mc = my + alpha * k * thetaP;
    const alphaPc = (0.0 - mc) / (k * thetaPc);
    return {
      k,
      my,
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
    const p2: Point = [output.thetaY, output.my];
    const p3: Point = [p2[0] + output.thetaP, output.mc];
    const p4: Point = [
      p3[0] + (output.mc - output.mRes) / (-output.alphaPc * output.k),
      output.mRes,
    ];
    if (output.thetaUlt > p4[0]) {
      const p5: Point = [output.thetaUlt, output.mRes];
      const p6: Point = [p5[0], 0];
      return [p1, p2, p3, p4, p5, p6];
    } else {
      const p5: Point = [
        output.thetaUlt,
        output.mc +
          output.alphaPc * output.k * (output.thetaPc - output.thetaUlt),
      ];
      const p6: Point = [p5[0], 0];
      return [p1, p2, p3, p5, p6];
    }
  }

  private getResult(output: Envelope | Backbone): Result {
    return {
      ix: this.ix,
      zx: this.zx,
      ry: this.ry,
      d: this.d,
      ...output,
      points: this.getPoints(output),
    };
  }

  get backboneWithRbs(): Result {
    return this.getResult(this.getBackboneRbs());
  }

  get backboneWithoutRbs(): Result {
    return this.getResult(this.getBackboneNonRbs());
  }

  get envelopeWithRbs(): Result {
    return this.getResult(this.getEnvelopeRbs());
  }

  get envelopeWithoutRbs(): Result {
    return this.getResult(this.getEnvelopeNonRbs());
  }

  option(backbone: Result, envelope: Result): EChartsOption {
    return {
      xAxis: {
        name: "Chord Rotation, \u03b8",
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

class Variable {
  public key: string;
  public text: string;
  public unit: string;
  public min: number;
  public max: number;
  constructor(options: {
    key: string;
    text: string;
    unit?: string;
    min: number;
    max: number;
    step?: number;
  }) {
    this.key = options.key;
    this.text = options.text;
    this.unit = options.unit ?? "";
    this.min = options.min;
    this.max = options.max;
  }
}

interface Result {
  // ke: number; // d
  my: number; // p
  mc: number; // y
  mRes: number; // b
  thetaP: number; // m
  thetaPc: number; // g
  thetaUlt: number;
  lamdba?: number; // w
  k: number;
  ix: number;
  zx: number;
  ry: number;
  d: number;
  thetaY: number;
  points: Point[];
}

interface Envelope {
  k: number;
  my: number;
  thetaY: number;
  mc: number;
  thetaP: number;
  thetaPc: number;
  res: number;
  mRes: number;
  thetaUlt: number;
  alpha: number;
  alphaPc: number;
  lRbs?: number;
}

interface Backbone extends Envelope {
  a: number;
  lambda: number;
}

type Point = [number, number];

type Database = "aisc" | "european" | "japanese";
</script>
