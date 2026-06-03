---
name: volcengine-iac
description: >-
  Use Terraform/IaC for Volcengine resources only when the user explicitly chooses
  Terraform/IaC, already has a Terraform workflow/state, or confirms they need
  plan/diff/drift/destroy safety for VKE, managed databases/cache/storage, load balancers,
  domains/certificates, logging/monitoring, or team-managed infrastructure.
license: MIT
metadata:
  openclaw:
    requires:
      bins:
        - terraform
        - jq
        - git
        - python3
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

# Volcengine IaC Skill

Generate, plan, and apply Volcengine infrastructure with Terraform when the user chooses IaC. `volcengine-deploy` still owns application packaging, runtime rollout, health checks, and CLI resource-ledger deployment.

When writing new examples, prefer the Cloud Control provider `volcengine/volcenginecc`. Clean no-op verified `volcenginecc` examples now cover network, VPC extras, VPC traffic mirror filters and CLB targets, private NAT, ECS, ECS placement/template extras, EBS snapshots, VKE, CR, TOS including bucket notification to veFaaS, TLS including scheduled SQL and TOS import tasks, CloudMonitor disabled alert rules, Redis, IAM, IAM users/groups, CLB instance/certificate/ACL, ALB full private entry traffic plus health check template/certificate/ACL/customized config, APIG private gateway/service, VPN IPsec gateway/connection/route plus SSL server, CEN with VPC attachment, DirectConnect gateway, TransitRouter, PrivateLink CLB endpoint service and endpoint, veFaaS, RDS MySQL, RDS PostgreSQL, Kafka allowlist, FileNAS, EFS, DNS, and PrivateZone under `assets/examples/`; `volcenginecc-ebs-snapshot-group`, `volcenginecc-autoscaling`, and `volcenginecc-rdsmssql` are lifecycle-verified only and have documented provider drift/destroy caveats. See the matching `references/volcenginecc-*.md` file for validation results and pitfalls. Blocked resources are tracked in [`references/volcenginecc-blocked.md`](./references/volcenginecc-blocked.md). Existing reusable modules under `assets/modules/` still use the legacy `volcengine/volcengine` provider until each component is re-verified with `volcenginecc`.

Use this skill when one of these is true:

- the user asks for Terraform or IaC,
- the user already has Terraform state/workspace,
- plan/diff/drift detection matters,
- the infrastructure is intended for long-term team-managed operation and the user chooses IaC,
- the deployment needs VKE, managed databases/cache/storage, load balancers, domains/certificates, IAM/KMS, logging, monitoring, or Serverless triggers and the user chooses IaC.

Do not use this skill just because a deployment is long-lived, VKE-based, or has managed dependencies. Recommend IaC where appropriate, but let the user choose. Do not use this skill when the user asks for CLI, a temporary demo/quick validation, a pure ECS single-VM service with no plan/diff/destroy requirement, or when Terraform/provider installation is blocked and the target can safely use the CLI fallback.

The skill ships forty-six clean no-op verified `volcenginecc` examples (`volcenginecc-network`, `volcenginecc-vpc-extras`, `volcenginecc-vpc-traffic-mirror-filter`, `volcenginecc-vpc-traffic-mirror-target`, `volcenginecc-private-nat`, `volcenginecc-ecs`, `volcenginecc-ecs-extras`, `volcenginecc-ecs-launch-template-version`, `volcenginecc-ebs-snapshot`, `volcenginecc-vke`, `volcenginecc-cr`, `volcenginecc-tos`, `volcenginecc-tos-notification`, `volcenginecc-tls`, `volcenginecc-tls-schedule-sql`, `volcenginecc-tls-import-task`, `volcenginecc-cloudmonitor`, `volcenginecc-redis`, `volcenginecc-redis-public-address`, `volcenginecc-iam`, `volcenginecc-iam-users`, `volcenginecc-iam-oidc-provider`, `volcenginecc-iam-saml-provider`, `volcenginecc-clb`, `volcenginecc-clb-certificate`, `volcenginecc-clb-acl`, `volcenginecc-alb`, `volcenginecc-alb-health-check`, `volcenginecc-alb-certificate`, `volcenginecc-alb-acl`, `volcenginecc-alb-customized-cfg`, `volcenginecc-apig`, `volcenginecc-vpn`, `volcenginecc-vpn-ssl`, `volcenginecc-cen`, `volcenginecc-directconnect`, `volcenginecc-transitrouter`, `volcenginecc-privatelink`, `volcenginecc-vefaas`, `volcenginecc-rdsmysql`, `volcenginecc-rdspostgresql`, `volcenginecc-kafka-allow-list`, `volcenginecc-filenas`, `volcenginecc-efs`, `volcenginecc-dns`, `volcenginecc-privatezone`), three lifecycle-verified examples (`volcenginecc-ebs-snapshot-group`, `volcenginecc-autoscaling`, `volcenginecc-rdsmssql`), six legacy reusable modules (`network`, `vke`, `cr`, `rds-mysql`, `redis`, `tos`), and four wrapper scripts (`gen_tfvars.py`, `plan_summary.sh`, `export_outputs.sh`, `check_drift.sh`).

