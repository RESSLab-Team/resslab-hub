import { publicPath } from '@/utils/common'

export function getResidualStressImage() {
  return publicPath + 'img/residuals/detail.png'
}

/**
 * The section sketch of a residual stress record: the hot-rolled one, or for a
 * built-up section one of four, by symmetry and flange cutting (#228).
 */
export function getResidualStressSchematic(record: {
  profile_type?: string | null
  sym?: string | null
  plt_cut_f?: string | null
}) {
  if (!(record.profile_type ?? '').toLowerCase().includes('built-up')) {
    return getResidualStressImage()
  }
  const symmetry = (record.sym ?? '').trim().toLowerCase() === 'mono' ? 'mono' : 'doubly'
  const flame = (record.plt_cut_f ?? '').trim().toLowerCase() === 'flame-cut'
  return publicPath + `img/residuals/built-up-${symmetry}-${flame ? 'flame' : 'no-flame'}.svg`
}
export function getConnectionSpecimenImage(specimen_type: string) {
  switch (specimen_type) {
    case 'Exterior - Beam Loaded - Subassembly':
      return publicPath + 'img/specimen-type/exterior-beam.svg'
    case 'Exterior - Column Loaded - Subassembly':
      return publicPath + 'img/specimen-type/exterior-column.svg'
    case 'Interior - Column Loaded - Subassembly':
      return publicPath + 'img/specimen-type/interior-column.svg'
    case 'Interior - Beam Loaded - Subassembly':
      return publicPath + 'img/specimen-type/interior-beam.svg'
    default:
      return ''
  }
}

// Connection-type sketches are named after the type itself (WUF-W → wuf-w.svg),
// so this is a slug rather than the switch the other families need.
export function getConnectionTypeImage(connection_type: string) {
  return publicPath + 'img/connection-type/' + connection_type.toLowerCase() + '.svg'
}

export function getSteelMaterialImage() {
  return publicPath + 'img/material/steel_material.jpg'
}

export function getTensileCouponImage() {
  return publicPath + 'img/material/detail.png'
}

export function getDuctileFractureImage() {
  return publicPath + 'img/material/detail.png'
}

// Annotated sketch of a specimen geometry family (issue #238). Undefined for an
// unknown type, which the tooltip reads as "no figure".
export function getDuctileFractureSpecimenImage(specimen_type: string): string | undefined {
  switch (specimen_type) {
    case 'CNT':
      return publicPath + 'img/ductile-fracture/cnt.png'
    case 'GP':
      return publicPath + 'img/ductile-fracture/gp.png'
    default:
      return undefined
  }
}

// Per-specimen geometry drawing, generated from the nominal dimensions by
// `make precompute-fracture-figures` and committed alongside the sketches.
export function getDuctileFractureFigure(id: string) {
  return publicPath + 'img/ductile-fracture/figures/' + id + '.svg'
}

export function getBraceImage(boundary_condition: string) {
  switch (boundary_condition) {
    case 'Gusset plate':
      return publicPath + 'img/brace/type/gusset-plate.png'
    case 'Pin-Pin end':
      return publicPath + 'img/brace/type/pinned-end.png'
    case 'Fixed-fixed end':
      return publicPath + 'img/brace/type/fixed-end.png'
    case 'Fixed_pinned end':
      return publicPath + 'img/brace/type/fixed-pinned.png'
  }
}

//Feel redundant but it's as required in #89
export function getColumnMapImage(
  axis_of_bending: string,
  boundary_condition: string
): string | undefined {
  if (boundary_condition === 'Fixed-Fixed') {
    return publicPath + 'img/column-type/Fixed_Fixed_StrongAxis.png'
  }
  if (boundary_condition === 'Fixed-Flexible') {
    return publicPath + 'img/column-type/Fixed_Flexible_StrongAxis.png'
  }
  if (axis_of_bending === 'Strong' && boundary_condition === 'Fixed-Free') {
    return publicPath + 'img/column-type/Fixed_Free_StrongAxis.png'
  }
  if (axis_of_bending === 'Weak' && boundary_condition === 'Fixed-Free') {
    return publicPath + 'img/column-type/Fixed_Free_WeakAxis.png'
  }
  if (axis_of_bending === 'Bi-axial' && boundary_condition === 'Fixed-Free') {
    return publicPath + 'img/column-type/Fixed_Free_Biaxial.png'
  }

  return undefined
}

export function getColumnImage(
  axis_of_bending: string,
  boundary_condition: string,
  direction_lp: string
): string | undefined {
  if (axis_of_bending === 'Bi-axial' && boundary_condition === 'Fixed-Flexible') {
    return publicPath + 'img/column-type/Biaxial_Fixed_Flexible.png'
  }
  if (axis_of_bending === 'Bi-axial' && boundary_condition === 'Fixed-Free') {
    return publicPath + 'img/column-type/Fixed_Free_Biaxial.png'
  }
  if (axis_of_bending === 'Strong' && boundary_condition === 'Fixed-Flexible') {
    return publicPath + 'img/column-type/Fixed_Flexible_StrongAxis.png'
  }
  if (axis_of_bending === 'Strong' && boundary_condition === 'Fixed-Fixed') {
    return publicPath + 'img/column-type/Fixed_Fixed_StrongAxis.png'
  }
  if (axis_of_bending === 'Weak' && boundary_condition === 'Fixed-Fixed') {
    return publicPath + 'img/column-type/Fixed_Fixed_WeakAxis.png'
  }
  if (axis_of_bending === 'Strong' && boundary_condition === 'Fixed-Free') {
    return publicPath + 'img/column-type/Fixed_Free_StrongAxis.png'
  }
  if (axis_of_bending === 'Weak' && boundary_condition === 'Fixed-Free') {
    return publicPath + 'img/column-type/Fixed_Free_WeakAxis.png'
  }
  if (direction_lp === 'Bidirectional') {
    return publicPath + 'img/column-type/Fixed_Free_WeakAxis.png'
  }
  return undefined
}

export function getHSSColumnImage(test_configuration: string): string {
  if (test_configuration === '3PB') {
    return publicPath + 'img/hss/type/3_point_bending.jpg'
  } else if (test_configuration === 'CF') {
    return publicPath + 'img/hss/type/cantilever.jpg'
  } else if (test_configuration === 'DC') {
    return publicPath + 'img/hss/type/double_curvature.jpg'
  } else {
    console.warn('Unknown test configuration: ' + test_configuration)
    return ''
  }
}

export const getEbfImage = (linkConfiguration: string): string => {
  let imageName = ''
  switch (linkConfiguration) {
    case 'TF1':
      imageName = 'EBF_1.png'
      break
    case 'TF2':
      imageName = 'EBF_2.png'
      break
    case 'TF2c':
      imageName = 'EBF_3.png'
      break
    case 'TF3c':
      imageName = 'EBF_4.png'
      break
    case 'TF4':
      imageName = 'EBF_5.png'
      break
    case 'TF4c':
      imageName = 'EBF_6.png'
      break
    case 'TF5':
      imageName = 'EBF_7.png'
      break
    default:
      console.warn('Unknown linkConfiguration: ' + linkConfiguration)
      return '' // No matching image
  }

  return publicPath + `img/ebf/${imageName}`
}
