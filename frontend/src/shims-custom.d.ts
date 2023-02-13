declare module "v-switch-case";

declare module "@/assets/connection/*-sections.csv" {
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
    a: number;
    iy: number;
  }[];
  export default content;
}

declare module "@/assets/material/parameter-material-list.csv" {
  const content: {
    steel: string;
    E: number;
    syo: number;
    Q_inf: number;
    b: number;
    D_inf: number;
    a: number;
    c1: number;
    gamma1: number;
    c2: number;
    gamma2: number;
  }[];
  export default content;
}
