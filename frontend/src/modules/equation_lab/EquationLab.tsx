import { useCallback, useEffect, useMemo, useRef, useState, type DragEvent, type FormEvent } from 'react'

import { loadPeriodicTableElements } from '../periodic_table'
import {
  balanceEquation,
  completeCatalogSpecies,
  findReactionCandidates,
  loadCatalogReaction,
  loadReactionDetail,
  searchCatalogSpecies,
} from './api'
import ChemistryNotation from './ChemistryNotation'
import SpeciesBlock from './palette/SpeciesBlock'
import ReactionCandidates from './reaction-builder/ReactionCandidates'
import EquationWorkbench, { type DraftSide, type DragTarget } from './workbench/EquationWorkbench'
import {
  addParticipant,
  addBuilderBlock,
  adjustBuilderBlock,
  canSubmitDraft,
  clearBuilderTray,
  resolveBuilderTray,
  serializeEquationDraft,
  updateParticipantPhase,
} from './composer'
import {
  loadPalettePreferences,
  recordPaletteRecent,
  resolvePaletteSpecies,
  savePalettePreferences,
  setPaletteChineseNames,
  togglePaletteFavorite,
} from './palette-preferences'
import type {
  BalanceEquationResponse,
  BuilderBlock,
  BuilderTrayEntry,
  CatalogSpecies,
  CatalogCompletionQuery,
  CatalogReactionEntry,
  CatalogReactionDetail,
  CatalogSpeciesQuery,
  EquationDraft,
  EquationDraftParticipant,
  EquationMode,
  ReactionCandidate,
  ReactionCandidateQuery,
} from './types'
import type { PeriodicTableElement } from '../periodic_table'
import './equation-lab.css'


interface EquationLabProps {
  onBack: () => void
  onNavigate?: (path: string) => void
  reactionId?: string | null
}

type PaletteMode = 'search' | 'builder'
type DraggedItem =
  | { kind: 'species'; species: CatalogSpecies }
  | { kind: 'participant'; side: DraftSide; applicationId: string }

interface DraftHistory {
  past: EquationDraft[]
  present: EquationDraft
  future: EquationDraft[]
}

type SearchSpecies = (
  query: CatalogSpeciesQuery,
  signal?: AbortSignal,
) => Promise<CatalogSpecies[]>

type FindCandidates = (
  query: ReactionCandidateQuery,
  signal?: AbortSignal,
) => Promise<ReactionCandidate[]>

const NO_REACTION_CANDIDATES: FindCandidates = async () => []
type LoadReaction = (consolidatedId: string, signal?: AbortSignal) => Promise<CatalogReactionEntry>
type CompleteSpecies = (
  query: CatalogCompletionQuery,
  signal?: AbortSignal,
) => Promise<CatalogSpecies[]>
type LoadReactionDetail = (
  consolidatedId: string,
  signal?: AbortSignal,
) => Promise<CatalogReactionDetail>

interface EquationLabViewProps extends EquationLabProps {
  onBalance: (
    equation: string,
    mode: EquationMode,
  ) => Promise<BalanceEquationResponse>
  onSearch?: SearchSpecies
  onCompleteSpecies?: CompleteSpecies
  onFindCandidates?: FindCandidates
  onLoadElements?: () => Promise<PeriodicTableElement[]>
  reactionId?: string | null
  onLoadReaction?: LoadReaction
  onLoadReactionDetail?: LoadReactionDetail
}

const EXAMPLES: Array<{
  label: string
  equation: string
}> = [
  { label: '水的生成', equation: 'H2 + O2 -> H2O' },
  {
    label: '沉淀示例',
    equation: 'Ag+(aq) + Cl-(aq) -> AgCl(s)',
  },
  {
    label: '无净反应示例',
    equation: 'Na+(aq) + NO3-(aq)',
  },
]

const CATEGORY_OPTIONS = [
  ['', '全部'],
  ['elemental_substance', '单质'],
  ['acid', '酸'],
  ['base', '碱'],
  ['salt', '盐'],
  ['oxide', '氧化物'],
  ['cation', '阳离子'],
  ['anion', '阴离子'],
  ['organic', '有机物'],
  ['other', '其他'],
] as const

const EXACT_LOOKUP_BATCH_SIZE = 50

const EMPTY_DRAFT: EquationDraft = {
  mode: 'molecular',
  reactants: [],
  products: [],
}

const HISTORY_LIMIT = 40

function sameDraft(left: EquationDraft, right: EquationDraft) {
  if (left.mode !== right.mode) return false
  return (['reactants', 'products'] as const).every((side) => (
    left[side].length === right[side].length
    && left[side].every((participant, index) => (
      participant.applicationId === right[side][index]?.applicationId
      && participant.phase === right[side][index]?.phase
    ))
  ))
}

const COMMON_ELEMENT_SYMBOLS = new Set([
  'H', 'C', 'N', 'O', 'F', 'Na', 'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'K', 'Ca', 'Fe', 'Cu', 'Zn', 'Ag', 'Ba',
])