Resources outside the six legacy modules (CLB/ALB, VKE, CR, databases, caches, object storage) should be added as verified `volcenginecc` examples first, then wrapped only after repeated use proves the interface is stable.

---

## 0. Prerequisites

Required env vars: `VOLCENGINE_ACCESS_KEY`, `VOLCENGINE_SECRET_KEY`, `VOLCENGINE_REGION`.

Required tools: `terraform >= 1.5`, `jq`, `git`, `python3` (for `gen_tfvars.py`).

Optional: `.volcengine/deploy-choice.json` from `volcengine-prepare`/`volcengine-deploy`. If absent, ask a short batch of Terraform-specific questions.

The skill writes Terraform working files into `.volcengine/terraform/` by default. State can use a TOS S3-compatible backend when the user wants remote state; see [`references/backend-tos.md`](./references/backend-tos.md). Local state is acceptable for small one-off experiments when the user accepts the tradeoff.

If invoked by `volcengine-deploy`, return outputs in `.volcengine/iac-outputs.json` and let deploy continue with image build/push, Cloud Assistant commands, Kubernetes manifests, veFaaS release, migrations, and health checks.

---

## 1. Generation Flow

### Path A — driven by `.volcengine/deploy-choice.json`

```bash
skill_dir="$(dirname "$0")"
work_dir="${work_dir:-.volcengine/terraform}"
workload="${workload:-standard}"
mkdir -p "$work_dir"

python3 "$skill_dir/scripts/gen_tfvars.py" \
  --input ".volcengine/deploy-choice.json" \
  --output "$work_dir/terraform.tfvars" \
  --workload "$workload"
```

`gen_tfvars.py` derives:
- `project`, `region`, AZ pair from the choice file and environment
- `enable_vke / enable_cr / enable_rds / enable_redis / enable_tos` flags from the chosen mode and known dependencies
- Sizing (instance type, node count, RDS spec, Redis capacity) from a coarse `--workload` tier

The user can override any value before applying.

### Path B — natural language input

When no prepare report exists, ask the user **one batch of questions**, then create a Terraform working directory from verified examples or legacy modules and generate matching variable values. Required answers:

1. Project name (resource prefix)
2. Region (e.g. `cn-beijing`)
3. Need VKE? (yes/no)
4. Stateful deps needed: MySQL? PostgreSQL? Redis? TOS bucket?
5. Workload tier: light / standard / heavy

### Files written

`gen_tfvars.py` writes only `terraform.tfvars`. The Terraform configuration files come from copied verified examples under `assets/examples/` or from a small root module assembled from `assets/modules/`; edit those files to match the selected stack instead of expecting the script to generate them.

| File | Purpose |
|---|---|
| `main.tf` / `variables.tf` | Copied or assembled Terraform configuration |
| `terraform.tfvars` | Concrete values generated by `gen_tfvars.py` or edited by hand |
| `backend.tf` | Generated only when TOS remote state is selected; otherwise omit it |

The full per-module variable schema lives in [`references/modules.md`](./references/modules.md). For new `volcenginecc` work, start from a verified example under `assets/examples/` instead of these legacy modules unless the user explicitly needs the old provider.

### Path C — `volcenginecc` verified examples

Copy the relevant verified example, then run the same init/validate/plan sequence:

```bash
cp -R "$skill_dir/assets/examples/<example-name>" "$work_dir/<component>"
cd "$work_dir/<component>"
terraform init -backend=false -input=false
terraform validate
terraform plan -out=tfplan.binary -input=false
```

Before apply, show the plan summary and require explicit user confirmation. Read the matching reference before changing inputs or destroying resources; the references contain field choices, validation notes, import IDs, and provider pitfalls.

