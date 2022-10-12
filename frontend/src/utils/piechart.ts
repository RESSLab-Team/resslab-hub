import * as d3 from "d3";

export interface Datum {
  name: string;
  value: number;
}

export const types = ["Steel Material", "Columns", "Components", "Braces"];

export interface OverviewMapOptions {
  name?: (arg0: any) => string;
  value?: (arg0: any) => number;
  width?: number;
  height?: number;
  innerRadius?: number;
  outerRadius?: number;
  labelRadius?: number;
  stroke?: number;
  strokeWidth?: number;
  strokeLinejoin?: string;
  padAngle?: number;
}

export function MarkerSVG(color: string) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 820" version="1.1" xml:space="preserve" style="fill-rule: evenodd; clip-rule: evenodd; stroke-linecap: round;"><g transform="matrix(19.5417,0,0,19.5417,-7889.1,-9807.44)"><path d="M416.544,503.612C409.971,503.612 404.5,509.303 404.5,515.478C404.5,518.256 406.064,521.786 407.194,524.224L416.5,542.096L425.762,524.224C426.892,521.786 428.5,518.433 428.5,515.478C428.5,509.303 423.117,503.612 416.544,503.612ZM416.544,510.767C419.128,510.784 421.223,512.889 421.223,515.477C421.223,518.065 419.128,520.14 416.544,520.156C413.96,520.139 411.865,518.066 411.865,515.477C411.865,512.889 413.96,510.784 416.544,510.767Z" stroke-width="1.1px" fill="${color}"/></g></svg>`;
}

export const scaleRadius = d3
  .scaleSqrt()
  .domain([0, 100])
  .rangeRound([40, 120]);

export const scaleColor = d3.scaleOrdinal(types, d3.schemeSet3);

export function PieChart(
  data: Datum[],
  options: OverviewMapOptions = {}
): SVGSVGElement | null {
  const name: (arg0: any) => string =
    options.name ||
    function ([x]) {
      return x;
    }; // given d in data, returns the (ordinal) label
  const value: (arg0: any) => number =
    options.value ||
    function ([_, y]) {
      return y;
    }; // given d in data, returns the (quantitative) value

  const width: number = options.width || 640;
  const height: number = options.height || 400;
  const innerRadius: number = options.innerRadius || 0; // inner radius of pie, in pixels (non-zero for donut)
  const outerRadius: number =
    options.outerRadius || Math.min(width, height) / 2; // outer radius of pie, in pixels
  const labelRadius: number =
    options.labelRadius || innerRadius * 0.2 + outerRadius * 0.6; // center radius of labels
  const stroke: number | string =
    options.stroke || innerRadius > 0 ? "none" : "white"; // stroke separating widths
  const strokeWidth: number = options.strokeWidth || 1; // width of stroke separating wedges
  const strokeLinejoin: string = options.strokeLinejoin || "round"; // line join of stroke separating wedges
  const padAngle: number =
    options.padAngle || stroke === "none" ? 1 / outerRadius : 0; // angular separation between wedges

  // Compute values.
  const N = data.map(name);
  const V = data.map(value);
  const I = d3.range(N.length).filter((i) => !isNaN(V[i]));

  const title = (index: number) => V[index];
  // Construct arcs.
  const arcs = d3
    .pie()
    .padAngle(padAngle)
    .sort(null)
    .value((d, i: number) => V[i])(I)
    .filter((d) => d.value > 0);

  const arc = d3.arc().innerRadius(innerRadius).outerRadius(outerRadius);
  const arcLabel = d3.arc().innerRadius(labelRadius).outerRadius(labelRadius);

  const svg = d3
    .create("svg")
    .attr("width", width)
    .attr("height", height)
    .attr("viewBox", [-width / 2, -height / 2, width, height])
    .attr("style", "max-width: 100%; height: auto; height: intrinsic;");

  svg
    .append("g")
    .attr("stroke", stroke)
    .attr("stroke-width", strokeWidth)
    .attr("stroke-linejoin", strokeLinejoin)
    .selectAll("path")
    .data(arcs)
    .join("path")
    .attr("fill", (d) => scaleColor(N[d.index]))
    .attr("d", (d: any) => arc(d))
    .append("title")
    .text((d) => title(d.index));

  svg
    .append("g")
    .attr("font-family", "sans-serif")
    .attr("font-size", 10)
    .attr("text-anchor", "middle")
    .attr("font-weight", "bold")
    .selectAll("text")
    .data(arcs)
    .join("text")
    .attr("transform", (d: any) =>
      arcs.length > 1 ? `translate(${arcLabel.centroid(d)})` : ""
    )
    .append("tspan")
    .attr("x", 0)
    .attr("y", 3)

    .text((d) => title(d.index));

  return svg.node();
}
