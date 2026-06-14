---
name: volcengine-serverless-vefaas-ops
description: Use for optional Volcengine serverless scenarios involving veFaaS deployments, function management, gateway/domain checks, environment variables, framework detection, build failures, runtime logs, or serverless troubleshooting. Use volcengine-vefaas for exact vefaas CLI command details.
---

# Volcengine Serverless veFaaS Operations

Use this optional extension skill for serverless workflows. Keep `volcengine-vefaas` as the exact command reference; this skill adds scenario guidance.

## Workflow

1. Identify the serverless task: deploy new app, update existing app, manage function, configure env vars, inspect domain, or troubleshoot.
2. Check prerequisites: Node.js version, `vefaas` installation, login status, app link status, gateway availability, and framework support.
3. For deployments, inspect project structure before choosing template, existing-code, or linked-app flow.
4. For changes to existing apps, state the target app/function and expected impact before deploying.
5. Verify deployment with domain listing, app status, and a runtime smoke test.

## Mock Scenario Coverage

- veFaaS new app deployment
- Existing project deployment
- Gateway/domain readiness checks
- Environment variable update checklist
- Build/runtime troubleshooting

## Notes

This prototype skill is intentionally lightweight. Replace the mock workflow with product-specific references as the serverless extension grows.
