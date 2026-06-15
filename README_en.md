# volcengine-skills

**English** | [简体中文](./README.md)

Volcengine Skills is a **Skill Marketplace** maintained by the Volcengine team for Claude Code, Codex, OpenCode, Cursor, Gemini CLI, and other agents. This repository is not a single monolithic bundle. It is a **multi-plugin repository**: install the core plugin by default, then install product-domain plugins on demand.

**[Quick Install →](#quick-install)** | **[Usage →](#usage)**

## Design Model

### Core Plugin

`volcengine-skills` is the default core plugin. It is backed by the root `skills/` directory and preserves compatibility with the existing install model:

- `volcengine-cli`: operate Volcengine resources through the `ve` CLI
- `volcengine-prepare` / `volcengine-deploy`: analyze and deploy projects to Volcengine
- `volcengine-api` / `volcengine-sdk-generator`: query API specs and generate SDK examples
- `volcengine-knowledge-search`: search Volcengine official docs
- `volcengine-troubleshooting`: troubleshoot Volcengine issues
- `volcengine-find-skill`: discover and recommend optional plugins / skills

### Optional Plugins

More focused product-domain capabilities live under `plugins/volcengine-*` and can be installed on demand:

| Plugin | Use case | Example Skill |
| --- | --- | --- |
| `volcengine-compute` | ECS / VKE / CLB / compute resource scenarios | `volcengine-compute-ecs-ops` |
| `volcengine-database` | RDS / Redis / AIDAP / database diagnostics and migrations | `volcengine-database-rds-ops` |
| `volcengine-storage` | TOS / object storage / lifecycle / access diagnosis | `volcengine-storage-tos-ops` |
| `volcengine-serverless` | veFaaS / functions / gateways / serverless deployment | `volcengine-serverless-vefaas-ops` |
| `volcengine-iac` | Terraform / landing zone / modules / IaC orchestration | `volcengine-iac-terraform-ops` |

### Find Skill

`volcengine-find-skill` ships with the core plugin. Users can install only core first, then ask it which optional plugin to install.

Example:

```text
Which Volcengine skill should I install to troubleshoot RDS slow queries?
```

It returns the recommended plugin, matching skill, reason, and install instructions for Codex / Claude Code / npx. The current implementation uses a mock OpenAPI script. When the real endpoint is ready, replace the lookup function in `skills/volcengine-find-skill/scripts/find_skill.py`.

## Quick Install

### Recommended: Install Through Plugin Marketplace

This is a multi-plugin marketplace. Add the marketplace first, then install core or optional plugins.

#### Codex

Add the marketplace:

```bash
codex plugin marketplace add sdk-liuzhaoliang/volcengine-skills
```

Then open Codex and run:

```text
/plugins
```

After adding the marketplace, Codex treats `volcengine-skills` as the default installed plugin. If your Codex version does not install it automatically, install the core plugin manually before installing extension plugins.

In the `Volcengine Skills` marketplace you will see:

- `volcengine-skills`: core plugin, installed by default
- `volcengine-compute`: compute extension
- `volcengine-database`: database extension
- `volcengine-storage`: storage extension
- `volcengine-serverless`: serverless extension
- `volcengine-iac`: IaC extension

#### Claude Code

Add the marketplace:

```bash
/plugin marketplace add sdk-liuzhaoliang/volcengine-skills
```

Install the core plugin. Claude Code currently requires this explicit install:

```bash
/plugin install volcengine@volcengine-skills
/reload-plugins
```

Install optional plugins when needed:

```bash
/plugin install volcengine-database@volcengine-skills
/plugin install volcengine-storage@volcengine-skills
/plugin install volcengine-serverless@volcengine-skills
```

Update the marketplace:

```bash
/plugin marketplace update volcengine-skills
```

### Compatible: Install Core Skills Only

If your agent does not support plugin marketplaces yet, use `npx skills add` to install the root `skills/` directory, which means core skills only:

```bash
npx skills add sdk-liuzhaoliang/volcengine-skills --global --yes
```

Interactive install:

```bash
npx skills add sdk-liuzhaoliang/volcengine-skills
```

Install skills from one optional plugin:

```bash
npx skills add sdk-liuzhaoliang/volcengine-skills/tree/main/plugins/volcengine-database/skills
```

Manual copy:

```text
Copy skills/ to ~/.claude/skills/     # Claude Code
Copy skills/ to ~/.agents/skills/     # Codex, etc.
```

## Usage

### Option 1: Install Core, Then Use Find Skill

After installing `volcengine-skills`, ask your agent:

```text
Which skill should I use to deploy this project to Volcengine?
```

```text
Which plugin should I install to troubleshoot TOS bucket permissions?
```

```text
Find a Volcengine skill for Redis connection failures.
```

The agent uses `volcengine-find-skill` and recommends something like:

```text
Install volcengine-database. The best matching skill is volcengine-database-rds-ops.
Reason: it matches database connection diagnosis, slow query triage, and migration planning.
Codex: add the marketplace, then install volcengine-database from /plugins.
Claude Code: /plugin install volcengine-database@volcengine-skills
```

### Option 2: Install a Known Product-Domain Plugin Directly

If you already know the scenario, install the matching plugin directly:

| Need | Install |
| --- | --- |
| ECS / VKE / CLB | `volcengine-compute` |
| RDS / Redis / AIDAP | `volcengine-database` |
| TOS / object storage | `volcengine-storage` |
| veFaaS / functions | `volcengine-serverless` |
| Terraform / landing zone | `volcengine-iac` |

### Option 3: Use Core Capabilities Only

Installing only `volcengine-skills` is enough for base workflows:

- Query API parameters, errors, and response structures
- Generate SDK examples
- Search official docs
- Operate resources through the `ve` CLI
- Analyze and deploy projects
- Run general troubleshooting workflows

## Prerequisites

Some skills call local tools. Install them as needed:

```bash
npm i -g @volcengine/cli
npm i -g https://vefaas-cli.tos-cn-beijing.volces.com/volcengine-vefaas-latest.tgz
```

For TOS tooling, see [installation commands](./skills/volcengine-tosutil/SKILL.md#安装命令).

## Credentials and Configuration

Skills that operate Volcengine products usually require credentials. The following methods are supported:

### AccessKey Environment Variables

```bash
export VOLCENGINE_ACCESS_KEY=<your-access-key-id>
export VOLCENGINE_SECRET_KEY=<your-secret-access-key>
export VOLCENGINE_REGION=cn-beijing
```

### ve CLI Profile

```bash
# ~/.volcengine/config.json
ve configure [--profile <PROFILE_NAME>]
```

After configuration, credentials are stored in `~/.volcengine/config.json`. Skills such as `volcengine-cli`, deployment, troubleshooting, and resource operation workflows can reuse that profile.

### Security Notes

- For local testing, use AccessKey environment variables or `ve configure [--profile <PROFILE_NAME>]`.
- Do not commit AK/SK values to repositories, logs, README files, shell scripts, or issues.
- For production environments, prefer least-privilege policies and temporary credentials.

## Other Agents

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

```text
volcengine-skills/
├── skills/                     # Core skills, default install and compatibility path
├── plugins/
│   ├── volcengine-skills -> ..  # Core plugin marketplace entry
│   ├── volcengine-compute/      # Optional compute plugin
│   ├── volcengine-database/     # Optional database plugin
│   ├── volcengine-storage/      # Optional storage plugin
│   ├── volcengine-serverless/   # Optional serverless plugin
│   └── volcengine-iac/          # Optional IaC plugin
├── .claude-plugin/             # Claude Code marketplace manifest
├── .codex-plugin/              # Codex core plugin manifest
├── .agents/plugins/            # Codex marketplace manifest
├── .opencode/                  # OpenCode configuration
├── .cursor/                    # Cursor rules
└── gemini-extension.json       # Gemini CLI extension manifest
```

## License

MIT — see [LICENSE](./LICENSE)
