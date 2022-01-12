<script lang="ts">
import DoubleChart, {
  DoubleField,
  MappingField,
} from "@/components/commons/charts/DoubleChart.vue";
import { Searches } from "@/utils/common";
import { Component, Prop, PropSync, Vue } from "vue-property-decorator";
import { Color } from "vuetify/lib/util/colors";

@Component({
  components: {
    DoubleChart,
  },
})
export default class DoubleChartMixin<T> extends Vue {
  @Prop({ type: Object as () => Color })
  readonly color: Color | undefined;
  @Prop({ type: Array as () => (T | DoubleField<T>)[] })
  readonly fields!: [T, DoubleField<T>];
  @Prop({ type: String })
  readonly query: string | undefined;
  @Prop({ type: String })
  readonly type: string | undefined;
  @PropSync("searches", { type: Object as () => Searches })
  fieldSearches: Searches | undefined;

  get requestFields(): [T, T] {
    const secondField: DoubleField<T> = this.fields[1];
    if (typeof secondField === "object") {
      return [this.fields[0], (secondField as MappingField<T>).id];
    } else {
      return [this.fields[0], secondField as T];
    }
  }
}
</script>
