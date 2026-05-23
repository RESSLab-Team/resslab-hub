export function displayLoading(loading: string | null | undefined): string {
  if (!loading) return ''
  if (loading.toLowerCase().includes('cyclic')) return 'Cyclic'
  if (loading.toLowerCase().includes('monotonic')) return 'Monotonic'
  return loading
}
