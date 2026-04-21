# agents/

存放仓库提供的 subagent 配置。

每个 subagent 一个子目录，目录名即 subagent 名。配置格式参考 [Claude Code subagents 文档](https://docs.claude.com/en/docs/claude-code/subagents)。

典型场景：长任务拆分、并行调用、独立上下文窗口的专家 agent（如 `volcengine-cost-analyzer`）。
