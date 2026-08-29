"""Deterministic application data setup for local development."""

import json

from sqlalchemy.orm import Session

from chem_wiki.config import Settings
from chem_wiki.infrastructure.database import create_database_engine
from chem_wiki.modules.element_data import (
    PubChemSnapshotAdapter,
    bootstrap_element_identities,
    import_pubchem_elements,
)


def main() -> None:
    engine = create_database_engine(Settings().database_url)
    try:
        with Session(engine) as session:
            identities = bootstrap_element_identities(session)
            properties = import_pubchem_elements(
                session,
                adapter=PubChemSnapshotAdapter(),
                atomic_numbers=range(1, 119),
            )
            session.commit()
        print(
            json.dumps(
                {
                    "elements": len(identities.element_ids),
                    "elementsCreated": identities.elements_created,
                    "identityClaimsCreated": identities.claims_created,
                    "propertyClaimsCreated": properties.claims_created,
                    "propertyPublicationsChanged": properties.publications_changed,
                    "sourceRecordsCreated": properties.source_records_created,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
