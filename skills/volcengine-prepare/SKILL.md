---
name: volcengine-prepare
description: >-
  Use when the user wants to deploy a local directory or GitHub repository to Volcengine and
  needs the project analyzed, the app shape understood, and a ranked recommendation across
  ECS, VKE, and veFaaS before choosing an execution path. Also trigger when the user asks
  "what deploy mode should I use", "is this repo ready for Volcengine", or "check my repo
  before deploying". This skill prepares the decision; `volcengine-deploy` performs the
  chosen deployment, and `volcengine-iac` is used only when the user chooses Terraform/IaC
  or the task already has an IaC workflow.
license: MIT
metadata:
  openclaw:
    envVars:
      - name: VOLCENGINE_ACCESS_KEY
        required: false
        description: AccessKey for AK/SK auth path (alternative to `ve login`)
      - name: VOLCENGINE_SECRET_KEY
        required: false
        description: SecretKey for AK/SK auth path
      - name: VOLCENGINE_SESSION_TOKEN
        required: false
        description: Optional STS session token for temporary credentials
      - name: VOLCENGINE_REGION
        required: false
        description: Default region; falls back to cn-beijing if unset
---

# Volcengine Prepare Skill

Analyze a repo, explain viable Volcengine deployment paths, and decide the resource management path. Treat this skill as decision support, not as a workflow engine. Do not make a heavy report schema the goal.

---

## 0. Core behavior

Default flow:

1. Resolve the repo from a local path or Git URL.
2. Run the analyzer to identify language, framework, port, Docker/compose shape, dependencies, migrations, and entrypoint.
3. Optionally verify the current Volcengine identity and region when credentials are available.
4. Present a ranked list of ECS / VKE / veFaaS. Never hide a path; explain why each path is attractive or costly. Use `ecs | vke | vefaas` as machine-readable mode values.
5. Recommend a resource management path, but ask the user to choose `cli` or `iac`. Recommend IaC for VKE, managed dependencies, team-managed infrastructure, or plan/diff/destroy requirements; recommend CLI for pure ECS single-VM deployments, temporary validation, missing Terraform, blocked provider registry access, or explicit CLI preference.
6. Ask only for product/lifecycle ambiguity, resource reuse, and the resource management choice. If the user says "you decide", use the first ranked runtime path, the recommended resource management path from these rules, and new isolated resources.
7. Persist only minimal state in `.volcengine/` when the work will continue across steps.

Do not run strict tool dependency checks during recommendation. Check path-specific tools only after the user chooses a path.

State directory:

```text
.volcengine/
  deploy-choice.json       # chosen mode/resource strategy, when persistence is useful
  created-resources.json   # maintained by deploy only for CLI fast path
  terraform/               # IaC working files, only when infra_management=iac
  iac-outputs.json         # Terraform outputs consumed by deploy
```

Use `/tmp` only for temporary clones or caches.

---

## 1. Resolve and analyze the repo

For Git URLs, clone to a temporary cache. For local paths, analyze in place.

```bash
input="${1:-.}"
if [[ "$input" =~ ^(https?|git@) ]]; then
  repo_name=$(basename "$input" .git)
  cache_dir="/tmp/volcengine-prepare/$repo_name"
  mkdir -p "$cache_dir"
  [ -d "$cache_dir/src/.git" ] || git clone --depth 1 "$input" "$cache_dir/src"
  repo_dir="$cache_dir/src"
else
  repo_dir=$(cd "$input" && pwd)
  repo_name=$(basename "$repo_dir")
fi
git_sha=$(cd "$repo_dir" && git rev-parse --short HEAD 2>/dev/null || echo "unversioned")
```

Run:

```bash
skill_dir="$(dirname "$0")"   # or the path to this skill
analysis=$(bash "$skill_dir/scripts/analyze-repo.sh" "$repo_dir")
echo "$analysis" | jq .
```

Show the important findings in plain language:

```text
Project: <repo_name> @ <git_sha>
Runtime: <language> / <framework>
Deployable subdir: <deploy_subdir or repo root>
Entrypoint: <entrypoint>
Port: <port>
Packaging signals: Dockerfile=<yes/no>, compose=<yes/no if detected>
Dependencies: <mysql, redis, ...>
Migrations: <paths or none>
```

If the analyzer cannot identify a runnable project, ask what runtime or subdirectory to deploy before recommending a path. A documentation HTML file alone is not a deployable app signal.

---

## 2. Optional cloud identity check

If `VOLCENGINE_ACCESS_KEY`, `VOLCENGINE_SECRET_KEY`, and `VOLCENGINE_REGION` are set, verify identity:

```bash
ve sts GetCallerIdentity
```

Do not read `~/.volcengine/config.json`; it may contain secrets. If env vars are absent, keep the recommendation going and tell the user credential checks will happen when executing the chosen path.

If cloud service availability matters for a near-term choice, run the read-only probe:

