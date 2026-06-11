# TESTING: volcengine-landing-zone

本文件提供最小可复现的自测步骤，用于验证 `volcengine-landing-zone` 的关键路径仍可用。

## 1. 覆盖范围

重点验证：

- skill frontmatter 与依赖声明完整
- 咨询路径不会误触发真实执行
- preflight 能检查工具、凭证和工作区前提
- 方案确认 HTML、汇总报告模板、baseline schema、Python helper 等关键资产存在
- 典型失败场景有清晰处置方式

不覆盖：

- 全量真实资源创建
- 多账号生产级联调
- 全自动 e2e 执行

## 2. 依赖检查

### 工具

```bash
for cmd in terraform ve python3; do
  command -v "$cmd" >/dev/null 2>&1 && echo "OK  $cmd" || echo "MISSING  $cmd"
done
```

### 环境变量

```bash
for v in VOLCENGINE_ACCESS_KEY VOLCENGINE_SECRET_KEY VOLCENGINE_SESSION_TOKEN VOLCENGINE_REGION; do
  [ -n "${!v}" ] && echo "OK  $v" || echo "EMPTY  $v"
done
```

### CLI 登录态

```bash
ve sts GetCallerIdentity 2>&1
```

期望：返回调用者身份信息；失败时回到 `references/preflight-checks.md` 的登录分流处理。

## 3. 冒烟矩阵

### 3.1 咨询路径

输入示例：

```text
我想先了解火山引擎 Landing Zone 的实施顺序和各阶段价值，先不要真实执行。
```

期望结果：

- 进入“咨询与方案设计”路径
- 输出以理念、阶段价值、实施顺序、落地建议为主
- 不直接进入 `ve login`、preflight、Terraform 或蓝图执行

### 3.2 preflight

```bash
which terraform && terraform version
which ve && ve version
which python3 && python3 --version
ve sts GetCallerIdentity 2>&1
```

期望结果：

- 工具存在时可输出版本信息
- CLI 凭证可用时，`ve sts GetCallerIdentity` 成功
- 即使 CLI 可用，也不会跳过 Terraform Provider 鉴权检查

### 3.3 工作区与蓝图副本

```bash
test -d ./skills/volcengine-landing-zone/assets/blueprints && echo "OK source blueprints"
test -f ./skills/volcengine-landing-zone/references/landing-zone-setup/guidebook.md && echo "OK setup guidebook"
test -f ./skills/volcengine-landing-zone/references/account-factory/guidebook.md && echo "OK account factory guidebook"
```

期望结果：

- 内置蓝图源目录存在
- 两份 guidebook 存在
- 真实执行发生在 `./volcengine-landing-zone-workspace/blueprints/`，而不是源码目录

### 3.4 方案确认文档与汇总报告模板

```bash
test -f ./skills/volcengine-landing-zone/assets/html/landing-zone-solution-plan.html && echo "OK solution plan html"
test -f ./skills/volcengine-landing-zone/assets/html/landing-zone-setup-report-template.html && echo "OK setup report template html"
# 资产路径仍被引用（防误删）
grep -n "landing-zone-solution-plan.html\|landing-zone-setup-report-template.html" ./skills/volcengine-landing-zone/SKILL.md
```

期望结果：

- 两个 HTML 文件都存在
- 资产路径仍能在 `SKILL.md` 命中
- 可确认真实搭建前会先展示方案确认 HTML，且结束时会生成并打开汇总报告

### 3.4b 红线引用闭环（防断链）

红线定义只在 `SKILL.md` 单一出处；其余文档只引用编号。下面的校验**闭环**确认：
所有文档里出现的每一个 `G<n>` 引用，在 `SKILL.md` 都有对应的 `🛑 G<n>` 定义（无断链）。

```bash
cd ./skills/volcengine-landing-zone
python3 - <<'PY'
import re, pathlib
root = pathlib.Path(".")
skill = (root / "SKILL.md").read_text(encoding="utf-8")
# SKILL.md 中的红线定义集合，如 {1,2,3,4,5,6}
 defined = set(int(n) for n in re.findall(r"^### G([1-6])\.", skill, flags=re.M))
print("defined in SKILL.md:", sorted(defined))

def strip_code(t):
    # 剥离反引号内联代码与围栏代码块，只在正文里找真实红线引用，
    # 避免把示例/说明文字里的 G7、G8 等误判为引用
    t = re.sub(r"```.*?```", "", t, flags=re.S)
    t = re.sub(r"`[^`]*`", "", t)
    return t

problems = []
for md in sorted(root.rglob("*.md")):
    text = strip_code(md.read_text(encoding="utf-8"))
    refs = set(int(n) for n in re.findall(r"\bG([0-9])\b", text))
    for n in sorted(refs):
        if n not in defined:
            problems.append("%s 引用了 G%d，但 SKILL.md 没有对应定义" % (md, n))

if problems:
    print("FAIL 红线引用断链:")
    for p in problems:
        print("  -", p)
    raise SystemExit(1)
print("OK 所有 G<n> 引用都有对应定义，无断链")
PY
```

期望结果：

- `SKILL.md` 定义出 `G1`–`G6` 全部六条
- 所有文档（含各 guidebook / reference / 阶段文档）里出现的 `G<n>` 引用都能在 `SKILL.md` 命中定义
- 出现任何超出红线编号范围或拼错的引用导致断链时，脚本以非零退出并列出具体文件

### 3.5 baseline schema

```bash
test -f ./skills/volcengine-landing-zone/references/account-factory/baseline.schema.json && echo "OK baseline schema"
python3 - <<'EOF'
import json
from pathlib import Path

schema_path = Path("./skills/volcengine-landing-zone/references/account-factory/baseline.schema.json")
schema = json.loads(schema_path.read_text(encoding="utf-8"))
assert schema["type"] == "object"
assert "modules" in schema["properties"]
assert "variables" in schema["properties"]
print("OK baseline schema json")
EOF
```

期望结果：baseline schema 存在、可正常读取，且包含 `modules` 与 `variables` 结构。

### 3.6 Python helper

```bash
python3 -m py_compile ./skills/volcengine-landing-zone/assets/blueprints/landing-zone-setup/04-log/tos_activate.py
```

期望结果：`tos_activate.py` 可通过语法编译检查。

## 4. 典型失败场景

- `ve` 未登录或凭证失效：不误判为 Terraform 蓝图错误，回到登录分流；只有用户确认继续真实执行后才进入 `ve login`
- Terraform Provider 鉴权缺失：识别为 Provider 凭证未注入，不误判为蓝图目录或 Terraform 代码错误
- 跨账号 AssumeRole 前置不满足：只在相关阶段前阻断，不提前影响前序阶段
- 部分成功或并发冲突：先对账再重新生成计划，默认只修复失败部分

## 5. 最小人工验收清单

- [ ] 咨询请求不会误触发真实执行
- [ ] preflight 工具检查和凭证检查可复现
- [ ] 工作区与蓝图执行副本约定清晰
- [ ] 方案确认 HTML 与汇总报告模板已接入主流程
- [ ] baseline schema 存在且结构固定
- [ ] `tos_activate.py` 可通过 `py_compile`
- [ ] 各文件出现的 G1~G6 引用，在 SKILL.md 红线区都有对应定义（无断链）
- [ ] 典型失败场景有明确处理方式
