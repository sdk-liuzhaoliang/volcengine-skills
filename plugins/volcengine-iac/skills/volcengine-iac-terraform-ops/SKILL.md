---
name: volcengine-iac-terraform-ops
description: Use for optional Volcengine infrastructure-as-code scenarios involving Terraform, provider selection, reusable modules, landing zone planning, plan review, drift checks, or provisioning workflows. Use volcengine-iac for existing Terraform provider details and volcengine-landing-zone for landing-zone setup details when installed.
---

# Volcengine IaC Terraform Operations

Use this optional extension skill for infrastructure-as-code workflows. Keep the core `volcengine-iac` and `volcengine-landing-zone` skills as detailed references when they are installed.

## Workflow

1. Classify the IaC task: design, generate, review, migrate, plan, apply, import, or troubleshoot.
2. Gather environment context: account, region, provider variant, state backend, target resources, naming policy, and expected lifecycle.
3. Prefer plan generation and review before apply. Do not run destructive operations without explicit confirmation.
4. Separate reusable module design from one-off stack code.
5. Verify with `terraform fmt`, `terraform validate`, plan review, and post-apply read checks when available.

## Mock Scenario Coverage

- Terraform stack generation checklist
- Module boundary review
- Landing-zone planning handoff
- Drift and import planning
- Apply safety review

## Notes

This prototype skill is intentionally lightweight. Replace the mock workflow with product-specific references as the IaC extension grows.
