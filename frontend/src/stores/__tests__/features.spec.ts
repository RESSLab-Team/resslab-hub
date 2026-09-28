import { useFeaturesStore } from '@/stores/features'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const getFeatures = vi.fn()

vi.mock('@/plugins/axios', () => ({
  defaultApi: {
    getFeatures: (...args: unknown[]) => getFeatures(...args)
  }
}))

describe('features store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('starts out not knowing, and asks only once', async () => {
    getFeatures.mockResolvedValue({ data: { contributions: true } })
    const store = useFeaturesStore()
    expect(store.contributions).toBeNull()

    await Promise.all([store.ensureLoaded(), store.ensureLoaded()])
    await store.ensureLoaded()

    expect(getFeatures).toHaveBeenCalledTimes(1)
    expect(store.contributions).toBe(true)
  })

  it('reads a switched-off deployment', async () => {
    getFeatures.mockResolvedValue({ data: { contributions: false } })
    const store = useFeaturesStore()
    await store.ensureLoaded()
    expect(store.contributions).toBe(false)
  })

  it('keeps the pipeline on when the request fails', async () => {
    // A passing error must not hide sign-in for the rest of the visit.
    getFeatures.mockRejectedValue(new Error('Network Error'))
    const store = useFeaturesStore()
    await store.ensureLoaded()
    expect(store.contributions).toBe(true)
  })
})
