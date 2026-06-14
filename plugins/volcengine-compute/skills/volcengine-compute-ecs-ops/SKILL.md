---
name: volcengine-compute-ecs-ops
description: Use for optional Volcengine compute scenarios involving ECS instance planning, creation, inspection, lifecycle operations, network attachment checks, or compute troubleshooting. Prefer this skill when the user explicitly asks for ECS, cloud server, VKE node, CLB-backed compute, instance sizing, image selection, security group, or compute resource operations. Use volcengine-cli for generic ve CLI syntax.
---

# Volcengine Compute ECS Operations

Use this optional extension skill for focused compute workflows. Keep `volcengine-cli` as the command reference; this skill adds scenario guidance for ECS-style work.

## Workflow

1. Identify the target compute scenario: create, inspect, resize, troubleshoot, or estimate.
2. Resolve the required resource context: region, zone, VPC, subnet, security group, image, instance type, billing mode, and key pair or login method.
3. Use `volcengine-cli` when exact `ve` command syntax or API details are needed.
4. Before write operations, present the planned resource changes and ask for confirmation if the operation creates, deletes, restarts, resizes, or changes billing.
5. After execution, verify resource state with a read command and summarize IDs, region, status, and follow-up checks.

## Mock Scenario Coverage

- ECS instance creation checklist
- Instance inventory and status inspection
- Security group and port exposure review
- VKE worker node readiness triage
- CLB backend compute attachment checks

## Notes

This prototype skill is intentionally lightweight. Replace the mock checklist with product-specific references as the compute extension grows.
