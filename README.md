# volcengine-skills

[English](./README_en.md) | **简体中文**

Volcengine Skills 是火山引擎团队维护的 **Skill Marketplace**，面向 Claude Code / Codex / OpenCode / Cursor / Gemini CLI 等 agent。这个仓库不是单一大包，而是一个 **多 Plugin 仓库**：默认安装 core plugin，产品域能力按需安装。

**[快速安装 →](#快速安装)** | **[如何使用 →](#如何使用)**

## 设计模型

### Core Plugin

`volcengine-skills` 是默认安装的 core plugin，内容来自根目录 `skills/`。它保留基础能力和历史兼容性：

- `volcengine-cli`：通过 `ve` CLI 操作火山引擎资源
- `volcengine-prepare` / `volcengine-deploy`：分析项目并部署到火山引擎
- `volcengine-api` / `volcengine-sdk-generator`：查询 API 规格并生成 SDK 示例
- `volcengine-knowledge-search`：检索火山引擎官方文档
- `volcengine-troubleshooting`：故障排查
- `volcengine-find-skill`：发现并推荐可选 plugin / skill

### Optional Plugins

更细的产品域能力放在 `plugins/volcengine-*` 下，用户按需安装：

| Plugin | 场景 | 示例 Skill |
| --- | --- | --- |
| `volcengine-compute` | ECS / VKE / CLB / 计算资源场景 | `volcengine-compute-ecs-ops` |
| `volcengine-database` | RDS / Redis / AIDAP / 数据库诊断与迁移 | `volcengine-database-rds-ops` |
| `volcengine-storage` | TOS / 对象存储 / 生命周期 / 访问诊断 | `volcengine-storage-tos-ops` |
| `volcengine-serverless` | veFaaS / 函数 / 网关 / serverless 部署 | `volcengine-serverless-vefaas-ops` |
| `volcengine-iac` | Terraform / Landing Zone / 模块 / IaC 编排 | `volcengine-iac-terraform-ops` |

### Find Skill

`volcengine-find-skill` 是 core plugin 自带的发现入口。用户只安装 core 时，可以先问它应该安装哪个可选 plugin。

示例：

```text
我想排查 RDS 慢查询，应该装哪个火山引擎 skill？
```

它会返回推荐的 plugin、匹配的 skill、推荐理由，以及 Codex / Claude Code / npx 的安装方式。当前实现使用 mock OpenAPI 脚本，真实接口就绪后替换 `skills/volcengine-find-skill/scripts/find_skill.py` 的查询函数即可。

## 快速安装

### 推荐路径：通过 Plugin Marketplace 安装

这个仓库是多 plugin marketplace。先添加 marketplace，再安装 core 或可选 plugin。

#### Codex

添加 marketplace：

```bash
codex plugin marketplace add sdk-liuzhaoliang/volcengine-skills
```

然后进入 Codex，执行：

```text
/plugins
```

添加 marketplace 后，Codex 会把 `volcengine-skills` 作为默认安装项。若你的 Codex 版本没有自动安装，请先手动安装 core plugin，再安装扩展 plugin。

在 `Volcengine Skills` marketplace 中可以看到：

- `volcengine-skills`：core plugin，默认安装项
- `volcengine-compute`：计算扩展
- `volcengine-database`：数据库扩展
- `volcengine-storage`：存储扩展
- `volcengine-serverless`：serverless 扩展
- `volcengine-iac`：IaC 扩展

#### Claude Code

添加 marketplace：

```bash
/plugin marketplace add sdk-liuzhaoliang/volcengine-skills
```

安装 core plugin（Claude Code 目前需要显式安装）：

```bash
/plugin install volcengine@volcengine-skills
/reload-plugins
```

按需安装可选 plugin：

```bash
/plugin install volcengine-database@volcengine-skills
/plugin install volcengine-storage@volcengine-skills
/plugin install volcengine-serverless@volcengine-skills
```

更新 marketplace：

```bash
/plugin marketplace update volcengine-skills
```

### 兼容路径：只安装 core skills

如果你的 agent 暂时不支持 plugin marketplace，可以用 `npx skills add` 安装根目录 `skills/`，也就是 core skills：

```bash
npx skills add sdk-liuzhaoliang/volcengine-skills --global --yes
```

交互式安装：

```bash
npx skills add sdk-liuzhaoliang/volcengine-skills
```

安装某个可选 plugin 下的 skills：

```bash
npx skills add sdk-liuzhaoliang/volcengine-skills/tree/main/plugins/volcengine-database/skills
```

手动复制：

```text
将 skills/ 目录复制到 ~/.claude/skills/     # Claude Code
将 skills/ 目录复制到 ~/.agents/skills/     # Codex 等
```

## 如何使用

### 方式一：先装 core，再用 Find Skill 推荐

安装 `volcengine-skills` 后，直接问 agent：

```text
我想把项目部署到火山引擎，应该用哪个 skill？
```

```text
我想排查 TOS bucket 权限问题，需要安装哪个插件？
```

```text
帮我找一个适合 Redis 连接失败排查的火山引擎 skill。
```

agent 会使用 `volcengine-find-skill`，推荐例如：

```text
推荐安装 volcengine-database，里面的 volcengine-database-rds-ops 最匹配。
原因：匹配数据库连接诊断、慢查询、迁移规划等场景。
Codex：codex plugin marketplace add ...，然后在 /plugins 安装 volcengine-database
Claude Code：/plugin install volcengine-database@volcengine-skills
```

### 方式二：直接安装已知产品域 plugin

如果你已经知道场景，可以直接安装对应 plugin：

| 需求 | 安装 |
| --- | --- |
| ECS / VKE / CLB | `volcengine-compute` |
| RDS / Redis / AIDAP | `volcengine-database` |
| TOS / 对象存储 | `volcengine-storage` |
| veFaaS / 函数 | `volcengine-serverless` |
| Terraform / Landing Zone | `volcengine-iac` |

### 方式三：只使用 core 基础能力

只安装 `volcengine-skills` 也可以完成基础工作：

- 查 API 参数、错误码和响应结构
- 生成 SDK 示例
- 检索官方文档
- 使用 `ve` CLI 操作资源
- 分析和部署项目
- 做通用故障排查

## 前置依赖

部分 skill 会调用本地工具。按需安装：

```bash
npm i -g @volcengine/cli
npm i -g https://vefaas-cli.tos-cn-beijing.volces.com/volcengine-vefaas-latest.tgz
```

TOS 工具见 [安装命令](./skills/volcengine-tosutil/SKILL.md#安装命令)。

## 其他 Agent

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

```text
volcengine-skills/
├── skills/                     # core skills，默认安装和历史兼容
├── plugins/
│   ├── volcengine-skills -> ..  # core plugin marketplace 入口
│   ├── volcengine-compute/      # optional compute plugin
│   ├── volcengine-database/     # optional database plugin
│   ├── volcengine-storage/      # optional storage plugin
│   ├── volcengine-serverless/   # optional serverless plugin
│   └── volcengine-iac/          # optional IaC plugin
├── .claude-plugin/             # Claude Code marketplace manifest
├── .codex-plugin/              # Codex core plugin manifest
├── .agents/plugins/            # Codex marketplace manifest
├── .opencode/                  # OpenCode 配置
├── .cursor/                    # Cursor 规则
└── gemini-extension.json       # Gemini CLI 扩展清单
```

## License

MIT — 见 [LICENSE](./LICENSE)
