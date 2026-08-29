import { useRef, useState, type DragEvent, type FormEvent, type KeyboardEvent, type MouseEvent } from 'react'

import ChemistryNotation, { ChemistryEquation } from '../ChemistryNotation'
import type {
  BalanceEquationResponse,
  CatalogReactionDetail,
  EquationDraft,
  EquationDraftParticipant,
  EquationMode,
  EquationPhase,
  ReactionCandidate,
  ReactionCandidateParticipant,
} from '../types'

export type DraftSide = 'reactants' | 'products'
export interface DragTarget { side: DraftSide; index?: number }

const MODE_LABELS: Record<EquationMode, string> = {
  molecular: '分子方程式',
  ionic: '离子方程式',
  net_ionic: '净离子方程式',
}

interface EquationWorkbenchProps {
  draft: EquationDraft
  focusedReaction: ReactionCandidate | null
  reactionDetail: CatalogReactionDetail | null
  reactionDetailLoading: boolean
  reactionDetailError: string | null
  result: BalanceEquationResponse | null
  error: string | null
  loading: boolean
  settled: boolean
  autoBalance: boolean
  dragTarget: DragTarget | null
  duplicatePulse: string | null
  canUndo: boolean
  canRedo: boolean
  manualInputOpen: boolean
  onSubmit: (event: FormEvent) => void
  onModeChange: (mode: EquationMode) => void
  onAutoBalanceChange: (enabled: boolean) => void
  onClearDraft: () => void
  onUndo: () => void
  onRedo: () => void
  onCopy: () => Promise<void>
  onManualInputToggle: () => void
  onEnterEdit: () => void
  onNavigateToElement: (symbol: string) => void
  onNavigateToStructure: (applicationId: string) => void
  onRemove: (side: DraftSide, applicationId: string) => void
  onPhase: (side: DraftSide, applicationId: string, phase: EquationPhase | null) => void
  onWorkbenchDragOver: (event: DragEvent<HTMLElement>) => void
  onWorkbenchDragLeave: (event: DragEvent<HTMLElement>) => void
  onParticipantDragOver: (event: DragEvent<HTMLElement>, target: DragTarget) => void
  onParticipantDragStart: (side: DraftSide, applicationId: string) => void
  onDrop: (event: DragEvent<HTMLElement>, target?: DragTarget) => void
  onDragEnd: () => void
}

interface DisplayParticipant {
  key: string
  applicationId: string | null
  nameZh: string
  formula: string
  charge: number
  phase: EquationPhase | null
  coefficient: number | string | null
  source: 'anchor' | 'canonical'
  entityKind: 'ion' | 'substance' | null
}

