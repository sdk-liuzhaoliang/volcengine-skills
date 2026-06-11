# AIDAP as a Deploy Database Provider

Use this reference from `volcengine-deploy` when the user selects `database_product=aidap`. AIDAP refers to Volcengine's `AI 原生 BaaS 平台 Supabase 版` product; in deploy flows, use its database workspace surface as the managed database provider. AIDAP deploy-facing database engines are `supabase` and `postgresql`; resolve current `CreateWorkspace` `EngineType` / `EngineVersion` enums from [`tool-reference.md`](./tool-reference.md) before creation.

## Selection

Use AIDAP when:

- The user selects AIDAP as the database product.
- The user selects the Supabase or PostgreSQL engine in the AIDAP workspace flow.
- The deployment accepts AIDAP service prerequisites.

Prefer RDS when:

- The user selects RDS MySQL, RDS PostgreSQL, or RDS SQL Server.
- The deployment needs mature private VPC/IaC-oriented database operations.
- The user needs mature Terraform/IaC coverage for the database resource.
- The account cannot complete enterprise real-name verification or AIDAP service activation.

## Provisioning Loop

1. Check `ve sts GetCallerIdentity`.
2. If `ve aidap DescribeWorkspaces --Limit 1` indicates the service is not enabled, ask the user to complete:

```text
https://console.volcengine.com/iam/service/attach_role/?ServiceName=aidap
```

3. If AK/SK environment variables are available, run enterprise verification:

```bash
python3 skills/volcengine-supabase/scripts/aidap_bootstrap.py get-verify-info
```

Treat the account as enterprise verified only when `verification.enterprise_verified=true`, which requires `IsVerified=true` and `IdentityType="enterprise"`.

4. Create or reuse the workspace with `ve aidap`, preserving `database_engine=supabase|postgresql`. For PostgreSQL, pass explicit `VpcId` and `SubnetId`; an existing `Available` default VPC/subnet is acceptable.
5. Wait for `DescribeWorkspaceDetail` to show `WorkspaceStatus=Running`, then `DescribeDefaultBranch` to show `BranchStatus=Ready`, then `DescribeComputes` to find the active primary database `ComputeId`.
6. Create or reuse an app DB account and database. Always pass the resolved `BranchId` to branch-scoped AIDAP actions.
7. Fetch endpoint/API key/DB connection information. For PostgreSQL, pass both `BranchId` and the primary `ComputeId` to `DescribeWorkspaceEndpoint` and `DescribeDBAccountConnection`.
8. Store `DATABASE_URL` in a local env file with mode `600`, inject runtime variables into ECS systemd env files, VKE Secrets, or veFaaS env vars, and do not print the full URL.
9. Run migrations with the app's migration tool, direct PostgreSQL client, or the preserved `supabase_dataplane.py apply-migration` command when compatibility with the old skill is required.
10. Verify one database-backed behavior with `psql` (`select 1` or a table-list query) or the app's health check.
11. Re-check `DescribeDBAccountConnection.Result.AllowHost`; if broad ranges such as `0.0.0.0/0` or `::/0` remain, warn that public access is not narrowed. `CreateAccessControlList` CLI array arguments have returned `InvalidParameterFormat`, so do not claim ACL tightening succeeded without this verification.

## Control-Plane DB Fallback

If `CreateDBAccount` or `CreateDatabase` fails with `PrimaryComputeNotFound`, gather these read-only facts before changing IDs or retrying blindly:

```bash
ve aidap DescribeDefaultBranch --WorkspaceId ws-xxxx
ve aidap DescribeBranches --WorkspaceId ws-xxxx
ve aidap DescribeComputes --WorkspaceId ws-xxxx --BranchId br-xxxx
```

When the target branch is the default branch and `DescribeComputes` reports a `Primary` database compute in `Active` state, treat the failure as AIDAP control-plane inconsistency. Use the admin `POSTGRES_URL` from deploy env vars as a fallback only after the user accepts using a credential-bearing database URL:

```bash
ve aidap DescribeSupabaseDeployEnvVars --WorkspaceId ws-xxxx --BranchId br-xxxx
psql "$POSTGRES_URL"
```

For the fallback, create the app role and database through SQL. `CREATE DATABASE appdb OWNER app_user` can fail for a non-superuser admin connection with `must be able to SET ROLE`. Use admin-owned database creation, then grant the app role access:

```sql
CREATE ROLE app_user LOGIN PASSWORD '<secret>';
CREATE DATABASE appdb;
\connect appdb
GRANT CONNECT ON DATABASE appdb TO app_user;
GRANT USAGE, CREATE ON SCHEMA public TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
```

Do not print or persist `POSTGRES_URL`, generated passwords, or SQL containing secrets.

## Runtime Variables

Common variables:

```text
DATABASE_URL
```

Supabase-compatible engine values:

```text
SUPABASE_URL
SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY
```

For frontend frameworks, only expose public URL and anon key values through framework-specific public prefixes. Keep service-role keys and database URLs server-side.

When writing `DATABASE_URL` locally for deployment handoff, use a credential file outside source-controlled paths when possible, set mode `600`, and report the file path instead of the URL value.

## Old Skill Data-Plane Compatibility

When `database_engine=supabase` and `volcengine-deploy` or a user workflow expects old Supabase skill actions, use:

```bash
python3 skills/volcengine-supabase/scripts/supabase_dataplane.py execute-sql --workspace-id ws-xxxx --query "select 1"
python3 skills/volcengine-supabase/scripts/supabase_dataplane.py apply-migration --workspace-id ws-xxxx --name deploy_migration --query-file ./migration.sql
python3 skills/volcengine-supabase/scripts/supabase_dataplane.py generate-typescript-types --workspace-id ws-xxxx --schemas public
```

Do not store service-role keys, generated connection URLs, or migration SQL containing secrets in `.volcengine/created-resources.json`.

## Cleanup

Record CLI-created workspaces, branches, databases, and accounts in `.volcengine/created-resources.json` when `volcengine-deploy` creates them. Do not record secret values. Destructive cleanup must require explicit user confirmation.
