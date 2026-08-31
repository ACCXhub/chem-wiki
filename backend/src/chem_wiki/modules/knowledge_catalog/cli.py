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
from .persistence import CatalogReleaseRow
from .release import PINNED_RELEASE


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import the pinned consolidated catalog")
    parser.add_argument(
        "--source",
        type=Path,
        default=(Path(value) if (value := os.environ.get("KNOWLEDGE_CATALOG_SOURCE")) else None),
        help="Local chem-knowledge-data checkout at the pinned release commit",
    )
    parser.add_argument(
        "--if-missing",
        action="store_true",
        help="Skip import when the pinned release already exists in catalog_release",
    )
    return parser


def main() -> None:
    arguments = _parser().parse_args()
    engine = create_database_engine(Settings().database_url)
    try:
        with Session(engine) as session:
            if arguments.if_missing and session.get(CatalogReleaseRow, PINNED_RELEASE.release):
                print(
                    json.dumps(
                        {"release": PINNED_RELEASE.release, "status": "already_imported"},
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                )
                return
            if arguments.source is None:
                raise SystemExit(
                    "数据库尚未导入 pinned catalog release；请设置 KNOWLEDGE_CATALOG_SOURCE "
                    "指向 chem-knowledge-data 的精确 pinned checkout"
                )
            result = import_consolidated_release(session, arguments.source)
            session.commit()
        print(json.dumps(asdict(result), ensure_ascii=False, sort_keys=True))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
