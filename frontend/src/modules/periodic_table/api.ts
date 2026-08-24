import type { PeriodicTableElement } from './types'

let canonicalRequest: Promise<PeriodicTableElement[]> | null = null

async function requestPeriodicTable(): Promise<PeriodicTableElement[]> {
  const response = await fetch('/v1/elements', {
    headers: { Accept: 'application/json' },
  })
  if (!response.ok) {
    throw new Error(`周期表数据加载失败（HTTP ${response.status}）`)
  }
  return (await response.json()) as PeriodicTableElement[]
}

export function loadPeriodicTableElements(): Promise<PeriodicTableElement[]> {
  canonicalRequest ??= requestPeriodicTable().catch((error: unknown) => {
    canonicalRequest = null
    throw error
  })
  return canonicalRequest
}