---

## 2. Deployment stack mapping

Use these opinionated stacks to choose verified examples. Start with examples; wrap into reusable modules only after repeated use proves the interface stable.

| Deployment shape | Examples to compose |
|---|---|
| `ecs-docker-public` / `ecs-systemd-public` | `volcenginecc-network`, `volcenginecc-ecs`, optional `volcenginecc-tls`, `volcenginecc-cloudmonitor` |
| `vke-webapp-cr-clb` | `volcenginecc-network`, `volcenginecc-vke`, `volcenginecc-cr`, `volcenginecc-clb` |
| `vke-webapp-cr-alb` | `volcenginecc-network`, `volcenginecc-vke`, `volcenginecc-cr`, `volcenginecc-alb`, optional ALB health/cert/ACL examples |
| `vefaas-http` | `volcenginecc-vefaas`, optional `volcenginecc-apig`, `volcenginecc-tls` |
| `webapp-rds-redis-tos` | runtime stack plus `volcenginecc-rdsmysql` or `volcenginecc-rdspostgresql`, `volcenginecc-redis`, `volcenginecc-tos` |
| `private-service-with-nat` | `volcenginecc-network`, `volcenginecc-private-nat`, runtime stack |
| `domain-and-edge-entry` | runtime stack plus `volcenginecc-dns`, ALB/CLB certificate examples, optional CDN/WAF only after verified examples exist |

The stack mapping is a selection guide, not a promise that a prebuilt module exists. Copy the relevant verified examples into `.volcengine/terraform/<component>` and keep component boundaries clear so plan/destroy output remains readable.

For the end-to-end VKE private CR nginx path, use `assets/examples/volcengine-vke-cr-nginx/` and read `references/volcengine-vke-cr-nginx.md` first. That example exists for the CR credential addon, `core-dns`, CR token expiry, and image architecture pitfalls found in a real run.

---

## 3. Catalog

### Verified `volcenginecc` examples