export default function EquationWorkbench({
  draft,
  focusedReaction,
  reactionDetail,
  reactionDetailLoading,
  reactionDetailError,
  result,
  error,
  loading,
  settled,
  autoBalance,
  dragTarget,
  duplicatePulse,
  canUndo,
  canRedo,
  manualInputOpen,
  onSubmit,
  onModeChange,
  onAutoBalanceChange,
  onClearDraft,
  onUndo,
  onRedo,
  onCopy,
  onManualInputToggle,
  onEnterEdit,
  onNavigateToElement,
  onNavigateToStructure,
  onRemove,
  onPhase,
  onWorkbenchDragOver,
  onWorkbenchDragLeave,
  onParticipantDragOver,
  onParticipantDragStart,
  onDrop,
  onDragEnd,
}: EquationWorkbenchProps) {
  const canSubmit = draft.reactants.length > 0 && (draft.products.length > 0 || draft.mode === 'net_ionic')
  const [copied, setCopied] = useState(false)
  const reactants = displayParticipants('reactants', draft, focusedReaction, result)
  const products = displayParticipants('products', draft, focusedReaction, result)
  const arrow = focusedReaction?.reversible ? '⇌' : '→'
  const settledExpression = result
    ? settledEquationExpression(reactants, products, focusedReaction?.reversible ?? false)
    : ''
  const stateLabel = loading ? '正在配平…' : error ? '配平失败' : result ? '已配平' : '配平工具'

  const copy = () => {
    void onCopy().then(() => {
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1200)
    })
  }

  return (
    <form className="composer-panel equation-workbench" onSubmit={onSubmit}>
      <div className="composer-toolbar">
        <div className="mode-switcher" role="group" aria-label="方程式模式">
          {Object.entries(MODE_LABELS).map(([value, label]) => (
            <button key={value} type="button" aria-pressed={draft.mode === value} onClick={() => onModeChange(value as EquationMode)}>
              {label}
            </button>
          ))}
        </div>
        <div className="workbench-controls">
          <button className="history-button" type="button" onClick={onUndo} disabled={!canUndo} aria-label="撤销">↶</button>
          <button className="history-button" type="button" onClick={onRedo} disabled={!canRedo} aria-label="重做">↷</button>
          <button className="copy-equation" type="button" onClick={copy} disabled={!reactants.length && !products.length}>{copied ? '已复制' : '复制'}</button>
          <button className="manual-input-toggle" type="button" aria-expanded={manualInputOpen} onClick={onManualInputToggle}>手动输入</button>
          <button className="clear-draft" type="button" onClick={onClearDraft} disabled={!draft.reactants.length && !draft.products.length}>清空</button>
        </div>
      </div>

      <div className={`equation-stage ${settled ? 'is-settled' : ''}`}>
        <div
          className={`equation-composer ${dragTarget ? 'is-dragging' : ''} ${focusedReaction ? 'is-focused' : ''}`}
          aria-label="结构化方程式草稿"
          aria-hidden={settled}
          onDragOver={onWorkbenchDragOver}
          onDragLeave={onWorkbenchDragLeave}
          onDrop={(event) => onDrop(event)}
        >
          <DraftSideLine side="reactants" participants={reactants} dragTarget={dragTarget} duplicatePulse={duplicatePulse} onRemove={onRemove} onPhase={onPhase} onParticipantDragOver={onParticipantDragOver} onParticipantDragStart={onParticipantDragStart} onDrop={onDrop} onDragEnd={onDragEnd} />
          <div className="composer-arrow" aria-label={focusedReaction?.reversible ? '可逆反应' : '生成'}>{arrow}</div>
          <DraftSideLine side="products" participants={products} dragTarget={dragTarget} duplicatePulse={duplicatePulse} onRemove={onRemove} onPhase={onPhase} onParticipantDragOver={onParticipantDragOver} onParticipantDragStart={onParticipantDragStart} onDrop={onDrop} onDragEnd={onDragEnd} />
        </div>
        <button className="settled-equation" type="button" aria-hidden={!settled} tabIndex={settled ? 0 : -1} aria-label={`编辑方程式：${settledExpression}`} onClick={onEnterEdit}>
          <ChemistryEquation expression={settledExpression} />
          <span>点击继续编辑</span>
        </button>
      </div>

      {focusedReaction ? (
        <FocusedReactionKnowledge
          reaction={focusedReaction}
          detail={reactionDetail}
          loading={reactionDetailLoading}
          error={reactionDetailError}
          onNavigateToElement={onNavigateToElement}
          onNavigateToStructure={onNavigateToStructure}
        />
      ) : null}
      {error ? <div className="lab-error compact" role="alert"><strong>无法配平</strong><span>{error}</span></div> : null}
      {result ? <EquationResultDetails result={result} /> : null}

      <details className="balance-tools">
        <summary>{stateLabel}</summary>
        <div className="balance-tool-row">
          <label className="auto-balance-control">
            <input type="checkbox" checked={autoBalance} onChange={(event) => onAutoBalanceChange(event.target.checked)} />
            <span>自动配平</span><strong>{autoBalance ? 'ON' : 'OFF'}</strong>
          </label>
          {!autoBalance ? <button className="lab-submit" type="submit" disabled={loading || !canSubmit}>{loading ? '正在计算…' : '配平'}</button> : null}
        </div>
      </details>
    </form>
  )
}

function canonicalRoleForSide(side: DraftSide, reaction: ReactionCandidate) {
  const canonicalRole = side === 'reactants' ? 'reactant' : 'product'
  if (reaction.orientation === 'canonical') return canonicalRole
  return canonicalRole === 'reactant' ? 'product' : 'reactant'
}

