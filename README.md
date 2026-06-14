# volcengine-skills

[English](./README_en.md) | **简体中文**

火山引擎团队维护的 skill 仓库，面向火山引擎（Volcengine）使用场景，为 Claude Code / Codex / OpenCode / Cursor / Gemini CLI 等 agent 提供开箱即用的 skills。

**[快速安装 →](#快速安装)**

## 仓库包含什么

### Skills

| Skill | 场景 |
| --- | --- |
| `volcengine-cli` | 用 `ve` CLI 创建/查询/管理云资源（ECS/VPC/CLB/RDS/Redis/TOS 等） |
| `volcengine-prepare` | 分析本地目录或 GitHub 仓库，推荐部署形态（ECS/VKE/veFaaS） |
| `volcengine-deploy` | 把本地目录或 GitHub 仓库部署到火山引擎 |
| `volcengine-iac` | 基于 Terraform 的火山引擎基础设施编排 |
| `volcengine-api` | 查询火山引擎 API 规格（参数、错误码、返回结构等） |
| `volcengine-sdk-generator` | 生成可运行的火山引擎 SDK 示例，并按需回答 SDK 配置问题 |
| `volcengine-tosutil` | 管理火山引擎 TOS 对象存储资源 |
| `volcengine-vefaas` | 部署与管理火山引擎 veFaaS serverless 应用 |
| `volcengine-db-supabase` | 管理火山引擎 AIDAP 数据库 workspace（Supabase / PostgreSQL），并作为部署数据库方案 |
| `volcengine-troubleshooting` | 火山引擎故障排查与诊断 |
| `volcengine-knowledge-search` | 检索火山引擎官方文档并获取全文（产品概念/用法/计费/部署/最佳实践/服务条款等） |
| `volcengine-find-skill` | 从火山引擎 skills marketplace 中发现并推荐可选 plugin / skill（当前为 mock OpenAPI 原型） |

### Optional Plugins

当前 `skills/` 目录保持为 core 必装能力。更细的产品域能力拆成可选 plugin，用户可以直接安装，也可以先用 `volcengine-find-skill` 查询推荐。

| Plugin | 场景 | 示例 Skill |
| --- | --- | --- |
| `volcengine-compute` | ECS / VKE / CLB / 计算资源场景 | `volcengine-compute-ecs-ops` |
| `volcengine-database` | RDS / Redis / AIDAP / 数据库诊断与迁移 | `volcengine-database-rds-ops` |
| `volcengine-storage` | TOS / 对象存储 / 生命周期 / 访问诊断 | `volcengine-storage-tos-ops` |
| `volcengine-serverless` | veFaaS / 函数 / 网关 / serverless 部署 | `volcengine-serverless-vefaas-ops` |
| `volcengine-iac` | Terraform / Landing Zone / 模块 / IaC 编排 | `volcengine-iac-terraform-ops` |

## 快速安装

### 前置依赖

#### 安装 ve 和 vefaas

```bash
npm i -g @volcengine/cli
npm i -g https://vefaas-cli.tos-cn-beijing.volces.com/volcengine-vefaas-latest.tgz
```

#### 安装 tosutil

见 [安装命令](./skills/volcengine-tosutil/SKILL.md#安装命令)

### 通用安装

```bash
# 以下三条任选其一

# 1) 推荐：全局安装、跳过所有确认提示
npx skills add sdk-liuzhaoliang/volcengine-skills --global --yes

# 2) 交互式：手动选择安装范围（global/project）、目标 agent 和具体 skill
npx skills add sdk-liuzhaoliang/volcengine-skills

# 3) 只装到指定 agent，并用复制代替软链（如安装到 Claude Code）
npx skills add sdk-liuzhaoliang/volcengine-skills --global --yes --agent claude-code --copy

# 或手动复制
# 将 skills/ 目录复制到 ~/.claude/skills/ (适用于 Claude Code)
# 将 skills/ 目录复制到 ~/.agents/skills/ (适用于 codex 等)
```

### Claude Code

**添加 marketplace**（仅首次）：

```bash
/plugin marketplace add sdk-liuzhaoliang/volcengine-skills
```

**安装并重新加载 plugin**：

```bash
/plugin install volcengine@volcengine-skills
/reload-plugins
```

**安装可选 plugin**：

```bash
/plugin install volcengine-database@volcengine-skills
/plugin install volcengine-storage@volcengine-skills
```

**更新**：

```bash
/plugin marketplace update volcengine-skills
```

### Codex

```bash
codex plugin marketplace add sdk-liuzhaoliang/volcengine-skills
```

```text
然后进入 Codex，执行 /plugins，选择 volcengine-skills 或可选 plugin 安装即可
```

### Discover Optional Skills

安装 core 后，可以让 agent 使用 `volcengine-find-skill` 推荐可选插件：

```text
我想排查 RDS 慢查询，应该装哪个火山引擎 skill？
```

当前 finder 使用 mock OpenAPI 脚本，真实接口就绪后可替换 `skills/volcengine-find-skill/scripts/find_skill.py` 中的查询函数。

### Gemini CLI

```bash
gemini extensions install https://github.com/sdk-liuzhaoliang/volcengine-skills
```

### OpenCode

直接在 OpenCode 中输入：

```text
Fetch and follow instructions from https://github.com/sdk-liuzhaoliang/volcengine-skills/blob/main/.opencode/INSTALL.md
```

### Cursor

在 Cursor Agent 聊天中输入：

```text
/add-plugin volcengine-skills@https://github.com/sdk-liuzhaoliang/volcengine-skills
```

## 目录结构

```
volcengine-skills/
├── skills/                 # core skills，保持默认安装和历史兼容
├── plugins/                # optional product-domain plugins
├── .claude-plugin/         # Claude Code plugin / marketplace manifest
├── .codex-plugin/          # Codex plugin / marketplace manifest
├── .opencode/              # OpenCode 配置
├── .cursor/                # Cursor 规则
└── gemini-extension.json   # Gemini CLI 扩展清单
```

## License

MIT — 见 [LICENSE](./LICENSE)
