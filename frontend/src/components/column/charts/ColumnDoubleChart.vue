<template>
  <double-chart
    label-prefix="column."
    :searches.sync="fieldSearches"
    :fields="fields"
    :query="query"
    :type="type"
    :color="color"
    :promise="promise"
    :number-field="numberField"
    :range-promise="rangePromise"
  ></double-chart>
</template>

<script lang="ts">
import {
  ColumnField,
  ColumnNumberField,
  CountModel,
  RangeModel,
} from "@/backend";
import DoubleChart from "@/components/commons/charts/DoubleChart.vue";
import { Searches } from "@/utils/common";
import { AxiosResponse } from "axios";
import { Component, Prop, PropSync, Vue } from "vue-property-decorator";
import { Color } from "vuetify/lib/util/colors";

@Component({
  components: {
    DoubleChart,
  },
})
export default class ColumnDoubleChart extends Vue {
  @PropSync("searches", { type: Object as () => Searches })
  fieldSearches: Searches | undefined;
  @Prop({ type: Array as () => ColumnField[] })
  readonly fields!: [ColumnField, ColumnField];
  @Prop({ type: String })
  readonly query: string | undefined;
  @Prop({ type: String })
  readonly type: string | undefined;
  @Prop({ type: Object as () => Color })
  readonly color: Color | undefined;

  get promise(): Promise<AxiosResponse<CountModel[]>> {
    return this.$columnsApi.getColumnsCounts(this.fields, this.query);
  }

  get numberField(): ColumnNumberField | undefined {
    const fieldString = this.fields[0].toString();
    return Object.values(ColumnNumberField).find(
      (numberField) => fieldString === numberField.toString()
    );
  }

  get rangePromise(): Promise<AxiosResponse<RangeModel>> | undefined {
    if (this.numberField) {
      return this.$columnsApi.getColumnsRange(this.numberField);
    } else {
      return undefined;
    }
  }
}
</script>
