import type {
  AnalyzeStructureResponse,
  CatalogStructureExploration,
  StructureInputFormat,
} from './types'


interface ErrorPayload {
  detail?: { message?: string } | string
}
export async function analyzeStructure(
  format: StructureInputFormat,
  text: string,
): Promise<AnalyzeStructureResponse> {
  const response = await fetch('/v1/structures/analyze', {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify({ format, text }),
  })
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as ErrorPayload | null
    const detail = payload?.detail
    const message = typeof detail === 'string'
      ? detail
      : detail?.message ?? `结构分析失败（HTTP ${response.status}）`
    throw new Error(message)
  }
  return (await response.json()) as AnalyzeStructureResponse
}

export async function loadStructureExploration(
  applicationSpeciesId: string,
): Promise<CatalogStructureExploration> {
  const response = await fetch(
    `/v1/catalog/species/${encodeURIComponent(applicationSpeciesId)}/structure-exploration`,
    { headers: { Accept: 'application/json' } },
  )
  if (!response.ok) throw new Error(`目录物质加载失败（HTTP ${response.status}）`)
  return (await response.json()) as CatalogStructureExploration
}
