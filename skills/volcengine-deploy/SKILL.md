---
name: volcengine-deploy
description: >-
  Use when deploying a local project directory or, when provided, a Git repository to Volcengine as a running service.
  Supports ECS (EIP + binary/systemd, Docker, or compose), VKE (container image + Kubernetes),
  and veFaaS execution through the `volcengine-vefaas` skill. Trigger when the user says "deploy to
  Volcengine", "deploy this repo", "push to VKE", "run on ECS", "deploy as serverless", or
  "volcengine deploy" — even without specifying the deploy mode. Run `volcengine-prepare`
  when the user has not chosen a deployment path. Ask the user to choose resource
  management (`cli` or `iac`): use `volcengine-iac` only when the user chooses Terraform/IaC
  or already has an IaC workflow; otherwise use direct `ve` CLI creation with a resource ledger.
license: MIT
---

# Volcengine Deploy Skill

Deploy a local project directory or remote Git URL to Volcengine after the user chooses ECS / VKE / veFaaS and resource management (`cli` or `iac`). Keep deployment execution pragmatic: use `volcengine-iac` only when the user chooses Terraform/IaC or already has an IaC workflow; otherwise use `ve` CLI plus `.volcengine/created-resources.json`.

---

## 0. Prerequisites

Volcengine authentication is checked by the execution skill you call (`volcengine-cli`, `volcengine-iac`, or `volcengine-vefaas`). Accept either the required AK/SK env vars for that skill or an already configured CLI profile when that skill supports it; do not duplicate their hard env requirements here.

Check tools after the user chooses a path:

| Mode | Required tools |
|---|---|
| ECS | `ve`, `git`, `jq`, `curl`; `ssh` only if the user opens port 22; `docker`/`docker compose` only for Docker or compose packaging |
| VKE | `ve`, `docker`, `kubectl`, `git`, `jq`, `curl` |
| veFaaS | switch to/call the `volcengine-vefaas` skill, which checks `vefaas`, Node.js, auth, framework detection, and deploy commands |

`tosutil` is optional for ECS artifact transfer and TOS buckets. Do not add it as a hard prerequisite for `volcengine-deploy`; if it is absent, use SSH/scp when allowed or ask the user for an existing artifact URL.

If the user has not chosen a mode, run `volcengine-prepare` inline or ask for these decisions:

```text
1. Deployment mode: ECS / VKE / veFaaS (recorded as `ecs` / `vke` / `vefaas`)
2. Resource strategy: new isolated project deploy-<repo>, or reuse existing resources
3. Resource management: CLI resource ledger / Terraform IaC (recorded as `cli` / `iac`)
```

Persistent local state lives under `.volcengine/` in the repo root:

```text
.volcengine/
  deploy-choice.json
  created-resources.json      # CLI fast path only
  iac-outputs.json
  terraform/                  # IaC-managed resources
```

---

## 1. Stage 0 — Resolve repo and choice

```bash
input="${1:-.}"
if [[ "$input" =~ ^(https?|git@) ]]; then
  repo_name=$(basename "$input" .git)
  work_dir="/tmp/volcengine-deploy/$repo_name"
  mkdir -p "$work_dir"
  if [ -d "$work_dir/src/.git" ]; then
    git -C "$work_dir/src" pull --ff-only
  else
    git clone --depth 1 "$input" "$work_dir/src"
  fi
  repo_dir="$work_dir/src"
else
  repo_dir=$(cd "${input:-.}" && pwd)
  repo_name=$(basename "$repo_dir")
  work_dir="$repo_dir/.volcengine"
  mkdir -p "$work_dir"
fi
git_sha=$(cd "$repo_dir" && git rev-parse --short HEAD 2>/dev/null || echo "$(date +%s)")
```

Local directories are deployed in place and are not cloned. For Git URLs, use shallow clone first; if clone repeatedly fails, try an archive/subdirectory path or stop with a clear "not suitable for quick remote build" message. Do not claim a README/static mirror is the deployed application.

Load `.volcengine/deploy-choice.json` if present. If absent, ask the fixed decisions above or run `volcengine-prepare`.

Choice file shape:

