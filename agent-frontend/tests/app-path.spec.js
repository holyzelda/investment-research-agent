import { describe, expect, it } from 'vitest'
import { appUrl, currentRouteLocation, loginUrl } from '@/utils/appPath'

describe('application base path helpers', () => {
  it('adds the investment prefix to browser-level app URLs', () => {
    expect(appUrl('/login')).toBe('/investment/login')
    expect(appUrl('/reports/42?download=1')).toBe('/investment/reports/42?download=1')
  })

  it('removes the investment prefix from the current router location', () => {
    expect(currentRouteLocation({
      pathname: '/investment/home',
      search: '?conversation=7',
      hash: '#result',
    })).toBe('/home?conversation=7#result')
  })

  it('builds a prefixed login URL without duplicating the app prefix', () => {
    expect(loginUrl({
      pathname: '/investment/home',
      search: '?conversation=7',
      hash: '',
    })).toBe('/investment/login?redirect=%2Fhome%3Fconversation%3D7')
  })
})