| Example | Purpose | Resources |
|---|---|---|
| `assets/examples/volcenginecc-network` | Network foundation for ECS/VKE/RDS/Redis/LB deployments | `vpc_vpc`, `vpc_subnet`, `vpc_route_table`, `vpc_security_group`, `vpc_eip`, `natgateway_ngw`, `natgateway_snatentry`, `natgateway_dnatentry` |
| `assets/examples/volcenginecc-vpc-extras` | Additional VPC controls for subnet ACLs, CIDR reuse, ENIs, HAVIP, and shared bandwidth | `vpc_prefix_list`, `vpc_network_acl`, `vpc_eni`, `vpc_ha_vip`, `vpc_bandwidth_package` |
| `assets/examples/volcenginecc-vpc-traffic-mirror-filter` | Traffic mirror filter conditions before ECS/CLB target/session wiring | `vpc_traffic_mirror_filter`, `vpc_traffic_mirror_filter_rule` |
| `assets/examples/volcenginecc-vpc-traffic-mirror-target` | Traffic mirror destination backed by a private CLB | `vpc_traffic_mirror_target`, `clb_clb` |
| `assets/examples/volcenginecc-private-nat` | Private NAT gateway and additional transit IP for private address translation | `natgateway_ngw`, `natgateway_nat_ip` |
| `assets/examples/volcenginecc-ecs` | Direct ECS deployments, utility hosts, launch templates, Cloud Assistant commands | `ecs_keypair`, `storageebs_volume`, `ecs_command`, `ecs_launch_template`, `ecs_instance`, second-stage `ecs_invocation` |
| `assets/examples/volcenginecc-ecs-extras` | ECS placement primitives without creating instances | `ecs_deployment_set`, `ecs_hpc_cluster` |
| `assets/examples/volcenginecc-ecs-launch-template-version` | Additional ECS launch template versions for controlled rollout changes | `ecs_launch_template`, `ecs_launch_template_version` |
| `assets/examples/volcenginecc-ebs-snapshot` | Manual snapshot backup for standalone EBS data disks | `storageebs_volume`, `storageebs_snapshot` |
| `assets/examples/volcenginecc-ebs-snapshot-group` | Snapshot consistency group for an attached ECS system volume | `storageebs_snapshot_group`, plus ECS/network prerequisites |
| `assets/examples/volcenginecc-autoscaling` | Lifecycle-verified Auto Scaling group/configuration/hook for ECS capacity control | `autoscaling_scaling_group`, `autoscaling_scaling_configuration`, `autoscaling_scaling_lifecycle_hook`, plus launch template/network prerequisites |
| `assets/examples/volcenginecc-vke` | Managed Kubernetes control plane, private kubeconfig, node pools, and managed addon | `vke_cluster`, `vke_node_pool`, `vke_default_node_pool`, `vke_addon`, `vke_kubeconfig` |
| `assets/examples/volcenginecc-cr` | Container Registry image repositories for build/deploy pipelines | `cr_registry`, `cr_name_space`, `cr_repository`, `cr_endpoint_acl_policy` |
| `assets/examples/volcenginecc-tos` | Object storage buckets for artifacts, static assets, logs, backups, or state prerequisites | `tos_bucket`, `tos_bucket_cors`, `tos_bucket_encryption` |
| `assets/examples/volcenginecc-tos-notification` | TOS object-created event notifications delivered to a released veFaaS function | `tos_bucket_notification`, `tos_bucket`, `vefaas_function`, `vefaas_release` |
| `assets/examples/volcenginecc-tls` | Log Service project/topic/index/rule/consumer group for application logs | `tls_project`, `tls_topic`, `tls_index`, `tls_rule`, `tls_consumer_group` |
| `assets/examples/volcenginecc-tls-schedule-sql` | Scheduled SQL analysis from one TLS topic to another | `tls_project`, `tls_topic`, `tls_index`, `tls_schedule_sql_task` |
| `assets/examples/volcenginecc-tls-import-task` | TOS-to-TLS import task with its target topic and source bucket | `tls_project`, `tls_topic`, `tls_index`, `tos_bucket`, `tls_import_task` |
| `assets/examples/volcenginecc-cloudmonitor` | Disabled CloudMonitor ECS CPU alert rule for lifecycle-verified monitoring policy management | `cloudmonitor_rule` |
| `assets/examples/volcenginecc-redis` | Redis cache instance with allowlist, parameter group, and app account | `redis_instance`, `redis_account`, `redis_allow_list`, `redis_parameter_group` |
| `assets/examples/volcenginecc-redis-public-address` | Redis public endpoint bound to a dedicated EIP; use only when public exposure is deliberate | `redis_endpoint_public_address`, `vpc_eip` |
| `assets/examples/volcenginecc-iam` | IAM project, assumable role, and custom policy primitives | `iam_project`, `iam_role`, `iam_policy` |
| `assets/examples/volcenginecc-iam-users` | IAM user and group identity primitives without access keys or login password | `iam_user`, `iam_group` |
| `assets/examples/volcenginecc-iam-oidc-provider` | External OIDC identity provider metadata for IAM federation | `iam_oidc_provider` |
| `assets/examples/volcenginecc-iam-saml-provider` | SAML identity provider metadata for IAM SSO | `iam_saml_provider` |
| `assets/examples/volcenginecc-clb` | Private Classic Load Balancer instance for entry traffic | `clb_clb` |
| `assets/examples/volcenginecc-clb-certificate` | CLB uploaded server certificate for HTTPS listeners | `clb_certificate` |
| `assets/examples/volcenginecc-clb-acl` | Classic Load Balancer access-control policy group | `clb_acl` |
| `assets/examples/volcenginecc-alb` | Private Basic Application Load Balancer, server group, listener, and rule | `alb_load_balancer`, `alb_server_group`, `alb_listener`, `alb_rule` |
| `assets/examples/volcenginecc-alb-health-check` | Reusable ALB health check template | `alb_health_check_template` |
| `assets/examples/volcenginecc-alb-certificate` | ALB uploaded server certificate for HTTPS listeners | `alb_certificate` |
| `assets/examples/volcenginecc-alb-acl` | ALB access-control policy group | `alb_acl` |
| `assets/examples/volcenginecc-alb-customized-cfg` | ALB reusable NGINX customized config | `alb_customized_cfg` |
| `assets/examples/volcenginecc-apig` | Private API Gateway entry point and service default domain | `apig_gateway`, `apig_gateway_service` |
| `assets/examples/volcenginecc-vpn` | Site-to-site IPsec VPN gateway, connection, and static route for VPC connectivity | `vpn_vpn_gateway`, `vpn_customer_gateway`, `vpn_vpn_connection`, `vpn_vpn_gateway_route` |
| `assets/examples/volcenginecc-vpn-ssl` | SSL VPN remote-access entry point for a VPC | `vpn_vpn_gateway`, `vpn_ssl_vpn_server` |
| `assets/examples/volcenginecc-cen` | Cloud Enterprise Network with a VPC attachment for cross-network connectivity | `cen_cen`, `vpc_vpc` |
| `assets/examples/volcenginecc-directconnect` | Direct Connect gateway foundation for dedicated-line connectivity | `directconnect_direct_connect_gateway` |
| `assets/examples/volcenginecc-transitrouter` | TransitRouter foundation before VPC/VPN/DirectConnect/peer attachments | `transitrouter_transit_router` |
| `assets/examples/volcenginecc-privatelink` | Interface PrivateLink service backed by private CLB plus consumer endpoint | `privatelink_endpoint_service`, `privatelink_vpc_endpoint`, `clb_clb` |
| `assets/examples/volcenginecc-vefaas` | Serverless function, release, and disabled timer trigger | `vefaas_function`, `vefaas_release`, `vefaas_timer` |
| `assets/examples/volcenginecc-rdsmysql` | MySQL instance, database, app account, allowlist, and parameter template | `rdsmysql_instance`, `rdsmysql_database`, `rdsmysql_db_account`, `rdsmysql_allow_list`, `rdsmysql_parameter_template` |
| `assets/examples/volcenginecc-rdspostgresql` | PostgreSQL instance, database, app account, schema, allowlist, endpoint, and backup | `rdspostgresql_instance`, `rdspostgresql_db_account`, `rdspostgresql_database`, `rdspostgresql_schema`, `rdspostgresql_allow_list`, `rdspostgresql_db_endpoint`, `rdspostgresql_backup` |
| `assets/examples/volcenginecc-rdsmssql` | Lifecycle-verified SQL Server Basic instance and allowlist with destroy retry caveat | `rdsmssql_instance`, `rdsmssql_allow_list` |
| `assets/examples/volcenginecc-kafka-allow-list` | Standalone Kafka access allowlist for future Kafka instances | `kafka_allow_list` |
| `assets/examples/volcenginecc-filenas` | NFS shared file system for ECS/VKE/application storage | `filenas_instance` |
| `assets/examples/volcenginecc-efs` | EFS shared file system for multi-node application or dataset storage | `efs_file_system` |
| `assets/examples/volcenginecc-dns` | Public DNS zone for application domains and edge CNAME targets | `dns_zone` |
| `assets/examples/volcenginecc-privatezone` | VPC-scoped private DNS zone and record for internal service discovery | `privatezone_private_zone`, `privatezone_record` |

