import { publicPath } from "@/utils/common";

export function getConnectionSpecimenImage(specimen_type: string) {
  switch (specimen_type) {
    case "Exterior - Beam Loaded - Subassembly":
      return publicPath + "img/specimen-type/exterior-beam.svg";
    case "Exterior - Column Loaded - Subassembly":
      return publicPath + "img/specimen-type/exterior-column.svg";
    case "Interior - Column Loaded - Subassembly":
      return publicPath + "img/specimen-type/interior-column.svg";
    case "Interior - Beam Loaded - Subassembly":
      return publicPath + "img/specimen-type/interior-beam.svg";
    default:
      return "";
  }
}

export function getSteelMaterialImage() {
  return publicPath + "img/material/steel_material.jpg";
}

export function getBraceImage(boundary_condition: string) {
  switch (boundary_condition) {
    case "Gusset plate":
      return publicPath + "img/brace/type/gusset-plate.png";
    case "Pin-Pin end":
      return publicPath + "img/brace/type/pinned-end.png";
    case "Fixed-fixed end":
      return publicPath + "img/brace/type/fixed-end.png";
    case "Fixed_pinned end":
      return publicPath + "img/brace/type/fixed-pinned.png";
  }
}

//Feel redundant but it's as required in #89
export function getColumnMapImage(
  axis_of_bending: string,
  boundary_condition: string
): string | undefined {
  if (boundary_condition === "Fixed-Fixed") {
    return publicPath + "img/column-type/fixed-fixed-strong-axis.png";
  }
  if (boundary_condition === "Fixed-Flexible") {
    return publicPath + "img/column-type/fixed-flexible-strong-axis.png";
  }
  if (axis_of_bending === "Strong" && boundary_condition === "Fixed-Free") {
    return publicPath + "img/column-type/fixed-free-strong-axis.png";
  }
  if (axis_of_bending === "Weak" && boundary_condition === "Fixed-Free") {
    return publicPath + "img/column-type/fixed-free-weak-axis.png";
  }

  return undefined;
}

export function getColumnImage(
  axis_of_bending: string,
  boundary_condition: string,
  direction_lp: string
): string | undefined {
  if (axis_of_bending === "Strong" && boundary_condition === "Fixed-Flexible") {
    return publicPath + "img/column-type/Fixed_Flexible_StrongAxis.png";
  }
  if (axis_of_bending === "Strong" && boundary_condition === "Fixed-Fixed") {
    return publicPath + "img/column-type/Fixed_Fixed_StrongAxis.png";
  }
  if (axis_of_bending === "Weak" && boundary_condition === "Fixed-Fixed") {
    return publicPath + "img/column-type/Fixed_Fixed_WeakAxis.png";
  }
  if (axis_of_bending === "Strong" && boundary_condition === "Fixed-Free") {
    return publicPath + "img/column-type/Fixed_Free_StrongAxis.png";
  }
  if (axis_of_bending === "Weak" && boundary_condition === "Fixed-Free") {
    return publicPath + "img/column-type/Fixed_Free_WeakAxis.png";
  }
  if (direction_lp === "Bidirectional") {
    return publicPath + "img/column-type/Fixed_Free_WeakAxis.png";
  }
  return undefined;
}
