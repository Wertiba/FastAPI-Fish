from math import isfinite
from typing import Any


def loc_to_field(loc: tuple[Any, ...]) -> str:
    parts = list(loc)
    if parts and parts[0] in ("body", "query", "path", "header", "cookie"):
        parts = parts[1:]
    out_parts: list[str] = []
    for p in parts:
        if isinstance(p, int):
            if not out_parts:
                out_parts.append(f"[{p}]")
            else:
                out_parts[-1] = f"{out_parts[-1]}[{p}]"
        else:
            out_parts.append(str(p))
    return ".".join(out_parts) if out_parts else ""


def rejected_value(err: dict[str, Any]) -> Any:
    inp = err.get("input")
    loc = err.get("loc", ())
    if isinstance(inp, dict) and loc:
        key = loc[-1]
        inp = inp.get(key)
    if isinstance(inp, float) and not isfinite(inp):
        return str(inp)
    return inp


def priority(err: dict[str, Any]) -> int:
    return 0 if "limit_value" in (err.get("ctx") or {}) else 1
