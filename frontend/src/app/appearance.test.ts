import { afterEach, expect, test } from 'vitest'

import {
  APPEARANCE_STORAGE_KEY,
  applyAppearance,
  persistAppearance,
  resolveTheme,
  savedAppearance,
} from './appearance'

afterEach(() => {
  window.localStorage.clear()
  delete document.documentElement.dataset.theme
})

test('defaults to Light when no saved preference exists', () => {
  expect(savedAppearance()).toBe('light')
  expect(applyAppearance('light', document.documentElement, false)).toBe('light')
  expect(document.documentElement.dataset.theme).toBe('light')
})

test('persists explicit Light and Dark selections', () => {
  persistAppearance('light')
  expect(window.localStorage.getItem(APPEARANCE_STORAGE_KEY)).toBe('light')
  persistAppearance('dark')
  expect(savedAppearance()).toBe('dark')
  applyAppearance('dark', document.documentElement, false)
  expect(document.documentElement.dataset.theme).toBe('dark')
})

test('System resolves with the current system preference', () => {
  expect(resolveTheme('system', false)).toBe('light')
  expect(resolveTheme('system', true)).toBe('dark')
})

test('restores a saved System preference', () => {
  window.localStorage.setItem(APPEARANCE_STORAGE_KEY, 'system')
  expect(savedAppearance()).toBe('system')
  expect(applyAppearance(savedAppearance(), document.documentElement, true)).toBe('dark')
})
