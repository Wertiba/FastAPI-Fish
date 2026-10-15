"""Выгрузить OpenAPI-схему для фронтенда:  python scripts/export_openapi.py [--out docs/openapi.json]"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app.bootstrap.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "openapi.json")
    args = parser.parse_args()

    settings = Settings(
        _env_file=None,
        APP_SECURITY_JWT_SECRET="export",  # noqa: S106
        LOG_FILE="",
        LOG_LEVEL="WARNING",
    )
    schema = create_app(settings).openapi()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"OpenAPI -> {args.out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