function displayParticipants(side: DraftSide, draft: EquationDraft, focusedReaction: ReactionCandidate | null, result: BalanceEquationResponse | null): DisplayParticipant[] {
  const anchors = draft[side]
  if (!focusedReaction) {
    return anchors.map((participant, index) => displayAnchor(participant, result?.[side][index]?.coefficient ?? null))
  }

  const canonical = focusedReaction.participants.filter((participant) => participant.role === canonicalRoleForSide(side, focusedReaction))
  const anchorById = new Map(anchors.map((participant) => [participant.applicationId, participant]))
  const represented = new Set<string>()
  const completed = canonical.flatMap((participant, index) => {
    const anchor = participant.applicationTargetId ? anchorById.get(participant.applicationTargetId) : undefined
    if (anchor) {
      represented.add(anchor.applicationId)
      return [{ ...displayAnchor(anchor, participant.coefficient), phase: anchor.phase ?? participant.phase }]
    }
    const projected = displayCanonical(participant, index)
    return projected ? [projected] : []
  })
  for (const anchor of anchors) {
    if (!represented.has(anchor.applicationId)) completed.push(displayAnchor(anchor, null))
  }
  return completed
}

function displayAnchor(participant: EquationDraftParticipant, coefficient: number | string | null): DisplayParticipant {
  return {
    key: participant.applicationId,
    applicationId: participant.applicationId,
    nameZh: participant.nameZh,
    formula: participant.formula,
    charge: participant.charge,
    phase: participant.phase,
    coefficient,
    source: 'anchor',
    entityKind: participant.entityKind,
  }
}

function displayCanonical(participant: ReactionCandidateParticipant, index: number): DisplayParticipant | null {
  if (!participant.formula && !participant.nonSpeciesRef) return null
  return {
    key: participant.applicationTargetId ?? participant.nonSpeciesRef ?? `canonical:${index}`,
    applicationId: participant.applicationTargetId,
    nameZh: participant.nameZh ?? participant.nonSpeciesRef ?? participant.formula ?? '参与者',
    formula: participant.formula ?? participant.nonSpeciesRef ?? '',
    charge: participant.charge ?? 0,
    phase: participant.phase,
    coefficient: participant.coefficient,
    source: 'canonical',
    entityKind: participant.targetType,
  }
}

interface DraftSideLineProps {
  side: DraftSide
  participants: DisplayParticipant[]
  dragTarget: DragTarget | null
  duplicatePulse: string | null
  onRemove: (side: DraftSide, applicationId: string) => void
  onPhase: (side: DraftSide, applicationId: string, phase: EquationPhase | null) => void
  onParticipantDragOver: (event: DragEvent<HTMLElement>, target: DragTarget) => void
  onParticipantDragStart: (side: DraftSide, applicationId: string) => void
  onDrop: (event: DragEvent<HTMLElement>, target?: DragTarget) => void
  onDragEnd: () => void
}

function DraftSideLine({ side, participants, dragTarget, duplicatePulse, onRemove, onPhase, onParticipantDragOver, onParticipantDragStart, onDrop, onDragEnd }: DraftSideLineProps) {
  const title = side === 'reactants' ? '反应物' : '生成物'
  return (
    <section className={`draft-side ${dragTarget?.side === side ? 'is-drag-target' : ''}`} aria-label={title} onDragOver={(event) => { event.stopPropagation(); onParticipantDragOver(event, { side }) }} onDrop={(event) => { event.stopPropagation(); onDrop(event, { side }) }}>
      <div className="draft-participants">
        {participants.map((participant, index) => (
          <span className="equation-term" key={participant.key}>
            {index ? <span className="equation-plus" aria-hidden="true">+</span> : null}
            <ParticipantBlock participant={participant} side={side} index={index} isDropTarget={dragTarget?.side === side && dragTarget.index === index} isPulsing={duplicatePulse === `${side}:${participant.applicationId}`} onRemove={onRemove} onPhase={onPhase} onDragOver={onParticipantDragOver} onDragStart={onParticipantDragStart} onDrop={onDrop} onDragEnd={onDragEnd} />
          </span>
        ))}
        {dragTarget?.side === side ? <span className="magnetic-drop-indicator" aria-hidden="true">放入{title}</span> : null}
      </div>
    </section>
  )
}

function settledEquationExpression(
  reactants: DisplayParticipant[],
  products: DisplayParticipant[],
  reversible: boolean,
): string {
  const formatTerm = (term: DisplayParticipant) => {
    const coefficient = term.coefficient === 1 ? '' : `${term.coefficient} `
    const chargeText = term.charge
      ? `^{${Math.abs(term.charge) === 1 ? '' : Math.abs(term.charge)}${term.charge > 0 ? '+' : '-'}}`
      : ''
    return `${coefficient}${term.formula}${chargeText}${term.phase ? `(${term.phase})` : ''}`
  }
  return `${reactants.map(formatTerm).join(' + ')} ${reversible ? '<=>' : '->'} ${products.map(formatTerm).join(' + ')}`
}