function elementBlock(element: PeriodicTableElement): BuilderBlock {
  return {
    id: `element:${element.id}`,
    label: element.nameZh,
    formula: element.symbol,
    composition: { [element.symbol]: 1 },
    charge: 0,
    kind: 'element',
  }
}

function ionBlock(species: CatalogSpecies): BuilderBlock | null {
  if (species.entityKind !== 'ion' || !species.composition) return null
  return {
    id: `catalog:${species.applicationId}`,
    label: species.nameZh,
    formula: species.formula,
    composition: species.composition,
    charge: species.charge,
    kind: 'ion',
  }
}

export function EquationLabView({
  onBack,
  onBalance,
  onSearch = searchCatalogSpecies,
  onCompleteSpecies = completeCatalogSpecies,
  onFindCandidates = NO_REACTION_CANDIDATES,
  onLoadElements = loadPeriodicTableElements,
  reactionId = null,
  onLoadReaction = loadCatalogReaction,
  onLoadReactionDetail,
  onNavigate,
}: EquationLabViewProps) {
  const [history, setHistory] = useState<DraftHistory>({ past: [], present: EMPTY_DRAFT, future: [] })
  const draft = history.present
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('')
  const [catalog, setCatalog] = useState<CatalogSpecies[]>([])
  const [quickAccessSpecies, setQuickAccessSpecies] = useState<CatalogSpecies[]>([])
  const [catalogLoading, setCatalogLoading] = useState(true)
  const [catalogError, setCatalogError] = useState<string | null>(null)
  const [paletteMode, setPaletteMode] = useState<PaletteMode>('search')
  const [preferences, setPreferences] = useState(loadPalettePreferences)
  const [builderElements, setBuilderElements] = useState<PeriodicTableElement[]>([])
  const [builderCations, setBuilderCations] = useState<CatalogSpecies[]>([])
  const [builderAnions, setBuilderAnions] = useState<CatalogSpecies[]>([])
  const [builderTray, setBuilderTray] = useState<BuilderTrayEntry[]>([])
  const [builderMatches, setBuilderMatches] = useState<CatalogSpecies[]>([])
  const [builderLoading, setBuilderLoading] = useState(false)
  const [builderError, setBuilderError] = useState<string | null>(null)
  const [showAllElements, setShowAllElements] = useState(false)
  const [directEquation, setDirectEquation] = useState(EXAMPLES[0].equation)
  const [manualInputOpen, setManualInputOpen] = useState(false)
  const [result, setResult] = useState<BalanceEquationResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [balancedDraftSignature, setBalancedDraftSignature] = useState<string | null>(null)
  const [settled, setSettled] = useState(false)
  const [editIntentSignature, setEditIntentSignature] = useState<string | null>(null)
  const [autoBalance, setAutoBalance] = useState(true)
  const [draggedItem, setDraggedItem] = useState<DraggedItem | null>(null)
  const [dragTarget, setDragTarget] = useState<DragTarget | null>(null)
  const [duplicatePulse, setDuplicatePulse] = useState<string | null>(null)
  const [reactionCandidates, setReactionCandidates] = useState<ReactionCandidate[]>([])
  const [selectedReactionId, setSelectedReactionId] = useState<string | null>(null)
  const [reactionDetail, setReactionDetail] = useState<CatalogReactionDetail | null>(null)
  const [reactionDetailLoading, setReactionDetailLoading] = useState(false)
  const [reactionDetailError, setReactionDetailError] = useState<string | null>(null)
  const [candidateLoading, setCandidateLoading] = useState(false)
  const [candidateError, setCandidateError] = useState<string | null>(null)
  const balanceRequestId = useRef(0)
  const loadedReactionId = useRef<string | null>(null)

  useEffect(() => {
    if (!reactionId || loadedReactionId.current === reactionId) return
    const controller = new AbortController()
    void onLoadReaction(reactionId, controller.signal).then(async (reaction) => {
      const applicationIds = reaction.participants.flatMap((participant) => (
        participant.applicationTargetId ? [participant.applicationTargetId] : []
      ))
      const species = await onSearch({
        applicationIds,
        equationMode: 'molecular',
        limit: 50,
      }, controller.signal)
      if (controller.signal.aborted) return
      const speciesById = new Map(species.map((item) => [item.applicationId, item]))
      const next: EquationDraft = { mode: 'molecular', reactants: [], products: [] }
      for (const participant of reaction.participants) {
        const match = participant.applicationTargetId
          ? speciesById.get(participant.applicationTargetId)
          : undefined
        if (!match || (participant.role !== 'reactant' && participant.role !== 'product')) continue
        next[participant.role === 'reactant' ? 'reactants' : 'products'].push({
          ...match,
          phase: participant.phase,
        })
      }
      loadedReactionId.current = reactionId
      setHistory({ past: [], present: next, future: [] })
      setSelectedReactionId(reaction.consolidatedId)
    }).catch((reason: unknown) => {
      if (reason instanceof DOMException && reason.name === 'AbortError') return
      setCatalogError(reason instanceof Error ? reason.message : '反应加载失败')
    })
    return () => controller.abort()
  }, [onLoadReaction, onSearch, reactionId])

  useEffect(() => {
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      setCatalogLoading(true)
      setCatalogError(null)
      void onSearch({
        query,
        primaryCategory: category || undefined,
        equationMode: draft.mode,
        limit: 50,
      }, controller.signal)
        .then(setCatalog)
        .catch((reason: unknown) => {
          if (reason instanceof DOMException && reason.name === 'AbortError') return
          setCatalog([])
          setCatalogError(reason instanceof Error ? reason.message : '物质库加载失败')
        })
        .finally(() => {
          if (!controller.signal.aborted) setCatalogLoading(false)
        })
    }, 160)
    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [category, draft.mode, onSearch, query])

  const savedApplicationIds = useMemo(
    () => [...new Set([...preferences.favorites, ...preferences.recents])],
    [preferences],
  )

  useEffect(() => {
    if (!savedApplicationIds.length) return
    const controller = new AbortController()
    const batches = Array.from(
      { length: Math.ceil(savedApplicationIds.length / EXACT_LOOKUP_BATCH_SIZE) },
      (_, index) => savedApplicationIds.slice(
        index * EXACT_LOOKUP_BATCH_SIZE,
        (index + 1) * EXACT_LOOKUP_BATCH_SIZE,
      ),
    )
    void Promise.all(batches.map((applicationIds) => onSearch({
      applicationIds,
      equationMode: draft.mode,
      limit: 50,
    }, controller.signal))).then((results) => {
      if (controller.signal.aborted) return
      const matches = results.flat()
      setQuickAccessSpecies(matches)
      const resolvedIds = new Set(matches.map((item) => item.applicationId))
      const unavailableIds = savedApplicationIds.filter((id) => !resolvedIds.has(id))
      if (!unavailableIds.length) return
      setPreferences((current) => {
        const next = {
          favorites: current.favorites.filter((id) => !unavailableIds.includes(id)),
          recents: current.recents.filter((id) => !unavailableIds.includes(id)),
          showChineseNames: current.showChineseNames,
        }
        if (
          next.favorites.length === current.favorites.length
          && next.recents.length === current.recents.length
        ) return current
        savePalettePreferences(next)
        return next
      })
    }).catch(() => {
      if (!controller.signal.aborted) setQuickAccessSpecies([])
    })
    return () => controller.abort()
  }, [draft.mode, onSearch, savedApplicationIds])

  useEffect(() => {
    if (paletteMode !== 'builder') return
    const controller = new AbortController()
    const blocksRequest = Promise.allSettled([
      onLoadElements(),
      onSearch({ primaryCategory: 'cation', equationMode: 'ionic', limit: 50 }, controller.signal),
      onSearch({ primaryCategory: 'anion', equationMode: 'ionic', limit: 50 }, controller.signal),
    ])
    void Promise.resolve().then(() => {
      if (!controller.signal.aborted) {
        setBuilderLoading(true)
        setBuilderError(null)
      }
    })
    void blocksRequest.then(([elements, cations, anions]) => {
      if (controller.signal.aborted) return
      if (elements.status === 'fulfilled') setBuilderElements(elements.value)
      if (cations.status === 'fulfilled') setBuilderCations(cations.value)
      if (anions.status === 'fulfilled') setBuilderAnions(anions.value)
      const failures = [elements, cations, anions].filter((item) => item.status === 'rejected')
      if (failures.length) {
        setBuilderError('部分构建块暂不可用；目录中可用的块仍可继续组合。')
      }
    }).finally(() => {
      if (!controller.signal.aborted) setBuilderLoading(false)
    })
    return () => controller.abort()
  }, [onLoadElements, onSearch, paletteMode])

  const builderResolution = useMemo(() => resolveBuilderTray(builderTray), [builderTray])

  useEffect(() => {
    if (!builderResolution || paletteMode !== 'builder') return
    const controller = new AbortController()
    const matchRequest = onCompleteSpecies({
      composition: builderResolution.composition,
      equationMode: draft.mode,
      entityKind: 'substance',
      limit: 50,
    }, controller.signal)
    void Promise.resolve().then(() => {
      if (!controller.signal.aborted) {
        setBuilderLoading(true)
        setBuilderError(null)
      }
    })
    void matchRequest.then((matches) => {
      if (!controller.signal.aborted) setBuilderMatches(matches)
    }).catch((reason: unknown) => {
      if (!controller.signal.aborted) {
        setBuilderMatches([])
        setBuilderError(reason instanceof Error ? reason.message : '已知物质匹配失败')
      }
    }).finally(() => {
      if (!controller.signal.aborted) setBuilderLoading(false)
    })
    return () => controller.abort()
  }, [builderResolution, draft.mode, onCompleteSpecies, paletteMode])

  const favoriteSpecies = useMemo(
    () => resolvePaletteSpecies(
      savedApplicationIds.length ? quickAccessSpecies : [],
      preferences.favorites,
    ),
    [preferences.favorites, quickAccessSpecies, savedApplicationIds.length],
  )
  const recentSpecies = useMemo(
    () => resolvePaletteSpecies(
      savedApplicationIds.length ? quickAccessSpecies : [],
      preferences.recents.filter((id) => !preferences.favorites.includes(id)),
    ),
    [preferences.favorites, preferences.recents, quickAccessSpecies, savedApplicationIds.length],
  )
  const quickSpecies = useMemo(
    () => [...favoriteSpecies, ...recentSpecies.filter(
      (item) => !preferences.favorites.includes(item.applicationId),
    )],
    [favoriteSpecies, preferences.favorites, recentSpecies],
  )
  const quickSpeciesIds = useMemo(
    () => new Set(quickSpecies.map((item) => item.applicationId)),
    [quickSpecies],
  )
  const visibleCatalog = useMemo(
    () => query.trim() ? catalog : catalog.filter((item) => !quickSpeciesIds.has(item.applicationId)),
    [catalog, query, quickSpeciesIds],
  )

  const reactionAnchorKey = useMemo(() => JSON.stringify({
    reactants: draft.reactants.map((participant) => participant.applicationId),
    products: draft.products.map((participant) => participant.applicationId),
  }), [draft.products, draft.reactants])

  useEffect(() => {
    const anchors = JSON.parse(reactionAnchorKey) as {
      reactants: string[]
      products: string[]
    }
    const controller = new AbortController()
    if (!anchors.reactants.length && !anchors.products.length) {
      void Promise.resolve().then(() => {
        if (controller.signal.aborted) return
        setReactionCandidates([])
        setSelectedReactionId(null)
        setCandidateError(null)
        setCandidateLoading(false)
      })
      return () => controller.abort()
    }
    void Promise.resolve().then(() => {
      if (controller.signal.aborted) return
      setSelectedReactionId(null)
      setCandidateLoading(true)
      setCandidateError(null)
    })
    const timer = window.setTimeout(() => {
      void onFindCandidates({
        reactantApplicationIds: anchors.reactants,
        productApplicationIds: anchors.products,
      }, controller.signal).then((candidates) => {
        if (controller.signal.aborted) return
        setReactionCandidates(candidates)
        setSelectedReactionId(candidates.length === 1 ? candidates[0].consolidatedId : null)
      }).catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === 'AbortError') return
        setReactionCandidates([])
        setCandidateError(reason instanceof Error ? reason.message : '候选反应加载失败')
      }).finally(() => {
        if (!controller.signal.aborted) setCandidateLoading(false)
      })
    }, 180)
    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [onFindCandidates, reactionAnchorKey])

  const focusedReaction = useMemo(
    () => reactionCandidates.find((candidate) => candidate.consolidatedId === selectedReactionId) ?? null,
    [reactionCandidates, selectedReactionId],
  )

  useEffect(() => {
    if (!selectedReactionId || !onLoadReactionDetail) {
      void Promise.resolve().then(() => {
        setReactionDetail(null)
        setReactionDetailLoading(false)
        setReactionDetailError(null)
      })
      return
    }
    const controller = new AbortController()
    void Promise.resolve().then(() => {
      setReactionDetail(null)
      setReactionDetailLoading(true)
      setReactionDetailError(null)
    })
    void onLoadReactionDetail(selectedReactionId, controller.signal)
      .then((detail) => {
        if (!controller.signal.aborted) setReactionDetail(detail)
      })
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === 'AbortError') return
        if (!controller.signal.aborted) {
          setReactionDetailError(reason instanceof Error ? reason.message : '反应知识加载失败')
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setReactionDetailLoading(false)
      })
    return () => controller.abort()
  }, [onLoadReactionDetail, selectedReactionId])

  const navigateToElement = useCallback(async (symbol: string) => {
    if (!onNavigate) return
    const elements = builderElements.length ? builderElements : await onLoadElements()
    if (!builderElements.length) setBuilderElements(elements)
    const element = elements.find((item) => item.symbol === symbol)
    if (element) onNavigate(`/elements/${encodeURIComponent(element.id)}`)
  }, [builderElements, onLoadElements, onNavigate])

  const invalidateBalance = useCallback(() => {
    balanceRequestId.current += 1
    setResult(null)
    setBalancedDraftSignature(null)
    setEditIntentSignature(null)
    setSettled(false)
    setError(null)
    setLoading(false)
  }, [])

  const runBalance = useCallback(async (
    equation: string,
    mode: EquationMode,
    draftSignature: string | null,
  ) => {
    const requestId = balanceRequestId.current + 1
    balanceRequestId.current = requestId
    setSettled(false)
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const response = await onBalance(equation, mode)
      if (requestId === balanceRequestId.current) {
        setResult(response)
        setBalancedDraftSignature(draftSignature)
      }
    } catch (reason) {
      if (requestId === balanceRequestId.current) {
        setError(reason instanceof Error ? reason.message : '方程式处理失败')
      }
    } finally {
      if (requestId === balanceRequestId.current) setLoading(false)
    }
  }, [onBalance])

  const handleComposerSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (!canSubmitDraft(draft)) return
    void runBalance(serializeEquationDraft(draft), draft.mode, draftSignature)
  }

  const handleDirectSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (!directEquation.trim()) return
    void runBalance(directEquation.trim(), draft.mode, null)
  }

  const chooseExample = (example: (typeof EXAMPLES)[number]) => {
    setDirectEquation(example.equation)
    invalidateBalance()
  }

  const commitDraft = useCallback((update: (current: EquationDraft) => EquationDraft) => {
    setHistory((current) => {
      const next = update(current.present)
      if (sameDraft(current.present, next)) return current
      return {
        past: [...current.past, current.present].slice(-HISTORY_LIMIT),
        present: next,
        future: [],
      }
    })
    invalidateBalance()
  }, [invalidateBalance])

  const changeSide = (side: DraftSide, update: (participants: EquationDraftParticipant[]) => EquationDraftParticipant[]) => {
    commitDraft((current) => ({ ...current, [side]: update(current[side]) }))
  }

  const addToSide = (side: DraftSide, species: CatalogSpecies) => {
    if (draft[side].some((participant) => participant.applicationId === species.applicationId)) {
      setDuplicatePulse(`${side}:${species.applicationId}`)
      window.setTimeout(() => setDuplicatePulse(null), 360)
      return
    }
    changeSide(side, (participants) => addParticipant(participants, species))
    setPreferences((current) => {
      const next = recordPaletteRecent(current, species.applicationId)
      savePalettePreferences(next)
      return next
    })
  }

  const toggleFavorite = (species: CatalogSpecies) => {
    setPreferences((current) => {
      const next = togglePaletteFavorite(current, species.applicationId)
      savePalettePreferences(next)
      return next
    })
  }

  const changeMode = (mode: EquationMode) => commitDraft((current) => ({ ...current, mode }))

  const undo = useCallback(() => {
    setHistory((current) => {
      const previous = current.past.at(-1)
      if (!previous) return current
      return { past: current.past.slice(0, -1), present: previous, future: [current.present, ...current.future] }
    })
    invalidateBalance()
  }, [invalidateBalance])

  const redo = useCallback(() => {
    setHistory((current) => {
      const next = current.future[0]
      if (!next) return current
      return { past: [...current.past, current.present].slice(-HISTORY_LIMIT), present: next, future: current.future.slice(1) }
    })
    invalidateBalance()
  }, [invalidateBalance])

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (!(event.ctrlKey || event.metaKey) || event.key.toLowerCase() !== 'z') return
      const target = event.target as HTMLElement | null
      if (target?.closest('input, textarea, select')) return
      event.preventDefault()
      if (event.shiftKey) redo()
      else undo()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [redo, undo])

  const getMagneticTarget = (event: DragEvent<HTMLElement>): DragTarget | null => {
    const bounds = event.currentTarget.getBoundingClientRect()
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) return null
    return { side: event.clientX < bounds.left + bounds.width / 2 ? 'reactants' : 'products' }
  }

  const handleWorkbenchDragOver = (event: DragEvent<HTMLElement>) => {
    if (!draggedItem) return
    const target = getMagneticTarget(event)
    if (!target) return
    event.preventDefault()
    event.dataTransfer.dropEffect = draggedItem.kind === 'species' ? 'copy' : 'move'
    setDragTarget(target)
  }

  const handleParticipantDragOver = (event: DragEvent<HTMLElement>, target: DragTarget) => {
    if (!draggedItem) return
    event.preventDefault()
    event.dataTransfer.dropEffect = draggedItem.kind === 'species' ? 'copy' : 'move'
    setDragTarget(target)
  }

  const handleWorkbenchDragLeave = (event: DragEvent<HTMLElement>) => {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragTarget(null)
  }

  const moveParticipantTo = (sourceSide: DraftSide, applicationId: string, target: DragTarget) => {
    commitDraft((current) => {
      const sourceIndex = current[sourceSide].findIndex((participant) => participant.applicationId === applicationId)
      if (sourceIndex < 0) return current
      const participant = current[sourceSide][sourceIndex]
      const targetItems = current[target.side]
      if (target.side !== sourceSide && targetItems.some((item) => item.applicationId === applicationId)) {
        return { ...current, [sourceSide]: current[sourceSide].filter((item) => item.applicationId !== applicationId) }
      }
      const nextSource = current[sourceSide].filter((item) => item.applicationId !== applicationId)
      const nextTargetBase = target.side === sourceSide ? nextSource : targetItems
      let insertion = target.index ?? nextTargetBase.length
      if (target.side === sourceSide && insertion > sourceIndex) insertion -= 1
      insertion = Math.max(0, Math.min(insertion, nextTargetBase.length))
      const nextTarget = [...nextTargetBase.slice(0, insertion), participant, ...nextTargetBase.slice(insertion)]
      return target.side === sourceSide
        ? { ...current, [sourceSide]: nextTarget }
        : { ...current, [sourceSide]: nextSource, [target.side]: nextTarget }
    })
  }

  const handleDrop = (event: DragEvent<HTMLElement>, preferredTarget?: DragTarget) => {
    if (!draggedItem) return
    event.preventDefault()
    const target = preferredTarget ?? getMagneticTarget(event)
    if (!target) return
    if (draggedItem.kind === 'species') addToSide(target.side, draggedItem.species)
    else moveParticipantTo(draggedItem.side, draggedItem.applicationId, target)
    setDraggedItem(null)
    setDragTarget(null)
  }

  const clearDrag = () => {
    setDraggedItem(null)
    setDragTarget(null)
  }

  const autoScrollPalette = (event: DragEvent<HTMLDivElement>) => {
    if (!draggedItem) return
    const element = event.currentTarget
    const bounds = element.getBoundingClientRect()
    const edge = 44
    if (event.clientY < bounds.top + edge) element.scrollTop -= 10
    if (event.clientY > bounds.bottom - edge) element.scrollTop += 10
  }

  const copyEquation = async () => {
    const text = focusedReaction?.equation ?? result?.formattedEquation ?? serializeEquationDraft(draft)
    if (!text) return
    await navigator.clipboard.writeText(text)
  }

  const draftSignature = `${draft.mode}:${serializeEquationDraft(draft)}`
  const canSettle = result?.state === 'balanced'
    && balancedDraftSignature === draftSignature
    && !loading
    && !error
    && !draggedItem

  useEffect(() => {
    if (!canSettle || settled || editIntentSignature === draftSignature) return
    const timer = window.setTimeout(() => setSettled(true), 240)
    return () => window.clearTimeout(timer)
  }, [canSettle, draftSignature, editIntentSignature, settled])

  const enterEdit = () => {
    setSettled(false)
    setEditIntentSignature(draftSignature)
  }

  const startSpeciesDrag = (species: CatalogSpecies) => {
    enterEdit()
    setDraggedItem({ kind: 'species', species })
  }

  const startParticipantDrag = (side: DraftSide, applicationId: string) => {
    enterEdit()
    setDraggedItem({ kind: 'participant', side, applicationId })
  }

  useEffect(() => {
    if (!autoBalance || !canSubmitDraft(draft)) return
    const equation = serializeEquationDraft(draft)
    const timer = window.setTimeout(() => {
      void runBalance(equation, draft.mode, draftSignature)
    }, 280)
    return () => window.clearTimeout(timer)
  }, [autoBalance, draft, draftSignature, runBalance])

  return (
    <main className="equation-lab-page">
      <nav className="lab-breadcrumb" aria-label="面包屑导航">
        <button type="button" onClick={onBack}>元素周期表</button>
        <span aria-hidden="true">/</span>
        <span>方程实验室</span>
      </nav>

      <header className="equation-lab-header">
        <div>
          <h1>方程实验室</h1>
          <p>把物质放入方程，逐步找到并完成已知反应。</p>
        </div>
      </header>

      <EquationWorkbench
        draft={draft}
        focusedReaction={focusedReaction}
        reactionDetail={reactionDetail}
        reactionDetailLoading={reactionDetailLoading}
        reactionDetailError={reactionDetailError}
        result={result}
        error={error}
        loading={loading}
        settled={settled}
        autoBalance={autoBalance}
        dragTarget={dragTarget}
        duplicatePulse={duplicatePulse}
        canUndo={history.past.length > 0}
        canRedo={history.future.length > 0}
        manualInputOpen={manualInputOpen}
        onSubmit={handleComposerSubmit}
        onModeChange={changeMode}
        onAutoBalanceChange={setAutoBalance}
        onClearDraft={() => commitDraft((current) => ({ ...current, reactants: [], products: [] }))}
        onUndo={undo}
        onRedo={redo}
        onCopy={copyEquation}
        onManualInputToggle={() => setManualInputOpen((open) => !open)}
        onEnterEdit={enterEdit}
        onNavigateToElement={(symbol) => { void navigateToElement(symbol) }}
        onNavigateToStructure={(applicationId) => onNavigate?.(`/structure-lab?species=${encodeURIComponent(applicationId)}`)}
        onRemove={(side, id) => changeSide(side, (items) => items.filter((item) => item.applicationId !== id))}
        onPhase={(side, id, phase) => changeSide(side, (items) => updateParticipantPhase(items, id, phase))}
        onWorkbenchDragOver={handleWorkbenchDragOver}
        onWorkbenchDragLeave={handleWorkbenchDragLeave}
        onParticipantDragOver={handleParticipantDragOver}
        onParticipantDragStart={startParticipantDrag}
        onDrop={handleDrop}
        onDragEnd={clearDrag}
      />

      {manualInputOpen ? (
        <form className="manual-equation-input" onSubmit={handleDirectSubmit}>
          <input
            id="direct-equation"
            aria-label="化学方程式"
            value={directEquation}
            onChange={(event) => setDirectEquation(event.target.value)}
            placeholder="输入完整方程式"
            spellCheck={false}
          />
          <span>{draft.mode === 'molecular' ? '分子' : draft.mode === 'ionic' ? '离子' : '净离子'}模式</span>
          <div className="lab-examples" aria-label="方程式示例">
            {EXAMPLES.map((example) => (
              <button key={example.label} type="button" onClick={() => chooseExample(example)}>{example.label}</button>
            ))}
          </div>
          <button type="submit" disabled={loading || !directEquation.trim()}>直接配平</button>
        </form>
      ) : null}

      <ReactionCandidates
        candidates={reactionCandidates}
        selectedId={selectedReactionId}
        loading={candidateLoading}
        error={candidateError}
        onSelect={(candidate) => setSelectedReactionId(candidate.consolidatedId)}
      />

      <section className="species-palette" aria-labelledby="palette-heading">
          <div className="lab-heading compact">
            <h2 id="palette-heading">物质库</h2>
            <div className="palette-heading-actions">
              <span>{catalogLoading ? '查询中…' : `${catalog.length} 项`}</span>
              <button
                className="name-display-toggle"
                type="button"
                aria-pressed={preferences.showChineseNames}
                aria-label={preferences.showChineseNames ? '隐藏中文名' : '显示中文名'}
                onClick={() => setPreferences((current) => {
                  const next = setPaletteChineseNames(current, !current.showChineseNames)
                  savePalettePreferences(next)
                  return next
                })}
              >
                中文名{preferences.showChineseNames ? ' ✓' : ''}
              </button>
            </div>
          </div>
          <div className="palette-mode-switch" role="group" aria-label="物质选择方式">
            <button type="button" aria-pressed={paletteMode === 'search'} onClick={() => setPaletteMode('search')}>搜索物质</button>
            <button type="button" aria-pressed={paletteMode === 'builder'} onClick={() => setPaletteMode('builder')}>构建物质</button>
          </div>
          {paletteMode === 'search' ? <>
            <label className="species-search">
              <span>搜索名称、别名或化学式</span>
              <input
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="例如：硫酸根 / sulfate / SO4"
              />
            </label>
            <div className="category-nav" aria-label="物质分类">
              {CATEGORY_OPTIONS.map(([value, label]) => (
              <button
                key={value || 'all'}
                type="button"
                aria-pressed={category === value}
                onClick={() => setCategory(value)}
              >
                {label}
              </button>
              ))}
            </div>
            {quickSpecies.length ? (
              <section className="quick-species-flow" aria-label="快捷物质">
                {quickSpecies.map((species) => (
                  <SpeciesBlock
                    key={species.applicationId}
                    species={species}
                    isFavorite={preferences.favorites.includes(species.applicationId)}
                    isRecent={preferences.recents.includes(species.applicationId)}
                    showChineseNames={preferences.showChineseNames}
                    onFavorite={toggleFavorite}
                    onAddToSide={addToSide}
                    onDragStart={startSpeciesDrag}
                    onDragEnd={clearDrag}
                  />
                ))}
              </section>
            ) : null}
            {catalogError ? <div className="catalog-state is-error" role="alert">{catalogError}</div> : null}
            {!catalogError && !catalogLoading && !catalog.length ? (
              <div className="catalog-state">没有匹配当前搜索与分类的物质。</div>
            ) : null}
            <div className="species-list" aria-live="polite" onDragOver={autoScrollPalette}>
              {visibleCatalog.map((species) => {
              const isFavorite = preferences.favorites.includes(species.applicationId)
              const isRecent = preferences.recents.includes(species.applicationId)
              return (
                <SpeciesBlock
                  key={species.consolidatedId}
                  species={species}
                  isFavorite={isFavorite}
                  isRecent={isRecent}
                  showChineseNames={preferences.showChineseNames}
                  onFavorite={toggleFavorite}
                  onAddToSide={addToSide}
                  onDragStart={startSpeciesDrag}
                  onDragEnd={clearDrag}
                />
              )
              })}
            </div>
          </> : <SpeciesBuilder
            elements={builderElements}
            cations={builderCations}
            anions={builderAnions}
            tray={builderTray}
            matches={builderResolution ? builderMatches : []}
            resolution={builderResolution}
            loading={builderLoading}
            error={builderError}
            showAllElements={showAllElements}
            onShowAllElements={() => setShowAllElements((value) => !value)}
            onAddBlock={(block) => setBuilderTray((current) => addBuilderBlock(current, block))}
            onAdjustBlock={(id, delta) => setBuilderTray((current) => adjustBuilderBlock(current, id, delta))}
            onClear={() => setBuilderTray(clearBuilderTray())}
            onAddToSide={addToSide}
            onDragStart={startSpeciesDrag}
            onDragEnd={clearDrag}
            showChineseNames={preferences.showChineseNames}
          />}
      </section>

    </main>
  )
}

