<template>
  <simple-parallel-chart
    label-prefix="connection."
    :id-field="idField"
    :searches.sync="fieldSearches"
    :fields="fields"
    :query="query"
    :color="color"
    :get-matrix="getMatrix"
  ></simple-parallel-chart>
</template>

<script lang="ts">
import { ConnectionField, MatrixModel } from "@/backend";
import SimpleParallelChart, {
  Division,
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
export default class ConnectionParallelChart extends Vue {
  readonly idField = ConnectionField.Id;

  @Prop({ type: Array as () => ConnectionField[] })
  readonly fields!: Field[];
  @Prop({ type: String })
  readonly query: string | undefined;
  @Prop({ type: Object as () => Color })
  readonly color: Color | undefined;
  @PropSync("searches", { type: Object as () => Searches })
  fieldSearches: Searches | undefined;

  getMatrix(fields: ConnectionField[]): Promise<AxiosResponse<MatrixModel>> {
    return this.$connectionsApi.getMatrix(fields, this.query);
  }
}

export type Field = ConnectionField | Division<ConnectionField>;
</script>
