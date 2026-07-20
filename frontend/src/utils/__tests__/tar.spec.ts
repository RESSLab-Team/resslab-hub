import { buildTar } from '@/utils/tar'
import { describe, expect, it } from 'vitest'

const BLOCK = 512
const decoder = new TextDecoder()

/** Read a NUL/space-terminated ustar header field. */
function field(archive: Uint8Array, offset: number, length: number): string {
  return decoder.decode(archive.subarray(offset, offset + length)).replace(/[\0 ]+$/, '')
}

describe('buildTar', () => {
  const archive = buildTar([{ path: 'braces/steel_braces.csv', content: 'id\nBRC-1\n' }])

  it('writes a ustar header describing the entry', () => {
    expect(field(archive, 0, 100)).toBe('braces/steel_braces.csv')
    expect(field(archive, 100, 8)).toBe('0000644')
    expect(parseInt(field(archive, 124, 12), 8)).toBe(9) // size, octal
    expect(archive[156]).toBe(0x30) // typeflag '0' — regular file
    expect(field(archive, 257, 6)).toBe('ustar')
    expect(field(archive, 263, 2)).toBe('00')
  })

  it('writes a checksum matching the header bytes', () => {
    const stored = parseInt(field(archive, 148, 8), 8)
    const header = archive.slice(0, BLOCK)
    header.fill(0x20, 148, 156)
    const computed = header.reduce((sum, byte) => sum + byte, 0)
    expect(stored).toBe(computed)
  })

  it('pads the body to a block and terminates with two zero blocks', () => {
    expect(archive.length).toBe(BLOCK * 4) // header + body + 2 terminators
    expect(decoder.decode(archive.subarray(BLOCK, BLOCK + 9))).toBe('id\nBRC-1\n')
    expect(archive.subarray(BLOCK * 2).every((byte) => byte === 0)).toBe(true)
  })

  it('lays entries out back to back', () => {
    const two = buildTar([
      { path: 'a.csv', content: 'a' },
      { path: 'b.csv', content: 'b' }
    ])
    expect(field(two, 0, 100)).toBe('a.csv')
    expect(field(two, BLOCK * 2, 100)).toBe('b.csv')
    expect(two.length).toBe(BLOCK * 6)
  })

  it('rejects a path too long for the ustar name field', () => {
    expect(() => buildTar([{ path: 'x'.repeat(101), content: '' }])).toThrow(RangeError)
  })
})
