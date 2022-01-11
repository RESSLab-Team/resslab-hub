<template>
  <single-chart
    label-prefix="column."
    :searches.sync="fieldSearches"
    :field="field"
    :query="query"
    :color="color"
    :promise="promise"
  >
  </single-chart>
</template>

<script lang="ts">
import { ColumnField, CountModel } from "@/backend";
import SingleChart from "@/components/commons/charts/SingleChart.vue";
import { Searches } from "@/utils/common";
import { AxiosResponse } from "axios";
import { Component, Prop, PropSync, Vue } from "vue-property-decorator";
import { Color } from "vuetify/lib/util/colors";

@Component({
  components: {
    SingleChart,
  },
})
export default class ColumnSingleChart extends Vue {
  @PropSync("searches", { type: Object as () => Searches })
  fieldSearches: Searches | undefined;
  @Prop({ type: String as () => ColumnField })
  readonly field!: ColumnField;
  @Prop({ type: String })
  readonly query: string | undefined;
  @Prop({ type: Object as () => Color })
  readonly color: Color | undefined;

  get promise(): Promise<AxiosResponse<CountModel[]>> {
    return this.$columnsApi.getColumnsCounts([this.field], this.query);
  }
}
</script>
