"""Выгрузить OpenAPI-схему для фронтенда:  python scripts/export_openapi.py [--out docs/openapi.json]"""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Схеме не нужны ни БД, ни секреты: конфиги читаются лениво, но логгер настраивается сразу.
os.environ.setdefault("LOG_CONSOLE_LEVEL", "WARNING")

from app.entrypoints.api import app  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "openapi.json")
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"OpenAPI -> {args.out.resolve().relative_to(ROOT)}")


if __name__ == "__main__":
    main()
