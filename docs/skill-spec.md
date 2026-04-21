# volcengine-skills 校验规格（skill-spec）

> 机器可读的校验规则清单，给 `volcengine-skill-validator`（计划中的校验 skill）和 CI lint 用。
> 人类向的贡献规范见 [`volcengine-skills-contributing-guide.md`](./volcengine-skills-contributing-guide.md)。

每条规则都以 `R-<DOMAIN>-<NNN>` 命名，标注严重级（`error` / `warning`）和检测方式（正则 / 命令 / 结构比对）。

---

## 1. Frontmatter 字段完整清单

### 1.1 必填

| 字段 | 类型 | 约束 |
|---|---|---|
| `name` | string | §R-NAME-* |
| `description` | string | §R-DESC-* |
| `version` | string | 语义化版本 `^\d+\.\d+\.\d+$` |
| `user-invocable` | bool | `true` / `false`（Claude Code 特有） |
| `allowed-tools` | string | 逗号分隔工具名（Claude Code 特有） |

### 1.2 条件必填

| 字段 | 何时必填 |
|---|---|
| `metadata.openclaw` | skill 读取任何环境变量 或 调用任何外部二进制时 |

### 1.3 可选（ClawHub 官方字段）

| 字段 | 类型 | 作用 |
|---|---|---|
| `emoji` | string | UI 展示图标 |
| `homepage` | string | 主页或文档链接 |
| `os` | string[] | OS 限制，如 `["macos", "linux"]` |
| `always` | bool | 是否始终激活（少用） |
| `skillKey` | string | 覆盖默认调用 key |
| `license` | string | 许可证标识（发布 ClawHub 需 `MIT-0`） |

### 1.4 别名

ClawHub 同时识别 `metadata.clawdbot` / `metadata.clawdis`。**本仓库统一用 `openclaw`**，禁止混用，命中即 warning。

---

## 2. `metadata.openclaw` 完整结构

```yaml
metadata:
  openclaw:
    primaryEnv: string              # 可选：主鉴权变量
    requires:
      env:     string[]             # 环境变量（必须全部存在）
      bins:    string[]             # 外部命令（必须全部安装）
      anyBins: string[]             # 外部命令（至少一个存在即可）
      config:  string[]             # 读取的配置文件路径
    install:                         # 可选：依赖自动安装规格
      - kind: brew|node|go|uv
        formula: string              # brew 用
        package: string              # node/go/uv 用
        bins:    string[]            # 装好后暴露的命令
```

---

## 3. 校验规则

### 3.1 命名（R-NAME-*）

| ID | 严重级 | 规则 | 检测 |
|---|---|---|---|
| R-NAME-001 | error | `name` 必须以 `volcengine-` 开头 | regex: `^name:\s*volcengine-` |
| R-NAME-002 | error | slug 符合 `^volcengine-[a-z0-9][a-z0-9-]*$` 且长度 ≤ 64 | 正则 + 长度 |
| R-NAME-003 | error | 不含连续 `--` | regex: `--` 不匹配 |
| R-NAME-004 | error | `frontmatter.name` == 父目录名 | 字符串比对 |

### 3.2 Description（R-DESC-*）

| ID | 严重级 | 规则 | 检测 |
|---|---|---|---|
| R-DESC-001 | error | 长度 1–1024 字符 | `1 <= len(description) <= 1024` |
| R-DESC-002 | warning | 以 `Use when` 或中文「当…时使用」开头 | 正则 prefix 匹配 |
| R-DESC-003 | warning | 禁止工作流短语 | regex（词边界）：`\b(first|then|next|after that|finally)\b` 或中文「先.*再」「然后」「接下来」「最后」 |
| R-DESC-004 | warning | 避免无信息通用词 | regex: `^(A skill for|Helps with|Handles)` |

### 3.3 openclaw 安全声明（R-OPENCLAW-*）

| ID | 严重级 | 规则 | 检测 |
|---|---|---|---|
| R-OPENCLAW-001 | error | 代码中读取的 env 必须全部声明在 `requires.env` | 扫 `SKILL.md` + `scripts/` + `references/`，正则 `\$[A-Z_]+\|getenv\("[^"]+"\)\|process\.env\.[A-Z_]+`，提取 set，比对 |
| R-OPENCLAW-002 | error | 代码中调用的外部命令必须全部在 `requires.bins ∪ anyBins` | 扫 `SKILL.md` + `scripts/`，比对白名单命令列表（见附录 A.1） |
| R-OPENCLAW-003 | warning | 系统变量（`PATH` / `HOME` / `PWD` / `USER` / `SHELL` / `TERM` / `LANG` / `TZ`）不应出现在 `requires.env` | 集合差集 |
| R-OPENCLAW-004 | error | `requires.bins` 中不含绝对路径 / 不含空格 | regex: `^[a-zA-Z0-9_-]+$` |
| R-OPENCLAW-005 | warning | `primaryEnv` 必须存在于 `requires.env` | 集合比对 |

