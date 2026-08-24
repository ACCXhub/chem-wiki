import { afterEach, expect, test, vi } from 'vitest'


afterEach(() => {
  vi.unstubAllGlobals()
})


test('loads an Element Wiki page through the stable UUID route', async () => {
  const payload = { identity: { symbol: 'Cl' } }
  const fetchStub = vi.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve(payload),
  })
  vi.stubGlobal('fetch', fetchStub)
  const { loadElementWiki } = await import('./api')

  await expect(loadElementWiki('element-id')).resolves.toEqual(payload)
  expect(fetchStub).toHaveBeenCalledWith('/v1/elements/element-id', {
    headers: { Accept: 'application/json' },
  })
})


test('reports a missing element without fabricating detail content', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 404 }))
  const { loadElementWiki } = await import('./api')

  await expect(loadElementWiki('missing-id')).rejects.toThrow(
    '元素详情加载失败（HTTP 404）',
  )
})
