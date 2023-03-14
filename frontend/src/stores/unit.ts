import { LocalStorageKey } from '@/utils/localStorage'
import type { UnitSystem } from '@/utils/unit'
import { defineStore } from 'pinia'

export const useUnitStore = defineStore('unit', {
  state: () => ({
    unitSystem: (localStorage.getItem(LocalStorageKey.UnitSystem) ?? 'metric') as UnitSystem
  }),
  actions: {
    setUnitSystem(value: UnitSystem) {
      this.unitSystem = value
      localStorage.setItem(LocalStorageKey.UnitSystem, value)
    }
  }
})
