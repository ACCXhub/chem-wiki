import { fireEvent, render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'

const elements = [
  {
    id: 'h-id',
    atomicNumber: 1,
    symbol: 'H',
    nameZh: '氢',
    nameEn: 'hydrogen',
    category: 'reactive-nonmetal',
    status: 'confirmed',
    layout: { period: 1, group: 1, row: 1, column: 1, block: 's' },
    properties: {
      electronegativity: { value: 2.2, unit: 'Pauling' },
      firstIonizationEnergy: { value: 13.598, unit: 'eV' },
    },
  },
  {
    id: 'he-id',
    atomicNumber: 2,
    symbol: 'He',
    nameZh: '氦',
    nameEn: 'helium',
    category: 'noble-gas',
    status: 'confirmed',
    layout: { period: 1, group: 18, row: 1, column: 18, block: 's' },
    properties: {
      electronegativity: { value: null, unit: null },
      firstIonizationEnergy: { value: 24.587, unit: 'eV' },
    },
  },
  {
    id: 'o-id',
    atomicNumber: 8,
    symbol: 'O',
    nameZh: '氧',
    nameEn: 'oxygen',
    category: 'reactive-nonmetal',
    status: 'confirmed',
    layout: { period: 2, group: 16, row: 2, column: 16, block: 'p' },
    properties: {
      electronegativity: { value: 3.44, unit: 'Pauling' },
      firstIonizationEnergy: { value: 13.618, unit: 'eV' },
    },
  },
] as const


test('click selects an element while hover provides a temporary preview', async () => {
  const { PeriodicTableView } = await import('./PeriodicTable')
  const onElementSelect = vi.fn()
  render(
    <PeriodicTableView
      elements={[...elements]}
      onElementSelect={onElementSelect}
    />,
  )

  fireEvent.click(screen.getByRole('button', { name: '2 氦 He' }))
  expect(screen.getByRole('heading', { name: '氦 He' })).toBeInTheDocument()
  expect(onElementSelect).toHaveBeenCalledWith('he-id')

  fireEvent.mouseEnter(screen.getByRole('button', { name: '8 氧 O' }))
  expect(screen.getByRole('heading', { name: '氧 O' })).toBeInTheDocument()

  fireEvent.mouseLeave(screen.getByRole('button', { name: '8 氧 O' }))
  expect(screen.getByRole('heading', { name: '氦 He' })).toBeInTheDocument()
  expect(screen.getByText('正式元素')).toBeInTheDocument()
})


test('property modes render a persistent heatmap legend and explicit missing values', async () => {
  const { PeriodicTableView } = await import('./PeriodicTable')
  render(<PeriodicTableView elements={[...elements]} />)

  fireEvent.click(screen.getByRole('button', { name: '电负性' }))

  expect(screen.getByRole('group', { name: '图例' })).toBeInTheDocument()
  expect(screen.getByText('低')).toBeInTheDocument()
  expect(screen.getByText('高')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: '2 氦 He' })).toHaveTextContent('暂无数据')

  fireEvent.click(screen.getByRole('button', { name: '第一电离能' }))
  expect(screen.getByRole('button', { name: '1 氢 H' })).toHaveTextContent('13.598')
  expect(screen.getByText('单位：eV')).toBeInTheDocument()
})


test('search locates by Chinese name, symbol, English name, or atomic number', async () => {
  const { PeriodicTableView } = await import('./PeriodicTable')
  const onElementSelect = vi.fn()
  render(
    <PeriodicTableView
      elements={[...elements]}
      onElementSelect={onElementSelect}
    />,
  )

  const input = screen.getByRole('searchbox', { name: '搜索元素' })
  fireEvent.change(input, { target: { value: 'oxygen' } })
  fireEvent.submit(input.closest('form')!)

  expect(screen.getByRole('heading', { name: '氧 O' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: '8 氧 O' })).toHaveFocus()
  expect(onElementSelect).toHaveBeenCalledWith('o-id')

  fireEvent.change(input, { target: { value: '999' } })
  fireEvent.submit(input.closest('form')!)
  expect(screen.getByRole('status')).toHaveTextContent('未找到匹配元素')
})
