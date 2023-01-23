import { AxiosResponse } from "axios";
import { Color } from "vuetify/lib/util/colors";

// TODO move back to frontend/src/components/commons/CommonDetail.vue
export interface CarouselItem {
  hidden?: boolean;
  promise?: Promise<Response>;
  promises?: Promise<Response>[];
  title: string;
  xAxisName: string;
  yAxisName: string;
  color?: Color;
}

// TODO move back to frontend/src/components/commons/charts/MultipleLineChart.vue
export type Response = AxiosResponse<number[][]> | number[][];