```bash
services=$(bash "$skill_dir/scripts/check-region-services.sh")
echo "$services" | jq .
```

Surface permission or region notes in the corresponding option; do not hide that option.

Prechecks are advisory, not gates. If you can cheaply check quotas or permissions, present the result as a risk:

```text
检测到 <quota/permission> 可能不足，继续可能在创建资源时失败。仍要继续吗？
```

If account real-name verification or balance cannot be queried reliably, give a short reminder instead of inventing a check:

```text
创建云资源可能要求账号已实名且余额/授信充足；如果创建失败，需要先在控制台处理账号状态。
```

---

## 3. Recommend deployment paths

Use [`references/deploy-mode-heuristics.md`](./references/deploy-mode-heuristics.md) for the detailed decision rules. Present a ranked list, not `recommended=true/false` flags or scoring internals.

Always include all three options:

- **ECS**: VM with EIP. Package as binary + systemd, Docker, or compose. Good for simple services, fast public access, and cases where the user wants fewer local/cloud dependencies.
- **VKE**: Container/Kubernetes path. Good for Dockerfile/compose projects, multi-service workloads, rolling updates, HPA, and longer-term production shape.
- **veFaaS**: Serverless path. Good for supported web frameworks and stateless workloads. If the user chooses it, switch to/call the `volcengine-vefaas` skill for deployment; if that fails, return to the main flow so the user can retry or choose ECS/VKE.

Include:

- why it is ranked where it is
- rough cost level (`低`, `中`, `中-高`)
- operational tradeoffs
- known blockers or setup needed if the user chooses it
- resource management recommendation (`iac` or `cli`) and why

Do not check every tool before the user chooses. Phrase setup needs as decision guidance:

```text
资源管理需要用户确认：VKE、托管数据库/缓存/存储/LB/域名/证书或团队长期资源推荐 Terraform/volcenginecc；纯 ECS 单机、临时验证、无 Terraform 或 provider registry 不通时推荐 ve CLI 快速创建并记录资源账本。
选择 VKE 后会检查 kubectl；如果用户选择 IaC，也会检查 terraform/provider 可用性。
选择 veFaaS 后会切换/调用 `volcengine-vefaas` skill 检查 vefaas CLI、登录状态和框架识别；失败时回到这里，用户可修复后重试或改选 ECS/VKE。
```

---

## 4. Ask only necessary questions

After showing the ranked list, ask only what cannot be safely inferred:

```text
1. 部署方式：默认使用推荐第一项。可选 ECS / VKE / veFaaS（记录为 `ecs` / `vke` / `vefaas`）。
2. 资源策略：默认新建独立项目 deploy-<repo> 并创建新资源；也可以复用已有资源。
3. 资源管理：推荐 <cli|iac>，请确认使用 CLI 资源账本还是 Terraform/IaC。
```

Ask whether to use Terraform/IaC explicitly. Give a recommendation, but do not turn it into a default:

```text
资源管理建议：VKE、托管依赖、团队长期资源或需要 plan/diff/destroy 时选 Terraform/volcenginecc；纯 ECS 单机、临时 demo、无 Terraform 或 provider registry 不通时选 ve CLI 快速创建并记录资源账本。请确认用 `iac` 还是 `cli`。
```

If the user says "you decide", use:

- deployment mode: first ranked option
- resources: create new isolated Volcengine project `deploy-<repo>`
- resource management: apply the table in [`references/deploy-mode-heuristics.md`](./references/deploy-mode-heuristics.md): plain ECS single-VM without managed dependencies can be `cli`; VKE, managed dependencies, team-owned infrastructure, or plan/diff/destroy needs are `iac`

If the user chooses reuse, ask for only the resource IDs needed by that path. Reused resources must not be destroyed by cleanup.

---

## 5. Persist the user's choice only when useful

If execution continues in the same conversation, no file is required. If the user may resume later or the next step needs a durable handoff, write only a small choice record:

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

Write it to `.volcengine/deploy-choice.json`.

Do not write score tables, rationale arrays, or a full recommendation matrix unless the user asks for a report.

---

## 6. Summary template

```text
项目检测：
- 运行时：<language>/<framework>
- 入口/端口：<entrypoint> / <port>
- 打包信号：Dockerfile=<yes/no>, Compose=<yes/no>
- 依赖：<deps or none>
- 迁移：<paths or none>
- 资源管理建议：<iac|cli>（VKE/托管依赖/团队资源通常建议 iac；纯 ECS 单机或 IaC 不可用通常建议 cli）

推荐顺序：
1. <mode>
   原因：...
   代价：...
   费用粗估：...

2. <mode>
   ...

3. <mode>
   ...

请确认：
1. 部署方式：默认 <first mode>
2. 资源策略：默认新建独立项目 deploy-<repo>；也可复用已有资源
3. 资源管理：建议 <iac|cli>；请确认用 `iac` 还是 `cli`
```
