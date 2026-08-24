import type { ElementWikiPage } from './types'


export async function loadElementWiki(elementId: string): Promise<ElementWikiPage> {
  const response = await fetch(`/v1/elements/${encodeURIComponent(elementId)}`, {
    headers: { Accept: 'application/json' },
  })
  if (!response.ok) {
    throw new Error(`元素详情加载失败（HTTP ${response.status}）`)
  }
  return (await response.json()) as ElementWikiPage
}
