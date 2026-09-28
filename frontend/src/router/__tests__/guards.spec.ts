import { resolveGuard } from '@/router/guards'
import { describe, expect, it } from 'vitest'
import type { RouteLocationNormalized } from 'vue-router'

/** Just enough of a route for the guard, which only reads meta and fullPath. */
function route(
  auth?: string,
  fullPath = '/contribute/new',
  contributions = false
): RouteLocationNormalized {
  const meta = { ...(auth ? { auth } : {}), ...(contributions ? { contributions } : {}) }
  return { fullPath, meta } as unknown as RouteLocationNormalized
}

describe('resolveGuard', () => {
  it('lets anyone into a page without meta.auth', () => {
    expect(resolveGuard(route(undefined, '/braces/database'), null, true)).toBe(true)
  })

  it('sends a visitor to sign in, remembering where they were going', () => {
    expect(resolveGuard(route('viewer'), null, true)).toEqual({
      name: 'Login',
      query: { next: '/contribute/new' }
    })
  })

  it('lets a signed-in user into a viewer page', () => {
    expect(resolveGuard(route('viewer'), { role: 'viewer' }, true)).toBe(true)
  })

  it('lets a stronger role into a weaker page', () => {
    expect(resolveGuard(route('contributor'), { role: 'admin' }, true)).toBe(true)
  })

  it('stops a role that is too weak, without asking them to sign in again', () => {
    expect(resolveGuard(route('curator', '/curation'), { role: 'contributor' }, true)).toEqual({
      name: 'Forbidden',
      query: { next: '/curation', need: 'curator' }
    })
  })

  it('sends a viewer away from the contribution editor (#248)', () => {
    expect(resolveGuard(route('contributor'), { role: 'viewer' }, true)).toEqual({
      name: 'Forbidden',
      query: { next: '/contribute/new', need: 'contributor' }
    })
  })

  it('treats a missing role as the weakest one', () => {
    expect(resolveGuard(route('contributor'), {}, true)).toEqual({
      name: 'Forbidden',
      query: { next: '/contribute/new', need: 'contributor' }
    })
  })

  it('sends a contribution route home when contributions are off', () => {
    for (const [auth, path] of [
      ['contributor', '/contribute/new'],
      ['curator', '/curation'],
      [undefined, '/login'],
      ['viewer', '/account']
    ] as const) {
      expect(resolveGuard(route(auth, path, true), { role: 'admin' }, false)).toEqual({
        path: '/',
        replace: true
      })
    }
  })

  it('lets a public page through even when contributions are off', () => {
    expect(resolveGuard(route(undefined, '/braces/database'), null, false)).toBe(true)
  })

  it('checks the flag before asking to sign in', () => {
    // A visitor on a switched-off deployment must not land on a sign-in page
    // that does not exist there either.
    expect(resolveGuard(route('contributor', '/contribute/new', true), null, false)).toEqual({
      path: '/',
      replace: true
    })
  })

  it('leaves a contribution route alone when contributions are on', () => {
    expect(resolveGuard(route('viewer', '/account', true), null, true)).toEqual({
      name: 'Login',
      query: { next: '/account' }
    })
  })
})