### 3.4 目录与结构（R-STRUCTURE-*）

| ID | 严重级 | 规则 | 检测 |
|---|---|---|---|
| R-STRUCTURE-001 | error | skill 目录下只允许子目录：`references/` / `scripts/` / `assets/` | 目录 ls 对比白名单 |
| R-STRUCTURE-002 | error | 禁止 `workflows/` 目录 | ls 命中即 error |
| R-STRUCTURE-003 | error | `SKILL.md` 存在且非空 | 文件检查 |

### 3.5 体量（R-SIZE-*）

| ID | 严重级 | 规则 | 检测 |
|---|---|---|---|
| R-SIZE-001 | warning | `SKILL.md` 行数 < 500 | `wc -l` |
| R-SIZE-002 | warning | `SKILL.md` token ≈ < 5000（按 `字符数 / 3.5` 粗估） | 字符数 / 3.5 |
| R-SIZE-003 | error | 总 bundle ≤ 50 MB（ClawHub 限制） | `du -sb` |
| R-SIZE-004 | warning | skill 目录下非 `.md` 文件数 ≤ 40（ClawHub embedding 限制） | 文件计数 |

### 3.6 代码块可运行性（R-CODE-*）

| ID | 严重级 | 规则 | 检测 |
|---|---|---|---|
| R-CODE-001 | error | `SKILL.md` / `scripts/**/*.md` 中所有代码块必须标注语言 | regex 扫描：`^\`\`\`\s*$` 紧跟非 `\`\`\`` 内容即 error |
| R-CODE-002 | error | `scripts/*.sh` 和 md 内 `bash` 代码块通过 `bash -n` | 提取 + 执行 |
| R-CODE-003 | error | `scripts/*.py` 和 md 内 `python` 代码块通过 `python -m py_compile` | 提取 + 执行 |
| R-CODE-004 | warning | 代码块不含 `<TODO>` / `<FIXME>` / `...` 占位符 | regex 扫描 |

### 3.7 提交规范（R-COMMIT-*）

| ID | 严重级 | 规则 | 检测 |
|---|---|---|---|
| R-COMMIT-001 | error | commit message 符合 Conventional Commits | regex: `^(feat\|fix\|docs\|refactor\|chore\|test)(\([a-z0-9-]+\))?: .+` |
| R-COMMIT-002 | error | 分支名前缀合规 | regex: `^(feat\|fix\|docs\|refactor)/.+` |
| R-COMMIT-003 | warning | subject 无无信息词 | 禁止：`update` / `修改` / `wip` / `fix bug` |

---

## 4. 校验器使用流程

计划中的 `volcengine-skill-validator` skill 消费本文档规则：

**输入**：skill 目录路径（如 `skills/volcengine-cli/`）
**输出**：规则执行结果 + 打分（见 §5）

```json
{
  "skill": "volcengine-cli",
  "score": 87,
  "grade": "B",
  "merge_eligible": true,
  "summary": { "errors": 0, "warnings": 2, "passed": 18 },
  "breakdown": {
    "metadata":         { "score": 18, "max": 20 },
    "security":         { "score": 30, "max": 30 },
    "naming_structure": { "score": 10, "max": 10 },
    "code_quality":     { "score": 22, "max": 25 },
    "content_size":     { "score": 10, "max": 10 },
    "self_test":        { "score": 2,  "max": 5  }
  },
  "results": [
    { "rule": "R-NAME-001", "status": "pass" },
    { "rule": "R-DESC-003", "status": "warn", "detail": "description 含工作流词 'then' @ line 3" },
    { "rule": "R-OPENCLAW-001", "status": "fail", "detail": "env 'VOLCENGINE_ENDPOINT' 在 scripts/call.sh:12 被读取但未声明" }
  ]
}
```

CI 集成：任何 `error` 阻塞合并；`warning` 仅提示。

---

## 5. 打分规则

validator 对 skill 输出 0–100 整数分。总分 = 6 个维度得分之和。

### 5.1 维度与权重

