export function formatNumber(value?: number, fractionDigits = 0): string {
  if (value === null || value === undefined) {
    return "Not Applicable";
  } else if (isNaN(value)) {
    return "Not Reported";
  } else {
    return value.toFixed(fractionDigits);
  }
}

export function formatString(value?: string): string {
  if (value === null || value === undefined) {
    return "Not Applicable";
  } else if (value === "NR") {
    return "Not Reported";
  } else {
    return value;
  }
}
