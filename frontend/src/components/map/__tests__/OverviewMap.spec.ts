import type { MapSite } from '@/backend'
import OverviewMap from '@/components/map/OverviewMap.vue'
import en from '@/locales/en.json'
import { siteFeatures } from '@/utils/mapSites'
import { SITES_SOURCE } from '@/utils/mapStyle'
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createI18n } from 'vue-i18n'

/**
 * jsdom has no WebGL, so MapLibre is replaced by a fake that records what the
 * component asks of it. The test fires the map events by hand ('load', then
 * 'render') and checks the markers, the panel and the filter.
 */
const fake = vi.hoisted(() => {
  type Handler = (event?: unknown) => void

  const setData = vi.fn()
  const getClusterLeaves = vi.fn()

  class FakeMap {
    static last: FakeMap | null = null
    static fail = false

    handlers = new Map<string, Handler[]>()
    sources = new Map<string, unknown>()
    layers = new Set<string>()
    /** what querySourceFeatures returns: set by the test */
    features: unknown[] = []

    addSource = vi.fn((id: string, spec: unknown) => void this.sources.set(id, spec))
    removeSource = vi.fn((id: string) => void this.sources.delete(id))
    getSource = vi.fn((id: string) =>
      this.sources.has(id) ? { setData, getClusterLeaves } : undefined
    )
    addLayer = vi.fn((layer: { id: string }) => void this.layers.add(layer.id))
    removeLayer = vi.fn((id: string) => void this.layers.delete(id))
    getLayer = vi.fn((id: string) => (this.layers.has(id) ? { id } : undefined))
    isSourceLoaded = () => true
    querySourceFeatures = vi.fn(() => this.features)
    fitBounds = vi.fn()
    easeTo = vi.fn()
    resize = vi.fn()
    remove = vi.fn()
    setMinZoom = vi.fn()
    addControl = vi.fn()
    zoomIn = vi.fn()
    zoomOut = vi.fn()
    project = () => ({ x: 100, y: 100 })
    getZoom = () => 1
    touchZoomRotate = { disableRotation: vi.fn() }

    constructor() {
      if (FakeMap.fail) throw new Error('Failed to initialize WebGL')
      FakeMap.last = this
    }

    on(event: string, handler: Handler) {
      this.handlers.set(event, [...(this.handlers.get(event) ?? []), handler])
      return this
    }

    fire(event: string, payload?: unknown) {
      for (const handler of this.handlers.get(event) ?? []) handler(payload)
    }
  }

  class FakeMarker {
    static added: FakeMarker[] = []
    element: HTMLElement
    remove = vi.fn()

    constructor(options: { element: HTMLElement }) {
      this.element = options.element
    }

    setLngLat() {
      return this
    }

    addTo() {
      FakeMarker.added.push(this)
      return this
    }
  }

  class FakeBounds {
    points: unknown[] = []
    extend(point: unknown) {
      this.points.push(point)
      return this
    }
    isEmpty() {
      return this.points.length === 0
    }
  }

  return { FakeMap, FakeMarker, FakeBounds, setData, getClusterLeaves }
})

vi.mock('maplibre-gl', () => ({
  Map: fake.FakeMap,
  Marker: fake.FakeMarker,
  LngLatBounds: fake.FakeBounds,
  AttributionControl: class {},
  setWorkerUrl: vi.fn()
}))

const getMapSites = vi.fn()

vi.mock('@/plugins/axios', () => ({
  mapApi: { getMapSites: (...args: unknown[]) => getMapSites(...args) }
}))

vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))

// A local instance rather than `@/plugins/i18n`: the plugin reads localStorage at
// import time, which the test environment does not provide.
const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })

const program = (category: MapSite['programs'][number]['category'], n: number) => ({
  category,
  program: `Program ${category}`,
  year: 2020,
  n,
  reference: null,
  link: null,
  first_id: `${category}-1`,
  figure: null
})

// Three sites named in assets/map-sites.json. Kyoto only has braces, so
// hiding braces drops it.
const SITES: MapSite[] = [
  {
    sid: '46.52,6.57',
    lat: 46.52,
    lng: 6.57,
    n: 30,
    counts: { materials: 20, braces: 10 },
    programs: [program('materials', 20), program('braces', 10)]
  },
  {
    sid: '35.03,135.78',
    lat: 35.03,
    lng: 135.78,
    n: 5,
    counts: { braces: 5 },
    programs: [program('braces', 5)]
  },
  {
    sid: '37.87,-122.24',
    lat: 37.87,
    lng: -122.24,
    n: 12,
    counts: { columns: 12 },
    programs: [program('columns', 12)]
  }
]

// What the source would give back at world zoom: EPFL alone, Kyoto and
// Berkeley merged into one cluster.
function features() {
  const [epfl, kyoto, berkeley] = siteFeatures(SITES, new Set()).features
  const cluster: Record<string, unknown> = { cluster: true, cluster_id: 7, point_count: 2 }
  for (const key of Object.keys(kyoto.properties)) {
    if (!key.startsWith('t')) continue
    const k = key as keyof typeof kyoto.properties
    cluster[key] = Number(kyoto.properties[k]) + Number(berkeley.properties[k])
  }
  return [epfl, { properties: cluster, geometry: { type: 'Point', coordinates: [180, 36] } }]
}

let width = 900

