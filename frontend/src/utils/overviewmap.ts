import {
  LocationBracesModel,
  LocationColumnsModel,
  LocationConnectionsModel,
  LocationMaterialsModel,
} from "@/backend";
import {
  getBraceImage,
  getColumnMapImage,
  getConnectionSpecimenImage,
  getSteelMaterialImage,
} from "@/utils/component";
import { MarkerSVG, scaleColor, typesNames } from "@/utils/piechart";
import { divIcon, Marker } from "leaflet";

export function createTooltipConnections(d: LocationConnectionsModel) {
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

export function createTooltipBraces(d: LocationBracesModel) {
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

export function createTooltipColumns(d: LocationColumnsModel) {
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

export function createTooltipMaterials(d: LocationMaterialsModel) {
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

export function createTooltip(
  d:
    | LocationBracesModel
    | LocationConnectionsModel
    | LocationColumnsModel
    | LocationMaterialsModel,
  type: string
) {
  switch (type) {
    case "Connections":
      return createTooltipConnections(d as LocationConnectionsModel);
    case "Columns":
      return createTooltipColumns(d as LocationColumnsModel);
    case "Braces":
      return createTooltipBraces(d as LocationBracesModel);
    case "Materials":
      return createTooltipMaterials(d as LocationMaterialsModel);
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

export function createMarkers(
  data: (
    | LocationBracesModel
    | LocationConnectionsModel
    | LocationColumnsModel
    | LocationMaterialsModel
  )[],
  type: string
) {
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
