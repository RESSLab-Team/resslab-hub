export type Value = string | boolean | number | string[];
export type Searches = Record<string, Value>;

export function sum(a: number, b: number): number {
  return a + b;
}

export function filterColumnValue(value: Value): boolean {
  if (typeof value === "string" || Array.isArray(value)) {
    return value.length > 0;
  } else {
    return true;
  }
}

export const publicPath: string = process.env.BASE_URL ?? "";

export const globalSearchKey = "search";

export interface Section {
  id: string;
  bf: number;
  h: number;
  tf: number;
  tw: number;
}
