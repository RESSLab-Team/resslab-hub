<script lang="ts">
import { Unit, units, UnitSystem } from "@/utils/unit";
import { Component, Prop, Vue } from "vue-property-decorator";

@Component
export default class UnitMixin extends Vue {
  @Prop({ type: String, default: "" })
  readonly unit!: string;
  @Prop({ type: String as () => UnitSystem })
  readonly unitSystem: UnitSystem | undefined;

  get filteredUnits(): Unit[] {
    return units.filter((u) => u.referenceUnit === this.unit);
  }

  get selectedUnit(): Unit | undefined {
    return this.filteredUnits.find((u) => u.system === this.unitSystem);
  }

  get unitLabel(): string {
    return this.selectedUnit?.unit ?? this.unit;
  }

  get ratio(): number {
    return this.selectedUnit?.ratio ?? 1;
  }
}
</script>
