import { displaySymbol, symbolHtml, type DictColumn } from '@/stores/dictionary'
import { describe, expect, it } from 'vitest'

function column(symbol: string): DictColumn {
  return {
    name: 'f_y',
    description: '',
    symbol,
    unit: 'MPa',
    type: 'Numeric',
    example: '',
    nullable: true
  }
}

describe('dictionary.displaySymbol', () => {
  it('drops the markdown backticks and the no-symbol sentinel', () => {
    expect(displaySymbol(column('`f_{y,n}`'))).toBe('f_{y,n}')
    expect(displaySymbol(column(' F<sub>y</sub> '))).toBe('F<sub>y</sub>')
    expect(displaySymbol(column('-'))).toBeUndefined()
    expect(displaySymbol(column(''))).toBeUndefined()
  })
})

describe('dictionary.symbolHtml', () => {
  it('keeps the formatting tags', () => {
    expect(symbolHtml('F<sub>y</sub>')).toBe('F<sub>y</sub>')
    expect(symbolHtml('L<sup>2</sup>')).toBe('L<sup>2</sup>')
    expect(symbolHtml('<i>t</i><em>f</em>')).toBe('<i>t</i><em>f</em>')
    expect(symbolHtml(undefined)).toBe('')
  })

  it('drops scripts, handlers and links from the data (#264)', () => {
    expect(symbolHtml('F<img src=x onerror="alert(1)">y')).toBe('Fy')
    expect(symbolHtml('<script>alert(1)</script>F')).toBe('F')
    expect(symbolHtml('<a href="javascript:alert(1)">F</a>')).toBe('F')
    expect(symbolHtml('<sub onclick="alert(1)">y</sub>')).toBe('<sub>y</sub>')
    expect(symbolHtml('<svg onload="alert(1)">F</svg>')).toBe('')
  })
})
