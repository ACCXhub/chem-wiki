import { afterEach, expect, test, vi } from 'vitest'

import { analyzeStructure } from './api'


afterEach(() => vi.unstubAllGlobals())

test('posts a library-neutral structure representation to the M06 boundary', async () => {
  const payload = { state: 'valid', canonicalSmiles: 'CCO', formula: 'C2H6O' }
  const fetchMock = vi.fn(() => Promise.resolve({
    ok: true,
    json: () => Promise.resolve(payload),
  }))
  vi.stubGlobal('fetch', fetchMock)

  await expect(analyzeStructure('smiles', 'CCO')).resolves.toBe(payload)
  expect(fetchMock).toHaveBeenCalledWith('/v1/structures/analyze', {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify({ format: 'smiles', text: 'CCO' }),
  })
})
test('surfaces an HTTP boundary error without fabricating chemistry results', async () => {
  vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({
    ok: false,
    status: 503,
    json: () => Promise.resolve({ detail: { message: '化学引擎暂不可用' } }),
  })))

  await expect(analyzeStructure('smiles', 'CCO')).rejects.toThrow('化学引擎暂不可用')
})
