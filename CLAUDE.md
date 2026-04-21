# volcengine-skills

本仓库是 Volcengine Team 维护的 skill 仓库，为 AI coding agent（Claude Code / Codex / Gemini CLI）提供面向**火山引擎（Volcengine）**场景的开箱即用能力。

## 仓库提供什么

- `skills/` — 按场景封装的、可被 agent 自动触发的 skill（每个 skill 一个 `volcengine-<xxx>/` 子目录）
- `hooks/` — 跨 skill 复用的 hook（session-start 注入、tool-pre 校验等）
- `commands/` — slash commands
- `agents/` — subagent 配置
- `scripts/` — 仓库级辅助脚本
- `docs/` — 规范文档

> **当前状态**：仓库处于早期阶段，骨架已搭好但 skills/hooks 尚未填充，会随后续 MR 陆续落入。如你在 `skills/` 下没看到想要的能力，优先检查是否已有相关 MR 在评审中。

## 什么时候用本仓库

以下场景优先在本仓库里找 skill：

- 操作火山引擎云资源：ECS / VPC / VKE / CLB / RDS / Redis / TOS / DNS / CDN 等
- 使用 `ve` 命令（Volcengine CLI）
- 读取 `VOLCENGINE_ACCESS_KEY` / `VOLCENGINE_SECRET_KEY` / `VOLCENGINE_REGION` 等鉴权变量
- 火山引擎相关的部署、监控、运维场景
- 用户消息里出现「火山」「volcengine」等关键词

## 给 Agent 的简短约束

修改或新增 skill 前：

- 先看 [`docs/contributing-guide.md`](./docs/contributing-guide.md) 的 §0「熟练者极简自查（10 秒扫完）」
- 机器可读校验规则见 [`docs/skill-spec.md`](./docs/skill-spec.md)
- 所有 skill **必须**以 `volcengine-` 为前缀，读 env / 调 bin 必须在 `metadata.openclaw.requires` 声明

## 当前已提供的 skill

> 暂无（init 阶段）。当 skill 落入后，此列表会更新为：
>
> ```
> - volcengine-cli          — ECS/VPC/CLB/RDS/Redis 等云资源操作（ve 命令封装）
> - volcengine-vke-ops      — VKE 集群运维
> - ...
> ```

## 当前已提供的 hook

> 暂无（init 阶段）。