### Legacy `volcengine` modules

| Module | Purpose | Key inputs | Key outputs |
|---|---|---|---|
| `network` | VPC + 2× AZ subnets + default SG | `project`, `az_*`, CIDRs | `vpc_id`, `subnet_ids`, `security_group_id` |
| `vke` | Cluster + node pool + addons | `vpc_id`, `subnet_ids`, `node_instance_type` | `cluster_id`, `kubeconfig_private` (base64) |
| `cr` | Registry + namespace + repository | `registry_name`, `namespace`, `repository_name` | `registry_endpoint`, `repository_uri`, `registry_username` |
| `rds-mysql` | HA MySQL instance | `subnet_id`, `primary_zone_id`, `secondary_zone_id`, `instance_type` | `instance_id`, `endpoints[]` |
| `redis` | Redis instance (single or HA) | `subnet_id`, `engine_version`, `shard_capacity` | `instance_id` (endpoint via `ve redis DescribeDBInstanceDetail`) |
| `tos` | Object storage bucket | `bucket_name`, `public_acl`, `storage_class` | `bucket_name`, `intranet_endpoint`, `extranet_endpoint` |

> **Why ECS / CLB are not modules yet**: ECS workloads vary too widely (build host vs runtime vs jumphost) for a single helpful interface, so ECS is a verified example rather than a module. EIP and NAT are covered in the verified `volcenginecc-network` example. CLB/ALB should be added as verified examples before they become reusable modules.

---

## 4. Init & Backend

```bash
cd "$work_dir"

# Map Volcengine creds to the Terraform s3 backend's required env variable names.
export AWS_ACCESS_KEY_ID="$VOLCENGINE_ACCESS_KEY"
export AWS_SECRET_ACCESS_KEY="$VOLCENGINE_SECRET_KEY"
export AWS_EC2_METADATA_DISABLED=true

terraform init -input=false
tf_workspace="${tf_workspace:-default}"
terraform workspace select "$tf_workspace" || \
  terraform workspace new "$tf_workspace"
```

