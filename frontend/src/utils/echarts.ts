export type VerticalAlign = 'top' | 'middle' | 'bottom'
export type ZRFontWeight = 'normal' | 'bold' | 'bolder' | 'lighter' | number

export const MAX_ECHARTS_POINTS = 1000

export function sampleArray<T>(arr: T[], sampleSize: number): T[] {
  if (sampleSize >= arr.length) {
    return arr
  }

  const skipFactor = Math.floor(arr.length / sampleSize)
  const sampledArray = []

  for (let i = 0; i < arr.length; i += skipFactor) {
    sampledArray.push(arr[i])
  }

  // In case the last point is missed and needed
  if (sampledArray.length < sampleSize && arr.length > 0) {
    sampledArray.push(arr[arr.length - 1])
  }

  return sampledArray
}
