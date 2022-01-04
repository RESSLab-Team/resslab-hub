<template>
  <simple-parallel-chart
    label-prefix="connection."
    :id-field="idField"
    :searches.sync="fieldSearches"
    :fields="fields"
    :query="query"
    :color="color"
    :promise="promise"
  ></simple-parallel-chart>
</template>

<script lang="ts">
import { ConnectionField, MatrixModel } from "@/backend";
import SimpleParallelChart from "@/components/commons/charts/SimpleParallelChart.vue";
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
  @PropSync("searches", { type: Object as () => Searches })
  fieldSearches: Searches | undefined;
  @Prop({ type: Array as () => ConnectionField[] })
  readonly fields!: ConnectionField[];
  @Prop({ type: String })
  readonly query: string | undefined;
  @Prop({ type: Object as () => Color })
  readonly color: Color | undefined;

  get promise(): Promise<AxiosResponse<MatrixModel>> {
    return this.$connectionsApi.getMatrix(this.fields, this.query);
  }

  get idField(): string {
    return ConnectionField.Id;
  }
}
</script>
