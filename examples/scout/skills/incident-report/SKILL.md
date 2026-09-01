---
name: incident-report
description: House format for writing a post-incident findings report, with the required sections and the citation rule
---

# Incident report format

## When to use

When writing anything to `/findings.md` or any file the incident review will read.

## Instructions

Use exactly these sections, in this order:

1. `# <node> outage` — one line stating the root cause.
2. `## Evidence` — a bullet per fact, each ending with `[source]` naming the file or
   tool it came from.
3. `## Not the cause` — what you ruled out, and why. Reviewers ask this first.
4. `## Action` — one sentence, imperative.

Never state a cause you cannot cite. "Probably" belongs in `## Not the cause`.
