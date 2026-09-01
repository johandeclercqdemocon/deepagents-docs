"""Prove your environment works before you start Chapter 1.

    uv run python scripts/verify.py

Checks versions, that an agent builds, that the built-in filesystem tools work,
that planning is available once you ask for it, and that the example runs.
Needs no API key and makes no network calls.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TICKS: list[bool] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    TICKS.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}{'  ' + detail if detail else ''}")


def main() -> int:
    v = sys.version_info
    check("Python >= 3.11", v >= (3, 11), f"found {v.major}.{v.minor}.{v.micro}")

    try:
        import importlib.metadata as md

        for pkg, floor in (("deepagents", (0, 7)), ("langchain", (1, 3)), ("langgraph", (1, 2))):
            raw = md.version(pkg)
            parts = tuple(int(x) for x in raw.split(".")[:2])
            check(f"{pkg} >= {'.'.join(map(str, floor))}", parts >= floor, f"found {raw}")
    except Exception as exc:  # pragma: no cover
        check("packages importable", False, str(exc))
        return report()

    # An agent builds, and is a LangGraph graph underneath (Chapter 5).
    try:
        from deepagents import create_deep_agent

        from examples.scout.fakes import ScriptedModel

        agent = create_deep_agent(model=ScriptedModel(script=["ok"]))
        check("build a deep agent", type(agent).__name__ == "CompiledStateGraph",
              f"got {type(agent).__name__}")
    except Exception as exc:
        check("build a deep agent", False, repr(exc))
        return report()

    # The harness injects filesystem tools you never wrote.
    try:
        model = ScriptedModel(script=["ok"])
        create_deep_agent(model=model).invoke({"messages": [{"role": "user", "content": "hi"}]})
        expected = {"ls", "read_file", "write_file", "edit_file", "glob", "grep", "task"}
        check("built-in tools present", expected <= set(model.bound_tools),
              f"missing {sorted(expected - set(model.bound_tools))}" if not expected <= set(model.bound_tools) else "")
    except Exception as exc:
        check("built-in tools present", False, repr(exc))

    # Planning is opt-in, not default. Chapter 6.
    try:
        from langchain.agents.middleware import TodoListMiddleware

        m = ScriptedModel(script=["ok"])
        create_deep_agent(model=m, middleware=[TodoListMiddleware()]).invoke(
            {"messages": [{"role": "user", "content": "hi"}]}
        )
        check("planning available when asked", "write_todos" in m.bound_tools)
    except Exception as exc:
        check("planning available when asked", False, repr(exc))

    # The example investigates and writes a report.
    try:
        from examples.scout.agent import investigate

        out = investigate()
        wrote = "/findings.md" in out["files"]
        check("the scout example runs", wrote and bool(out.get("todos")),
              f"findings written={wrote}, todos={len(out.get('todos', []))}")
    except Exception as exc:
        check("the scout example runs", False, repr(exc))

    return report()


def report() -> int:
    print()
    if all(TICKS):
        print(f"All {len(TICKS)} checks passed. You are ready for Chapter 1.")
        return 0
    print(f"{TICKS.count(False)} of {len(TICKS)} checks failed. See README.md -> Before you begin.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
