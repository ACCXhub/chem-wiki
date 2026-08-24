import { afterEach, expect, test, vi } from 'vitest'

afterEach(() => {
  vi.unstubAllGlobals()
  vi.resetModules()
})


test('loads the canonical periodic table from the stable API boundary', async () => {
  const payload = [{ atomicNumber: 1, symbol: 'H' }]
  const fetchStub = vi.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve(payload),
  })
  vi.stubGlobal('fetch', fetchStub)
  const { loadPeriodicTableElements } = await import('./api')

  const first = loadPeriodicTableElements()
  const second = loadPeriodicTableElements()

  await expect(first).resolves.toEqual(payload)
  await expect(second).resolves.toEqual(payload)
  expect(fetchStub).toHaveBeenCalledTimes(1)
  expect(fetchStub).toHaveBeenCalledWith('/v1/elements', {
    headers: { Accept: 'application/json' },
  })
})


test('reports an API failure instead of rendering fabricated element data', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 503 }))
  const { loadPeriodicTableElements } = await import('./api')

  await expect(loadPeriodicTableElements()).rejects.toThrow(
    '周期表数据加载失败（HTTP 503）',
  )
})
