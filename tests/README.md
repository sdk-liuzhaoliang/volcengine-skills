# tests/

仓库级测试（跨 skill 的集成测试、规范校验、meta 测试）。

**注意**：skill **自身**的自测请放在 `skills/<name>/TESTING.md` 或 `skills/<name>/tests/`。这里只放仓库级的测试。

常见测试：
- `spec-consistency` — 确认每个 skill 的 frontmatter 满足 `docs/skill-spec.md` 规则
- `validator-selftest` — `volcengine-skill-validator` 对自身的自测
