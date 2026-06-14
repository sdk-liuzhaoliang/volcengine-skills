---
name: volcengine-database-rds-ops
description: Use for optional Volcengine database scenarios involving RDS, Redis, PostgreSQL, MySQL, AIDAP/Supabase workspaces, database connection failures, schema migration planning, slow query triage, backup/restore checks, or database capacity planning. Use volcengine-db-supabase for existing AIDAP workspace management details and volcengine-cli for generic ve CLI syntax.
---

# Volcengine Database Operations

Use this optional extension skill for database-focused workflows. Keep the core `volcengine-db-supabase` and `volcengine-cli` skills available for exact tool details when needed.

## Workflow

1. Classify the database task: provision, connect, migrate, diagnose, tune, back up, or restore.
2. Gather required context: engine, region, VPC/subnet, instance ID, account, database name, connection method, and observed error or performance symptom.
3. For live operations, prefer read-only diagnostics first: instance status, endpoint, whitelist/security group, account state, parameter group, backup policy, and recent events.
4. For schema or data changes, require an explicit plan, rollback path, and user confirmation.
5. Verify the result with a read query, connection test, or instance status check.

## Mock Scenario Coverage

- RDS connection and whitelist diagnosis
- Redis connectivity and memory pressure triage
- Slow query investigation checklist
- Migration readiness review
- AIDAP/Supabase workspace handoff to core skill

## Notes

This prototype skill is intentionally lightweight. Replace the mock workflow with product-specific references as the database extension grows.
