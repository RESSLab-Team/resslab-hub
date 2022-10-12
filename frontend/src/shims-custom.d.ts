declare module "v-switch-case";

declare module "*-sections.csv" {
  const content: {
    id: string;
    bf: number;
    h: number;
    tf: number;
    tw: number;
    ix: number;
    zx: number;
    ry: number;
    d: number;
  }[];
  export default content;
}

declare module "*overviewmap.csv" {
  const content: {
    id: string;
    experimental_program: string;
    date: number;
    latitude: number;
    longitude: number;
    type: string;
  }[];
  export default content;
}
