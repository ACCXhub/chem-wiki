"""PostgreSQL adapter for the M04 Element Wiki read model."""

from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from chem_wiki.modules.element_data import (
    ElementClaimRow,
    ElementPropertyRow,
    ElementPublishedValueRow,
    ElementSourceRecordRow,
    ElementSourceRow,
)
from chem_wiki.modules.periodic_table import PeriodicTableElement

from .read_model import (
    CanonicalElementWikiSnapshot,
    ElementWikiPage,
    PublishedFieldSource,
    build_element_wiki,
)


class PeriodicTableReader(Protocol):
    def list_elements(self) -> list[PeriodicTableElement]: ...


class PostgresElementWikiReader:
    def __init__(self, session: Session, periodic_table_reader: PeriodicTableReader) -> None:
        self._session = session
        self._periodic_table_reader = periodic_table_reader

    def get_element(self, element_id: UUID) -> ElementWikiPage | None:
        element = next(
            (
                candidate
                for candidate in self._periodic_table_reader.list_elements()
                if candidate.id == element_id
            ),
            None,
        )
        if element is None:
            return None

        property_row = self._session.execute(
            select(
                ElementPropertyRow.atomic_weight_value,
                ElementPropertyRow.atomic_weight_lower,
                ElementPropertyRow.atomic_weight_upper,
                ElementPropertyRow.atomic_weight_uncertainty,
                ElementPropertyRow.electronegativity_value,
                ElementPropertyRow.electronegativity_scale,
                ElementPropertyRow.first_ionization_energy_value,
                ElementPropertyRow.first_ionization_energy_unit,
                ElementPropertyRow.atomic_radius_value,
                ElementPropertyRow.atomic_radius_unit,
                ElementPropertyRow.atomic_radius_qualifier,
            ).where(ElementPropertyRow.element_id == element_id)
        ).one_or_none()
        published_rows = self._session.execute(
            select(
                ElementPublishedValueRow.field_name,
                ElementSourceRow.source_key,
                ElementSourceRow.title,
                ElementSourceRow.publisher,
                ElementSourceRecordRow.source_url,
                ElementSourceRow.base_url,
                ElementSourceRow.license_code,
                ElementSourceRecordRow.retrieved_at,
            )
            .join(ElementClaimRow, ElementClaimRow.id == ElementPublishedValueRow.claim_id)
            .join(
                ElementSourceRecordRow,
                ElementSourceRecordRow.id == ElementClaimRow.source_record_id,
            )
            .join(ElementSourceRow, ElementSourceRow.id == ElementSourceRecordRow.source_id)
            .where(ElementPublishedValueRow.element_id == element_id)
            .order_by(ElementSourceRow.source_key, ElementPublishedValueRow.field_name)
        ).all()

        def number(name: str) -> float | None:
            if property_row is None:
                return None
            value = getattr(property_row, name)
            return float(value) if value is not None else None

        def text(name: str) -> str | None:
            return getattr(property_row, name) if property_row is not None else None

        snapshot = CanonicalElementWikiSnapshot(
            atomic_weight_value=number("atomic_weight_value"),
            atomic_weight_lower=number("atomic_weight_lower"),
            atomic_weight_upper=number("atomic_weight_upper"),
            atomic_weight_uncertainty=number("atomic_weight_uncertainty"),
            electronegativity_value=number("electronegativity_value"),
            electronegativity_scale=text("electronegativity_scale"),
            first_ionization_energy_value=number("first_ionization_energy_value"),
            first_ionization_energy_unit=text("first_ionization_energy_unit"),
            atomic_radius_value=number("atomic_radius_value"),
            atomic_radius_unit=text("atomic_radius_unit"),
            atomic_radius_qualifier=text("atomic_radius_qualifier"),
            published_sources=tuple(
                PublishedFieldSource(
                    field_name=row.field_name,
                    source_key=row.source_key,
                    title=row.title,
                    publisher=row.publisher,
                    url=row.source_url or row.base_url,
                    license_code=row.license_code,
                    retrieved_at=row.retrieved_at,
                )
                for row in published_rows
            ),
        )
        return build_element_wiki(element, snapshot)
