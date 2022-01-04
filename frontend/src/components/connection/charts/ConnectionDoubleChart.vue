<template>
  <double-chart
    label-prefix="connection."
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
  ConnectionField,
  ConnectionNumberField,
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
export default class ConnectionDoubleChart extends Vue {
  @PropSync("searches", { type: Object as () => Searches })
  fieldSearches: Searches | undefined;
  @Prop({ type: Array as () => ConnectionField[] })
  readonly fields!: [ConnectionField, ConnectionField];
  @Prop({ type: String })
  readonly query: string | undefined;
  @Prop({ type: String })
  readonly type: string | undefined;
  @Prop({ type: Object as () => Color })
  readonly color: Color | undefined;

  get promise(): Promise<AxiosResponse<CountModel[]>> {
    return this.$connectionsApi.getCounts(this.fields, this.query);
  }

  get numberField(): ConnectionNumberField | undefined {
    const fieldString = this.fields[0].toString();
    return Object.values(ConnectionNumberField).find(
      (numberField) => fieldString === numberField.toString()
    );
  }

  get rangePromise(): Promise<AxiosResponse<RangeModel>> | undefined {
    if (this.numberField) {
      return this.$connectionsApi.getRange(this.numberField);
    } else {
      return undefined;
    }
  }
}
</script>
