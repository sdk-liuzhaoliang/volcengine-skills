# Deploy Mode Heuristics

Use this when `volcengine-prepare` explains ECS / VKE / veFaaS choices. The output is a ranked recommendation for the user, not a score table and not a filter. Always show all three paths, pick a default deployment mode, and ask for lifecycle, reuse, and resource-management choices. Use `ecs | vke | vefaas` as machine-readable mode values.

## Ranking rules

Rank by project shape first. Do not demote a path just because a local tool is missing; tool checks happen after the user chooses.

If analysis reports `deploy_subdir`, rank the app in that subdirectory. Only treat a subdirectory as deployable when it has runnable signals such as Docker/compose, package scripts, or language entrypoints; static documentation or example HTML alone is not enough.

### Prefer ECS when

- The user wants the fastest path to a public URL.
- The service can run as a binary, a single process, Docker, or docker compose.
- The project is simple enough for one VM or a small number of VMs.
- The repo has external dependencies but does not need Kubernetes-level rollout, autoscaling, or multi-service orchestration.
- The user needs a quick validation, fastest public URL, or one-VM shape. For resource management, recommend CLI for pure ECS single-VM deployments, especially when Terraform or provider registry access is unavailable. Recommend IaC for ECS when it is team-managed, needs managed dependencies, or needs plan/diff/destroy safety.

ECS packaging:

| Signal | Packaging |
|---|---|
| `compose.yaml` / `compose.yml` / `docker-compose.yml` / `docker-compose.yaml` exists | `ecs-compose` |
| Dockerfile exists | `ecs-docker` |
| Go / Rust / Java / .NET or clear single-process app | `binary-systemd` |
| Unclear app start but can be containerized | ask one follow-up for start command or Dockerfile choice |

Explain the default ECS shape:

- It creates or reuses an ECS instance.
- New public services get an EIP as the access endpoint.
- Ask the user whether to open SSH 22. If they do not want SSH, deploy and debug through Cloud Assistant.
- Approximate cost: `中` (ECS instance + system disk + EIP/bandwidth; plus any managed dependencies).

### Prefer VKE when

- The repo already has Dockerfile/compose and looks like a containerized app.
- The app needs multiple replicas, rolling updates, HPA, Kubernetes Jobs, or network policies.
- The repo has multiple services, multiple languages, or several long-running processes.
- Migrations or workers need a cleaner lifecycle than a single systemd service.
- The user wants a production-shaped container platform.

Recommend Terraform/volcenginecc for VKE resource creation because clusters, node pools, CR, LB, and managed dependencies benefit from plan/diff/destroy safety. Use `ve` CLI plus `.volcengine/created-resources.json` only if the user chooses CLI after seeing the tradeoff, for temporary validation, or when Terraform is unavailable.

Approximate cost: `中-高` (VKE nodes + CR + CLB/EIP + bandwidth; plus databases/cache/storage).

### Prefer veFaaS when

- The app is stateless and has a single supported entrypoint.
- There are no in-band DB migrations or long-running workers.
- The framework is likely supported by the `volcengine-vefaas` skill, such as FastAPI, Django, Flask, Express, Next.js, Nuxt, NestJS, Remix, Vite, Astro, Vitepress, or Angular.
- Low operational overhead and pay-by-use economics matter more than infrastructure control.

If the user chooses veFaaS, switch to/call the `volcengine-vefaas` skill. If it fails, return to the main deployment flow and let the user retry veFaaS or switch to ECS/VKE. Do not use the legacy ZIP/API flow in `volcengine-deploy`.

Approximate cost: `低-中` (function resources + API Gateway; plus dependency services if used).

## Common warning signals

Mention these in the relevant option, but do not hide the option:

| Signal | What to tell the user |
|---|---|
| `migration_paths` non-empty | veFaaS may need a separate migration step; VKE can run a Job, ECS can run a one-shot command. |
| WebSocket / long-lived connections | ECS or VKE is usually safer than veFaaS. |
| Compose file with Redis/MySQL/etc. | ECS compose can run it quickly, but data durability and scaling are weaker than managed services or VKE. |
| Many stateful dependencies | VKE or managed services may be more appropriate; ECS remains possible for quick validation. |
| External MySQL/PostgreSQL/Redis dependency | Recommend managed RDS/Redis by default; same VPC, private endpoint, explicit migration step. |
| Project only uses SQLite | Keep it as a valid choice; warn about single-node/disk durability, but do not imply RDS migration is required. |
| Long-lived cloud resources | Recommend IaC for VKE, managed dependencies, team-owned infrastructure, or plan/diff/destroy needs. Recommend CLI for pure ECS single-VM services when speed and fewer dependencies matter more. |
| Static frontend | veFaaS/static serving may be possible, but ECS/VKE are still valid if the user wants one service shape. |
| Unknown port or start command | Ask one concise follow-up after the user chooses a path. |
| Region/service permission notes | Surface them next to the affected path and let the user decide. |

## Suggested recommendation patterns

### Go API with Redis, no Dockerfile

1. ECS
   - Reason: compiled service can run directly under systemd; Redis can be managed or run via compose for quick validation.
   - Tradeoff: single-VM operation unless expanded later.
2. VKE
   - Reason: good if the user wants replicas, rolling rollout, or managed Redis wiring.
   - Tradeoff: more resources and setup.
3. veFaaS
   - Reason: low ops if the app is stateless.
   - Warning: Redis and any migration/worker behavior must be confirmed.

### Existing Dockerfile plus database migrations

1. VKE
   - Reason: containerized app and migrations map cleanly to Deployment + Job.
2. ECS
   - Reason: simpler if one VM is enough; run Docker or compose on ECS.
3. veFaaS
   - Warning: migrations need a separate plan and framework support must be verified by `volcengine-vefaas`; failure should return to the main flow for retry or ECS/VKE selection.

### FastAPI / Next.js with no external dependencies

1. veFaaS
   - Reason: supported framework shape, low ops, pay-by-use.
2. ECS
   - Reason: fastest predictable VM path with EIP.
3. VKE
   - Reason: valid but heavier unless the user wants Kubernetes.

## Resource management recommendation

Recommend resource management, then ask the user to choose:

| Signal | Resource management |
|---|---|
| User says "temporary", "demo", "quick validation", or "just run it" | `cli` fast path with `.volcengine/created-resources.json` |
| Pure ECS single-VM service with no managed dependencies and no explicit plan/diff/destroy requirement | `cli` fast path with `.volcengine/created-resources.json` |
| Any VKE, managed DB/cache/storage/LB/domain/certificate, or team-owned service | `iac` |
| User needs plan/diff/drift/destroy or may resume later | `iac` |
| Terraform/provider/network unavailable and the user accepts lower reproducibility | `cli` fallback |
| User explicitly says "no Terraform/IaC" | `cli` |

For China network conditions, include a note when Docker images are involved: Docker Hub and GHCR may be slow or blocked. Deployment should prefer Volcengine CR, user-provided registries, or an inspected domestic mirror/sync URL over direct public registry pulls.

## User confirmation

After presenting the ranked list, ask only:

```text
1. 部署方式：默认使用推荐第一项。可选 ECS / VKE / veFaaS（记录为 `ecs` / `vke` / `vefaas`）。
2. 资源策略：默认新建独立项目 deploy-<repo> 并创建新资源；也可以复用已有资源。
3. 资源管理：建议 <cli|iac>；请确认用 CLI 资源账本还是 Terraform/IaC。
```

Mention the resource management recommendation, then ask for confirmation:

```text
资源管理建议：VKE、托管依赖和团队资源选 Terraform/volcenginecc；纯 ECS 单机、临时验证或 IaC 不可用时选 ve CLI 快速创建并记录资源账本。请确认用 `iac` 还是 `cli`。
```
