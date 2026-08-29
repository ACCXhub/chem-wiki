import type { CSSProperties } from 'react'

import type { ReactionCandidate } from '../types'
import { ChemistryEquation } from '../ChemistryNotation'


interface ReactionCandidatesProps {
  candidates: ReactionCandidate[]
  selectedId: string | null
  loading: boolean
  error: string | null
  onSelect: (candidate: ReactionCandidate) => void
}

const ORBIT_LIMIT = 6

function candidateLabel(candidate: ReactionCandidate) {
  return candidate.equation ?? candidate.nameZh
}

export default function ReactionCandidates({
  candidates,
  selectedId,
  loading,
  error,
  onSelect,
}: ReactionCandidatesProps) {
  if (loading && !candidates.length) {
    return <div className="reaction-candidate-state" aria-live="polite">正在查找相关反应…</div>
  }
  if (error) return <div className="reaction-candidate-state is-error" role="alert">{error}</div>
  if (!candidates.length) return null

  const selected = candidates.find((candidate) => candidate.consolidatedId === selectedId)
  const center = selected ?? candidates[0]
  const alternatives = candidates
    .filter((candidate) => candidate.consolidatedId !== center.consolidatedId)
    .slice(0, ORBIT_LIMIT - 1)
  const hiddenCount = Math.max(0, candidates.length - alternatives.length - 1)

  if (candidates.length === 1) return null

  return (
    <section className="reaction-candidates" aria-labelledby="candidate-heading">
      <div className="candidate-heading">
        <h2 id="candidate-heading">候选反应</h2>
        <span>{candidates.length} 个匹配</span>
      </div>
      <div className="reaction-cluster" aria-label="相关反应">
        <CandidateButton candidate={center} central onSelect={onSelect} />
        {alternatives.map((candidate, index) => (
          <CandidateButton
            key={candidate.consolidatedId}
            candidate={candidate}
            index={index}
            count={alternatives.length}
            onSelect={onSelect}
          />
        ))}
      </div>
      {hiddenCount ? <p className="candidate-overflow">另有 {hiddenCount} 个相关反应</p> : null}
    </section>
  )
}

function CandidateButton({
  candidate,
  central = false,
  index = 0,
  count = 1,
  onSelect,
}: {
  candidate: ReactionCandidate
  central?: boolean
  index?: number
  count?: number
  onSelect: (candidate: ReactionCandidate) => void
}) {
  const angle = (-90 + (360 / count) * index) * (Math.PI / 180)
  const style = central ? undefined : ({
    '--candidate-x': `${Math.cos(angle) * 15}rem`,
    '--candidate-y': `${Math.sin(angle) * 3.6}rem`,
  } as CSSProperties)
  return (
    <button
      className={`reaction-candidate ${central ? 'is-central' : 'is-alternative'}`}
      type="button"
      style={style}
      onClick={() => onSelect(candidate)}
      aria-label={`选择反应 ${candidate.nameZh}`}
    >
      <strong>{candidate.equation ? <ChemistryEquation expression={candidate.equation} /> : candidateLabel(candidate)}</strong>
      <span>{candidate.nameZh}</span>
    </button>
  )
}