interface ParticipantBlockProps {
  participant: DisplayParticipant
  side: DraftSide
  index: number
  isDropTarget: boolean
  isPulsing: boolean
  onRemove: (side: DraftSide, applicationId: string) => void
  onPhase: (side: DraftSide, applicationId: string, phase: EquationPhase | null) => void
  onDragOver: (event: DragEvent<HTMLElement>, target: DragTarget) => void
  onDragStart: (side: DraftSide, applicationId: string) => void
  onDrop: (event: DragEvent<HTMLElement>, target?: DragTarget) => void
  onDragEnd: () => void
}

function ParticipantBlock({ participant, side, index, isDropTarget, isPulsing, onRemove, onPhase, onDragOver, onDragStart, onDrop, onDragEnd }: ParticipantBlockProps) {
  const [phaseOpen, setPhaseOpen] = useState(false)
  const clickTimer = useRef<number | null>(null)
  const suppressClick = useRef(false)
  const isAnchor = participant.source === 'anchor' && participant.applicationId !== null

  const clearClickTimer = () => {
    if (clickTimer.current !== null) window.clearTimeout(clickTimer.current)
    clickTimer.current = null
  }
  const deferPhase = () => {
    if (!isAnchor || suppressClick.current) return
    clearClickTimer()
    clickTimer.current = window.setTimeout(() => { setPhaseOpen((current) => !current); clickTimer.current = null }, 180)
  }
  const handleDoubleClick = (event: MouseEvent<HTMLElement>) => {
    if (!isAnchor || !participant.applicationId) return
    event.preventDefault()
    clearClickTimer()
    setPhaseOpen(false)
    onRemove(side, participant.applicationId)
  }
  const handleKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (!isAnchor || !participant.applicationId) return
    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); clearClickTimer(); setPhaseOpen((current) => !current) }
    if (event.key === 'Delete' || event.key === 'Backspace') { event.preventDefault(); clearClickTimer(); setPhaseOpen(false); onRemove(side, participant.applicationId) }
  }
  const handleDragStart = (event: DragEvent<HTMLElement>) => {
    if (!isAnchor || !participant.applicationId) { event.preventDefault(); return }
    suppressClick.current = true
    clearClickTimer()
    setPhaseOpen(false)
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('application/x-chem-wiki-participant', `${side}:${participant.applicationId}`)
    onDragStart(side, participant.applicationId)
  }
  const handleDragEnd = () => {
    onDragEnd()
    window.setTimeout(() => { suppressClick.current = false }, 140)
  }
  const gestureLabel = isAnchor ? '点击编辑物态，双击移除' : '由当前反应补全'
  return (
    <div className={`draft-participant kind-${participant.entityKind ?? 'reference'} source-${participant.source} ${isDropTarget ? 'is-drop-target' : ''} ${isPulsing ? 'is-pulsing' : ''}`} draggable={isAnchor} tabIndex={isAnchor ? 0 : undefined} onClick={deferPhase} onDoubleClick={handleDoubleClick} onKeyDown={handleKeyDown} onDragStart={handleDragStart} onDragEnd={handleDragEnd} onDragOver={(event) => { event.stopPropagation(); onDragOver(event, { side, index }) }} onDrop={(event) => { event.stopPropagation(); onDrop(event, { side, index }) }} aria-label={`${participant.nameZh}，${gestureLabel}`}>
      <ChemistryNotation formula={participant.formula} charge={participant.charge} phase={participant.phase} coefficient={participant.coefficient ?? undefined} />
      <span>{participant.nameZh}</span>
      {phaseOpen && participant.applicationId ? <div className="phase-selector" role="group" aria-label={`${participant.nameZh}的物态`} onClick={(event) => event.stopPropagation()}>
        {([null, 's', 'l', 'g', 'aq'] as Array<EquationPhase | null>).map((phase) => <button key={phase ?? 'none'} type="button" aria-pressed={participant.phase === phase} onClick={() => { onPhase(side, participant.applicationId as string, phase); setPhaseOpen(false) }}>{phase ? `(${phase})` : '—'}</button>)}
      </div> : null}
    </div>
  )
}

