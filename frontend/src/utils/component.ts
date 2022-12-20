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

export function getColumnImage(
  axis_of_bending: string,
  boundary_condition: string,
  direction_lp: string
): string | undefined {
  if (axis_of_bending === "Strong" && boundary_condition === "Fixed-Flexible") {
    return publicPath + "img/column-type/fixed-flexible-strong-axis.png";
  }
  if (axis_of_bending === "Strong" && boundary_condition === "Fixed-Fixed") {
    return publicPath + "img/column-type/fixed-fixed-strong-axis.png";
  }
  if (axis_of_bending === "Weak" && boundary_condition === "Fixed-Fixed") {
    return publicPath + "img/column-type/fixed-fixed-weak-axis.png";
  }
  if (axis_of_bending === "Strong" && boundary_condition === "Fixed-Free") {
    return publicPath + "img/column-type/fixed-free-strong-axis.png";
  }
  if (axis_of_bending === "Weak" && boundary_condition === "Fixed-Free") {
    return publicPath + "img/column-type/fixed-free-weak-axis.png";
  }
  if (direction_lp === "Birectional") {
    return publicPath + "img/column-type/bidirectional.png";
  }
  return undefined;
}
