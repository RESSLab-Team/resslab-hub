import { publicPath } from "@/utils/common";

export function specimenTypeImageSrc(specimen_type: string) {
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
