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
  axisLabel?: {
    show?: boolean;
    margin?: number;
    formatter?: string | ((name: string) => string);
  };
}

interface SurfaceSeries {
  type: "surface";
  equation?: {
    x?: EquationValue;
    y?: EquationValue;
    z?: (x: number, y: number) => number;
  };
  data?: [number, number, number][];
}

interface EquationValue {
  step?: number;
  min?: number;
  max?: number;
}