When remote state is requested, generate `backend.tf` from `references/backend-tos.md`. The verified TOS backend shape requires `skip_requesting_account_id = true` and must not set `force_path_style` or `use_path_style`.

Provider download (~30–60 seconds first time) goes through `registry.terraform.io`. In China networks this may be blocked or slow. If public registry access fails and the user still wants IaC, configure Terraform `provider_installation` with a filesystem or internal mirror. Otherwise return to `volcengine-deploy` and ask whether to use the CLI resource-ledger path.

For the TOS bucket prerequisite (must exist before `init`), see [`references/backend-tos.md`](./references/backend-tos.md). Without a TOS bucket, omit `backend.tf` and Terraform falls back to local state.

---

## 5. Plan

```bash
terraform plan -out=tfplan.binary -input=false
terraform show -json tfplan.binary > tfplan.json
bash "$skill_dir/scripts/plan_summary.sh" tfplan.json
```

`plan_summary.sh` groups changes by action (CREATE / UPDATE / DELETE / REPLACE) and prints a one-line summary at the end. Show this to the user before any apply.

Watch for:
- **DELETEs you didn't ask for** — usually a sign of drift or a mistakenly removed module call
- **REPLACEs on stateful resources** — RDS / Redis replace = data loss; abort and inspect the diff with `terraform show tfplan.binary`

---

## 6. Apply

**Always require explicit user confirmation.** Do not pass `-auto-approve`. The pattern:

```text
The plan above will create N resources, change M, destroy K. Approve apply? [yes/no]
```

After yes:

```bash
terraform apply tfplan.binary
```

VKE cluster creation takes ~10–15 minutes. RDS HA instances take ~20 minutes. Surface the long-running message to the user once at apply start so they don't think it hung.

After apply succeeds, run `export_outputs.sh` automatically:

```bash
bash "$skill_dir/scripts/export_outputs.sh"
echo "Resources ready. .volcengine/iac-outputs.json now contains downstream consumption keys."
```

---

## 7. Outputs for Downstream

`export_outputs.sh` writes `terraform output -json` to `.volcengine/iac-outputs.json` (mode 0600). The schema downstream skills (`volcengine-deploy`) consume:

```json
{
  "vpc_id":            { "value": "vpc-xxxx" },
  "subnet_ids":        { "value": ["subnet-aaa", "subnet-bbb"] },
  "security_group_id": { "value": "sg-xxxx" },
  "cluster_id":        { "value": "cluster-xxxx" },
  "kubeconfig_private":{ "value": "<base64>", "sensitive": true },
  "registry_endpoint": { "value": "cr-xxx.cr.volces.com" },
  "repository_uri":    { "value": "cr-xxx.cr.volces.com/myapp/myapp" },
  "cr_username":       { "value": "..." },
  "mysql_endpoint":    { "value": "<addr>:<port>" },
  "redis_instance_id": { "value": "redis-xxxx" },
  "tos_bucket":        { "value": "myapp-bucket" }
}
```

Some keys are conditional on which modules were enabled. Consumers must `jq` defensively (use `// empty` defaults).

---

## 8. Destroy

```bash
# Show what will be destroyed first
terraform plan -destroy -out=destroy.binary
terraform show -json destroy.binary | bash "$skill_dir/scripts/plan_summary.sh"
```

Then:

```text
This will permanently delete N resources including RDS / Redis / TOS bucket data. Confirm? [yes/no]
```

On yes:

```bash
terraform destroy
# Note: provider does not accept -auto-approve=false; we rely on the agent-level prompt above.
```

**Hard rule**: never destroy in `prod` workspace without a second confirmation. The agent should explicitly re-prompt:

```text
Workspace = prod. Re-confirm destroy by typing 'destroy prod':
```

---

## 9. Drift Detection

```bash
bash "$skill_dir/scripts/check_drift.sh"
```

Returns:
- `0` and `{"drift": false, ...}` — no drift
- `2` and `{"drift": true, "changed_resources": N, ...}` — N resources changed outside Terraform
- `1` and `{"drift": "error", ...}` — refresh-only plan errored

