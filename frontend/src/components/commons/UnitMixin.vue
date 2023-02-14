<script lang="ts">
import { useUnitStore } from "@/stores/unit";
import { Unit, units } from "@/utils/unit";
import { Component, Prop, Vue } from "vue-property-decorator";

@Component
export default class UnitMixin extends Vue {
  unitStore = useUnitStore();

  @Prop({ type: String, default: "" })
  readonly unit!: string;

  get filteredUnits(): Unit[] {
    return units.filter((u) => u.referenceUnit === this.unit);
  }

  get selectedUnit(): Unit | undefined {
    const unitSystem = this.unitStore.unitSystem;
    return this.filteredUnits.find((u) => u.system === unitSystem);
  }

  get unitLabel(): string {
    return this.selectedUnit?.unit ?? this.unit;
  }

  get ratio(): number {
    return this.selectedUnit?.ratio ?? 1;
  }
}
</script>