| 维度 | 满分 | 评分方式 |
|---|---|---|
| **Metadata** 元数据完整度 | 20 | 必填字段齐全 +10；description 合规（R-DESC-001/002/003 全通过）+10 |
| **Security** 安全声明覆盖率 | 30 | env 完全声明（R-OPENCLAW-001 通过）+15；bins 完全声明（R-OPENCLAW-002 通过）+10；无系统变量误声明 +5 |
| **Naming/Structure** 命名与结构 | 10 | R-NAME-* 全通过 +5；R-STRUCTURE-* 全通过 +5 |
| **Code Quality** 代码可运行性 | 25 | 所有代码块标语言 +10；`bash -n` 全通过 +8；`py_compile` 全通过 +5；无占位符 +2 |
| **Content Size** 内容体量 | 10 | 行数 < 500 +5；token 估算 < 5000 +5 |
| **Self-test** 自测完备度 | 5 | 有 `TESTING.md` 或 MR 冒烟记录 或 e2e 链接 +5（任一即可） |

### 5.2 等级映射

| Grade | Score | 含义 |
|---|---|---|
| **A** | 90–100 | 质量优，可直接合并 |
| **B** | 75–89 | 合格，建议优化但可合并 |
| **C** | 60–74 | 有明显短板，必须修改后再提 |
| **D** | < 60 | 不合规，打回重写 |

### 5.3 合并门槛

同时满足两条才 `merge_eligible: true`：

1. `summary.errors == 0`（无任何 error 级规则失败）
2. `score >= 75`（即 Grade ≥ B）

**注意**：即使分数 90+，只要有 1 个 error（比如漏声明 env），`merge_eligible` 也是 `false`。错误级问题不能用"其他维度得高分"来抵消。

### 5.4 扣分示例

假设一个 skill：
- metadata 完整、description 合规 → Metadata 20
- env 声明齐全、bins 缺了一个 → Security 20 (缺 bins 10 分)
- 命名/结构都 OK → Naming/Structure 10
- 有 1 个代码块没标语言，bash -n 通过，py_compile 通过，无占位符 → Code Quality 15 (缺标语言 10 分)
- 600 行超标 → Content Size 5 (缺行数 5 分)
- 没自测 → Self-test 0

总分 = 20 + 20 + 10 + 15 + 5 + 0 = **70，Grade C，不可合并**。必须先把 bins 声明补上（消除 error）+ 代码块补标语言，才能提 MR。

---

## 6. TESTING.md 参考模板（非强制）

<a id="testing-template"></a>

推荐附一份自测文档。下面是参考模板，按需裁剪：

````markdown
# TESTING: volcengine-<xxx>

## 1. 依赖检查
```bash
for v in VOLCENGINE_ACCESS_KEY VOLCENGINE_SECRET_KEY VOLCENGINE_REGION; do
  [ -z "${!v}" ] && echo "❌ $v" || echo "✅ $v"
done
command -v ve >/dev/null && echo "✅ ve $(ve --version)" || echo "❌ ve not found"
```

## 2. 冒烟用例
**操作**：
```bash
ve ecs DescribeInstances --region $VOLCENGINE_REGION --max-results 1
```
**期望输出**（脱敏）：
```json
{ "Instances": [{ "InstanceId": "i-xxx", "Status": "RUNNING" }], "TotalCount": 1 }
```

## 3. 典型失败场景
- `InvalidAccessKeyId.NotFound` → 检查 `VOLCENGINE_ACCESS_KEY` 或 AK 状态
- `command not found: ve` → 安装 `ve` CLI
- `region is invalid` → 确认 region 代码 / 权限
````

---

## 附录 A：辅助数据

### A.1 外部命令扫描关键字（R-OPENCLAW-002 用）

初版白名单扫描关键字（可扩充）：

```
ve kubectl curl jq aws gcloud docker git python python3 node npm pnpm yarn make go go-task terraform helm
```

### A.2 系统环境变量黑名单（R-OPENCLAW-003 用）

```
PATH HOME PWD USER SHELL TERM LANG LC_ALL TZ DISPLAY XDG_RUNTIME_DIR
```

### A.3 严重级定义

- **error**：必须修复才能合并
- **warning**：提示给作者 + reviewer，不阻塞

---

## 附录 B：ClawHub 文件/体积约束

- 总 bundle ≤ 50 MB
- Embedding 包含 `SKILL.md` + 最多 ~40 个非 `.md` 文件
- 文件类型白名单：`text/*` + JSON / YAML / TOML / JS / TS / Markdown / SVG

---

## 附录 C：License

如发布到 ClawHub：所有 skill 必须采用 `MIT-0` 许可。建议在仓库根目录放一份 `LICENSE`，skill frontmatter 的 `license` 字段填 `MIT-0`。

内部私有仓库不发布则可忽略。

---

## 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-04-21 | 初版，规则 R-NAME/DESC/OPENCLAW/STRUCTURE/SIZE/CODE/COMMIT 七组 |