Use this:
- After known manual interventions (someone resized a node pool via console)
- Periodically as a CI job (weekly)
- Before any non-trivial `apply` to confirm baseline matches state

---

## 10. Import Existing Resources

If the user has resources created via `volcengine-cli` (or console) and wants to adopt them under Terraform, use `terraform import`. The import ID format differs per resource. Common cases:

```bash
# VPC
terraform import 'module.network.volcengine_vpc.main' vpc-xxxxxxxx

# Subnet
terraform import 'module.network.volcengine_subnet.primary' subnet-xxxxxxxx

# VKE cluster
terraform import 'module.vke.volcengine_vke_cluster.main' cluster-xxxxxxxx

# CR registry — replace cr-basic with the actual registry name
terraform import 'module.cr.volcengine_cr_registry.main' cr-basic

# CR namespace (compound ID: registry:namespace)
terraform import 'module.cr.volcengine_cr_namespace.main' cr-basic:my-namespace

# CR repository (compound ID: registry:namespace:repo)
terraform import 'module.cr.volcengine_cr_repository.main' cr-basic:my-namespace:my-repo

# RDS MySQL
terraform import 'module.rds_mysql.volcengine_rds_mysql_instance.main' mysql-xxxxxxxx

# Redis
terraform import 'module.redis.volcengine_redis_instance.main' redis-xxxxxxxx

# TOS bucket — replace my-bucket with the actual globally-unique name
terraform import 'module.tos.volcengine_tos_bucket.main' my-bucket
```

After import, run `terraform plan` to surface any divergence between your `.tf` config and the imported reality, and reconcile by editing the config (not the state).

---

## 11. Safety Rules

| Rule | Reason |
|---|---|
| Never read `~/.volcengine/config.json` | File contains plaintext AK/SK |
| Never commit `terraform.tfstate*` | Contains sensitive state |
| Always `.gitignore` `.volcengine/iac-outputs.json` | Contains kubeconfig + DB creds |
| Never pass `-auto-approve` to `terraform apply/destroy` | Bypasses human gate |
| Run `check_drift.sh` before every apply on shared envs | Prevents trampling out-of-band changes |
| Set `chmod 0600` on any file holding kubeconfig or secrets | Defense-in-depth |
| Pin provider versions in every module/example | Provider on `0.0.x` line — patch bumps may still change behavior |

The skill's scripts enforce most of these mechanically (`export_outputs.sh` chmods 0600). Apply and destroy gates are the agent's responsibility.

---

## 12. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `terraform init`: "Failed to query available provider packages" | Outbound to `registry.terraform.io` blocked | If the user still wants IaC, set up a `provider_installation` filesystem mirror and rerun `init`; otherwise return to `volcengine-deploy` and ask whether to use CLI resource-ledger provisioning. |
| `terraform init`: "InvalidAccessKeyId" against TOS backend | Terraform s3 backend env vars are not exported | Export `AWS_ACCESS_KEY_ID="$VOLCENGINE_ACCESS_KEY"`, `AWS_SECRET_ACCESS_KEY="$VOLCENGINE_SECRET_KEY"`, and `AWS_EC2_METADATA_DISABLED=true`. |
| `terraform init`: TOS backend returns `InvalidPathAccess` | Backend uses path-style access or an unsupported workspace prefix shape | Use the verified template in `references/backend-tos.md`: keep `skip_requesting_account_id = true` and remove `force_path_style` / `use_path_style`. |
| `apply` succeeds for VPC but fails for subnet with `InvalidVpc.InvalidStatus` | VPC not yet `Available` | Add `depends_on = [volcengine_vpc.main]` (already in network module) |
| VKE cluster stuck in `Creating` for >20 minutes | Quota or AZ capacity | `ve vke DescribeClusters --body '{"Filter":{"Ids":["..."]}}' | jq .Result.Items[0].Status` for the actual reason |
| `redis` module output missing endpoint | Provider does not export it | Resolve via `ve redis DescribeDBInstanceDetail --InstanceId $(jq -r '.redis_instance_id.value' .volcengine/iac-outputs.json)` |
| `terraform plan` shows unexpected changes after no edits | Drift, or provider patch bump silently changing default value | Run `check_drift.sh`, inspect `tfplan.json`, decide whether to accept or revert |
| Two engineers' `apply` collide | TOS backend has no DynamoDB-style locking | Coordinate manually; see [`references/backend-tos.md`](./references/backend-tos.md) |
