import {
  filterColumnValue,
  isHttpUrl,
  isStructuredFilterValue,
  shareCurrentUrl,
  sum
} from '@/utils/common'
import { afterEach, describe, expect, it, vi } from 'vitest'

describe('common.isHttpUrl', () => {
  it('accepts web addresses only', () => {
    expect(isHttpUrl('https://doi.org/10.1000/xyz')).toBe(true)
    expect(isHttpUrl(' http://example.org ')).toBe(true)
  })

  it('rejects the markers the CSVs put in the link column', () => {
    for (const marker of [
      'NA',
      'NR',
      'TBA',
      'Not available',
      'Not applicable',
      '',
      null,
      undefined
    ]) {
      expect(isHttpUrl(marker)).toBe(false)
    }
  })

  it('rejects links that are not web addresses (#264)', () => {
    for (const link of [
      'javascript:alert(1)',
      'JavaScript:alert(1)',
      ' javascript:alert(1)',
      'java\tscript:alert(1)',
      'data:text/html,<script>alert(1)</script>',
      'vbscript:msgbox(1)',
      '//evil.example/x',
      'ftp://example.org/file',
      'https:evil.example',
      42,
      { href: 'https://example.org' }
    ]) {
      expect(isHttpUrl(link)).toBe(false)
    }
  })
})

describe('common.isStructuredFilterValue', () => {
  it('recognises the grammar the rail inputs emit', () => {
    expect(isStructuredFilterValue('=RBS')).toBe(true)
    expect(isStructuredFilterValue(['RBS', 'WUF-W'])).toBe(true)
    expect(isStructuredFilterValue('20<<80')).toBe(true)
  })

  it('treats typed text, numbers and empty values as unstructured', () => {
    expect(isStructuredFilterValue('RBS')).toBe(false)
    expect(isStructuredFilterValue('0.17')).toBe(false)
    expect(isStructuredFilterValue(42)).toBe(false)
    expect(isStructuredFilterValue('')).toBe(false)
    expect(isStructuredFilterValue([])).toBe(false)
    expect(isStructuredFilterValue(undefined)).toBe(false)
  })
})

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
