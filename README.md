# volcengine-skills

火山引擎团队维护的 skill 仓库，面向火山引擎（Volcengine）使用场景，为 Claude Code / Codex / Gemini CLI 等 agent 提供开箱即用的 skills 与 hooks。

**[快速安装 →](#快速安装)**

## 仓库包含什么

### Skills

按场景封装的、agent 可自动触发的能力。每个 skill 一个子目录，命名以 `volcengine-` 为前缀。

> _暂无 skill（仓库处于 init 阶段，skills 会随后续 MR 陆续落入）。_
>
> 落入后此列表将更新为：
>
> | Skill | 场景 |
> | --- | --- |
> | _待填充_ | _待填充_ |

### Hooks

跨 skill 复用的钩子（session-start 注入、tool-pre 校验等）。

> _暂无 hook。_

### Commands & Agents

仓库级 slash commands 与 subagent 配置。

> _暂无。_

## 快速安装

### 前置条件

- 已配置火山引擎鉴权环境变量（`VOLCENGINE_ACCESS_KEY` / `VOLCENGINE_SECRET_KEY` / `VOLCENGINE_REGION`）
- 已安装 `ve`（Volcengine CLI），可被 skill 调用
- 对应 agent host 已就绪（Claude Code / Codex / Gemini CLI 任一）

### Claude Code

**添加 marketplace**（仅首次）：

```bash
/plugin marketplace add volcengine/volcengine-skills
```

**安装 plugin**：

```bash
/plugin install volcengine@volcengine-skills
```

**更新**：

```bash
/plugin marketplace update volcengine-skills
```

### Gemini CLI

```bash
gemini extensions install https://github.com/volcengine/volcengine-skills
```

### Codex / 其他 host

将本仓库 clone 到本地后挂载：

```bash
git clone https://github.com/volcengine/volcengine-skills ~/.agent-skills/volcengine-skills
```

然后在对应 host 的配置里把 `~/.agent-skills/volcengine-skills/skills` 纳入 skills 搜索路径。

## 目录结构

```
volcengine-skills/
├── skills/           # 所有 skill（一个 skill 一个子目录）
├── hooks/            # 所有 hook
├── commands/         # slash commands
├── agents/           # subagent 配置
├── scripts/          # 通用辅助脚本
├── docs/             # 规范文档
│   ├── contributing-guide.md   # 贡献规范
│   └── skill-spec.md           # 机器可读校验规格
└── tests/            # 仓库级测试
```

## 贡献

- 先读 [`docs/contributing-guide.md`](./docs/contributing-guide.md)（附 `/volcengine-skill-validator` 一键校验）
- skill 必须以 `volcengine-` 为前缀，env / bin 依赖必须在 `metadata.openclaw.requires` 中声明
- 单次 MR 只解决一个问题；commit message 遵循 [Conventional Commits](https://www.conventionalcommits.org/)

## License

MIT — 见 [LICENSE](./LICENSE)