```json
{
  "schema_version": "1",
  "repo_dir": "/absolute/path",
  "repo_name": "my-app",
  "git_sha": "abc1234",
  "region": "cn-beijing",
  "mode": "ecs",
  "port": 8080,
  "dependencies": ["postgresql", "redis"],
  "database_product": "aidap",
  "database_engine": "supabase",
  "resource_strategy": "create-isolated-project",
  "project": "deploy-my-app",
  "infra_management": "cli"
}
```

Confirm before creating resources:

```text
Deploying <repo_name> via <mode> in <region>.
Resources: <new isolated project deploy-... | reuse existing resources>
Proceed? [y/N]
```

---

## 2. Resource ledger

Use the resource ledger only for CLI-created resources. IaC-created resources are tracked by Terraform state and exported through `.volcengine/iac-outputs.json`.

Every resource created by `volcengine-deploy` must be appended to `.volcengine/created-resources.json` immediately after creation. This is mandatory for cleanup and failure recovery.

Ledger entry:

```json
{
  "type": "eip",
  "id": "eip-xxxx",
  "name": "deploy-myapp-eip",
  "region": "cn-beijing",
  "project": "deploy-myapp",
  "reused": false,
  "created_at": "2026-05-29T00:00:00Z",
  "delete_command": "ve vpc ReleaseEipAddress --AllocationId eip-xxxx"
}
```

Rules:

- New resources: `reused=false`, include exact delete command.
- Reused resources: `reused=true`, do not include them in destructive cleanup.
- If an EIP is created inline with an ECS instance and released with that instance, mark it as `dependent=true` / `cleanup_optional=true` or omit it as an independent ledger item. Do not make cleanup fail just because the instance already released the EIP.
- On failure, print cleanup commands in reverse ledger order. There is currently no one-command cleanup runner; the user must review and run ledger `delete_command` values manually. Do not silently delete unless the user confirms.
- Prefer creating or using an isolated Volcengine project named `deploy-<repo>` for new resources, but confirm the project exists or can be created before passing that project name to resource creation. If project creation is unavailable, use `default` and isolate resources with names and tags.

---

## 3. Resource management dispatch

Before provisioning, confirm one resource management path with the user:

| Condition | Path |
|---|---|
| VKE, managed DB/cache/storage/LB/domain/certificate, team-owned infra, or plan/diff/destroy matters | `volcengine-iac` |
| Pure ECS single-VM service with no managed dependencies and no explicit plan/diff/destroy requirement | CLI fast path |
| User says temporary/demo/quick validation/just run it | CLI fast path |
| Terraform/provider registry is unavailable, especially in China networks, and the target is not VKE/managed dependencies/team-owned infra | CLI fallback |
| User explicitly says no Terraform/IaC | CLI fast path |

These are recommendations, not defaults. If `.volcengine/deploy-choice.json` lacks `infra_management`, ask before creating resources:

```text
Resource management recommendation: <cli|iac>, reason: <short reason>. Confirm the CLI resource ledger or Terraform/IaC? (`cli` / `iac`)
```

When using IaC:

1. Call or switch to `volcengine-iac` with `.volcengine/deploy-choice.json`.
2. Run Terraform generation, validate, plan, and explicit apply confirmation under that skill.
3. Consume `.volcengine/iac-outputs.json` for VPC/subnet/security group/cluster/CR/database/cache outputs.
4. Continue deployment packaging and runtime steps here: build/pull image, run Cloud Assistant, apply Kubernetes manifests, run migrations, and verify health.

When using CLI:

1. Create resources directly with `ve`.
2. Append every created resource to `.volcengine/created-resources.json` immediately.
3. Print reverse-order cleanup commands on failure.

---

## 4. Environment and Dependency Wiring

Before starting ECS services or applying Kubernetes manifests, resolve runtime configuration:

1. Read `.env.example`, `.env.sample`, framework config, and dependency outputs from IaC/CLI provisioning.
2. Split non-sensitive values into config and sensitive values into secrets. Treat connection strings, passwords, tokens, AK/SK, and session tokens as secrets.
3. Ask the user for missing required values. Do not print secret values back to the user, do not write them to logs, and write generated local files with mode `0600`.
4. For ECS systemd, write `/opt/<repo>/.env` before starting the service; the unit template reads it through `EnvironmentFile=-/opt/<repo>/.env`.
5. For VKE, generate ConfigMap and Secret manifests from the resolved values. Never leave `<connection-string>` placeholders in an applied Secret.

