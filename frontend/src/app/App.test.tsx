import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'


afterEach(() => {
  window.history.replaceState(null, '', '/')
  vi.unstubAllGlobals()
  vi.resetModules()
})

test('renders the periodic-table entry and its loading state', async () => {
  vi.stubGlobal('fetch', vi.fn(() => new Promise(() => undefined)))
  const { default: App } = await import('./App')
  render(<App />)

  expect(
    screen.getByRole('heading', {
      level: 1,
      name: '高中化学交互式 Wiki',
    }),
  ).toBeInTheDocument()
  expect(screen.getByText('正在读取 canonical 元素数据…')).toBeInTheDocument()
})


test('selecting an M03 element navigates to its M04 Wiki UUID route', async () => {
  const elementId = '12345678-1234-5678-1234-567812345678'
  const periodicElement = {
    id: elementId,
    atomicNumber: 17,
    symbol: 'Cl',
    nameZh: '氯',
    nameEn: 'chlorine',
    category: 'halogen',
    status: 'confirmed',
    layout: { period: 3, group: 17, row: 3, column: 17, block: 'p' },
    properties: {
      electronegativity: { value: 3.16, unit: 'Pauling' },
      firstIonizationEnergy: { value: 12.968, unit: 'eV' },
    },
  }
  const wikiPage = {
    identity: {
      id: elementId,
      atomicNumber: 17,
      symbol: 'Cl',
      nameZh: '氯',
      nameEn: 'chlorine',
      status: 'confirmed',
    },
    classification: { category: 'halogen', period: 3, group: 17, block: 'p' },
    properties: [],
    sections: {
      ions: [],
      substances: [],
      reactions: [],
      phenomena: [],
      concepts: [],
      questions: [],
    },
    graph: {
      centerNodeId: elementId,
      nodes: [{ id: elementId, type: 'Element', label: '氯 Cl' }],
      edges: [],
      emptyReason: '暂无已审核的相关物质、反应或概念数据',
    },
    sources: [],
  }
  vi.stubGlobal(
    'fetch',
    vi.fn((input: string | URL | Request) => {
      const url = String(input)
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(url === '/v1/elements' ? [periodicElement] : wikiPage),
      })
    }),
  )
  const { default: App } = await import('./App')
  render(<App />)

  fireEvent.click(await screen.findByRole('button', { name: '17 氯 Cl' }))

  expect(window.location.pathname).toBe(`/elements/${elementId}`)
  expect(await screen.findByRole('heading', { level: 1, name: '氯' })).toBeInTheDocument()
})
