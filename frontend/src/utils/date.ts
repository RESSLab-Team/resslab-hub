const dailyMilliseconds = 24 * 60 * 60 * 1000;

export function mapDateToNumber(value: string) {
  return new Date(value).getTime() / dailyMilliseconds;
}

export function mapNumberToDate(value: number) {
  return new Date(value * dailyMilliseconds).toISOString().split("T", 1)[0];
}
