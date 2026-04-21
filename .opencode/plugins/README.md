# .opencode/plugins/

OpenCode 插件 JS 入口放这里。

**当前状态**：init 阶段，尚未实现 plugin runtime。OpenCode 用户请参考 [`../INSTALL.md`](../INSTALL.md) 使用 symlink 方式挂载 `skills/` 目录。

待 plugin runtime 落地后，此目录会放一个 `volcengine-skills.js`，并同步更新根目录 `package.json` 的 `main` 字段。
