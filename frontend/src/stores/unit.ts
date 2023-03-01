import { UnitSystem } from "@/utils/unit";
import { defineStore } from "pinia";

const localStorageKey = "unitSystem";

export const useUnitStore = defineStore("unit", {
  state: () => ({
    unitSystem: (localStorage.getItem(localStorageKey) ??
      "metric") as UnitSystem,
    showUnitToggle: true,
  }),
  actions: {
    setUnitSystem(value: UnitSystem) {
      this.unitSystem = value;
      localStorage.setItem(localStorageKey, value);
    },
    setShowUnitToggle(value: boolean) {
      this.showUnitToggle = value;
    },
  },
});
