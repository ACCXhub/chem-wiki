import type { AnalyzeStructureResponse, StructureInputFormat } from './types'


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
