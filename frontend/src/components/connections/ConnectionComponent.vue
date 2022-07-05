<template>
  <v-row>
    <v-col cols="12">
      <h1>Backbone Curve Plotter for Steel Components</h1>
    </v-col>
    <v-col cols="6" md="9">
      <p>
        Construct the backbone curve of beams with RBS and beams other-than-RBS.
        For further information refer to
        <a
          href="http://ascelibrary.org/doi/abs/10.1061/(ASCE)ST.1943-541X.0000376"
          target="_blank"
        >
          Lignos and Krawinkler (2011)
        </a>
      </p>
    </v-col>
    <v-col cols="6" md="3">
      <toggle v-model="unitSystem" :items="unitSystems"></toggle>
    </v-col>
    <v-col cols="12">
      <v-card>
        <v-card-title>
          Select Steel W-Shape
          <info-tooltip>
            Here, you may choose to either select a W-Shape from the AISC
            database or input your own dimensions using the sliders below
          </info-tooltip>
        </v-card-title>
        <v-card-text>
          <v-row>
            <v-col v-bind="variableBind">
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
            </v-col>
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
    <v-col cols="12">
      <v-card>
        <v-card-title>
          Specify Member Properties
          <info-tooltip>
            Here you need to specify the beam full length (L), the beam unbraced
            length (L<sub>b</sub>), which is defined as the distance from the
            column face to the nearest lateral brace, the expected yield stress,
            F<sub>y</sub> of the steel material, the capping-to-yield ratio
            <sup>Mc</sup>/<sub>My</sub>, the expected residual strength ratio,
            K, and the ultimate rotation &theta;<sub>u</sub> of the steel
            component.
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
                :default-unit="item.unit"
                :units="item.units"
                :unit-system="unitSystem"
              ></unit-slider>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>
    </v-col>
    <v-col v-bind="chartBind">
      <v-card>
        <v-card-title>Beams without RBS</v-card-title>
        <v-card-text>
          <unit-chart
            :option="option(backboneCurveWithoutRbs)"
            :unit-system="unitSystem"
            x-unit="rad"
            y-unit="kN⋅mm"
          ></unit-chart>
        </v-card-text>
      </v-card>
    </v-col>
    <v-col v-bind="chartBind">
      <v-card>
        <v-card-title>Beams with RBS</v-card-title>
        <v-card-text>
          <unit-chart
            :option="option(backboneCurveWithRbs)"
            :unit-system="unitSystem"
            x-unit="rad"
            y-unit="kN⋅mm"
          ></unit-chart>
        </v-card-text>
      </v-card>
    </v-col>
    <v-col cols="12" lg="6">
      <v-card>
        <v-card-title>
          Computed Backbone Curve Values
          <info-tooltip>
            Provided that the steel member is in double curvature
          </info-tooltip>
        </v-card-title>
        <v-card-text>
          <v-simple-table dense fixed-header>
            <template #default>
              <thead>
                <tr>
                  <th>Parameter</th>
                  <th>Unit</th>
                  <th>Value (Beams without RBS)</th>
                  <th>Value (Beams with RBS)</th>
                </tr>
              </thead>
              <tbody>
                <unit-table-row
                  v-for="item in rows"
                  :key="item.key"
                  :field="item.key"
                  :text="item.text"
                  :unit="item.unit"
                  :columns="[backboneCurveWithoutRbs, backboneCurveWithRbs]"
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
import { Section } from "@/utils/common";
import { UnitSystem, unitSystems } from "@/utils/unit";
import { primaryColor, secondaryColor, SelectItem } from "@/utils/vuetify";
import { EChartsOption } from "echarts/types/dist/shared";
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
  readonly databases: Database[] = ["aisc", "european", "japanese"];

  readonly variableBind = {
    cols: "12",
    sm: "6",
    md: "4",
    lg: "3",
    xl: "2",
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
      key: "ratio",
      text: "Flange Reduction for RBS",
      min: 0,
      max: 0.5,
    }),
    new Variable({
      key: "lb",
      text: "L<sub>b</sub>",
      unit: "mm",
      min: 1000,
      max: 12000,
    }),
    new Variable({
      key: "l",
      text: "L",
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
    new Variable({
      key: "mc_my",
      text: "<sup>Mc</sup>/<sub>My</sub>",
      min: 1,
      max: 1.5,
    }),
    new Variable({
      key: "k",
      text: "K",
      min: 0,
      max: 0.5,
    }),
    new Variable({
      key: "thetau",
      text: "&theta;<sub>u</sub>",
      unit: "rad",
      min: 0.05,
      max: 0.5,
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
      key: "mr",
      text: "M<sub>r</sub>",
      unit: "kN⋅mm",
    },
    {
      key: "thetap",
      text: "&theta;<sub>p</sub>",
      unit: "rad",
    },
    {
      key: "thetapc",
      text: "&theta;<sub>pc</sub>",
      unit: "rad",
    },
    {
      key: "thetau",
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
  ];

  readonly c1 = 1;
  readonly c2 = 1;
  readonly e = 2e5;

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

  bf = 100;
  h = 100;
  tf = 5;
  tw = 5;
  ratio = 0;
  lb = 1000;
  l = 1000;
  fy = 250;
  mc_my = 1;
  k = 0;
  thetau = 0.05;

  private get ix(): number {
    return (
      (this.bf * Math.pow(this.d, 3) -
        Math.pow(this.h, 3) * (this.bf - this.tw)) /
      12
    );
  }

  private get iy(): number {
    return (this.tf * Math.pow(this.bf, 3) + this.h * Math.pow(this.tw, 3)) / 6;
  }

  private get a(): number {
    return this.bf * this.d - this.h * (this.bf - this.tw);
  }

  private get ry(): number {
    return Math.sqrt(this.iy / this.a);
  }

  private get d(): number {
    return this.h + 2 * this.tf;
  }

  private get ke(): number {
    return ((6 * this.e * this.ix) / this.l) * 1e-3;
  }

  private get h_tw(): number {
    return this.h / this.tw;
  }

  private get bf_2tf(): number {
    return this.bf / (2 * this.tf);
  }
  private get lb_ry(): number {
    return this.lb / this.ry;
  }

  private get l_d(): number {
    return this.l / this.d;
  }

  private get c1_d(): number {
    return (this.c1 * this.d) / 533;
  }

  private get c2_fy(): number {
    return (this.c2 * this.fy) / 355;
  }

  private mc(isRbs: boolean): number {
    return this.mc_my * this.my(isRbs);
  }

  private zx(isRbs: boolean): number {
    const zx =
      this.bf * this.tf * (this.d - this.tf) +
      0.25 * this.tw * Math.pow(this.d - 2 * this.tf, 2);
    if (isRbs) {
      return (1 - this.ratio) * zx;
    } else {
      return zx;
    }
  }

  private my(isRbs: boolean): number {
    return 1.1 * this.zx(isRbs) * this.fy * 1e-3;
  }

  private mr(isRbs: boolean): number {
    return this.k * this.my(isRbs);
  }

  private thetap(isRbs: boolean): number {
    if (isRbs) {
      return (
        0.19 *
        Math.pow(this.h_tw, -0.314) *
        Math.pow(this.bf_2tf, -0.1) *
        Math.pow(this.lb_ry, -0.185) *
        Math.pow(this.l_d, 0.113) *
        Math.pow(this.c1_d, -0.76) *
        Math.pow(this.c2_fy, -0.07)
      );
    } else {
      if (this.d < 533) {
        return (
          0.0865 *
          Math.pow(this.h_tw, -0.365) *
          Math.pow(this.bf_2tf, -0.14) *
          Math.pow(this.l_d, 0.34) *
          Math.pow(this.c1_d, -0.721) *
          Math.pow(this.c2_fy, -0.23)
        );
      } else {
        return (
          0.318 *
          Math.pow(this.h_tw, -0.55) *
          Math.pow(this.bf_2tf, -0.345) *
          Math.pow(this.lb_ry, 0.023) *
          Math.pow(this.l_d, 0.09) *
          Math.pow(this.c1_d, -0.33) *
          Math.pow(this.c2_fy, -0.13)
        );
      }
    }
  }

  private thetapc(isRbs: boolean): number {
    if (isRbs) {
      return (
        9.52 *
        Math.pow(this.h_tw, -0.513) *
        Math.pow(this.bf_2tf, -0.863) *
        Math.pow(this.lb_ry, -0.108) *
        Math.pow(this.c2_fy, -0.36)
      );
    } else {
      if (this.d < 533) {
        return (
          5.63 *
          Math.pow(this.h_tw, -0.565) *
          Math.pow(this.bf_2tf, -0.8) *
          Math.pow(this.c1_d, -0.28) *
          Math.pow(this.c2_fy, -0.43)
        );
      } else {
        return (
          7.5 *
          Math.pow(this.h_tw, -0.61) *
          Math.pow(this.bf_2tf, -0.71) *
          Math.pow(this.lb_ry, -0.11) *
          Math.pow(this.c1_d, -0.161) *
          Math.pow(this.c2_fy, -0.32)
        );
      }
    }
  }

  private lamdba(isRbs: boolean): number {
    if (isRbs) {
      return (
        585 *
        Math.pow(this.h_tw, -1.14) *
        Math.pow(this.bf_2tf, -0.632) *
        Math.pow(this.lb_ry, -0.205) *
        Math.pow(this.c2_fy, -0.391)
      );
    } else {
      if (this.d < 533) {
        return (
          495 *
          Math.pow(this.h_tw, -1.34) *
          Math.pow(this.bf_2tf, -0.595) *
          Math.pow(this.c2_fy, -0.36)
        );
      } else {
        return (
          536 *
          Math.pow(this.h_tw, -1.26) *
          Math.pow(this.bf_2tf, -0.525) *
          Math.pow(this.lb_ry, -0.13) *
          Math.pow(this.c2_fy, -0.291)
        );
      }
    }
  }

  private residualStrengthData(
    my: number,
    mc: number,
    mr: number,
    thetap: number,
    thetapc: number,
    v: number
  ): [number, number][] {
    const a = (thetapc * mr) / mc;
    const c = thetap + v + (thetapc - a);
    if (c < this.thetau) {
      return [
        [c, mr],
        [this.thetau, mr],
        [this.thetau, 0],
      ];
    } else {
      return [
        [
          this.thetau,
          this.thetau < v + thetap
            ? my + ((mc - my) / thetap) * (this.thetau - v)
            : (-1 * (this.thetau - thetapc - thetap - v) * mc) / thetapc,
        ],
        [this.thetau, 0],
      ];
    }
  }

  private backboneCurve(isRbs: boolean): BackboneCurve {
    const my = this.my(isRbs);
    const mc = this.mc(isRbs);
    const mr = this.mr(isRbs);
    const v = my / this.ke;
    const thetap = this.thetap(isRbs);
    const thetapc = this.thetapc(isRbs);
    return {
      ke: this.ke,
      my: my,
      mc: mc,
      mr: mr,
      thetap: thetap,
      thetapc: this.thetapc(isRbs),
      thetau: this.thetau,
      lamdba: this.lamdba(isRbs),
      k: this.k,
      backboneCurveData: [
        [0, 0],
        [v, my],
        [v + thetap, this.mc_my * my],
        [v + thetap + thetapc, 0],
      ],
      residualStrengthData: this.residualStrengthData(
        my,
        mc,
        mr,
        thetap,
        thetapc,
        v
      ),
    };
  }

  get backboneCurveWithoutRbs(): BackboneCurve {
    return this.backboneCurve(false);
  }

  get backboneCurveWithRbs(): BackboneCurve {
    return this.backboneCurve(true);
  }

  option(backboneCurve: BackboneCurve): EChartsOption {
    return {
      grid: {
        left: 30,
        top: 10,
        right: 20,
        bottom: 20,
        containLabel: true,
      },
      xAxis: {
        name: "Chord Rotation, \u03b8",
        nameLocation: "middle",
        nameGap: 26,
      },
      yAxis: {
        name: "Moment, M",
        nameLocation: "middle",
        nameGap: 65,
      },
      tooltip: {
        trigger: "axis",
        confine: true,
      },
      series: [
        {
          type: "line",
          name: "Backbone Curve",
          data: backboneCurve.backboneCurveData,
          color: primaryColor.base,
        },
        {
          type: "line",
          name: "Residual Strength",
          data: backboneCurve.residualStrengthData,
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

interface BackboneCurve {
  ke: number; // d
  my: number; // p
  mc: number; // y
  mr: number; // b
  thetap: number; // m
  thetapc: number; // g
  thetau: number;
  lamdba: number; // w
  k: number;
  backboneCurveData: [number, number][];
  residualStrengthData: [number, number][];
}

type Database = "aisc" | "european" | "japanese";
</script>
