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
metadata:
  openclaw:
    requires:
      bins:
        - git
        - jq
        - curl
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
1. 部署方式：ECS / VKE / veFaaS（记录为 `ecs` / `vke` / `vefaas`）
2. 资源策略：新建独立项目 deploy-<repo>，或复用已有资源
3. 资源管理：CLI 资源账本 / Terraform IaC（记录为 `cli` / `iac`）
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
  "dependencies": ["redis"],
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
资源管理建议：<cli|iac>，原因：<short reason>。确认用 CLI 资源账本还是 Terraform/IaC？（`cli` / `iac`）
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

- MySQL/PostgreSQL: create or reuse the instance, database, and app account; use the private endpoint; build `DATABASE_URL`; add the ECS/VKE subnet CIDR or security group source to the database allowlist; run migrations explicitly when `migration_paths` is non-empty.
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

Packaging selection:

| Signal | Packaging |
|---|---|
| `compose.yaml` / `compose.yml` / `docker-compose.yml` / `docker-compose.yaml` | Docker compose on ECS |
| Dockerfile exists | Docker on ECS |
| compiled binary or clear single process | binary + systemd |
| unclear start command | ask one follow-up |

Provisioning:

1. Use IaC-created VPC/subnet/security group/EIP/ECS outputs when `infra_management=iac`.
2. Reuse a user-specified instance, or find one tagged for this project.
3. Otherwise, in the CLI fast path, create a new ECS instance with an EIP, security group, system disk, and Cloud Assistant installed.
4. Do not hardcode one instance type. Query available resources in the target zone and pick a small general-purpose type that is actually available.
5. If `RunInstances` still reports the selected type unavailable or sold out, automatically try the next available candidate before failing.
6. Use a known-good public OS image query strategy; avoid fuzzy searches that return GPU, WebUI, marketplace, or unrelated images.
7. `RunInstances` requires a login credential even when SSH is closed. Provide a generated one-time strong `--Password` or an existing `--KeyPairName`; do not print or write generated passwords to ledger/state.
8. Record ECS, EIP, security group, and rule resources in the ledger only for CLI-created resources.

Security group:

- Open the application port for public access.
- Ask whether to open SSH 22. If the user declines, do not open 22 and use Cloud Assistant.
- If the user opens 22, detect the current outbound IP immediately before writing the rule and restrict SSH to that CIDR when possible. Re-check before deploy if there was a delay; update the rule if the IP changed.

Command channel:

1. If SSH is allowed and reachable, SSH may be used for upload/deploy/debug.
2. If SSH is not allowed, blocked, or slow to connect, use Cloud Assistant.
3. Always ensure Cloud Assistant is available for fallback when creating a new instance.

RunCommand caveat:

Volcengine RunCommand is asynchronous. Do not treat the scheduling response as command success. Read the invocation ID, then poll invocation results until success/failure before continuing.

Deployment:

- `binary-systemd`: build or package the app, upload, generate systemd unit, start service.
- `ecs-docker`: install/start Docker if needed, run the image with restart policy.
- `ecs-compose`: run the compose file with the compose command available on the target host, and explain volume persistence for stateful services such as Redis.

Docker image pulling in China:

1. Prefer Volcengine CR or a user-provided registry for images produced by this deployment.
2. For public Docker Hub images during temporary validation, test the listed mirror candidates with bounded timeouts and keep the first one that pulls the required image.
3. For public images outside Docker Hub, or when a registry mirror fails, inspect the exact pull command from a domestic mirror/sync site instead of assuming the site hostname is a universal registry path.
4. If public registry pulls fail or hang, fall back to release binary + systemd when the project supports it.

Docker build architecture:

- For VKE workloads, build and push images for the node architecture. Default to `linux/amd64` unless cluster/node pool data proves otherwise.
- On Apple Silicon or other arm64 developer machines, do not trust the local Docker default platform. Use `docker buildx build --platform linux/amd64 ...` or pull/build with `--platform linux/amd64`, then inspect the pushed image architecture before rollout.
- For ECS Docker, align the image platform with the selected ECS instance architecture.

Data dependencies:

- If dependencies include MySQL/PostgreSQL/Redis, recommend managed RDS/Redis by default. Keep them in the same VPC as ECS/VKE, use private endpoints, and run migrations explicitly.
- If the project only uses SQLite, do not imply it must migrate to RDS. Warn that SQLite is single-node storage and data is tied to the instance/disk.
- If the user opts out of managed services, containerized Redis/DB or SQLite is acceptable for quick validation, but state the durability and scaling tradeoff.

Health gate:

- Check that the process listens on the expected port with `ss -ltnp` before diagnosing security groups or EIP.
- Check `http://localhost:<port><health_path>` when a health path is known. If no health path is detected, use TCP/listening checks and root-path smoke checks instead of assuming `/health`.
- Check public `http://<EIP>:<port>` from outside after the security group is open.
- On failure, print logs and reverse-order cleanup commands from the ledger.

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

Required after choosing VKE:

- `docker` for image build
- `kubectl` for Kubernetes apply/rollout
- `terraform`/`jq` for IaC resource provisioning unless using CLI fast path
- `ve` for CLI fallback, CR authentication, and read-only diagnostics

Flow:

1. Generate or use Dockerfile.
2. Build and smoke-test the image locally with a platform matching the VKE node architecture; default to `linux/amd64`.
3. Use IaC outputs for VPC/subnets/security group/VKE/CR when available; otherwise create or reuse them through CLI fast path and record resources.
4. Authenticate to CR using CR authorization token.
5. Fetch kubeconfig after cluster is running, or read it from `.volcengine/iac-outputs.json`.
6. Before applying workloads, confirm VKE addons: `core-dns` must be present for in-cluster service discovery/DNS, and `cr-credential-controller` should be present when pulling private Volcengine CR images without managing registry passwords in app manifests.
7. Push image to CR and inspect the pushed image platform before rollout.
8. Generate Kubernetes manifests with resolved ConfigMap/Secret values and health probes matched to the app.
9. Run migrations as a Kubernetes Job when migration paths exist.
10. Wait for rollout and public LoadBalancer/EIP.
11. Verify the public endpoint.

For managed dependencies, prefer managed Volcengine services when practical; otherwise state clearly when the plan is deploying stateful containers inside VKE.

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
- veFaaS deploy handoff details: [`references/faas-deploy-steps.md`](./references/faas-deploy-steps.md)
- Dockerfile templates: [`references/dockerfile-templates.md`](./references/dockerfile-templates.md)
- Kubernetes manifests: [`references/k8s-manifests.md`](./references/k8s-manifests.md)
- Runtime dependencies: [`references/supported-dependencies.md`](./references/supported-dependencies.md)

---

## 11. Common failure modes

| Symptom | Likely cause | Action |
|---|---|
| ECS instance type creation fails | type not available in zone | Query `DescribeAvailableResource` and pick another available type. |
| SSH blocked | port 22 closed or network policy | Use Cloud Assistant; do not wait on long SSH retries. |
| RunCommand appears successful but app not changed | only scheduling result was checked | Poll invocation results before continuing. |
| RunCommand `Success` but app is not usable | script exited successfully before real runtime verification | Check unit/container status, listening port, logs, and one core app behavior; HTTP 200 alone is not acceptance. |
| `RunInstances` returns `MissingParameter.PasswordAndKeyPair` | ECS requires `Password` or `KeyPairName` even with SSH closed | Generate a one-time strong password or use an existing key pair; do not print generated credentials. |
| `InvalidEipAddressChargeType.Malformed` | Used EIP billing value from another API | For `RunInstances --EipAddress.ChargeType`, use `PayByBandwidth`, `PayByTraffic`, or `PrePaid`. |
| Cloud Assistant status jq returns empty | Wrong response path | Use `.Result.Instances[0].Status`; wait for `Running`. |
| Docker Hub/GHCR pull hangs or times out | China network or public registry throttling | Prefer CR/user registry; for Docker Hub test `docker.1ms.run`, `dockerproxy.net`, `proxy.vvvv.ee`, or `dockerproxy.link`; for sync/search sites such as `docker.aityp.com`, inspect the image detail page and use the exact pull command; fall back to binary/systemd when possible. |
| Domestic mirror hostname returns `no basic auth credentials` | The site may be a search/sync frontend, not a drop-in registry path for every image | Open/parse the image detail page and use the exact "国内镜像" / `docker pull` command it provides. |
| `docker login` returns 401 | wrong CR username | Re-read `Result.Username` from `GetAuthorizationToken`; if it is missing, inspect the CR API response instead of inventing a fallback username. |
| app starts but config-dependent requests fail | `.env` or Kubernetes Secret was not generated from required values | Resolve `.env.example`/dependency outputs, inject ECS `.env` or K8s Secret, then restart/roll out. |
| app cannot connect to RDS/Redis | private endpoint or allowlist not wired | Use private endpoint, build `DATABASE_URL`/`REDIS_URL`, and add ECS/VKE subnet CIDR or security group source to the service allowlist. |
| PostgreSQL migrations fail on `public` schema | database owner and schema owner differ | Set database owner to the app account and use `rdspostgresql ModifySchemaOwner` for `public` before migrations. |
| Shell health check fails with `curl: (23)` | `curl | head` under `set -o pipefail` | Avoid piping curl to early-closing consumers; write to a file or use `curl -o /dev/null`. |
| container fails with `exec format error` | image architecture does not match VKE/ECS node architecture | Rebuild/pull/push with the node platform, usually `linux/amd64`, and inspect the image before rollout. |
| `BLB no available backend` | Pod readinessProbe failing, often because `/health` does not exist | Use a detected health path or switch probes to `tcpSocket`; inspect with `kubectl describe pod` and `kubectl logs`. |
| `CreateKubeconfig` returns `OperationDenied` | cluster not yet `Running` | Poll `DescribeClusters` until phase=Running first |
| `RunCommand` returns `InvalidParameter.Timeout` | timeout too low for the current API/CLI | Pass `--Timeout 60` minimum (see `volcengine-cli/references/ecs.md`) |
| veFaaS setup fails | `vefaas` CLI/auth/framework issue | Return to the main deploy flow, summarize the failure, and let the user retry veFaaS or switch to ECS/VKE. |
| K8s `LoadBalancer` stuck in `<pending>` | CLB subnet annotation missing | Add `service.beta.kubernetes.io/volcengine-loadbalancer-subnet-id` to Service annotations |
