---
name: volcengine-find-skill
description: Find and recommend optional Volcengine plugins and skills from the Volcengine skills marketplace. Use when the user asks which Volcengine skill or plugin to install, wants to discover capabilities by product or scenario, asks for compute/database/storage/serverless/IaC skill recommendations, or has a Volcengine task that is not covered by the currently installed core skills. This prototype uses a mock OpenAPI lookup script.
---

# Volcengine Skill Finder

Use this core skill to help users discover optional Volcengine plugins and scenario skills. It recommends installable plugin bundles rather than copying extension skill content into core.

## Workflow

1. Summarize the user's target scenario in one short query.
2. Run the mock OpenAPI lookup script:

```bash
python3 {skill_dir}/scripts/find_skill.py "<query>"
```

3. Read the returned recommendation:
   - `plugin`: installable plugin bundle
   - `skill`: matching skill inside that plugin
   - `reason`: why it matches
   - `install.codex`: Codex install path
   - `install.claude`: Claude Code install path
4. Tell the user whether the recommendation requires installing an optional plugin.
5. If the user asks to install it and the current environment supports plugin installation, use the relevant host's plugin install path. Otherwise, provide the exact command or UI path.

## Guidance

- Keep `volcengine-skills` as the core plugin. It contains this finder plus base skills such as CLI, deploy, API lookup, SDK generation, knowledge search, and troubleshooting.
- Recommend optional plugins by product domain:
  - `volcengine-compute` for ECS, VKE, CLB, and compute scenarios
  - `volcengine-database` for RDS, Redis, AIDAP/Supabase, and database scenarios
  - `volcengine-storage` for TOS and object storage scenarios
  - `volcengine-serverless` for veFaaS and serverless scenarios
  - `volcengine-iac` for Terraform, landing zone, modules, and IaC scenarios
- When no strong optional match exists, recommend staying in core and using `volcengine-cli`, `volcengine-api`, `volcengine-knowledge-search`, or `volcengine-troubleshooting`.

## Output Shape

Answer concisely:

```text
推荐安装 <plugin>，里面的 <skill> 最匹配。
原因：...
Codex：...
Claude Code：...
```

If multiple plugins are relevant, list the top two and say which one to install first.
