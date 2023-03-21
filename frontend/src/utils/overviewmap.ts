import {
  BraceField,
  BraceModel,
  ColumnField,
  ColumnModel,
  ConnectionField,
  ConnectionModel,
  MaterialField,
  MaterialModel,
} from "@/backend";
import { Type, typesNames } from "@/utils/backend";
import {
  getBraceImage,
  getColumnMapImage,
  getConnectionSpecimenImage,
  getSteelMaterialImage,
} from "@/utils/component";
import { MarkerSVG, scaleColor } from "@/utils/piechart";
import { divIcon, Marker } from "leaflet";

// First we list all the fields that we want to use in the tooltip
// We will use these fields as argument fot get_fields api
const locationCommonFields = [
  "id",
  "link",
  "date",
  "reference",
  "latitude",
  "longitude",
] as const;
const _locationBraceFields = [
  ...locationCommonFields,
  "cross_section_size",
  "investigator",
  "kl_r",
  "boundary_condition",
] as const;
export const locationBraceFields: BraceField[] = [..._locationBraceFields];
const _locationColumnFields = [
  ...locationCommonFields,
  "boundary_condition",
  "experimental_program",
  "axial_lp",
  "p_g_over_p_ym",
  "section_c",
  "axis_of_bending",
] as const;
export const locationColumnFields: ColumnField[] = [..._locationColumnFields];
const _locationConnectionFields = [
  ...locationCommonFields,
  "experimental_program",
  "specimen_type",
  "section_b",
  "section_c",
  "connection_type",
] as const;
export const locationConnectionFields: ConnectionField[] = [
  ..._locationConnectionFields,
];
const _locationMaterialFields = [
  ...locationCommonFields,
  "profile_type",
  "profile",
  "experimental_program",
] as const;
export const locationMaterialFields: MaterialField[] = [
  ..._locationMaterialFields,
];

// Then we use the fields list to create fields types for each model
// Finally we use Pick to extract type from bigger model type using only the fields we want
export type LocationBrace = Pick<
  BraceModel,
  (typeof _locationBraceFields)[number]
>;
export type LocationColumn = Pick<
  ColumnModel,
  (typeof _locationColumnFields)[number]
>;
export type LocationConnection = Pick<
  ConnectionModel,
  (typeof _locationConnectionFields)[number]
>;
export type LocationMaterial = Pick<
  MaterialModel,
  (typeof _locationMaterialFields)[number]
>;
type LocationGlobal =
  | LocationBrace
  | LocationColumn
  | LocationConnection
  | LocationMaterial;

// Now we use the newly created types for our specific tooltip functions

export function createTooltipConnections(d: LocationConnection) {
  return `<div class="tooltip">
        <h3><a target="_blank" href="${d.link}">${d.experimental_program} (${
    d.date
  })</a></h3>
        <br>
        <ul>
          <li>${d.specimen_type}</li>
          <li>${d.connection_type}, Beam: ${d.section_b} Col: ${
    d.section_c
  }</li>
          <li>
            <img alt="${d.specimen_type}" src="${getConnectionSpecimenImage(
    d.specimen_type
  )}"></img>
          </li>
          <li><a href='/connections/database?id=${
            d.id
          }&detail=true'>View experimental data</a></li>
        </ul>
        </div>`;
}

export function createTooltipBraces(d: LocationBrace) {
  return `<div class="tooltip">
        <h3><a target="_blank" href="${d.link}">${d.investigator} (${
    d.date
  })</a></h3>
        <br>
        <ul>
          <li>Cross section: ${d.cross_section_size}</li>
          <li>KL/r:   ${d.kl_r}</li>
          <li>
            <img alt="Braces placeholder image" src="${getBraceImage(
              d.boundary_condition
            )}"></img>
          </li>
          <li><a href='/braces/database?id=${
            d.id
          }&detail=true'>View experimental data</a></li>
        </ul>
        </div>`;
}

export function createTooltipColumns(d: LocationColumn) {
  return `<div class="tooltip">
        <h3><a target="_blank" href="${d.link}">${d.experimental_program} (${
    d.date
  })</a></h3>
        <br>
        <ul>
          <li>${d.boundary_condition}</li>
          <li>${d.axial_lp} (Pg/Py = ${d.p_g_over_p_ym}), Column: ${
    d.section_c
  }</li>
          <li>
            <img alt="Columns placeholder image" src="${getColumnMapImage(
              d.axis_of_bending,
              d.boundary_condition
            )}"></img>
          </li>
          <li><a href='/columns/database?id=${
            d.id
          }&detail=true'>View experimental data</a></li>
        </ul>
        </div>`;
}

export function createTooltipMaterials(d: LocationMaterial) {
  return `<div class="tooltip">
        <h3><a target="_blank" href="${d.link}">${d.experimental_program} (${
    d.date
  })</a></h3>
        <br>
        <ul>
          <li>Profile type: ${d.profile_type}</li>
          <li>Cross section: ${d.profile}</li>
          <li>
            <img alt="Materials placeholder image" src="${getSteelMaterialImage()}"></img>
          </li>
          <li><a href='/materials/database?id=${
            d.id
          }&detail=true'>View experimental data</a></li>
        </ul>
        </div>`;
}

export function createTooltip(d: LocationGlobal, type: Type) {
  switch (type) {
    case "Connections":
      return createTooltipConnections(d as LocationConnection);
    case "Columns":
      return createTooltipColumns(d as LocationColumn);
    case "Braces":
      return createTooltipBraces(d as LocationBrace);
    case "Materials":
      return createTooltipMaterials(d as LocationMaterial);
    default:
      return `<h3>No tooltip constructor found for ${d} type is ${type}</h3>`;
  }
}
export const icons = new Map(
  typesNames.map((type) => [
    type,
    divIcon({
      html: MarkerSVG(scaleColor(type)),
      className: "",
      iconSize: [30, 30],
      iconAnchor: [15, 30],
    }),
  ])
);

export function createMarkers(data: LocationGlobal[], type: Type) {
  return data.map((d) => {
    const marker = new Marker([d.latitude, d.longitude], {
      icon: icons.get(type),
    }).bindPopup(createTooltip(d, type));
    marker.feature = {
      type: "Feature",
      properties: Object.assign(d, { type }),
      geometry: {
        type: "Point",
        coordinates: [d.latitude, d.longitude],
      },
    };
    return marker;
  });
}
