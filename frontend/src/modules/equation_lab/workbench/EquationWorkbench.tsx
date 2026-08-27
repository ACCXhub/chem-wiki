import { useRef, useState, type DragEvent, type FormEvent, type KeyboardEvent, type MouseEvent } from 'react'

import ChemistryNotation from '../ChemistryNotation'
import type {
  BalanceEquationResponse,
  EquationDraft,
  EquationDraftParticipant,
  EquationMode,
  EquationPhase,
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
  result: BalanceEquationResponse | null
  error: string | null
  loading: boolean
  autoBalance: boolean
  dragTarget: DragTarget | null
  duplicatePulse: string | null
  canUndo: boolean
  canRedo: boolean
  onSubmit: (event: FormEvent) => void
  onModeChange: (mode: EquationMode) => void
  onAutoBalanceChange: (enabled: boolean) => void
  onClearDraft: () => void
  onUndo: () => void
  onRedo: () => void
  onCopy: () => Promise<void>
  onClearSide: (side: DraftSide) => void
  onRemove: (side: DraftSide, applicationId: string) => void
  onPhase: (side: DraftSide, applicationId: string, phase: EquationPhase | null) => void
  onWorkbenchDragOver: (event: DragEvent<HTMLElement>) => void
  onWorkbenchDragLeave: (event: DragEvent<HTMLElement>) => void
  onParticipantDragOver: (event: DragEvent<HTMLElement>, target: DragTarget) => void
  onParticipantDragStart: (side: DraftSide, applicationId: string) => void
  onDrop: (event: DragEvent<HTMLElement>, target?: DragTarget) => void
  onDragEnd: () => void
}

export default function EquationWorkbench({
  draft,
  result,
  error,
  loading,
  autoBalance,
  dragTarget,
  duplicatePulse,
  canUndo,
  canRedo,
  onSubmit,
  onModeChange,
  onAutoBalanceChange,
  onClearDraft,
  onUndo,
  onRedo,
  onCopy,
  onClearSide,
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

  const copy = () => {
    void onCopy().then(() => {
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1200)
    })
  }

  const stateLabel = loading
    ? '正在配平…'
    : error
      ? '无法配平'
      : result
        ? '已配平'
        : '草稿'

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
          <label className="auto-balance-control">
            <input type="checkbox" checked={autoBalance} onChange={(event) => onAutoBalanceChange(event.target.checked)} />
            <span>自动配平</span><strong>{autoBalance ? 'ON' : 'OFF'}</strong>
          </label>
          <button className="history-button" type="button" onClick={onUndo} disabled={!canUndo} aria-label="撤销">↶</button>
          <button className="history-button" type="button" onClick={onRedo} disabled={!canRedo} aria-label="重做">↷</button>
          <button className="clear-draft" type="button" onClick={onClearDraft} disabled={!draft.reactants.length && !draft.products.length}>清空</button>
        </div>
      </div>

      <div
        className={`equation-composer ${dragTarget ? 'is-dragging' : ''}`}
        aria-label="结构化方程式草稿"
        onDragOver={onWorkbenchDragOver}
        onDragLeave={onWorkbenchDragLeave}
        onDrop={(event) => onDrop(event)}
      >
        <DraftSidePanel
          title="反应物"
          side="reactants"
          participants={draft.reactants}
          dragTarget={dragTarget}
          duplicatePulse={duplicatePulse}
          onClear={() => onClearSide('reactants')}
          onRemove={onRemove}
          onPhase={onPhase}
          onParticipantDragOver={onParticipantDragOver}
          onParticipantDragStart={onParticipantDragStart}
          onDrop={onDrop}
          onDragEnd={onDragEnd}
        />
        <div className="composer-arrow" aria-label="生成">→</div>
        <DraftSidePanel
          title="生成物"
          side="products"
          participants={draft.products}
          dragTarget={dragTarget}
          duplicatePulse={duplicatePulse}
          onClear={() => onClearSide('products')}
          onRemove={onRemove}
          onPhase={onPhase}
          onParticipantDragOver={onParticipantDragOver}
          onParticipantDragStart={onParticipantDragStart}
          onDrop={onDrop}
          onDragEnd={onDragEnd}
        />
      </div>

      <section className="equation-live-surface" aria-live="polite" aria-label="实时方程式">
        <div className="live-heading"><p>实时方程式</p><span className={`equation-state ${error ? 'is-error' : ''}`}>{stateLabel}</span></div>
        <div className="live-equation-row"><LiveEquation draft={draft} result={result} /><button type="button" className="copy-equation" onClick={copy}>{copied ? '已复制' : '复制'}</button></div>
        {error ? <div className="lab-error compact" role="alert"><strong>无法配平</strong><span>{error}</span></div> : null}
        {result ? <EquationResultDetails result={result} /> : null}
      </section>

      <div className="composer-actions">
        <p>{draft.mode === 'net_ionic' && draft.reactants.length && !draft.products.length
          ? '净离子模式可检查“无净离子反应”。'
          : autoBalance ? '从物质库拖入；有效草稿会自动配平。' : '自动配平已关闭；完成编辑后可手动配平。'}</p>
        {!autoBalance ? <button className="lab-submit" type="submit" disabled={loading || !canSubmit}>{loading ? '正在计算…' : '配平'}</button> : null}
      </div>
    </form>
  )
}

