import { filterColumnValue, shareCurrentUrl, sum } from '@/utils/common'
import { afterEach, describe, expect, it, vi } from 'vitest'

describe('common.sum', () => {
  it('adds two numbers (used as a reduce seed)', () => {
    expect(sum(2, 3)).toBe(5)
    expect([1, 2, 3, 4].reduce(sum, 0)).toBe(10)
  })
})

describe('common.filterColumnValue', () => {
  it('drops null', () => {
    expect(filterColumnValue(null as unknown as string)).toBe(false)
  })

  it('keeps non-empty strings and drops empty ones', () => {
    expect(filterColumnValue('S355')).toBe(true)
    expect(filterColumnValue('')).toBe(false)
  })

  it('keeps non-empty arrays and drops empty ones', () => {
    expect(filterColumnValue(['a'])).toBe(true)
    expect(filterColumnValue([])).toBe(false)
  })

  it('always keeps booleans and numbers', () => {
    expect(filterColumnValue(false)).toBe(true)
    expect(filterColumnValue(0)).toBe(true)
    expect(filterColumnValue(42)).toBe(true)
  })
})

describe('common.shareCurrentUrl', () => {
  const origin = window.location.origin

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('prefers the native share sheet when available', () => {
    const share = vi.fn()
    vi.stubGlobal('navigator', { share })
    const notify = vi.fn()

    shareCurrentUrl('/columns?search=foo', notify)

    expect(share).toHaveBeenCalledWith({ url: `${origin}/columns?search=foo` })
    expect(notify).not.toHaveBeenCalled()
  })

  it('falls back to the clipboard and notifies the user', () => {
    const writeText = vi.fn()
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    const notify = vi.fn()

    shareCurrentUrl('/columns', notify)

    expect(writeText).toHaveBeenCalledWith(`${origin}/columns`)
    expect(notify).toHaveBeenCalledWith('Copied to clipboard')
  })

  it('falls back to a notification link when neither API exists', () => {
    vi.stubGlobal('navigator', {})
    const notify = vi.fn()

    shareCurrentUrl('/columns', notify)

    const url = `${origin}/columns`
    expect(notify).toHaveBeenCalledWith(url, url)
  })
})
