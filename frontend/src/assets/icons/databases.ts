import { h } from 'vue'
import type { IconProps, IconSet } from 'vuetify'

/**
 * Custom thin-line database icons, one per component type plus the materials
 * group fallback. Drawn on the Material 24×24 grid (live area ~2–22) with a
 * uniform 1.8 stroke, matching the wall weight of the mdi outline icons.
 *
 * Values are inner-SVG markup rendered inside a stroke-styled <svg> by the
 * `rl` icon set below; elements needing a fill (e.g. bolt heads) override the
 * inherited stroke/fill via an inline style.
 */
export const rlIcons: Record<string, string> = {
  // Beam framing into a column: column flanges, beam flanges, bolt pair.
  connections: [
    '<path d="M4.5 3 V21 M8 3 V21"/>',
    '<path d="M8.75 9 H21 M8.75 15 H21"/>',
    '<circle cx="10.75" cy="11" r="0.75" style="fill:currentColor;stroke:none"/>',
    '<circle cx="10.75" cy="13" r="0.75" style="fill:currentColor;stroke:none"/>'
  ].join(''),
  // Wide-flange (I/H) cross-section outline. Flange and web are 3 units of
  // metal — the same section thickness the HSS tube wall uses.
  columns: '<path d="M4 3 H20 V6 H13.5 V18 H20 V21 H4 V18 H10.5 V6 H4 Z"/>',
  // X-braced frame bay: columns on foundation lines, open at the bottom.
  braces: [
    '<path d="M4 19.5 V4.5 H20 V19.5"/>',
    '<path d="M2 19.5 H6 M18 19.5 H22"/>',
    '<path d="M4.75 5.25 L19.25 18.75 M19.25 5.25 L4.75 18.75"/>'
  ].join(''),
  // Hollow square section: outer tube wall + inner void, 3 units of metal to
  // match the wide-flange section above.
  hss: '<rect x="3.5" y="3.5" width="17" height="17" rx="1.5"/><rect x="6.5" y="6.5" width="11" height="11" rx="0.5"/>',
  // EBF bay on foundation lines: chevron braces meeting the short link under the beam.
  ebf: [
    '<path d="M4 19.5 V4.5 H20 V19.5"/>',
    '<path d="M2 19.5 H6 M18 19.5 H22"/>',
    '<path d="M9.5 5.25 V7.5 H14.5 V5.25"/>',
    '<path d="M4.75 18.75 L9.5 7.5 M19.25 18.75 L14.5 7.5"/>'
  ].join(''),
  // Hysteresis loop over centred stress–strain axes.
  cyclic: [
    '<path d="M12 3.5 V20.5 M3.5 12 H20.5"/>',
    '<path d="M5 16.5 C6.5 10.5 11.5 8 19 7.5 C17.5 13.5 12.5 16 5 16.5 Z"/>'
  ].join(''),
  // Dogbone tensile coupon.
  tensile:
    '<path d="M3 7 H7 C8.5 7 8.5 9.5 10 9.5 H14 C15.5 9.5 15.5 7 17 7 H21 V17 H17 C15.5 17 15.5 14.5 14 14.5 H10 C8.5 14.5 8.5 17 7 17 H3 Z"/>',
  // Dogbone coupon fractured through the gauge length.
  'ductile-fracture': [
    '<path d="M2.5 7 H6.5 C8 7 8 9.5 9.5 9.5 H11.6 L10.3 12 L11.6 14.5 H9.5 C8 14.5 8 17 6.5 17 H2.5 Z"/>',
    '<path d="M21.5 7 H17.5 C16 7 16 9.5 14.8 9.5 L13.5 12 L14.8 14.5 C16 14.5 16 17 17.5 17 H21.5 Z"/>'
  ].join(''),
  // Self-equilibrated residual stress distribution across a flange.
  residuals: [
    '<path d="M3 17 H21"/>',
    '<path d="M3 20.5 C7.5 20.5 9 7 12 7 C15 7 16.5 20.5 21 20.5"/>'
  ].join(''),
  // Monotonic stress–strain curve (materials group fallback).
  materials: [
    '<path d="M4.5 3.5 V19.5 H20.5"/>',
    '<path d="M4.5 19.5 L9.5 8.7 C10.5 6.6 12 6.2 20.5 6"/>'
  ].join('')
}

/**
 * Vuetify icon set: use as `icon="rl:braces"`. Mirrors mdi-svg's VSvgIcon
 * markup (same class/sizing) but styles the svg for stroke rendering — the
 * inline style is required to beat `.v-icon__svg { fill: currentColor }`.
 */
export const rl: IconSet = {
  component: (props: IconProps) => {
    const { icon, tag, ...rest } = props
    return h(tag as string, rest as Record<string, unknown>, [
      h('svg', {
        class: 'v-icon__svg',
        xmlns: 'http://www.w3.org/2000/svg',
        viewBox: '0 0 24 24',
        role: 'img',
        'aria-hidden': 'true',
        style: {
          fill: 'none',
          stroke: 'currentColor',
          strokeWidth: '1.8',
          strokeLinecap: 'butt',
          strokeLinejoin: 'miter'
        },
        innerHTML: rlIcons[String(icon)] ?? ''
      })
    ])
  }
}
