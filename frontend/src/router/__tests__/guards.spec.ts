import { resolveGuard } from '@/router/guards'
import { describe, expect, it } from 'vitest'
import type { RouteLocationNormalized } from 'vue-router'

/** Just enough of a route for the guard, which only reads meta and fullPath. */
function route(auth?: string, fullPath = '/contribute/new'): RouteLocationNormalized {
  return { fullPath, meta: auth ? { auth } : {} } as unknown as RouteLocationNormalized
}

describe('resolveGuard', () => {
  it('lets anyone into a page without meta.auth', () => {
    expect(resolveGuard(route(undefined, '/braces/database'), null)).toBe(true)
  })

  it('sends a visitor to sign in, remembering where they were going', () => {
    expect(resolveGuard(route('viewer'), null)).toEqual({
      name: 'Login',
      query: { next: '/contribute/new' }
    })
  })

  it('lets a signed-in user into a viewer page', () => {
    expect(resolveGuard(route('viewer'), { role: 'viewer' })).toBe(true)
  })

  it('lets a stronger role into a weaker page', () => {
    expect(resolveGuard(route('contributor'), { role: 'admin' })).toBe(true)
  })

  it('stops a role that is too weak, without asking them to sign in again', () => {
    expect(resolveGuard(route('curator', '/curation'), { role: 'contributor' })).toEqual({
      name: 'Forbidden',
      query: { next: '/curation', need: 'curator' }
    })
  })

  it('treats a missing role as the weakest one', () => {
    expect(resolveGuard(route('contributor'), {})).toEqual({
      name: 'Forbidden',
      query: { next: '/contribute/new', need: 'contributor' }
    })
  })
})
