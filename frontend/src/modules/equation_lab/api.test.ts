import { afterEach, expect, test, vi } from 'vitest'

import {
  balanceEquation,
  completeCatalogSpecies,
  findReactionCandidates,
  loadReactionDetail,
  searchCatalogSpecies,
} from './api'


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

test('posts structured material anchors to the M07 candidate boundary', async () => {
  const candidate = { consolidatedId: 'reaction:water' }
  const fetchMock = vi.fn(() => Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ candidates: [candidate] }),
  }))
  vi.stubGlobal('fetch', fetchMock)

  await expect(findReactionCandidates({
    reactantApplicationIds: ['h2', 'o2'],
    productApplicationIds: ['h2o'],
  })).resolves.toEqual([candidate])
  expect(fetchMock).toHaveBeenCalledWith('/v1/reaction-builder/candidates', {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify({
      reactantApplicationIds: ['h2', 'o2'],
      productApplicationIds: ['h2o'],
    }),
    signal: undefined,
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

test('passes controlled composition resolution facts to the existing catalog endpoint', async () => {
  const fetchMock = vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve([]) }))
  vi.stubGlobal('fetch', fetchMock)

  await searchCatalogSpecies({
    equationMode: 'ionic',
    composition: { Na: 2, O: 4, S: 1 },
    charge: 0,
    entityKind: 'substance',
  })

  expect(fetchMock).toHaveBeenCalledWith(
    '/v1/catalog/species?equation_mode=ionic&limit=50&composition=%7B%22Na%22%3A2%2C%22O%22%3A4%2C%22S%22%3A1%7D&charge=0&entity_kind=substance',
    { headers: { Accept: 'application/json' }, signal: undefined },
  )
})

test('queries the backend-owned composition completion endpoint without partial charge', async () => {
  const payload = [{ consolidatedId: 'species:strontium-sulfate', formula: 'SrSO4' }]
  const fetchMock = vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve(payload) }))
  vi.stubGlobal('fetch', fetchMock)

  await expect(completeCatalogSpecies({
    composition: { O: 4, S: 1, Sr: 1 },
    equationMode: 'molecular',
  })).resolves.toBe(payload)

  expect(fetchMock).toHaveBeenCalledWith(
    '/v1/catalog/species/completions?composition=%7B%22O%22%3A4%2C%22S%22%3A1%2C%22Sr%22%3A1%7D&entity_kind=substance&limit=50&equation_mode=molecular',
    { headers: { Accept: 'application/json' }, signal: undefined },
  )
})

test('loads reviewed reaction detail from its catalog boundary', async () => {
  const payload = { consolidatedId: 'reaction:agno3-nacl', concepts: [], phenomena: [] }
  const fetchMock = vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve(payload) }))
  vi.stubGlobal('fetch', fetchMock)

  await expect(loadReactionDetail('reaction:agno3-nacl')).resolves.toBe(payload)
  expect(fetchMock).toHaveBeenCalledWith(
    '/v1/catalog/reactions/reaction%3Aagno3-nacl/detail',
    { headers: { Accept: 'application/json' }, signal: undefined },
  )
})

test('serializes saved palette identities as repeated exact catalog query parameters', async () => {
  const fetchMock = vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve([]) }))
  vi.stubGlobal('fetch', fetchMock)

  await searchCatalogSpecies({
    applicationIds: ['saved-water', 'saved-long-tail'],
    equationMode: 'molecular',
    limit: 50,
  })

  expect(fetchMock).toHaveBeenCalledWith(
    '/v1/catalog/species?equation_mode=molecular&limit=50&application_id=saved-water&application_id=saved-long-tail',
    { headers: { Accept: 'application/json' }, signal: undefined },
  )
})
