# volcengine-skills 贡献规范（v0.1）

> 适用仓库：`volcengine/volcengine-skills`
> 配套机器可读校验规格：[`skill-spec.md`](./skill-spec.md)
> 上游参考：[ClawHub skill-format](https://github.com/openclaw/clawhub/blob/main/docs/skill-format.md) · [agentskills.io](https://agentskills.io/specification)

---

## 📌 不想看完？一条命令搞定

文档很长，但 **99% 的场景你不需要全部读完**。仓库自带 `volcengine-skill-validator` skill，一键跑完所有规则校验 + 输出质量打分：

```bash
claude "/volcengine-skill-validator ./skills/volcengine-xxx"
```

输出示例：

```text
✅ Skill: volcengine-cli    Score: 87/100    Grade: B
   Errors: 0   Warnings: 2   Passed: 18

  Metadata         ████████████████░░░░  18/20
  Security         ████████████████████  30/30
  Naming/Structure ████████████████████  10/10
  Code Quality     ██████████████████░░  22/25
  Content Size     ████████████████████  10/10
  Self-test        ████████████░░░░░░░░   2/5

⚠️  R-DESC-003 (warn): description 含工作流词 "then" @ line 3
⚠️  R-CODE-004 (warn): scripts/run.sh 包含 '...' 占位符
```

**合并门槛**：0 errors + score ≥ 75。本文用于排查 validator 提示、手工核对细则、或想理解"为什么这么规定"。

---

## 0. 熟练者极简自查（10 秒扫完）

写完 skill 提 MR 前扫一眼，下面打完勾就基本稳了：

- [ ] `name` 以 `volcengine-` 开头
- [ ] `description` 以 `Use when` 开头、不含"先…再…"动作链
- [ ] 读 env / 调 bin 全部声明在 `openclaw.requires`
- [ ] 所有代码块都标语言，`bash -n` / `py_compile` 通过
- [ ] SKILL.md < 500 行
- [ ] commit 遵循 `<type>(<scope>): <subject>`
- [ ] 跑一次 `/volcengine-skill-validator`，score ≥ 75 且无 error

不熟的同学继续往下看。

---

## 0.1 一分钟速览（完整版）

合规 skill = 满足下面 5 条：

1. **命名** 以 `volcengine-` 开头，slug `^[a-z0-9][a-z0-9-]*$`
2. **Frontmatter** 必填字段齐全；读 env / 调 bin 必须声明 `metadata.openclaw`
3. **正文** SKILL.md < 500 行 / < 5000 tokens
4. **脚本可运行**：所有代码块必须标注语言、CI 检测能直接执行
5. **提交** Conventional Commits + MR 模板

> 自测文档不是硬规范，但**强烈建议**附一份或链接到集成测试，方便 reviewer 复现（见 §6）。

---

## 0.5 写 skill 之前（4 条原则）

来自 [agentskills.io best practices](https://agentskills.io/skill-creation/best-practices)：

1. **从真实任务提炼**，别让 LLM 凭空生成。先跑一个真实任务，把你纠正过的点、补充过的上下文、踩过的边界提炼成 skill
2. **只写 agent 不知道的**。不解释 HTTP / PDF / SQL 是什么。判断：去掉这段 agent 会搞错吗？不会 → 删
3. **给默认值，别罗列选项**。❌ "可用 A/B/C/D" → ✅ "用 A，OCR 场景回退 B"
4. **教方法，别给具体答案**。❌ 给具体 join 语句 → ✅ 给可复用的查询步骤

---

## 1. 仓库结构

```
volcengine-skills/
├── skills/
│   └── volcengine-<xxx>/
│       ├── SKILL.md          # 必填
│       ├── references/       # 可选：长文档
│       ├── scripts/          # 可选：可执行脚本
│       └── assets/           # 可选：模板 / 资源
├── hooks/
└── .github/workflows/        # CI 校验
```

子目录命名对齐 [agentskills.io](https://agentskills.io/specification) 官方：`references/` / `scripts/` / `assets/`。不采纳 `workflows/` 等自造目录。

---

## 2. 命名规范（硬性）

- **必须以 `volcengine-` 为前缀**
- slug 正则：`^[a-z0-9][a-z0-9-]*$`，长度 ≤ 64
- **目录名 = frontmatter `name`**，必须一致

合法：`volcengine-cli` / `volcengine-ecs-manager`
非法：`VolcengineCLI` / `ve-cli`（无前缀） / `volcengine--cli` / `-volcengine`

---

## 3. Frontmatter（硬性）

### 3.1 最小合规示例

```yaml
---
name: volcengine-cli
description: Use when the user asks to create, query, modify, or delete Volcengine cloud resources, or mentions `ve`, ECS/VPC/CLB/RDS — even if they don't explicitly say "Volcengine".
version: 1.0.0
user-invocable: true
allowed-tools: Bash, Read, Write
metadata:
  openclaw:
    primaryEnv: VOLCENGINE_ACCESS_KEY
    requires:
      env:  [VOLCENGINE_ACCESS_KEY, VOLCENGINE_SECRET_KEY, VOLCENGINE_REGION]
      bins: [ve]
---
```

### 3.2 必填字段

| 字段 | 约束 |
|---|---|
| `name` | 见 §2 |
| `description` | ≤ 1024 字符；见 §3.3 |
| `version` | 语义化版本，如 `1.0.0` |
| `user-invocable` | `true` / `false` |
| `allowed-tools` | 逗号分隔工具名 |
| `metadata.openclaw` | 读 env / 调 bin 必填，见 §4 |

> **可选字段**（`emoji` / `homepage` / `os` / `install` 等）大部分 skill 用不到，完整字段清单见 [`skill-spec.md`](./skill-spec.md)。

### 3.3 `description` 写法（最易踩坑）

`description` 是 Claude 决定是否加载 skill 的唯一依据。三条规则：

1. **祈使句 + 聚焦用户意图**：`Use when the user asks to…`
2. **可以 pushy**：显式列场景，包括用户没直说的情况（`even if they don't explicitly mention…`）
3. **不要描述工作流**：禁止"先…再…"动作链（会让 Claude 跳过 SKILL.md 正文）

| ❌ 错 | ✅ 对 |
|---|---|
| `First check credentials, then call ve, then format output.`（工作流） | `Use when user asks to create/query/delete Volcengine resources, or mentions ve/ECS/VPC/CLB/RDS.` |

---

## 4. `metadata.openclaw` 安全声明（硬性）

### 4.1 什么时候必填

任一条满足即必填：
1. 读取**任何**环境变量
2. 调用**任何**外部二进制

未声明 → claw hub 校验失败 → MR 无法合并。

### 4.2 字段结构

```yaml
metadata:
  openclaw:
    primaryEnv: VOLCENGINE_ACCESS_KEY    # 主鉴权变量
    requires:
      env:  [...]                         # 实际读的环境变量
      bins: [...]                         # 调用的裸命令名
```

> `requires` 还支持 `anyBins` / `config`、以及 `install` 依赖安装区块，不常用，见 [`skill-spec.md`](./skill-spec.md)。

### 4.3 自查脚本（提 MR 前跑）

```bash
# 扫环境变量
grep -rhoE '\$[A-Z_]+|getenv\("[^"]+"\)|process\.env\.[A-Z_]+' \
  SKILL.md scripts/ references/ 2>/dev/null | sort -u

# 扫外部命令（按实际用到的补全关键字）
grep -rhE '\b(ve|kubectl|curl|jq|aws)\b' SKILL.md scripts/ 2>/dev/null | sort -u
```

输出 vs frontmatter `requires.env` / `bins`，缺一补一。

---

## 5. 内容规范

- **语言**：中英不限。`name` / `description` 推荐英文
- **体量**：SKILL.md < 500 行 / < 5000 tokens；长内容拆 `references/`；可复用脚本进 `scripts/`
- **推荐章节**：概述 / 什么时候用 / 前置条件 / 使用方法 / 常见问题

### 5.1 代码块可运行性（硬性）

**SKILL.md / scripts/ 里所有代码块必须可直接执行**。提交前自查：

```bash
# 所有代码块必须标注语言（不能是裸 ``` ）
# Bash 语法检查
for f in scripts/*.sh; do bash -n "$f" || echo "❌ $f"; done
# Python 语法检查
for f in scripts/*.py; do python -m py_compile "$f" || echo "❌ $f"; done
```

CI 会跑同样的检测。

**禁止**：裸 ``` 代码块（没标语言）、伪代码 / `<TODO>` / `...` 占位符。

---

## 6. 自测（建议，非强制）

不强制，但**强烈建议**提供其中之一：

- 同目录放一份 `TESTING.md`（参考模板：[`skill-spec.md#testing-template`](./skill-spec.md#testing-template)）
- MR 描述里贴一段真实冒烟用例的执行记录（命令 + 脱敏输出）
- 链接到已有的集成测试 / e2e 脚本

目的只有一个：让 reviewer 能在 5 分钟内判断 "这个 skill 真的能跑"。

---

## 7. 提交规范

### 7.1 分支

- `feat/volcengine-xxx` — 新增
- `fix/volcengine-xxx` — 修 bug
- `docs/xxx` — 文档
- `refactor/xxx` — 重构

### 7.2 commit message（Conventional Commits）

```
<type>(<scope>): <subject>
```

`type` = `feat` / `fix` / `docs` / `refactor` / `chore` / `test`
`subject` = 祈使句、无句号、有信息量（禁 `update` / `wip`）

示例：
```
feat(volcengine-cli): add skill for managing Volcengine ECS
fix(volcengine-cli): correct env var name VOLCENGINE_REGION
```

### 7.3 MR 模板

```markdown
## 改动说明
<一句话说清楚做了什么>

## 自测
<贴冒烟用例执行记录，或链接 TESTING.md / e2e 测试>

## 自查
- [ ] Frontmatter 必填字段齐全
- [ ] 读 env / 调 bin 全部在 `openclaw.requires` 里
- [ ] 所有代码块可直接执行（本地 `bash -n` / `py_compile`）
- [ ] `skills-ref validate` + claw hub 校验通过
- [ ] commit 符合 Conventional Commits
```

---

## 8. CI 校验（三层）

| 层 | 工具 | 检查什么 |
|---|---|---|
| 1 | [`skills-ref validate`](https://github.com/agentskills/agentskills/tree/main/skills-ref) | 官方 frontmatter 格式 |
| 2 | 本仓库 lint | 规则定义在 [`skill-spec.md`](./skill-spec.md)，计划做一个 skill-validator skill 自动跑 |
| 3 | claw hub openclaw 校验 | 扫代码实际读的 env，必须全部声明 |

---

## 9. Checklist（作者 / Reviewer 共用）

- [ ] 目录以 `volcengine-` 开头、与 `name` 一致
- [ ] Frontmatter 必填字段齐全，`description` 只写触发条件
- [ ] 跑过 §4.3 自查脚本，env/bins 全部在 `requires` 里
- [ ] 所有代码块标了语言、本地通过 `bash -n` / `py_compile`
- [ ] SKILL.md ≤ 500 行
- [ ] 有自测证据（TESTING.md / MR 冒烟记录 / e2e 链接 任选其一）
- [ ] 分支 / commit / MR 合规
- [ ] CI 三层全绿

---

## 10. 反模式

| 反模式 | 正确做法 |
|---|---|
| `description` 描述工作流 | 只写触发条件（Use when…） |
| 读 env 没声明 | 补 `openclaw.requires.env` |
| 代码块没标语言 / 跑不通 | 标语言 + `bash -n` 自查 |
| 伪代码 / `<TODO>` 占位 | 给真实可运行示例 |
| 调 `sed` / `awk` 改文件 | 引导用 Claude Edit |
| 正文塞 300 行参考 | 拆到 `references/` |
| 自造 `workflows/` 目录 | 用 `scripts/` + SKILL.md 写流程 |

---

## 11. 参考

- [ClawHub skill-format](https://github.com/openclaw/clawhub/blob/main/docs/skill-format.md)（metadata 权威）
- [agentskills.io 规范](https://agentskills.io/specification)
- [agentskills.io best practices](https://agentskills.io/skill-creation/best-practices) · [optimizing descriptions](https://agentskills.io/skill-creation/optimizing-descriptions)
- [`skill-spec.md`](./skill-spec.md) — 本仓库机器可读校验规格
