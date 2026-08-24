import { render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'

import type { ElementWikiPage } from './types'


const page: ElementWikiPage = {
  identity: {
    id: '12345678-1234-5678-1234-567812345678',
    atomicNumber: 17,
    symbol: 'Cl',
    nameZh: '氯',
    nameEn: 'chlorine',
    status: 'confirmed',
  },
  classification: {
    category: 'halogen',
    period: 3,
    group: 17,
    block: 'p',
  },
  properties: [
    {
      key: 'atomicWeight',
      label: '相对原子质量',
      status: 'missing',
      value: null,
      lower: null,
      upper: null,
      unit: null,
      qualifier: null,
      uncertainty: null,
      sourceKeys: [],
    },
    {
      key: 'firstIonizationEnergy',
      label: '第一电离能',
      status: 'available',
      value: 12.968,
      lower: null,
      upper: null,
      unit: 'eV',
      qualifier: null,
      uncertainty: null,
      sourceKeys: ['nist-asd'],
    },
  ],
  sections: {
    ions: [],
    substances: [],
    reactions: [],
    phenomena: [],
    concepts: [],
    questions: [],
  },
  graph: {
    centerNodeId: '12345678-1234-5678-1234-567812345678',
    nodes: [
      {
        id: '12345678-1234-5678-1234-567812345678',
        type: 'Element',
        label: '氯 Cl',
        secondaryLabel: '原子序数 17',
        href: '/elements/12345678-1234-5678-1234-567812345678',
      },
    ],
    edges: [],
    emptyReason: '暂无已审核的相关物质、反应或概念数据',
  },
  sources: [
    {
      key: 'nist-asd',
      title: 'NIST Atomic Spectra Database',
      publisher: 'NIST',
      url: 'https://physics.nist.gov/asd',
      licenseCode: null,
      retrievedAt: '2026-08-24T00:00:00Z',
      fields: ['firstIonizationEnergy'],
    },
  ],
}


test('renders structured identity, calibrated properties, sources, and honest graph gaps', async () => {
  const { ElementWikiView } = await import('./ElementWiki')
  render(<ElementWikiView page={page} onBack={vi.fn()} />)

  expect(screen.getByRole('heading', { level: 1, name: '氯' })).toBeInTheDocument()
  expect(screen.getByText('Cl')).toBeInTheDocument()
  expect(screen.getByText('卤素')).toBeInTheDocument()
  expect(screen.getByText('12.968')).toBeInTheDocument()
  expect(screen.getByText('eV')).toBeInTheDocument()
  expect(screen.getByText('相对原子质量').closest('article')).toHaveTextContent(
    '暂无数据',
  )
  expect(screen.getByRole('heading', { name: '相关物质' })).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: '相关反应' })).toBeInTheDocument()
  expect(screen.getByText('暂无已审核的相关物质、反应或概念数据')).toBeInTheDocument()
  expect(
    screen.getByRole('link', { name: 'NIST Atomic Spectra Database' }),
  ).toHaveAttribute('href', 'https://physics.nist.gov/asd')
  expect(screen.queryByText(/raw_payload|claim_id|selection_reason/i)).not.toBeInTheDocument()
})
