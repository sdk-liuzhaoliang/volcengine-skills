# scripts/

仓库级通用辅助脚本（CI、lint、发布等）。

**注意**：skill **内部**的脚本请放到 `skills/<name>/scripts/`，不要放这里。这里只放跨 skill 的工具。

常见脚本：
- `validate-all.sh` — 对仓库内所有 skill 跑一遍 validator
- `sync-spec.sh` — 从 docs/skill-spec.md 同步规则到 CI 配置
