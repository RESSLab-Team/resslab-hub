import { h } from 'vue'
import type { IconProps, IconSet } from 'vuetify'

/**
 * Custom thin-line database icons, one per component type plus the materials
 * group fallback. Drawn on the Material 24×24 grid (live area ~2–22) with a
 * uniform 1.5 stroke so they sit next to the @mdi/js chrome icons.
 *
 * Values are inner-SVG markup rendered inside a stroke-styled <svg> by the
 * `rl` icon set below; elements needing a fill (e.g. bolt heads) override the
 * inherited stroke/fill via an inline style.
 */
export const rlIcons: Record<string, string> = {
  // Beam framing into a column: column flanges, end plate, beam flanges, bolts.
  connections: [
    '<path d="M4.5 3 V21 M8 3 V21"/>',
    '<path d="M8 6.5 H10.5 V17.5 H8"/>',
    '<path d="M10.5 9.5 H21.5 M10.5 14.5 H21.5"/>',
    '<circle cx="9.25" cy="8" r="0.9" style="fill:currentColor;stroke:none"/>',
    '<circle cx="9.25" cy="16" r="0.9" style="fill:currentColor;stroke:none"/>'
  ].join(''),
  // Wide-flange (I/H) cross-section outline.
  columns: '<path d="M4 3 H20 V6 H13.5 V18 H20 V21 H4 V18 H10.5 V6 H4 Z"/>',
  // X-braced frame bay.
  braces: '<path d="M3 4.5 H21 V19.5 H3 Z"/><path d="M3 4.5 L21 19.5 M21 4.5 L3 19.5"/>',
  // Hollow square section: outer tube wall + inner void.
  hss: '<rect x="3.5" y="3.5" width="17" height="17" rx="1.5"/><rect x="7.5" y="7.5" width="9" height="9" rx="0.5"/>',
  // EBF bay: chevron braces meeting the beam either side of the short link.
  ebf: [
    '<path d="M3 5 H21 V19 H3 Z"/>',
    '<path d="M3 19 L9.5 5 M21 19 L14.5 5"/>',
    '<path d="M9.5 3 V7 M14.5 3 V7"/>'
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
    '<path d="M2.5 7 H6.5 C8 7 8 9.5 9.5 9.5 H11.6 L10.5 11.3 L11.9 12.7 L11 14.5 H9.5 C8 14.5 8 17 6.5 17 H2.5 Z"/>',
    '<path d="M21.5 7 H17.5 C16 7 16 9.5 14.5 9.5 H13.6 L12.5 11.3 L13.9 12.7 L13 14.5 H14.5 C16 14.5 16 17 17.5 17 H21.5 Z"/>'
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
          strokeWidth: '1.5',
          strokeLinecap: 'square',
          strokeLinejoin: 'miter'
        },
        innerHTML: rlIcons[String(icon)] ?? ''
      })
    ])
  }
}
