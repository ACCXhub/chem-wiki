import type {
  BalanceEquationResponse,
  CatalogSpecies,
  CatalogSpeciesQuery,
  EquationMode,
  ReactionCandidate,
  ReactionCandidateQuery,
  CatalogReactionEntry,
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
  for (const applicationId of query.applicationIds ?? []) {
    parameters.append('application_id', applicationId)
  }
  const normalizedQuery = query.query?.trim()
  if (normalizedQuery) parameters.set('q', normalizedQuery)
  if (query.primaryCategory) parameters.set('primary_category', query.primaryCategory)
  if (query.composition) parameters.set('composition', JSON.stringify(query.composition))
  if (query.charge !== undefined) parameters.set('charge', String(query.charge))
  if (query.entityKind) parameters.set('entity_kind', query.entityKind)

  const response = await fetch(`/v1/catalog/species?${parameters}`, {
    headers: { Accept: 'application/json' },
    signal,
  })
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as ErrorPayload | null
    throw apiError(payload, response.status, '物质库加载失败')
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

export async function findReactionCandidates(
  query: ReactionCandidateQuery,
  signal?: AbortSignal,
): Promise<ReactionCandidate[]> {
  const response = await fetch('/v1/reaction-builder/candidates', {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify(query),
    signal,
  })
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as ErrorPayload | null
    throw apiError(payload, response.status, '候选反应加载失败')
  }
  const payload = (await response.json()) as { candidates: ReactionCandidate[] }
  return payload.candidates
}

export async function loadCatalogReaction(
  consolidatedId: string,
  signal?: AbortSignal,
): Promise<CatalogReactionEntry> {
  const response = await fetch(`/v1/catalog/reactions/${encodeURIComponent(consolidatedId)}`, {
    headers: { Accept: 'application/json' },
    signal,
  })
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as ErrorPayload | null
    throw apiError(payload, response.status, '反应加载失败')
  }
  return (await response.json()) as CatalogReactionEntry
}
