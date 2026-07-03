import { describe, expect, it } from 'vitest'
import { THEME_KEY } from 'vue-echarts'

// main.ts provides the ECharts theme under the literal 'ecTheme' instead of
// importing THEME_KEY — importing it there would pull all of echarts/zrender
// into the entry chunk. This pin fails if a vue-echarts upgrade ever changes
// the injection key, so the theme can't silently stop applying.
describe('vue-echarts theme injection key', () => {
  it("is the literal 'ecTheme' main.ts provides", () => {
    expect(THEME_KEY).toBe('ecTheme')
  })
})
