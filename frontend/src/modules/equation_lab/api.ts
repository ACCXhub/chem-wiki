import type { BalanceEquationResponse, EquationMode } from './types'


interface ErrorPayload {
  detail?: { message?: string } | string
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
    const detail = payload?.detail
    const message =
      typeof detail === 'string' ? detail : detail?.message ?? `方程式处理失败（HTTP ${response.status}）`
    throw new Error(message)
  }
  return (await response.json()) as BalanceEquationResponse
}
