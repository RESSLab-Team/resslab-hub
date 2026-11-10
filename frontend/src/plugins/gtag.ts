import type { PluginOptions } from 'vue-gtag'

// `bootstrap: false`: vue-gtag loads nothing until main.ts calls bootstrap(),
// after the visitor accepts the EPFL cookie banner (#264).
export const options: PluginOptions = {
  bootstrap: false,
  config: { id: 'G-HDDWMBZ6XJ', params: { anonymize_ip: true } }
}
