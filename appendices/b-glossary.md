# Appendix B — Glossary

Terms as this book uses them, with the chapter that covers each properly.

**Artefact** — a file the agent produced. For most deep agents this is the deliverable, not
the final message. → Ch 4, 26

**Backend** — where the filesystem tools actually store files: graph state, real disk, or a
Store. The decision with the largest blast radius in the book. → Ch 8

**`CompositeBackend`** — routes paths to different backends. The realistic production shape,
and a **security boundary**. → Ch 8, 28

**`create_deep_agent`** — the constructor. Returns a LangGraph `CompiledStateGraph` — the same
object `create_agent` returns, with the harness's middleware attached. → Ch 2, 5

**`create_file_data`** — builds the `{content, encoding, created_at, modified_at}` dict for
seeding `files`. → Ch 4

**`DeepAgentState`** — the state schema carrying `files`. Subclass it when extending state;
subclassing anything else loses the filesystem. → Ch 14

**Deep agent** — an agent with a harness: filesystem, subagents, planning, skills, memory. Use
one when the task is long and **context is the problem**. → Ch 1

**`FilesystemBackend`** — real files on real disk. Its own docstring calls it a security
warning. **`virtual_mode=True` is not a sandbox** — it constrains paths, not access. → Ch 8, 28

**Harness** — the middleware Deep Agents pre-attaches. You configure it; you do not implement
it, and you cannot remove it. → Ch 1, 14

**`interrupt_on`** — pause before named tools for approval. LangGraph's `interrupt()`
underneath; needs a checkpointer **to resume**. → Ch 13

**Progressive disclosure** — advertising a skill by name and description on every call, and
loading its body only when the agent decides it applies. → Ch 10

**`response_format`** — a schema for the final answer; adds `structured_response` **alongside**
`messages` and `files`. Guarantees shape, not correctness. → Ch 15

**Skill** — a folder with a `SKILL.md` and required frontmatter. Instructions, **not a tool**,
appearing in the system prompt one line each. Needs a backend; **not inherited by subagents**.
→ Ch 10

**`StateBackend`** — the default. Files live in graph state; nothing touches disk. Right for
almost everything. → Ch 8

**`StoreBackend`** — files in a LangGraph Store, so they outlive the thread. `namespace` is a
**callable**, and it is the access-control boundary. → Ch 8, 11, 28

**Subagent** — a fresh agent spawned by `task`, with an isolated context. Measured: its model
call saw **2 messages, not the parent's history**. Only its answer returns. → Ch 9

**`task`** — the delegation tool. `description` is the **entire brief**; there is no follow-up.
→ Ch 9

**`TodoListMiddleware`** — enables `write_todos`. From `langchain.agents.middleware`, and
**not enabled by default** despite what most write-ups say. → Ch 6

**Todos** — the agent's plan, in state. Advisory, not enforced. **Survives summarisation**, and
an unchanged list is the best stuck-detector available. → Ch 6, 22

**Virtual filesystem** — the `files` state field: a dict keyed by absolute path. Exists so the
agent's working area is **not its message list**. → Ch 4, 7

**`write_todos`** — the planning tool. Rewrites the whole list; statuses are `pending`,
`in_progress`, `completed`. → Ch 6

---

Previous: [Appendix A — API cheatsheet](a-cheatsheet.md) ·
Next: [Appendix C — Further reading](c-further-reading.md)
