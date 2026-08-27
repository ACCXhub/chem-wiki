import { afterEach, expect, test, vi } from 'vitest'

import { balanceEquation, searchCatalogSpecies } from './api'


afterEach(() => vi.unstubAllGlobals())

test('posts the equation mode to the M05 balance boundary', async () => {
  const payload = { state: 'balanced', formattedEquation: '2H₂ + O₂ → 2H₂O' }
  const fetchMock = vi.fn(() =>
    Promise.resolve({ ok: true, json: () => Promise.resolve(payload) }),
  )
  vi.stubGlobal('fetch', fetchMock)

  await expect(balanceEquation('H2 + O2 -> H2O', 'molecular')).resolves.toBe(payload)
  expect(fetchMock).toHaveBeenCalledWith('/v1/reactions/balance', {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify({ equation: 'H2 + O2 -> H2O', mode: 'molecular' }),
  })
})

test('surfaces the Chinese domain error from an invalid equation', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 400,
        json: () =>
          Promise.resolve({ detail: { state: 'invalid', message: '方程式没有非零守恒解' } }),
      }),
    ),
  )

  await expect(balanceEquation('H2 -> H2O', 'molecular')).rejects.toThrow(
    '方程式没有非零守恒解',
  )
})

test('queries the catalog with combined search, category and equation mode filters', async () => {
  const payload = [{ consolidatedId: 'species:inorganic:ion:sulfate', formula: 'SO4' }]
  const fetchMock = vi.fn(() =>
    Promise.resolve({ ok: true, json: () => Promise.resolve(payload) }),
  )
  vi.stubGlobal('fetch', fetchMock)

  await expect(searchCatalogSpecies({
    query: 'sulfate',
    primaryCategory: 'anion',
    equationMode: 'ionic',
    limit: 50,
  })).resolves.toBe(payload)

  expect(fetchMock).toHaveBeenCalledWith(
    '/v1/catalog/species?equation_mode=ionic&limit=50&q=sulfate&primary_category=anion',
    { headers: { Accept: 'application/json' }, signal: undefined },
  )
})