function FocusedReactionKnowledge({
  reaction,
  detail,
  loading,
  error,
  onNavigateToElement,
  onNavigateToStructure,
}: {
  reaction: ReactionCandidate
  detail: CatalogReactionDetail | null
  loading: boolean
  error: string | null
  onNavigateToElement: (symbol: string) => void
  onNavigateToStructure: (applicationId: string) => void
}) {
  const reactionTypes = detail?.reactionTypes ?? reaction.reactionTypes
  const conditions = detail?.conditions ?? reaction.conditions
  return (
    <section className="focused-reaction-knowledge" aria-label="当前反应">
      <div className="focused-reaction-summary">
        <div className="focused-reaction-title"><span>当前反应</span><strong>{reaction.nameZh}</strong></div>
        {detail?.equation ? <ChemistryEquation expression={detail.equation} /> : null}
        {reactionTypes.length ? <p><span>反应类型</span>{reactionTypes.join(' · ')}</p> : null}
        {conditions.length ? <p><span>反应条件</span>{conditions.join(' · ')}</p> : null}
      </div>
      {loading ? <span className="reaction-detail-state">正在加载反应知识…</span> : null}
      {error ? <span className="reaction-detail-state is-error">{error}</span> : null}
      {detail ? (
        <div className="reaction-learning-detail">
          {detail.phenomena.map((item) => (
            <details key={item.consolidatedId} className="reaction-learning-item">
              <summary>现象 · {item.displayNameZh}</summary>
              <p>{item.contentZh}</p>
            </details>
          ))}
          {detail.concepts.map((item) => (
            <details key={item.consolidatedId} className="reaction-learning-item">
              <summary>概念 · {item.displayNameZh}</summary>
              <p>{item.contentZh}</p>
            </details>
          ))}
          {detail.relatedSpecies.length ? (
            <details className="reaction-related-species">
              <summary>相关物质 · {detail.relatedSpecies.length}</summary>
              <div className="reaction-species-list">
                {detail.relatedSpecies.map((species) => (
                  <div className="reaction-species-item" key={species.applicationId}>
                    <span><ChemistryNotation formula={species.formula} charge={species.charge} /><strong>{species.nameZh}</strong></span>
                    <div>
                      {Object.keys(species.composition ?? {}).map((symbol) => (
                        <button key={symbol} type="button" onClick={() => onNavigateToElement(symbol)}>{symbol} 元素</button>
                      ))}
                      {species.structureAvailable ? (
                        <button type="button" onClick={() => onNavigateToStructure(species.applicationId)}>查看结构</button>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            </details>
          ) : null}
          {detail.sources.length ? (
            <details className="reaction-sources">
              <summary>来源</summary>
              <ul>{detail.sources.map((source) => (
                <li key={`${source.name}:${source.url ?? ''}`}>
                  {source.url ? <a href={source.url} target="_blank" rel="noreferrer">{source.name}</a> : source.name}
                </li>
              ))}</ul>
            </details>
          ) : null}
        </div>
      ) : null}
    </section>
  )
}

function EquationResultDetails({ result }: { result: BalanceEquationResponse }) {
  const inputLabel = result.state === 'no_net_ionic' ? '无净离子反应' : result.inputState === 'balanced' ? '输入已经守恒' : '输入未配平，已求得最简整数比'
  return <details className="equation-result-details"><summary><span className={`lab-status state-${result.state}`}>{inputLabel}</span><span>守恒详情</span></summary>{result.message ? <p className="lab-message">{result.message}</p> : null}{result.phenomenon ? <p className="lab-phenomenon"><strong>现象</strong>{result.phenomenon}</p> : null}{result.products.length > 0 && result.conservation.elements.length > 0 ? <div className="conservation-table-wrap"><table><caption>守恒核对</caption><thead><tr><th>项目</th><th>反应物侧</th><th>生成物侧</th><th>状态</th></tr></thead><tbody>{result.conservation.elements.map((item) => <tr key={item.element}><th>{item.element}</th><td>{item.reactants}</td><td>{item.products}</td><td>{item.conserved ? '守恒' : '不守恒'}</td></tr>)}{result.conservation.charge ? <tr><th>总电荷</th><td>{result.conservation.charge.reactants}</td><td>{result.conservation.charge.products}</td><td>{result.conservation.charge.conserved ? '守恒' : '不守恒'}</td></tr> : null}</tbody></table></div> : null}</details>
}
