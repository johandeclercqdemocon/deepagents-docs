"""The incident `scout` investigates, as a virtual filesystem.

Deep agents read and write files rather than passing everything through the
message list, so the example's input is a small file tree rather than a blob of
text. Seeding it here keeps every chapter's output reproducible.
"""

from __future__ import annotations

from deepagents.backends.utils import create_file_data

FILES: dict[str, str] = {
    "/logs/api.log": (
        "2026-08-31T09:38:02Z INFO  starting api v4.2.1\n"
        "2026-08-31T09:40:11Z WARN  disk usage 91% on node-3\n"
        "2026-08-31T09:41:03Z ERROR write failed: no space left on device\n"
        "2026-08-31T09:41:04Z ERROR write failed: no space left on device\n"
        "2026-08-31T09:41:20Z INFO  shedding load\n"
    ),
    "/logs/media.log": (
        "2026-08-31T09:40:58Z WARN  jitter 38ms exceeds threshold\n"
        "2026-08-31T09:41:05Z INFO  jitter buffer grown to 120ms\n"
    ),
    "/config/limits.yaml": (
        "node-3:\n"
        "  disk_quota: 10Gi\n"
        "  log_retention_days: 90    # never applied; see runbook\n"
    ),
    "/runbooks/disk.md": (
        "# Disk pressure\n\n"
        "`no space left on device` on a media node is almost always log retention,\n"
        "not media storage. Check log_retention_days is actually enforced.\n"
    ),
}


def seed() -> dict:
    """The `files` value to pass as agent input."""
    return {path: create_file_data(text) for path, text in FILES.items()}
