/**
 * The EPFL cookie banner (index.html loads it from www.epfl.ch, #264).
 *
 * The banner is Osano cookieconsent v3, set up by EPFL with one "OK" button.
 * It sends no event and has no callback we can hook into. The only trace of
 * the answer is the `petitpois` cookie, set on the registrable domain
 * (epfl.ch), with the value `dismiss` after "OK". Scroll, timeout and clicks
 * outside the banner do not answer it, only its own buttons do.
 *
 * The dev server strips the banner (vite.config.ts), so in dev there is no
 * cookie and the callbacks below never run.
 */

const CONSENT_COOKIE = 'petitpois'

// The same rule as `hasConsented` in the banner script.
const CONSENT_VALUES = ['allow', 'dismiss']

function readCookie(name: string): string | undefined {
  const prefix = `${name}=`
  for (const part of document.cookie.split('; ')) {
    if (part.startsWith(prefix)) {
      return part.slice(prefix.length)
    }
  }
  return undefined
}

export function hasCookieConsent(): boolean {
  const value = readCookie(CONSENT_COOKIE)
  return value !== undefined && CONSENT_VALUES.includes(value)
}

/**
 * Calls `callback` once the visitor accepted the banner: now if the cookie
 * is already there, if not after the click that writes it.
 *
 * The banner writes the cookie in its own click handler, on the banner
 * element. A click listener on `document` (bubble phase) runs after it, so
 * the cookie is there when we read it. This way we need no polling and no
 * banner class names.
 */
export function onCookieConsent(callback: () => void): void {
  if (hasCookieConsent()) {
    callback()
    return
  }
  const onClick = (): void => {
    if (hasCookieConsent()) {
      document.removeEventListener('click', onClick)
      callback()
    }
  }
  document.addEventListener('click', onClick)
}

/**
 * index.html loads the banner stylesheet with `media="print"`, so it does not
 * block the first paint. This switches it to `all` once it is loaded. It used
 * to be an inline `onload` in index.html, which the CSP had to allow with a
 * hash (#264 M2).
 */
export function showConsentStylesheet(): void {
  const link = document.querySelector<HTMLLinkElement>('link[href$="epfl-cookie-consent.css"]')
  if (!link) {
    return
  }
  if (link.sheet) {
    link.media = 'all'
    return
  }
  link.addEventListener('load', () => {
    link.media = 'all'
  })
}
