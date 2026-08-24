import { render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'

import App from './App'

test('renders the M03 periodic-table entry and its loading state', () => {
  vi.stubGlobal('fetch', vi.fn(() => new Promise(() => undefined)))
  render(<App />)

  expect(
    screen.getByRole('heading', {
      level: 1,
      name: '高中化学交互式 Wiki',
    }),
  ).toBeInTheDocument()
  expect(screen.getByText('正在读取 canonical 元素数据…')).toBeInTheDocument()
})
