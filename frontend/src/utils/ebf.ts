export const linkConfigurationMapping = new Map([
  ['TF1', 'Isolated link'],
  ['TF2', 'Link in bare frame'],
  ['TF2C', 'Link in composite frame'],
  ['TF3', 'Link in system'],
  ['TF3c', 'Link in system - configuration c'],
  ['LC1', 'Connection Configuration 1'],
  ['LC5', 'Connection Configuration 5']
])

export const linkTypeMapping = new Map([
  ['short', 'Short'],
  ['intermediate', 'Intermediate'],
  ['long', 'Long']
])

export const sectionTypeMapping = new Map([
  ['hot-rolled', 'Hot-Rolled'],
  ['built-up', 'Built-up']
])

export const getEbfImagePath = (linkConfiguration: string): string => {
  const publicPath = process.env.BASE_URL || '/'

  if (!linkConfiguration) return ''

  const configKey = linkConfiguration.toLowerCase()
  let imageName = ''
  switch (configKey) {
    case 'tf1':
      imageName = 'EBF_1.png'
      break
    case 'tf2':
      imageName = 'EBF_2.png'
      break
    case 'tf2c':
      imageName = 'EBF_3.png'
      break
    case 'tf3c':
      imageName = 'EBF_4.png'
      break
    default:
      return '' // No matching image
  }

  return `${publicPath}img/ebf/link_config/${imageName}`
}
