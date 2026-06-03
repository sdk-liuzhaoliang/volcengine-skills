#!/usr/bin/env python3
"""Validate the Codex plugin marketplace layout for this repository."""

from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE_PATH = REPO_ROOT / ".agents" / "plugins" / "marketplace.json"
PLUGIN_NAME = "volcengine-skills"
PLUGIN_PATH = "./plugins/volcengine-skills"


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"missing {path.relative_to(REPO_ROOT)}")
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON in {path.relative_to(REPO_ROOT)}: {exc}")


def main() -> None:
    marketplace = load_json(MARKETPLACE_PATH)
    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list):
        fail("marketplace plugins must be a list")

    matches = [plugin for plugin in plugins if plugin.get("name") == PLUGIN_NAME]
    if len(matches) != 1:
        fail(f"expected exactly one {PLUGIN_NAME!r} marketplace entry")

    entry = matches[0]
    source = entry.get("source")
    if not isinstance(source, dict):
        fail("plugin source must be an object")
    if source.get("source") != "local":
        fail("plugin source.source must be 'local'")

    relative_path = source.get("path")
    if not isinstance(relative_path, str) or not relative_path:
        fail("plugin source.path must be a non-empty string")
    if relative_path != PLUGIN_PATH:
        fail(f"plugin source.path must be {PLUGIN_PATH!r}")
    if Path(relative_path).is_absolute():
        fail("plugin source.path must be relative")

    plugin_root = (REPO_ROOT / relative_path).resolve()
    manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
    if not manifest_path.is_file():
        fail(f"plugin source.path does not resolve to .codex-plugin/plugin.json: {relative_path}")

    manifest = load_json(manifest_path)
    if manifest.get("name") != entry.get("name"):
        fail("marketplace entry name must match plugin.json name")

    policy = entry.get("policy")
    if not isinstance(policy, dict):
        fail("plugin entry policy must be an object")
    if policy.get("installation") not in {"NOT_AVAILABLE", "AVAILABLE", "INSTALLED_BY_DEFAULT"}:
        fail("plugin entry policy.installation is invalid")
    if policy.get("authentication") not in {"ON_INSTALL", "ON_USE"}:
        fail("plugin entry policy.authentication is invalid")
    if not isinstance(entry.get("category"), str) or not entry["category"]:
        fail("plugin entry category must be a non-empty string")

    print("Codex plugin layout validation passed")


if __name__ == "__main__":
    main()