Managed dependency wiring must be completed before health checks:

- RDS database (`database_product=rds`, engine `mysql` / `postgresql` / `sqlserver`): create or reuse the instance, database, and app account; use the private endpoint; build `DATABASE_URL`; add the ECS/VKE subnet CIDR or security group source to the database allowlist; run migrations explicitly when `migration_paths` is non-empty.
- AIDAP database (`database_product=aidap`, engine `supabase` / `postgresql`): call `volcengine-supabase` to create or reuse the workspace, branch, app DB account/database, and return database/AIDAP env values before app health checks.
- Redis: create or reuse the instance and app account/password; use the private endpoint; build `REDIS_URL`; add the ECS/VKE subnet CIDR or security group source to the Redis allowlist.
- If the user declines managed services for a detected dependency, state the persistence/scaling tradeoff and wire the chosen alternative into the same env/Secret path.

---

## 5. Branch dispatch

```bash
case "$deploy_mode" in
  ecs)  proceed_ecs ;;
  vke)  proceed_vke ;;
  vefaas) run_vefaas_skill ;;
  *)    echo "Unknown deploy mode: $deploy_mode"; exit 2 ;;
esac
```

---

## 6. ECS branch

ECS is the default lightweight VM path. Public services must get an EIP so the user can access the service after deployment.

Select packaging from the repo shape: compose file -> compose on ECS; Dockerfile -> Docker on ECS; clear binary or single process -> binary + systemd; otherwise ask one focused start-command question.

Keep these hard boundaries in the main context:

- Use IaC outputs when `infra_management=iac`; otherwise use the CLI ledger path and record every CLI-created resource immediately.
- Do not hardcode instance type or OS image. Query availability and avoid fuzzy image matches that return GPU, WebUI, marketplace, or unrelated images.
- If SSH 22 is not explicitly approved, keep it closed and use Cloud Assistant. If SSH is approved, restrict it to the current outbound IP when possible.
- Volcengine RunCommand is asynchronous. Poll invocation results before treating the command as successful.
- Generated one-time ECS passwords must not be printed or written to ledger/state.
- Validate listening port, local health/root path, public endpoint, logs, and one core app behavior where possible.

Read [`references/ecs-deploy-steps.md`](./references/ecs-deploy-steps.md) for the detailed ECS packaging, upload, Cloud Assistant, Docker mirror, architecture, health-gate, and cleanup workflow.

---

## 7. veFaaS branch

Do not duplicate veFaaS deployment details here. If the user chooses veFaaS, switch to/call the `volcengine-vefaas` skill with:

- repo path
- app name
- region
- detected framework/port if known
- environment variable notes
- any warning from prepare

Tell the user the `volcengine-vefaas` skill will run `vefaas inspect`, verify login, create/link the app, configure env vars if needed, deploy, and print domains.

If the `volcengine-vefaas` skill fails, return to this main deployment flow. Summarize the failure, then offer the user a choice:

- fix the veFaaS issue and retry,
- switch to ECS,
- switch to VKE.

---

## 8. VKE branch

Recommend `volcengine-iac` for VKE resource provisioning because cluster, node pool, CR, LB, and managed dependencies benefit from plan/diff/destroy safety. Use `ve` CLI plus the resource ledger when the user chooses CLI after seeing the tradeoff, for temporary validation, explicit user preference, or IaC fallback.

After choosing VKE, check `docker`, `kubectl`, `ve`, and `terraform`/`jq` if using IaC. Build for the node architecture, defaulting to `linux/amd64` unless cluster data proves otherwise; inspect the pushed image platform before rollout.

Keep this ordered execution skeleton — these actions must be chained in sequence, and a later step run before an earlier one converges is the most common VKE failure:

1. Provision or reuse VKE + CR (IaC outputs or CLI fast path).
2. Wait for the cluster to be `Running`, then fetch the kubeconfig (from IaC outputs or `CreateKubeconfig`).
3. Verify addons: `core-dns` present; prefer `cr-credential-controller` for private CR pulls.
4. Build the image for the node architecture.
5. Authenticate to CR, push the image, and inspect the pushed platform.
6. Resolve env/Secret values and dependency outputs.
7. Generate manifests from resolved values.
8. Run migrations as a Kubernetes Job when migration paths exist.
9. Apply, then wait for rollout and the LoadBalancer/EIP.
10. Verify the public endpoint and one core app behavior.

