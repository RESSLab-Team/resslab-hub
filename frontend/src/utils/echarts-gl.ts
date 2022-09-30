declare module "echarts-gl/charts" {
  // eslint-disable-next-line @typescript-eslint/no-empty-interface
  interface SurfaceChart {}
}
declare module "echarts-gl/components" {
  // eslint-disable-next-line @typescript-eslint/no-empty-interface
  interface Grid3DComponent {}
}

/**
 * https://echarts.apache.org/en/option-gl.html
 */
export interface EChartsGlOption {
  grid3D?: {
    viewControl?: {
      zoomSensitivity?: number;
      distance?: number;
    };
  };
  xAxis3D?: Axis3D;
  yAxis3D?: Axis3D;
  zAxis3D?: Axis3D;
  series?: SurfaceSeries[];
}

interface Axis3D {
  show?: boolean;
  name?: string;
  min?: number | "dataMin";
  max?: number | "dataMax";
  axisLabel?: {
    show?: boolean;
    margin?: number;
    formatter?: string | ((value: number) => string);
  };
}

interface SurfaceSeries {
  type: "surface";
  parametric?: boolean;
  wireframe?: {
    show?: boolean;
    lineStyle?: {
      color?: string;
      opacity?: number;
      width?: number;
    };
  };
  equation?: {
    x?: EquationValue;
    y?: EquationValue;
    z?: (x: number, y: number) => number;
  };
  parametricEquation?: {
    u: EquationValue;
    v: EquationValue;
    x: ParametricEquationValue;
    y: ParametricEquationValue;
    z: ParametricEquationValue;
  };
  itemStyle?: {
    color?: string;
    opacity?: number;
  };
  data?: [number, number, number][];
  shading?: "color" | "lambert" | "realistic";
}

interface EquationValue {
  step?: number;
  min?: number;
  max?: number;
}

type ParametricEquationValue = (u: number, v: number) => number;
