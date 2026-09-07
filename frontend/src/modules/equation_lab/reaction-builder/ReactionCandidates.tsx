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
  const visibleCandidates = selected
    ? [selected, ...candidates.filter((candidate) => candidate.consolidatedId !== selected.consolidatedId)].slice(0, ORBIT_LIMIT)
    : candidates.slice(0, ORBIT_LIMIT)
  const hiddenCount = Math.max(0, candidates.length - visibleCandidates.length)

  if (candidates.length === 1) return null

  return (
    <section className="reaction-candidates" aria-labelledby="candidate-heading">
      <div className="candidate-heading">
        <div>
          <span>Reaction Match</span>
          <h2 id="candidate-heading">候选反应</h2>
        </div>
        <span>{candidates.length} 个匹配</span>
      </div>
      <div className="reaction-list" aria-label="相关反应">
        {visibleCandidates.map((candidate, index) => (
          <CandidateButton
            key={candidate.consolidatedId}
            candidate={candidate}
            selected={candidate.consolidatedId === selectedId}
            primary={!selectedId && index === 0}
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
  selected,
  primary,
  onSelect,
}: {
  candidate: ReactionCandidate
  selected: boolean
  primary: boolean
  onSelect: (candidate: ReactionCandidate) => void
}) {
  return (
    <button
      className={`reaction-candidate ${selected || primary ? 'is-central' : 'is-alternative'} ${selected ? 'is-selected' : ''} ${primary ? 'is-primary' : ''}`}
      type="button"
      onClick={() => onSelect(candidate)}
      aria-label={`选择反应 ${candidate.nameZh}`}
      aria-pressed={selected}
    >
      <span className="candidate-content">
        <strong>{candidate.equation ? <ChemistryEquation expression={candidate.equation} /> : candidateLabel(candidate)}</strong>
        <span>{candidate.nameZh}</span>
      </span>
      {selected ? <span className="candidate-selected-label">已选择</span> : null}
    </button>
  )
}