function LiveEquation({ draft, result }: { draft: EquationDraft; result: BalanceEquationResponse | null }) {
  if (result) return <div className="formatted-equation" aria-label="配平结果">{result.formattedEquation}</div>
  const renderSide = (participants: EquationDraftParticipant[]) => participants.length
    ? participants.map((participant, index) => <span className="live-term" key={participant.applicationId}>{index ? <span className="live-plus"> + </span> : null}<ChemistryNotation formula={participant.formula} charge={participant.charge} phase={participant.phase} /></span>)
    : <span className="live-placeholder">{draft.reactants.length ? '等待生成物' : '从下方物质库拖放'}</span>
  return <div className="formatted-equation live-draft">{renderSide(draft.reactants)}{draft.reactants.length ? <span className="live-arrow"> → </span> : null}{draft.reactants.length ? renderSide(draft.products) : null}</div>
}

interface DraftSidePanelProps {
  title: string
  side: DraftSide
  participants: EquationDraftParticipant[]
  dragTarget: DragTarget | null
  duplicatePulse: string | null
  onClear: () => void
  onRemove: (side: DraftSide, applicationId: string) => void
  onPhase: (side: DraftSide, applicationId: string, phase: EquationPhase | null) => void
  onParticipantDragOver: (event: DragEvent<HTMLElement>, target: DragTarget) => void
  onParticipantDragStart: (side: DraftSide, applicationId: string) => void
  onDrop: (event: DragEvent<HTMLElement>, target?: DragTarget) => void
  onDragEnd: () => void
}

function DraftSidePanel({ title, side, participants, dragTarget, duplicatePulse, onClear, onRemove, onPhase, onParticipantDragOver, onParticipantDragStart, onDrop, onDragEnd }: DraftSidePanelProps) {
  return (
    <section
      className={`draft-side ${dragTarget?.side === side ? 'is-drag-target' : ''}`}
      aria-label={title}
      onDragOver={(event) => { event.stopPropagation(); onParticipantDragOver(event, { side }) }}
      onDrop={(event) => { event.stopPropagation(); onDrop(event, { side }) }}
    >
      <header><h2>{title}</h2><button type="button" onClick={onClear} disabled={!participants.length}>清空</button></header>
      {!participants.length ? <p className="draft-placeholder">拖到这里</p> : null}
      <div className="draft-participants">
        {participants.map((participant, index) => (
          <ParticipantBlock
            key={participant.applicationId}
            participant={participant}
            side={side}
            index={index}
            isDropTarget={dragTarget?.side === side && dragTarget.index === index}
            isPulsing={duplicatePulse === `${side}:${participant.applicationId}`}
            onRemove={onRemove}
            onPhase={onPhase}
            onDragOver={onParticipantDragOver}
            onDragStart={onParticipantDragStart}
            onDrop={onDrop}
            onDragEnd={onDragEnd}
          />
        ))}
      </div>
    </section>
  )
}

