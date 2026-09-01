"""Run the scout example.

    uv run python -m examples.scout
"""

from .agent import build, investigate
from .workspace import seed


def main() -> None:
    print("== the workspace it starts with ==")
    for path in sorted(seed()):
        print(f"  {path}")

    out = investigate()

    print("\n== the investigation (ch 2-6) ==")
    for m in out["messages"]:
        print(f"  {type(m).__name__:13} {str(m.content)[:58]}")

    print("\n== plan it kept (ch 6) ==")
    for todo in out.get("todos", []):
        print(f"  [{todo['status']:11}] {todo['content']}")

    print("\n== files afterwards (ch 7) ==")
    for path in sorted(out["files"]):
        marker = "  <- written by the agent" if path == "/findings.md" else ""
        print(f"  {path}{marker}")

    print("\n== the report (ch 7) ==")
    for line in out["files"]["/findings.md"]["content"].splitlines():
        print(f"  {line}")

    print("\n== planning is opt-in, not default (ch 6) ==")
    for label, todos in (("with TodoListMiddleware", True), ("without", False)):
        print(f"  {label:24} write_todos offered: {'write_todos' in offered(todos=todos)}")


def offered(*, todos: bool) -> list[str]:
    """What the model is actually offered. Chapter 6 explains why this matters."""
    from .fakes import ScriptedModel

    model = ScriptedModel(script=["ok"])
    build(todos=todos, model=model).invoke({"messages": [{"role": "user", "content": "hi"}]})
    return model.bound_tools


if __name__ == "__main__":
    main()
