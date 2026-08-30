const TEACHING_GROUP_HEADERS = [
  { modernGroups: [1], label: 'IA' },
  { modernGroups: [2], label: 'IIA' },
  { modernGroups: [3], label: 'IIIB' },
  { modernGroups: [4], label: 'IVB' },
  { modernGroups: [5], label: 'VB' },
  { modernGroups: [6], label: 'VIB' },
  { modernGroups: [7], label: 'VIIB' },
  { modernGroups: [8, 9, 10], label: 'VIII' },
  { modernGroups: [11], label: 'IB' },
  { modernGroups: [12], label: 'IIB' },
  { modernGroups: [13], label: 'IIIA' },
  { modernGroups: [14], label: 'IVA' },
  { modernGroups: [15], label: 'VA' },
  { modernGroups: [16], label: 'VIA' },
  { modernGroups: [17], label: 'VIIA' },
  { modernGroups: [18], label: '0' },
] as const

export const teachingGroupHeaders = TEACHING_GROUP_HEADERS

export function teachingGroupLabel(group: number | null): string {
  if (group === null) return '镧锕系'
  return TEACHING_GROUP_HEADERS.find((header) => (header.modernGroups as readonly number[]).includes(group))?.label ?? '—'
}
