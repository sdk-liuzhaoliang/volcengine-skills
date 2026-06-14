# volcengine-skills

**English** | [简体中文](./README.md)

A skills repository maintained by the Volcengine team, targeting Volcengine use cases and providing out-of-the-box skills for agents such as Claude Code / Codex / OpenCode / Cursor / Gemini CLI.

**[Quick Install →](#quick-install)**

## What's Included

### Skills

| Skill | Use case |
| --- | --- |
| `volcengine-cli` | Create/query/manage cloud resources via the `ve` CLI (ECS/VPC/CLB/RDS/Redis/TOS, etc.) |
| `volcengine-prepare` | Analyze a local directory or GitHub repo and recommend a deployment shape (ECS/VKE/veFaaS) |
| `volcengine-deploy` | Deploy a local directory or GitHub repo to Volcengine |
| `volcengine-iac` | Terraform-based infrastructure orchestration for Volcengine |
| `volcengine-api` | Query Volcengine API specs (parameters, error codes, response structures, etc.) |
| `volcengine-sdk-generator` | Generate runnable Volcengine SDK examples and answer SDK config questions on demand |
| `volcengine-tosutil` | Manage Volcengine TOS object storage resources |
| `volcengine-vefaas` | Deploy and manage Volcengine veFaaS serverless applications |
| `volcengine-db-supabase` | Manage Volcengine AIDAP database workspaces (Supabase / PostgreSQL) and use them as deployment database providers |
| `volcengine-troubleshooting` | Troubleshoot and diagnose Volcengine issues |
| `volcengine-knowledge-search` | Search Volcengine official docs and fetch full text (product concepts/usage/billing/deploy/best practices/terms) |
| `volcengine-find-skill` | Discover and recommend optional plugins / skills from the Volcengine skills marketplace (currently a mock OpenAPI prototype) |

### Optional Plugins

The root `skills/` directory remains the core install. More focused product-domain capabilities are split into optional plugins. Users can install them directly or ask `volcengine-find-skill` for a recommendation first.

| Plugin | Use case | Example Skill |
| --- | --- | --- |
| `volcengine-compute` | ECS / VKE / CLB / compute resource scenarios | `volcengine-compute-ecs-ops` |
| `volcengine-database` | RDS / Redis / AIDAP / database diagnostics and migrations | `volcengine-database-rds-ops` |
| `volcengine-storage` | TOS / object storage / lifecycle / access diagnosis | `volcengine-storage-tos-ops` |
| `volcengine-serverless` | veFaaS / functions / gateways / serverless deployment | `volcengine-serverless-vefaas-ops` |
| `volcengine-iac` | Terraform / landing zone / modules / IaC orchestration | `volcengine-iac-terraform-ops` |

## Quick Install

### Prerequisites

#### Install ve and vefaas

```bash
npm i -g @volcengine/cli
npm i -g https://vefaas-cli.tos-cn-beijing.volces.com/volcengine-vefaas-latest.tgz
```

#### Install tosutil

See [installation commands](./skills/volcengine-tosutil/SKILL.md#安装命令).

### Generic Install

```bash
# Choose one of the following three

# 1) Recommended: install globally, skip all confirmation prompts
npx skills add sdk-liuzhaoliang/volcengine-skills --global --yes

# 2) Interactive: manually choose scope (global/project), target agents, and specific skills
npx skills add sdk-liuzhaoliang/volcengine-skills

# 3) Install to specific agents only, copying files instead of symlinking (eg. Claude Code)
npx skills add sdk-liuzhaoliang/volcengine-skills --global --yes --agent claude-code --copy

# Or copy manually
# Copy the skills/ directory to ~/.claude/skills/ (for Claude Code)
# Copy the skills/ directory to ~/.agents/skills/ (for Codex, etc.)
```

### Claude Code

**Add the marketplace** (first time only):

```bash
/plugin marketplace add sdk-liuzhaoliang/volcengine-skills
```

**Install and reload the plugin**:

```bash
/plugin install volcengine@volcengine-skills
/reload-plugins
```

**Install optional plugins**:

```bash
/plugin install volcengine-database@volcengine-skills
/plugin install volcengine-storage@volcengine-skills
```

**Update**:

```bash
/plugin marketplace update volcengine-skills
```

### Codex

```bash
codex plugin marketplace add sdk-liuzhaoliang/volcengine-skills
```

```text
Then open Codex, run /plugins, and install volcengine-skills or an optional plugin.
```

### Discover Optional Skills

After installing core, ask the agent to use `volcengine-find-skill` to recommend optional plugins:

```text
Which Volcengine skill should I install to troubleshoot RDS slow queries?
```

The finder currently uses a mock OpenAPI script. When the real endpoint is ready, replace the lookup function in `skills/volcengine-find-skill/scripts/find_skill.py`.

### Gemini CLI

```bash
gemini extensions install https://github.com/sdk-liuzhaoliang/volcengine-skills
```

### OpenCode

Type the following directly in OpenCode:

```text
Fetch and follow instructions from https://github.com/sdk-liuzhaoliang/volcengine-skills/blob/main/.opencode/INSTALL.md
```

### Cursor

Type the following in the Cursor Agent chat:

```text
/add-plugin volcengine-skills@https://github.com/sdk-liuzhaoliang/volcengine-skills
```

## Directory Structure

```
volcengine-skills/
├── skills/                 # Core skills, preserving default install compatibility
├── plugins/                # Optional product-domain plugins
├── .claude-plugin/         # Claude Code plugin / marketplace manifest
├── .codex-plugin/          # Codex plugin / marketplace manifest
├── .opencode/              # OpenCode configuration
├── .cursor/                # Cursor rules
└── gemini-extension.json   # Gemini CLI extension manifest
```

## License

MIT — see [LICENSE](./LICENSE)
