import i18n from '@/plugins/i18n'

export const linkConfigurationMapping = new Map([
  ['TF1', i18n.global.t('enum.isolatedLink')],
  ['TF2', i18n.global.t('enum.linkInBareFrame')],
  ['TF2C', i18n.global.t('enum.linkInCompositeFrame')],
  ['TF3', i18n.global.t('enum.linkInSystem')],
  ['TF3c', i18n.global.t('enum.linkInSystemConfigurationC')],
  ['TF4', i18n.global.t('enum.edgeLinkInBareFrame')],
  ['TF4c', i18n.global.t('enum.edgeLinkInCompositeFrame')],
  ['TF5', i18n.global.t('enum.continuousLink')],
  ['LC1', i18n.global.t('enum.connectionConfiguration1')],
  ['LC5', i18n.global.t('enum.connectionConfiguration5')]
])

export const linkTypeMapping = new Map([
  ['short', i18n.global.t('enum.short')],
  ['intermediate', i18n.global.t('enum.intermediate')],
  ['long', i18n.global.t('enum.long')]
])

export const sectionTypeMapping = new Map([
  ['hot-rolled', i18n.global.t('enum.hotRolled')],
  ['built-up', i18n.global.t('enum.builtUp')]
])
