import i18n from '@/plugins/i18n'

/** A function, not a constant, so the labels follow the current locale. */
export function testConfigurationNameMapping(): Map<string, string> {
  const t = i18n.global.t
  return new Map([
    ['3PB', t('enum.threePointBending')],
    ['CF', t('enum.cantilever')],
    ['DC', t('enum.doubleCurvature')]
  ])
}
