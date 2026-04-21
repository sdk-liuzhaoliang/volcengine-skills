# hooks/

存放仓库级 hook（Claude Code / Codex hook 配置）。

常见用途：
- `session-start`：会话开始时注入上下文（如自动挂载某个 skill）
- `tool-pre`：工具调用前校验（如拦截未声明 env 的 Bash 调用）
- `tool-post`：工具调用后处理（如自动格式化输出）

每个 hook 一个子目录，命名建议用 `<trigger>-<purpose>` 格式，例如 `session-start-load-volcengine-auth/`。
