import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Export this project's OpenAPI schema to a JSON file.")
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "docs" / "api-docs.json",
        help="Output path (default: docs/api-docs.json)",
    )
    args = parser.parse_args()

    from app.main import app

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote OpenAPI spec to {args.out}")


if __name__ == "__main__":
    main()
