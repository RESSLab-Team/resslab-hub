import { AXIS, EXISTING, INK, NAME, RED, SANS, TICK } from '@/plugins/echarts-theme'
import { themes } from '@/plugins/vuetify'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

/**
 * The same brand values exist in three places, and they have to: the CSS
 * custom properties are the source, but Vuetify's theme wants plain hex (it
 * splits it into the rgb triplet behind `--v-theme-*`) and ECharts draws on a
 * canvas, where `var(--epfl-red)` means nothing. Nothing keeps the copies in
 * step, so this reads the real token file and compares.
 *
 * A failure here means one copy moved. Move the other two, do not relax the
 * test. See docs/src/design-system.md.
 */

const TOKENS = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '../../assets/styles/epfl-tokens.css'
)

/** Read the custom properties of one selector block out of the token file. */
function tokensOf(selector: string): Record<string, string> {
  const css = readFileSync(TOKENS, 'utf8')
  const start = css.indexOf(selector + ' {')
  if (start < 0) throw new Error(`no "${selector}" block in epfl-tokens.css`)
  const block = css.slice(start, css.indexOf('\n}', start))
  const out: Record<string, string> = {}
  for (const [, name, value] of block.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) {
    out[name] = value.trim()
  }
  return out
}

const light = tokensOf(':root')
const dark = tokensOf('body.theme-dark')

/** Hex compares case-insensitively; the files disagree on case on purpose. */
const same = (a: string, b: string) => a.toLowerCase() === b.toLowerCase()

/** Follow `var(--x)` through the light tokens until a plain value. */
function resolved(value: string): string {
  const match = /^var\((--[\w-]+)\)$/.exec(value.trim())
  return match ? resolved(light[match[1]]) : value
}

describe('the token file is the source of the brand values', () => {
  it('has the raw palette the rest of the app copies', () => {
    expect(light['--epfl-red']).toBeDefined()
    expect(light['--epfl-leman']).toBeDefined()
    expect(light['--epfl-black']).toBeDefined()
  })

  describe('Vuetify theme (plugins/vuetify.ts)', () => {
    it('uses the token red as primary, in both themes', () => {
      expect(same(themes.light.colors.primary, light['--epfl-red'])).toBe(true)
      expect(same(themes.dark.colors.primary, light['--epfl-red'])).toBe(true)
    })

    it('uses the token leman as accent', () => {
      expect(same(themes.light.colors.accent, light['--epfl-leman'])).toBe(true)
      expect(same(themes.dark.colors.accent, light['--epfl-leman'])).toBe(true)
    })

    it('matches the light surfaces', () => {
      expect(same(themes.light.colors.background, light['--epfl-white'])).toBe(true)
      expect(same(themes.light.colors.surface, light['--epfl-white'])).toBe(true)
    })

    it('matches the dark surfaces and muted ink', () => {
      expect(same(themes.dark.colors.background, dark['--bg'])).toBe(true)
      expect(same(themes.dark.colors.surface, dark['--bg-muted'])).toBe(true)
      expect(same(themes.dark.colors.secondary, dark['--fg-muted'])).toBe(true)
    })
  })

  describe('ECharts theme (plugins/echarts-theme.ts)', () => {
    it('uses the token red for brush bands and emphasis', () => {
      expect(same(RED, light['--epfl-red'])).toBe(true)
    })

    it('draws its ink in the token soft black', () => {
      expect(same(INK, light['--epfl-black'])).toBe(true)
    })

    it('draws axis lines and ticks in the token greys', () => {
      expect(same(AXIS, light['--epfl-gray-300'])).toBe(true)
      expect(same(TICK, light['--epfl-gray-500'])).toBe(true)
    })

    it('draws axis names in the dark-mode subtle grey', () => {
      // On purpose: the axis name is quieter than the tick label, and this is
      // the one grey in the file that lands there.
      expect(same(NAME, dark['--fg-subtle'])).toBe(true)
    })

    it('draws submitted data in the token red and existing data in the token grey', () => {
      expect(same(RED, resolved(light['--data-submitted']))).toBe(true)
      expect(same(EXISTING, resolved(light['--data-existing']))).toBe(true)
    })

    it('renders text in the brand face, since a canvas cannot read a var()', () => {
      // First family of a stack, without the escaping each file needs.
      const firstFamily = (stack: string) =>
        stack
          .split(',')[0]
          .replace(/\\/g, '')
          .replace(/^["']|["']$/g, '')
          .trim()

      expect(firstFamily(light['--font-sans'])).toBe("Suisse Int'l")
      expect(firstFamily(SANS)).toBe(firstFamily(light['--font-sans']))
    })
  })
})