interface ParticipantBlockProps {
  participant: EquationDraftParticipant
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

  const clearClickTimer = () => {
    if (clickTimer.current !== null) window.clearTimeout(clickTimer.current)
    clickTimer.current = null
  }
  const deferPhase = () => {
    if (suppressClick.current) return
    clearClickTimer()
    clickTimer.current = window.setTimeout(() => { setPhaseOpen((current) => !current); clickTimer.current = null }, 180)
  }
  const handleDoubleClick = (event: MouseEvent<HTMLElement>) => {
    event.preventDefault()
    clearClickTimer()
    setPhaseOpen(false)
    onRemove(side, participant.applicationId)
  }
  const handleKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); clearClickTimer(); setPhaseOpen((current) => !current) }
    if (event.key === 'Delete' || event.key === 'Backspace') { event.preventDefault(); clearClickTimer(); setPhaseOpen(false); onRemove(side, participant.applicationId) }
  }
  const handleDragStart = (event: DragEvent<HTMLElement>) => {
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
  return (
    <div
      className={`draft-participant kind-${participant.entityKind} ${isDropTarget ? 'is-drop-target' : ''} ${isPulsing ? 'is-pulsing' : ''}`}
      draggable
      tabIndex={0}
      onClick={deferPhase}
      onDoubleClick={handleDoubleClick}
      onKeyDown={handleKeyDown}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      onDragOver={(event) => { event.stopPropagation(); onDragOver(event, { side, index }) }}
      onDrop={(event) => { event.stopPropagation(); onDrop(event, { side, index }) }}
      aria-label={`${participant.nameZh}，点击编辑物态，双击移除`}
    >
      <ChemistryNotation formula={participant.formula} charge={participant.charge} phase={participant.phase} />
      <span>{participant.nameZh}</span>
      {phaseOpen ? <div className="phase-selector" role="group" aria-label={`${participant.nameZh}的物态`} onClick={(event) => event.stopPropagation()}>
        {([null, 's', 'l', 'g', 'aq'] as Array<EquationPhase | null>).map((phase) => <button key={phase ?? 'none'} type="button" aria-pressed={participant.phase === phase} onClick={() => { onPhase(side, participant.applicationId, phase); setPhaseOpen(false) }}>{phase ? `(${phase})` : '—'}</button>)}
      </div> : null}
    </div>
  )
}

function EquationResultDetails({ result }: { result: BalanceEquationResponse }) {
  const inputLabel = result.state === 'no_net_ionic' ? '无净离子反应' : result.inputState === 'balanced' ? '输入已经守恒' : '输入未配平，已求得最简整数比'
  return <details className="equation-result-details"><summary><span className={`lab-status state-${result.state}`}>{inputLabel}</span><span>守恒详情</span></summary>{result.message ? <p className="lab-message">{result.message}</p> : null}{result.phenomenon ? <p className="lab-phenomenon"><strong>现象</strong>{result.phenomenon}</p> : null}{result.products.length > 0 && result.conservation.elements.length > 0 ? <div className="conservation-table-wrap"><table><caption>守恒核对</caption><thead><tr><th>项目</th><th>反应物侧</th><th>生成物侧</th><th>状态</th></tr></thead><tbody>{result.conservation.elements.map((item) => <tr key={item.element}><th>{item.element}</th><td>{item.reactants}</td><td>{item.products}</td><td>{item.conserved ? '守恒' : '不守恒'}</td></tr>)}{result.conservation.charge ? <tr><th>总电荷</th><td>{result.conservation.charge.reactants}</td><td>{result.conservation.charge.products}</td><td>{result.conservation.charge.conserved ? '守恒' : '不守恒'}</td></tr> : null}</tbody></table></div> : null}<aside className="redox-boundary"><strong>不从配平结果推断机理</strong><p>{result.redox.message}</p></aside></details>
}
