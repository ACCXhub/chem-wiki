"""CLI for importing the pinned consolidated release from a local checkout/cache."""

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from sqlalchemy.orm import Session

from chem_wiki.config import Settings
from chem_wiki.infrastructure.database import create_database_engine

from .importer import import_consolidated_release


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import the pinned consolidated catalog")
    parser.add_argument(
        "--source",
        type=Path,
        default=(Path(value) if (value := os.environ.get("KNOWLEDGE_CATALOG_SOURCE")) else None),
        help="Local chem-knowledge-data checkout at the pinned release commit",
    )
    return parser


def main() -> None:
    arguments = _parser().parse_args()
    if arguments.source is None:
        raise SystemExit("--source or KNOWLEDGE_CATALOG_SOURCE is required")
    engine = create_database_engine(Settings().database_url)
    try:
        with Session(engine) as session:
            result = import_consolidated_release(session, arguments.source)
            session.commit()
        print(json.dumps(asdict(result), ensure_ascii=False, sort_keys=True))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
