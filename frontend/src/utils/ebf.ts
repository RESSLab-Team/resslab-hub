import i18n from '@/plugins/i18n'

// Functions, not constants, so the labels follow the current locale.

export function linkConfigurationMapping(): Map<string, string> {
  const t = i18n.global.t
  return new Map([
    ['TF1', t('enum.isolatedLink')],
    ['TF2', t('enum.linkInBareFrame')],
    ['TF2C', t('enum.linkInCompositeFrame')],
    ['TF3', t('enum.linkInSystem')],
    ['TF3c', t('enum.linkInSystemConfigurationC')],
    ['TF4', t('enum.edgeLinkInBareFrame')],
    ['TF4c', t('enum.edgeLinkInCompositeFrame')],
    ['TF5', t('enum.continuousLink')],
    ['LC1', t('enum.connectionConfiguration1')],
    ['LC5', t('enum.connectionConfiguration5')]
  ])
}

export function sectionTypeMapping(): Map<string, string> {
  const t = i18n.global.t
  return new Map([
    ['hot-rolled', t('enum.hotRolled')],
    ['built-up', t('enum.builtUp')]
  ])
}
