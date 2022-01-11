<template>
  <simple-parallel-chart
    label-prefix="column."
    :id-field="idField"
    :searches.sync="fieldSearches"
    :fields="fields"
    :query="query"
    :color="color"
    :get-matrix="getMatrix"
  ></simple-parallel-chart>
</template>

<script lang="ts">
import { ColumnField, MatrixModel } from "@/backend";
import SimpleParallelChart, {
  ParallelField,
} from "@/components/commons/charts/SimpleParallelChart.vue";
import { Searches } from "@/utils/common";
import { AxiosResponse } from "axios";
import { Component, Prop, PropSync, Vue } from "vue-property-decorator";
import { Color } from "vuetify/lib/util/colors";

@Component({
  components: {
    SimpleParallelChart,
  },
})
export default class ColumnParallelChart extends Vue {
  readonly idField = ColumnField.Id;

  @Prop({ type: Array as () => ColumnField[] })
  readonly fields!: ParallelField<ColumnField>[];
  @Prop({ type: String })
  readonly query: string | undefined;
  @Prop({ type: Object as () => Color })
  readonly color: Color | undefined;
  @PropSync("searches", { type: Object as () => Searches })
  fieldSearches: Searches | undefined;

  getMatrix(fields: ColumnField[]): Promise<AxiosResponse<MatrixModel>> {
    return this.$columnsApi.getColumnsMatrix(fields, this.query);
  }
}
</script>