interface SpeciesBuilderProps {
  elements: PeriodicTableElement[]
  cations: CatalogSpecies[]
  anions: CatalogSpecies[]
  tray: BuilderTrayEntry[]
  matches: CatalogSpecies[]
  resolution: ReturnType<typeof resolveBuilderTray>
  loading: boolean
  error: string | null
  showAllElements: boolean
  onShowAllElements: () => void
  onAddBlock: (block: BuilderBlock) => void
  onAdjustBlock: (id: string, delta: -1 | 1) => void
  onClear: () => void
  onAddToSide: (side: DraftSide, species: CatalogSpecies) => void
  onDragStart: (species: CatalogSpecies) => void
  onDragEnd: () => void
  showChineseNames: boolean
}

function SpeciesBuilder({
  elements,
  cations,
  anions,
  tray,
  matches,
  resolution,
  loading,
  error,
  showAllElements,
  onShowAllElements,
  onAddBlock,
  onAdjustBlock,
  onClear,
  onAddToSide,
  onDragStart,
  onDragEnd,
  showChineseNames,
}: SpeciesBuilderProps) {
  const [source, setSource] = useState<'cation' | 'anion' | 'element'>('cation')
  const visibleElements = showAllElements
    ? elements
    : elements.filter((element) => COMMON_ELEMENT_SYMBOLS.has(element.symbol))
  const cationBlocks = cations.flatMap((species) => {
    const block = ionBlock(species)
    return block ? [block] : []
  })
  const anionBlocks = anions.flatMap((species) => {
    const block = ionBlock(species)
    return block ? [block] : []
  })
  const sourceBlocks = source === 'cation'
    ? cationBlocks
    : source === 'anion'
      ? anionBlocks
      : visibleElements.map(elementBlock)
  const sourceLabel = source === 'cation'
    ? '阳离子'
    : source === 'anion'
      ? '阴离子'
      : showAllElements ? '全部元素' : '常用元素'
  return (
    <section className="species-builder" aria-label="构建物质">
      {error ? <div className="catalog-state is-error" role="alert">{error}</div> : null}
      <div className="builder-layout">
        <div className="builder-input">
          <div className="builder-source-switch" role="group" aria-label="构建素材">
            {([['cation', '阳离子'], ['anion', '阴离子'], ['element', '元素']] as const).map(([value, label]) => (
              <button key={value} type="button" aria-pressed={source === value} onClick={() => setSource(value)}>{label}</button>
            ))}
          </div>
          <BuilderBlockGroup title={sourceLabel} blocks={sourceBlocks} onAddBlock={onAddBlock} />
          {source === 'element' && (elements.length > visibleElements.length || showAllElements) ? (
            <button className="show-elements" type="button" onClick={onShowAllElements}>
              {showAllElements ? '常用元素' : `全部元素 ${elements.length}`}
            </button>
          ) : null}
          <div className="builder-composition" aria-label="当前组合">
            <div className="builder-composition-heading">
              <strong>当前组合</strong>
              <button type="button" onClick={onClear} disabled={!tray.length}>清空</button>
            </div>
            {!tray.length ? <p>选择素材开始组合。</p> : (
              <div className="tray-entries">
                {tray.map((entry) => (
                  <div className="tray-entry" key={entry.block.id}>
                    <ChemistryNotation formula={entry.block.formula} charge={entry.block.charge} />
                    <div className="tray-count">
                      <button type="button" onClick={() => onAdjustBlock(entry.block.id, -1)} aria-label={`减少${entry.block.label}`}>−</button>
                      <strong>{entry.count > 1 ? entry.count : ''}</strong>
                      <button type="button" onClick={() => onAdjustBlock(entry.block.id, 1)} aria-label={`增加${entry.block.label}`}>+</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
            {resolution ? <p className="builder-facts">{Object.entries(resolution.composition).map(([element, count]) => `${element}${count > 1 ? count : ''}`).join(' ')}<span>总电荷 {resolution.totalCharge > 0 ? '+' : ''}{resolution.totalCharge}</span></p> : null}
          </div>
        </div>
        <div className="builder-matches" aria-live="polite">
          <strong>候选物质</strong>
          {!resolution ? <p>添加素材后显示结果。</p> : loading ? <p>匹配中…</p> : !matches.length ? (
            <p>未找到匹配物质</p>
          ) : (
            <>
              <p>{matches.length === 1 ? '1 个候选' : `${matches.length} 个候选`}</p>
              <div className="builder-match-list">
                {matches.map((species) => (
                  <SpeciesBlock
                    key={species.applicationId}
                    species={species}
                    showChineseNames={showChineseNames}
                    onAddToSide={onAddToSide}
                    onDragStart={onDragStart}
                    onDragEnd={onDragEnd}
                  />
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </section>
  )
}

function BuilderBlockGroup({
  title,
  blocks,
  onAddBlock,
}: {
  title: string
  blocks: BuilderBlock[]
  onAddBlock: (block: BuilderBlock) => void
}) {
  if (!blocks.length) return null
  return (
    <div className="builder-block-group">
      <strong>{title}</strong>
      <div className="builder-blocks">
        {blocks.map((block) => (
          <button type="button" key={block.id} onClick={() => onAddBlock(block)} aria-label={`添加${block.label}`}>
            <ChemistryNotation formula={block.formula} charge={block.charge} />
            <span>{block.label}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

export default function EquationLab({ onBack, onNavigate, reactionId }: EquationLabProps) {
  return (
    <EquationLabView
      onBack={onBack}
      onNavigate={onNavigate}
      onBalance={balanceEquation}
      onFindCandidates={findReactionCandidates}
      onCompleteSpecies={completeCatalogSpecies}
      onLoadReactionDetail={loadReactionDetail}
      reactionId={reactionId}
    />
  )
}
