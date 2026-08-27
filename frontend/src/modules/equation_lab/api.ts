import type {
  BalanceEquationResponse,
  CatalogSpecies,
  CatalogSpeciesQuery,
  EquationMode,
} from './types'


interface ErrorPayload {
  detail?: { message?: string } | string
}

function apiError(payload: ErrorPayload | null, status: number, fallback: string): Error {
  const detail = payload?.detail
  const message = typeof detail === 'string'
    ? detail
    : detail?.message ?? `${fallback}（HTTP ${status}）`
  return new Error(message)
}

export async function searchCatalogSpecies(
  query: CatalogSpeciesQuery,
  signal?: AbortSignal,
): Promise<CatalogSpecies[]> {
  const parameters = new URLSearchParams({
    equation_mode: query.equationMode,
    limit: String(query.limit ?? 50),
  })
  const normalizedQuery = query.query?.trim()
  if (normalizedQuery) parameters.set('q', normalizedQuery)
  if (query.primaryCategory) parameters.set('primary_category', query.primaryCategory)

  const response = await fetch(`/v1/catalog/species?${parameters}`, {
    headers: { Accept: 'application/json' },
    signal,
  })
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as ErrorPayload | null
    throw apiError(payload, response.status, '物种目录加载失败')
  }
  return (await response.json()) as CatalogSpecies[]
}

export async function balanceEquation(
  equation: string,
  mode: EquationMode,
): Promise<BalanceEquationResponse> {
  const response = await fetch('/v1/reactions/balance', {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify({ equation, mode }),
  })
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as ErrorPayload | null
    throw apiError(payload, response.status, '方程式处理失败')
  }
  return (await response.json()) as BalanceEquationResponse
}
