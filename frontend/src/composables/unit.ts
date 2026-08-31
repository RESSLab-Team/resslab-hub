import { useUnitStore } from '@/stores/unit'
import { units } from '@/utils/unit'
import { computed } from 'vue'

export function useUnits(unit = '') {
  const unitStore = useUnitStore()

  const filteredUnits = computed(() => units.filter((u) => u.referenceUnit === unit))
  const selectedUnit = computed(() => {
    const unitSystem = unitStore.unitSystem
    return filteredUnits.value.find((u) => u.system === unitSystem)
  })
  return {
    unitLabel: computed(() => selectedUnit.value?.unit ?? unit),
    ratio: computed(() => selectedUnit.value?.ratio ?? 1)
  }
}
