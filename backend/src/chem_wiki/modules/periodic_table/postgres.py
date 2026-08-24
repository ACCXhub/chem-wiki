"""PostgreSQL adapter for the M03 periodic-table read model."""

from sqlalchemy import and_, select
from sqlalchemy.orm import Session, aliased

from chem_wiki.modules.element_data import (
    ElementPropertyRow,
    ElementPublishedValueRow,
    ElementRow,
)

from .read_model import (
    CanonicalElementSnapshot,
    PeriodicTableElement,
    build_periodic_table,
    validate_canonical_range,
)


class PostgresPeriodicTableReader:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_elements(self) -> list[PeriodicTableElement]:
        electronegativity_publication = aliased(ElementPublishedValueRow)
        ionization_publication = aliased(ElementPublishedValueRow)
        rows = self._session.execute(
            select(
                ElementRow.id,
                ElementRow.atomic_number,
                ElementRow.symbol,
                ElementRow.name_zh,
                ElementRow.name_en,
                ElementPropertyRow.electronegativity_value,
                ElementPropertyRow.electronegativity_scale,
                ElementPropertyRow.first_ionization_energy_value,
                ElementPropertyRow.first_ionization_energy_unit,
                electronegativity_publication.claim_id.label("electronegativity_publication_id"),
                ionization_publication.claim_id.label("ionization_publication_id"),
            )
            .outerjoin(ElementPropertyRow, ElementPropertyRow.element_id == ElementRow.id)
            .outerjoin(
                electronegativity_publication,
                and_(
                    electronegativity_publication.element_id == ElementRow.id,
                    electronegativity_publication.field_name == "electronegativity",
                ),
            )
            .outerjoin(
                ionization_publication,
                and_(
                    ionization_publication.element_id == ElementRow.id,
                    ionization_publication.field_name == "first_ionization_energy",
                ),
            )
            .order_by(ElementRow.atomic_number)
        ).all()
        validate_canonical_range(row.atomic_number for row in rows)

        snapshots = [
            CanonicalElementSnapshot(
                id=row.id,
                atomic_number=row.atomic_number,
                symbol=row.symbol,
                name_zh=row.name_zh,
                name_en=row.name_en,
                electronegativity=(
                    float(row.electronegativity_value)
                    if row.electronegativity_publication_id is not None
                    and row.electronegativity_value is not None
                    else None
                ),
                electronegativity_scale=(
                    row.electronegativity_scale
                    if row.electronegativity_publication_id is not None
                    else None
                ),
                first_ionization_energy=(
                    float(row.first_ionization_energy_value)
                    if row.ionization_publication_id is not None
                    and row.first_ionization_energy_value is not None
                    else None
                ),
                first_ionization_energy_unit=(
                    row.first_ionization_energy_unit
                    if row.ionization_publication_id is not None
                    else None
                ),
            )
            for row in rows
        ]
        return build_periodic_table(snapshots)
