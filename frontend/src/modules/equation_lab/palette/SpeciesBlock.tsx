import { useState, type DragEvent, type KeyboardEvent, type MouseEvent } from 'react'

import ChemistryNotation from '../ChemistryNotation'
import type { CatalogSpecies } from '../types'

type DraftSide = 'reactants' | 'products'

interface SpeciesBlockProps {
  species: CatalogSpecies
  isFavorite?: boolean
  isRecent?: boolean
  favoriteLabel?: string
  onFavorite?: (species: CatalogSpecies) => void
  onAddToSide: (side: DraftSide, species: CatalogSpecies) => void
  onDragStart: (species: CatalogSpecies) => void
  onDragEnd: () => void
}

function setCompactDragImage(event: DragEvent<HTMLElement>, species: CatalogSpecies) {
  const ghost = document.createElement('div')
  ghost.className = 'species-drag-ghost'
  ghost.textContent = `${species.formula}  ${species.nameZh}`
  document.body.append(ghost)
  event.dataTransfer.setDragImage(ghost, 16, 16)
  window.setTimeout(() => ghost.remove(), 0)
}

export default function SpeciesBlock({
  species,
  isFavorite = false,
  isRecent = false,
  favoriteLabel,
  onFavorite,
  onAddToSide,
  onDragStart,
  onDragEnd,
}: SpeciesBlockProps) {
  const [placementOpen, setPlacementOpen] = useState(false)
  const [dragging, setDragging] = useState(false)
  const openPlacement = () => setPlacementOpen((current) => !current)

  const handleKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      openPlacement()
    }
  }

  const handleDragStart = (event: DragEvent<HTMLElement>) => {
    setDragging(true)
    event.dataTransfer.effectAllowed = 'copy'
    event.dataTransfer.setData('application/x-chem-wiki-species', species.applicationId)
    setCompactDragImage(event, species)
    onDragStart(species)
  }

  const handleDragEnd = () => {
    setDragging(false)
    onDragEnd()
  }

  const add = (event: MouseEvent<HTMLButtonElement>, side: DraftSide) => {
    event.stopPropagation()
    setPlacementOpen(false)
    onAddToSide(side, species)
  }

  return (
    <article
      className={`species-block kind-${species.entityKind} ${dragging ? 'is-dragging' : ''} ${placementOpen ? 'is-placement-open' : ''}`}
      draggable
      tabIndex={0}
      onClick={openPlacement}
      onKeyDown={handleKeyDown}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      aria-label={`拖拽物质 ${species.nameZh}`}
      title={species.nameEn ?? undefined}
    >
      <ChemistryNotation formula={species.formula} charge={species.charge} />
      <strong>{species.nameZh}</strong>
      {onFavorite ? (
        <button
          type="button"
          className="species-favorite"
          aria-pressed={isFavorite}
          onClick={(event) => { event.stopPropagation(); onFavorite(species) }}
          aria-label={favoriteLabel ?? `${isFavorite ? '取消收藏' : '收藏'}${species.nameZh}`}
        >
          {isFavorite ? '★' : '☆'}
        </button>
      ) : null}
      {isRecent ? <span className="recent-label">最近</span> : null}
      {placementOpen ? (
        <div className="species-placement" aria-label={`放置${species.nameZh}`}>
          <button type="button" onClick={(event) => add(event, 'reactants')}>放入反应物</button>
          <button type="button" onClick={(event) => add(event, 'products')}>放入生成物</button>
        </div>
      ) : null}
    </article>
  )
}
