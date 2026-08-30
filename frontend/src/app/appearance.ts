export const APPEARANCE_STORAGE_KEY = 'chem-wiki.appearance'

export type AppearanceMode = 'light' | 'dark' | 'system'
export type ResolvedTheme = 'light' | 'dark'

function isAppearanceMode(value: string | null): value is AppearanceMode {
  return value === 'light' || value === 'dark' || value === 'system'
}

export function systemTheme(matchesDark: boolean): ResolvedTheme {
  return matchesDark ? 'dark' : 'light'
}

export function resolveTheme(mode: AppearanceMode, matchesDark: boolean): ResolvedTheme {
  return mode === 'system' ? systemTheme(matchesDark) : mode
}

export function savedAppearance(storage: Storage = window.localStorage): AppearanceMode {
  try {
    const value = storage.getItem(APPEARANCE_STORAGE_KEY)
    return isAppearanceMode(value) ? value : 'light'
  } catch {
    return 'light'
  }
}

export function applyAppearance(
  mode: AppearanceMode,
  documentElement: HTMLElement = document.documentElement,
  matchesDark = window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false,
): ResolvedTheme {
  const theme = resolveTheme(mode, matchesDark)
  documentElement.dataset.theme = theme
  return theme
}

export function persistAppearance(
  mode: AppearanceMode,
  storage: Storage = window.localStorage,
) {
  try {
    storage.setItem(APPEARANCE_STORAGE_KEY, mode)
  } catch {
    // A blocked private-mode storage must not prevent the app from rendering.
  }
}
