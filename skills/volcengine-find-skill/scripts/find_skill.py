#!/usr/bin/env python3
"""Mock Volcengine skill marketplace OpenAPI lookup.

This prototype keeps the interface stable while the real marketplace API is not
available yet. Replace MOCK_CATALOG and mock_openapi_search with an HTTP client
when the backend endpoint is ready.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Iterable


MARKETPLACE = "sdk-liuzhaoliang/volcengine-skills"


@dataclass(frozen=True)
class SkillRecord:
    plugin: str
    skill: str
    category: str
    triggers: tuple[str, ...]
    reason: str


MOCK_CATALOG: tuple[SkillRecord, ...] = (
    SkillRecord(
        plugin="volcengine-compute",
        skill="volcengine-compute-ecs-ops",
        category="compute",
        triggers=("ecs", "cloud server", "instance", "vke", "clb", "compute", "security group"),
        reason="Matches compute resource planning, ECS operations, VKE node checks, or CLB-backed workload scenarios.",
    ),
    SkillRecord(
        plugin="volcengine-database",
        skill="volcengine-database-rds-ops",
        category="database",
        triggers=("rds", "redis", "database", "mysql", "postgresql", "supabase", "aidap", "slow query"),
        reason="Matches database provisioning, connection diagnosis, migration planning, or query troubleshooting scenarios.",
    ),
    SkillRecord(
        plugin="volcengine-storage",
        skill="volcengine-storage-tos-ops",
        category="storage",
        triggers=("tos", "bucket", "object", "storage", "upload", "download", "lifecycle", "replication"),
        reason="Matches TOS bucket, object access, upload/download, lifecycle, or storage troubleshooting scenarios.",
    ),
    SkillRecord(
        plugin="volcengine-serverless",
        skill="volcengine-serverless-vefaas-ops",
        category="serverless",
        triggers=("vefaas", "serverless", "function", "gateway", "domain", "runtime", "deploy function"),
        reason="Matches veFaaS deployment, function management, gateway/domain, or serverless troubleshooting scenarios.",
    ),
    SkillRecord(
        plugin="volcengine-iac",
        skill="volcengine-iac-terraform-ops",
        category="iac",
        triggers=("terraform", "iac", "landing zone", "module", "plan", "apply", "drift"),
        reason="Matches Terraform, landing-zone planning, reusable modules, plan review, or IaC provisioning workflows.",
    ),
)


def score_record(query: str, record: SkillRecord) -> int:
    normalized = query.lower()
    return sum(1 for trigger in record.triggers if trigger in normalized)


def install_hints(plugin: str) -> dict[str, str]:
    return {
        "codex": (
            f"codex plugin marketplace add {MARKETPLACE}; then open /plugins "
            f"and install {plugin}"
        ),
        "claude": (
            f"/plugin marketplace add {MARKETPLACE}; "
            f"/plugin install {plugin}@volcengine-skills"
        ),
        "npx": f"npx skills add {MARKETPLACE}/tree/main/plugins/{plugin}/skills",
    }


def mock_openapi_search(query: str, limit: int = 3) -> list[dict[str, object]]:
    """Return ranked mock recommendations in the shape expected from OpenAPI."""
    ranked = sorted(
        MOCK_CATALOG,
        key=lambda record: (score_record(query, record), record.plugin),
        reverse=True,
    )
    matched = [record for record in ranked if score_record(query, record) > 0]

    if not matched:
        return [
            {
                "plugin": "volcengine-skills",
                "skill": "volcengine-cli",
                "category": "core",
                "reason": "No optional product plugin strongly matched. Stay in core and use CLI/API/docs/troubleshooting skills first.",
                "install": {
                    "codex": f"codex plugin marketplace add {MARKETPLACE}; then install volcengine-skills from /plugins",
                    "claude": f"/plugin marketplace add {MARKETPLACE}; /plugin install volcengine@volcengine-skills",
                    "npx": f"npx skills add {MARKETPLACE}",
                },
            }
        ]

    return [
        {
            "plugin": record.plugin,
            "skill": record.skill,
            "category": record.category,
            "reason": record.reason,
            "install": install_hints(record.plugin),
        }
        for record in matched[:limit]
    ]


def parse_args(argv: Iterable[str]) -> str:
    query = " ".join(argv).strip()
    if not query:
        raise SystemExit("usage: find_skill.py <scenario query>")
    return query


def main(argv: list[str]) -> int:
    query = parse_args(argv[1:])
    payload = {
        "query": query,
        "source": "mock-openapi",
        "marketplace": MARKETPLACE,
        "recommendations": mock_openapi_search(query),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