async function mountMap() {
  const wrapper = mount(OverviewMap, {
    attachTo: document.body,
    global: { plugins: [i18n], stubs: { VIcon: true } }
  })
  await flushPromises()
  return wrapper
}

/** Mount, load the data and draw the markers once. */
async function mountReady() {
  const wrapper = await mountMap()
  const map = fake.FakeMap.last!
  map.features = features()
  map.fire('load')
  map.fire('render')
  await flushPromises()
  return { wrapper, map }
}

function markerFor(label: string): HTMLElement {
  const marker = fake.FakeMarker.added.find((m) =>
    m.element.getAttribute('aria-label')?.startsWith(label)
  )
  if (!marker) throw new Error(`no marker for ${label}`)
  return marker.element
}

describe('OverviewMap', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    fake.FakeMap.last = null
    fake.FakeMap.fail = false
    fake.FakeMarker.added = []
    width = 900
    getMapSites.mockResolvedValue({ data: { sites: SITES, skipped: 4 } })
    vi.stubGlobal(
      'ResizeObserver',
      class {
        observe() {}
        disconnect() {}
      }
    )
    vi.stubGlobal('matchMedia', (query: string) => ({
      matches: false,
      media: query,
      addEventListener() {},
      removeEventListener() {}
    }))
    // jsdom does no layout, so every width would be 0 and the map compact.
    vi.spyOn(HTMLElement.prototype, 'clientWidth', 'get').mockImplementation(() => width)
    vi.spyOn(HTMLElement.prototype, 'clientHeight', 'get').mockImplementation(() => 600)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
    document.body.innerHTML = ''
  })

  it('adds the sites as a clustered source once the map has loaded', async () => {
    const { map } = await mountReady()

    expect(map.addSource).toHaveBeenCalledTimes(1)
    const [id, spec] = map.addSource.mock.calls[0] as [string, Record<string, unknown>]
    expect(id).toBe(SITES_SOURCE)
    expect(spec.cluster).toBe(true)
    expect(Object.keys(spec.clusterProperties as object).sort()).toEqual(
      Array.from({ length: 9 }, (_, i) => `t${i}`).sort()
    )
    expect((spec.data as { features: unknown[] }).features).toHaveLength(3)
  })

  it('draws one marker per site or cluster, and keeps them on the next frame', async () => {
    const { map } = await mountReady()

    expect(fake.FakeMarker.added).toHaveLength(2)
    expect(markerFor('EPFL').textContent).toContain('EPFL')
    expect(markerFor('2 sites').classList.contains('mg-cluster')).toBe(true)

    map.fire('render')
    expect(fake.FakeMarker.added).toHaveLength(2)
  })

  it('shows the totals and the tests left out', async () => {
    const { wrapper } = await mountReady()
    const caption = wrapper.find('.om-tr').text()
    expect(caption).toContain('3 sites')
    expect(caption).toContain('47 tests')
    expect(caption).toContain('4 tests without coordinates')
  })

  it('filters the source from the legend', async () => {
    const { wrapper } = await mountReady()

    await wrapper.findAll('.ml-lg')[0].trigger('click')

    expect(fake.setData).toHaveBeenCalledTimes(1)
    const data = fake.setData.mock.calls[0][0] as { features: { properties: { sid: string } }[] }
    expect(data.features.map((f) => f.properties.sid)).toEqual(['46.52,6.57', '37.87,-122.24'])
    expect(wrapper.find('.om-tr').text()).toContain('2 sites')
  })

  it('opens the site in the side panel on a marker click', async () => {
    const { wrapper } = await mountReady()
    expect(wrapper.find('.om-panel').exists()).toBe(false)

    markerFor('EPFL').click()
    await flushPromises()

    const panel = wrapper.find('.om-panel')
    expect(panel.exists()).toBe(true)
    expect(panel.text()).toContain('EPFL')
    expect(panel.text()).toContain('2 programs')
    expect(markerFor('EPFL').classList.contains('is-sel')).toBe(true)
  })

  it('zooms to a cluster and lists its sites', async () => {
    const { wrapper, map } = await mountReady()
    fake.getClusterLeaves.mockResolvedValue([
      { properties: { sid: '35.03,135.78' } },
      { properties: { sid: '37.87,-122.24' } }
    ])

    markerFor('2 sites').click()
    await flushPromises()

    expect(fake.getClusterLeaves).toHaveBeenCalledWith(7, Infinity, 0)
    expect(map.fitBounds).toHaveBeenLastCalledWith(
      expect.objectContaining({
        points: [
          [135.78, 35.03],
          [-122.24, 37.87]
        ]
      }),
      expect.objectContaining({ maxZoom: 8 })
    )
    const panel = wrapper.find('.om-panel').text()
    expect(panel).toContain('Kyoto University')
    expect(panel).toContain('UC Berkeley')
  })

  it('uses the bottom sheet and the chips in a narrow frame', async () => {
    width = 420
    const { wrapper } = await mountReady()

    expect(wrapper.find('.ml-chips').exists()).toBe(true)
    markerFor('EPFL').click()
    await flushPromises()
    expect(wrapper.find('.om-panel').exists()).toBe(false)
    expect(wrapper.find('.ms').text()).toContain('EPFL')
  })

  it('says so when the browser has no WebGL', async () => {
    fake.FakeMap.fail = true
    const wrapper = await mountMap()
    expect(wrapper.find('.om-state').text()).toContain('WebGL is off')
    expect(wrapper.find('.om-ctrl').exists()).toBe(false)
  })
})
