import type { CatalogSpecies } from './types'

const STORAGE_KEY = 'chem-wiki.equation-lab.palette-preferences.v1'
const MAX_RECENTS = 8

export interface PalettePreferences {
  favorites: string[]
  recents: string[]
}

const EMPTY_PREFERENCES: PalettePreferences = { favorites: [], recents: [] }

function uniqueIds(values: unknown): string[] {
  if (!Array.isArray(values)) return []
  return [...new Set(values.filter((value): value is string => typeof value === 'string'))]
}

export function loadPalettePreferences(storage: Storage = window.localStorage): PalettePreferences {
  try {
    const parsed: unknown = JSON.parse(storage.getItem(STORAGE_KEY) ?? 'null')
    if (!parsed || typeof parsed !== 'object') return EMPTY_PREFERENCES
    const value = parsed as { version?: unknown; favorites?: unknown; recents?: unknown }
    if (value.version !== 1) return EMPTY_PREFERENCES
    return { favorites: uniqueIds(value.favorites), recents: uniqueIds(value.recents).slice(0, MAX_RECENTS) }
  } catch {
    return EMPTY_PREFERENCES
  }
}

export function savePalettePreferences(
  preferences: PalettePreferences,
  storage: Storage = window.localStorage,
): void {
  storage.setItem(STORAGE_KEY, JSON.stringify({ version: 1, ...preferences }))
}

export function togglePaletteFavorite(
  preferences: PalettePreferences,
  applicationId: string,
): PalettePreferences {
  const exists = preferences.favorites.includes(applicationId)
  return {
    ...preferences,
    favorites: exists
      ? preferences.favorites.filter((id) => id !== applicationId)
      : [applicationId, ...preferences.favorites],
  }
}

export function recordPaletteRecent(
  preferences: PalettePreferences,
  applicationId: string,
): PalettePreferences {
  return {
    ...preferences,
    recents: [applicationId, ...preferences.recents.filter((id) => id !== applicationId)]
      .slice(0, MAX_RECENTS),
  }
}

export function resolvePaletteSpecies(
  species: CatalogSpecies[],
  applicationIds: string[],
): CatalogSpecies[] {
  const byApplicationId = new Map(species.map((item) => [item.applicationId, item]))
  return applicationIds.flatMap((id) => {
    const item = byApplicationId.get(id)
    return item ? [item] : []
  })
}
