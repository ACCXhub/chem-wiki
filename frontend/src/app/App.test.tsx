import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'

import App from './App'

test('renders the application title', () => {
  render(<App />)

  expect(
    screen.getByRole('heading', {
      level: 1,
      name: '高中化学交互式 Wiki',
    }),
  ).toBeInTheDocument()
})