Keep these hard boundaries in the main context:

- Use IaC outputs for VPC/subnets/security group/VKE/CR when available; otherwise create or reuse through the CLI fast path and record resources.
- `CreateKubeconfig` before the cluster is `Running` returns `OperationDenied` — poll to `Running` first.
- Confirm `core-dns` before relying on in-cluster DNS.
- Prefer `cr-credential-controller` for private Volcengine CR image pulls instead of storing registry passwords in app manifests.
- Re-read `Result.Username` from `GetAuthorizationToken` for `docker login`; never invent a fallback username.
- Resolve ConfigMap/Secret values before applying workloads; never leave placeholders in applied Secret manifests.
- Run migrations as a Kubernetes Job when migration paths exist.
- Wait for rollout and LoadBalancer/EIP, then verify the public endpoint.

For managed dependencies, prefer managed Volcengine services when practical; otherwise state clearly when the plan is deploying stateful containers inside VKE.

Read [`references/vke-deploy-steps.md`](./references/vke-deploy-steps.md) for the full VKE pipeline (cluster wait, kubeconfig, addon checks, CR auth/push, rollout, endpoint verify), with [`references/k8s-manifests.md`](./references/k8s-manifests.md) for manifest templates and [`references/dockerfile-templates.md`](./references/dockerfile-templates.md) for image build templates.

---

## 9. Deployment summary

Print one access card:

```text
volcengine-deploy — <repo_name> (<git_sha>)

Mode:        <ecs|vke|vefaas>
Region:      <region>
Project:     <deploy-project or reused resources>
URL:         <public endpoint>
Health:      <checked URL/status>
Acceptance:  <core app behavior checked, or reason only transport health was possible>
Resources:   .volcengine/created-resources.json
IaC:         <.volcengine/terraform + .volcengine/iac-outputs.json | n/a>
Logs:        <journalctl / docker logs / kubectl logs / vefaas logs command>
Cleanup:     <reverse-order cleanup commands or ledger path>
Notes:       <credentials/env/migration warnings>
```

Do not add custom domain, HTTPS, dashboards, or cost cards unless the user asks; those are day-2 tasks.

---

## 10. Reference details

Use these references only when executing the corresponding path:

- ECS build/systemd/upload details: [`references/ecs-deploy-steps.md`](./references/ecs-deploy-steps.md)
- VKE deploy pipeline (cluster/kubeconfig/addons/CR/rollout): [`references/vke-deploy-steps.md`](./references/vke-deploy-steps.md)
- veFaaS deploy handoff details: [`references/faas-deploy-steps.md`](./references/faas-deploy-steps.md)
- Dockerfile templates: [`references/dockerfile-templates.md`](./references/dockerfile-templates.md)
- Kubernetes manifests: [`references/k8s-manifests.md`](./references/k8s-manifests.md)
- Runtime dependencies: [`references/supported-dependencies.md`](./references/supported-dependencies.md)

---

## 11. Common failure modes

Common gotchas are intentionally kept as references so the main skill stays adaptive:

- ECS instance/image/Cloud Assistant/SSH/Docker mirror issues: [`references/ecs-deploy-steps.md`](./references/ecs-deploy-steps.md)
- Container architecture and Dockerfile pitfalls: [`references/dockerfile-templates.md`](./references/dockerfile-templates.md)
- VKE pipeline sequencing (kubeconfig/addons/CR auth/rollout): [`references/vke-deploy-steps.md`](./references/vke-deploy-steps.md)
- Kubernetes readiness, LoadBalancer, probes, and manifest issues: [`references/k8s-manifests.md`](./references/k8s-manifests.md)
- Managed dependency wiring and migrations: [`references/supported-dependencies.md`](./references/supported-dependencies.md)
- veFaaS CLI/auth/framework setup: [`references/faas-deploy-steps.md`](./references/faas-deploy-steps.md) and `volcengine-vefaas`
