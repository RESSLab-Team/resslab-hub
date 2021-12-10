export type Searches = Record<string, string | boolean>;

export function sum(a: number, b: number): number {
  return a + b;
}

export const publicPath: string = process.env.BASE_URL;

export const globalSearchKey = "search";
