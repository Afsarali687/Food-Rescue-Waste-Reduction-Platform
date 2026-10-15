"""Part 1 checks: syntax, imports, config, and optional MongoDB ping."""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PYTHON_FILES = [
    ROOT / "app.py",
    ROOT / "seed_data.py",
    *sorted((ROOT / "food_rescue").glob("*.py")),
    *sorted((ROOT / "tests").glob("*.py")),
]


def check_syntax():
    failed = []
    for path in PYTHON_FILES:
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            failed.append(f"{path.name}: {exc}")
    return failed


def main():
    print("=== Syntax ===")
    syntax_errors = check_syntax()
    if syntax_errors:
        print("FAILED")
        for item in syntax_errors:
            print(" ", item)
        return 1
    print("OK — parsed", len(PYTHON_FILES), "Python files")

    print("=== Imports and config ===")
    from food_rescue import create_app
    from food_rescue.config import get_config

    config = get_config()
    print("MONGO_DB =", config["MONGO_DB"])
    print("MONGO_URI set =", bool(config["MONGO_URI"]))
    if "PASSWORD" in config["MONGO_URI"] and "USERNAME" not in config["MONGO_URI"]:
        print("WARNING: MONGO_URI looks like it may contain a real Atlas password. Do not commit .env.")

    app = create_app()
    print("create_app() OK")

    print("=== /health ===")
    client = app.test_client()
    response = client.get("/health")
    payload = response.get_json() or {}
    print("HTTP", response.status_code, payload.get("mongodb"), payload.get("status"))
    if response.status_code == 503:
        print("MongoDB was not reachable. Pages still run and show a warning.")
        print(payload.get("message"))
        print("What was NOT tested: live inserts, indexes on the server, and seed_data.py against a real database.")
        return 0

    print("MongoDB ping succeeded. Database:", payload.get("database"))
    print("Collection counts:", payload.get("collection_counts"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
