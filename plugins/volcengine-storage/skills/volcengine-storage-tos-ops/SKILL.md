---
name: volcengine-storage-tos-ops
description: Use for optional Volcengine storage scenarios involving TOS buckets, object upload/download, bucket policy, public access, lifecycle rules, cross-region replication, static assets, or object storage troubleshooting. Use volcengine-tosutil for exact tosutil command details and volcengine-cli for generic ve CLI syntax.
---

# Volcengine Storage TOS Operations

Use this optional extension skill for TOS and storage workflows. Keep `volcengine-tosutil` as the exact command reference; this skill adds scenario guidance.

## Workflow

1. Identify the storage scenario: create bucket, inspect access, upload/download, configure lifecycle, replicate, or troubleshoot.
2. Gather bucket name, region, endpoint, object prefix, auth method, expected access pattern, and error message if present.
3. For access issues, check identity, bucket policy, ACL/public access settings, endpoint, signature region, and object key spelling before changing policy.
4. For lifecycle or replication, state cost and data-retention implications before applying changes.
5. Verify with a read/list/head operation and summarize bucket, object key, policy state, and next checks.

## Mock Scenario Coverage

- TOS bucket access diagnosis
- Upload/download planning
- Static asset hosting checklist
- Lifecycle and retention review
- Cross-region replication readiness

## Notes

This prototype skill is intentionally lightweight. Replace the mock workflow with product-specific references as the storage extension grows.
