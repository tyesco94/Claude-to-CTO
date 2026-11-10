"""Shared helpers for power-kit hooks. Standard library only."""
import hashlib
import json
import os
import re
import sys
from pathlib import Path


def read_hook_input():
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def kit_home():
    base = os.environ.get("POWER_KIT_HOME") or str(Path.home() / ".claude" / "power-kit")
    return Path(base)


def project_dir(cwd):
    """One memory folder per project, named after the folder plus a short hash of its path."""
    cwd = os.path.abspath(cwd or os.getcwd())
    name = re.sub(r"[^A-Za-z0-9_-]+", "-", os.path.basename(cwd) or "root").strip("-") or "root"
    digest = hashlib.sha1(cwd.encode("utf-8")).hexdigest()[:8]
    d = kit_home() / "memory" / f"{name}-{digest}"
    d.mkdir(parents=True, exist_ok=True)
    return d, cwd
