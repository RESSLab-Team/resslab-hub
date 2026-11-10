import { afterEach, describe, expect, it, vi } from 'vitest'

import { hasCookieConsent, onCookieConsent, showConsentStylesheet } from '../cookieConsent'

function setConsent(value: string): void {
  document.cookie = `petitpois=${value}; path=/`
}

function click(): void {
  document.body.dispatchEvent(new MouseEvent('click', { bubbles: true }))
}

afterEach(() => {
  document.cookie = 'petitpois=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/'
  document.head.innerHTML = ''
})

describe('hasCookieConsent', () => {
  it('is false without the cookie', () => {
    expect(hasCookieConsent()).toBe(false)
  })

  it('is true for dismiss and allow, false for deny', () => {
    setConsent('dismiss')
    expect(hasCookieConsent()).toBe(true)
    setConsent('allow')
    expect(hasCookieConsent()).toBe(true)
    setConsent('deny')
    expect(hasCookieConsent()).toBe(false)
  })

  it('does not take another cookie whose name ends the same way', () => {
    document.cookie = 'xpetitpois=dismiss; path=/'
    expect(hasCookieConsent()).toBe(false)
    document.cookie = 'xpetitpois=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/'
  })
})

describe('onCookieConsent', () => {
  it('runs at once when the cookie is already there', () => {
    setConsent('dismiss')
    const callback = vi.fn()
    onCookieConsent(callback)
    expect(callback).toHaveBeenCalledOnce()
  })

  it('waits while there is no answer, clicks included', () => {
    const callback = vi.fn()
    onCookieConsent(callback)
    click()
    click()
    expect(callback).not.toHaveBeenCalled()
  })

  it('runs once, on the click that writes the cookie', () => {
    const callback = vi.fn()
    onCookieConsent(callback)
    click()
    setConsent('dismiss')
    click()
    click()
    expect(callback).toHaveBeenCalledOnce()
  })

  it('does not run when the answer is deny', () => {
    const callback = vi.fn()
    onCookieConsent(callback)
    setConsent('deny')
    click()
    expect(callback).not.toHaveBeenCalled()
  })
})

describe('showConsentStylesheet', () => {
  it('switches the banner stylesheet to all once it is loaded', () => {
    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = 'https://www.epfl.ch/css/epfl-cookie-consent.css'
    link.media = 'print'
    document.head.appendChild(link)

    showConsentStylesheet()
    expect(link.media).toBe('print')
    link.dispatchEvent(new Event('load'))
    expect(link.media).toBe('all')
  })

  it('does nothing when the page has no banner stylesheet', () => {
    expect(() => showConsentStylesheet()).not.toThrow()
  })
})
