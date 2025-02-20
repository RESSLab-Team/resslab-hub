import type {
  BraceField,
  BraceModel,
  ColumnField,
  ColumnModel,
  ConnectionField,
  ConnectionModel,
  HSSColumnField,
  HSSColumnModel,
  MaterialField,
  MaterialModel,
  ResidualStressField,
  ResidualStressModel
} from '@/backend'
import TooltipContent from '@/components/map/TooltipContent.vue'
import { typesNames, type Type } from '@/utils/backend'
import { MarkerSVG, scaleColor } from '@/utils/piechart'
import { divIcon, Marker } from 'leaflet'
import { createApp } from 'vue'

// First we list all the fields that we want to use in the tooltip
// We will use these fields as argument fot get_fields api
const locationCommonFields = ['id', 'date', 'reference', 'latitude', 'longitude'] as const
const _locationBraceFields = [
  ...locationCommonFields,
  'cross_section_size',
  'link',
  'investigator',
  'kl_r',
  'boundary_condition'
] as const
export const locationBraceFields: BraceField[] = [..._locationBraceFields]
const _locationColumnFields = [
  ...locationCommonFields,
  'link',
  'boundary_condition',
  'experimental_program',
  'axial_lp',
  'p_g_over_p_ym',
  'section_c',
  'axis_of_bending'
] as const
export const locationColumnFields: ColumnField[] = [..._locationColumnFields]
const _locationConnectionFields = [
  ...locationCommonFields,
  'link',
  'experimental_program',
  'specimen_type',
  'section_b',
  'section_c',
  'connection_type'
] as const
export const locationConnectionFields: ConnectionField[] = [..._locationConnectionFields]
const _locationMaterialFields = [
  ...locationCommonFields,
  'link',
  'profile_type',
  'profile',
  'experimental_program'
] as const
export const locationMaterialFields: MaterialField[] = [..._locationMaterialFields]
const _locationResidualStressFields = [
  ...locationCommonFields,
  'link',
  'profile_type',
  'profile',
  'experimental_program'
] as const
export const locationResidualStressFields: ResidualStressField[] = [
  ..._locationResidualStressFields
]
const _locationHSSColumnFields = [
  ...locationCommonFields,
  'investigator',
  'test_type',
  'test_configuration',
  'tube_section',
  'url'
] as const
export const locationHSSColumnFields: HSSColumnField[] = [..._locationHSSColumnFields]

// Then we use the fields list to create fields types for each model
// Finally we use Pick to extract type from bigger model type using only the fields we want
export type LocationBrace = Pick<BraceModel, (typeof _locationBraceFields)[number]>
export type LocationColumn = Pick<ColumnModel, (typeof _locationColumnFields)[number]>
export type LocationConnection = Pick<ConnectionModel, (typeof _locationConnectionFields)[number]>
export type LocationMaterial = Pick<MaterialModel, (typeof _locationMaterialFields)[number]>
export type LocationResidualStress = Pick<
  ResidualStressModel,
  (typeof _locationResidualStressFields)[number]
>
export type LocationHSSColumn = Pick<HSSColumnModel, (typeof _locationHSSColumnFields)[number]>

type LocationGlobal =
  | LocationBrace
  | LocationColumn
  | LocationConnection
  | LocationMaterial
  | LocationResidualStress
  | LocationHSSColumn

type LocationWithCoordinates = LocationGlobal & { latitude: number; longitude: number }

export const icons = new Map(
  typesNames.map((type) => [
    type,
    divIcon({
      html: MarkerSVG(scaleColor(type)),
      className: '',
      iconSize: [30, 30],
      iconAnchor: [15, 30]
    })
  ])
)

export function hasCoordinates(d: LocationGlobal): d is LocationWithCoordinates {
  if (d.latitude && d.longitude) return true
  else return false
}

export function createMarkers(data: LocationGlobal[], type: Type) {
  return data.filter<LocationWithCoordinates>(hasCoordinates).map((d) => {
    // Create a container element to mount the Vue tooltip component
    const container = document.createElement('div')

    // Create the Vue app with your TooltipContent component and pass props
    createApp(TooltipContent, { data: d, type }).mount(container)

    // Create a marker with a popup bound to the container's innerHTML
    const marker = new Marker([d.latitude, d.longitude], {
      icon: icons.get(type)
    }).bindPopup(container.innerHTML, { autoPanPadding: [50, 150] })

    marker.feature = {
      type: 'Feature',
      properties: Object.assign(d, { type }),
      geometry: {
        type: 'Point',
        coordinates: [d.latitude, d.longitude]
      }
    }
    return marker
  })
}
