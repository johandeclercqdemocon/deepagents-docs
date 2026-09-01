"""`scout` -- the running example: an incident investigator.

Given a small file tree of logs, config and runbooks, it plans, reads, delegates
and writes a findings report. It exercises every capability the harness adds:
todos, the virtual filesystem, subagents, and skills.

Everything is deterministic. `ScriptedModel` replays fixed replies with real tool
calls, so the harness drives it exactly as it would drive Claude -- and every
output printed in this book is reproducible, offline, and free.
"""

from __future__ import annotations

import pathlib

from deepagents import create_deep_agent
from langchain.agents.middleware import TodoListMiddleware
from langchain_core.tools import tool

from .fakes import ScriptedModel
from .workspace import seed

SKILLS_DIR = pathlib.Path(__file__).parent / "skills"

SYSTEM_PROMPT = """You investigate production incidents.

Work from the files you are given. Read the logs, check the config against the
runbooks, and write your conclusion to /findings.md. Cite the file each claim
came from. If the evidence does not support a conclusion, say so."""


@tool(parse_docstring=True)
def check_metric(name: str) -> str:
    """Look up the current value of a named infrastructure metric.

    Args:
        name: One of "disk_used_pct", "jitter_ms", "error_rate".
    """
    return {
        "disk_used_pct": "node-3 disk_used_pct = 97",
        "jitter_ms": "node-3 jitter_ms = 38",
        "error_rate": "api error_rate = 0.04",
    }.get(name, f"unknown metric {name!r}")


TOOLS = [check_metric]

# The investigation the book walks through, as a fixed script.
DEFAULT_SCRIPT = [
    {
        "text": "Planning the investigation.",
        "tool_calls": [
            {
                "name": "write_todos",
                "args": {
                    "todos": [
                        {"content": "Read the logs", "status": "in_progress"},
                        {"content": "Check config against the runbook", "status": "pending"},
                        {"content": "Write findings", "status": "pending"},
                    ]
                },
            }
        ],
    },
    {
        "text": "Finding the errors.",
        "tool_calls": [{"name": "grep", "args": {"pattern": "ERROR", "path": "/logs"}}],
    },
    {
        "text": "Reading the runbook.",
        "tool_calls": [{"name": "read_file", "args": {"file_path": "/runbooks/disk.md"}}],
    },
    {
        "text": "Confirming with a metric.",
        "tool_calls": [{"name": "check_metric", "args": {"name": "disk_used_pct"}}],
    },
    {
        "text": "Writing it up.",
        "tool_calls": [
            {
                "name": "write_file",
                "args": {
                    "file_path": "/findings.md",
                    "content": (
                        "# node-3 outage\n\n"
                        "Disk exhaustion, not media storage.\n\n"
                        "- `no space left on device` at 09:41 [/logs/api.log]\n"
                        "- disk_used_pct = 97 [check_metric]\n"
                        "- log_retention_days set but never applied [/config/limits.yaml]\n"
                        "- runbook predicts exactly this [/runbooks/disk.md]\n"
                    ),
                },
            }
        ],
    },
    {"text": "Root cause: log retention was never enforced on node-3."},
]


def build(script: list | None = None, *, todos: bool = True, **kwargs):
    """The scout agent.

    `todos=True` adds `TodoListMiddleware`. It is NOT on by default in
    deepagents 0.7.11 despite what most write-ups say -- see Chapter 6.

    Swap `ScriptedModel` for a real one to spend money:

        build(model="claude-sonnet-5")
    """
    middleware = [TodoListMiddleware()] if todos else []
    kwargs.setdefault("model", ScriptedModel(script=script or DEFAULT_SCRIPT))
    return create_deep_agent(
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
        middleware=middleware,
        **kwargs,
    )


def investigate(agent=None, question: str = "why did node-3 fail?") -> dict:
    """Run the investigation against the seeded workspace."""
    agent = agent or build()
    return agent.invoke({"messages": [{"role": "user", "content": question}], "files": seed()})
