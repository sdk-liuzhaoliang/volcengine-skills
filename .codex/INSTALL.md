# 在 Codex 中安装 volcengine-skills

通过 Codex 原生 skill 发现机制启用本仓库的 skills。只需 clone 并 symlink 即可。

## 前置条件

- Git

## 安装步骤

1. **Clone 仓库：**
   ```bash
   git clone git@github.com:volcengine/volcengine-skills.git ~/.codex/volcengine-skills
   ```

2. **创建 skills 软链：**
   ```bash
   mkdir -p ~/.agents/skills
   ln -s ~/.codex/volcengine-skills/skills ~/.agents/skills/volcengine-skills
   ```

   **Windows (PowerShell):**
   ```powershell
   New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.agents\skills"
   cmd /c mklink /J "$env:USERPROFILE\.agents\skills\volcengine-skills" "$env:USERPROFILE\.codex\volcengine-skills\skills"
   ```

3. **重启 Codex**（退出并重新启动 CLI）让 skill 被发现。

## 验证

```bash
ls -la ~/.agents/skills/volcengine-skills
```

应该看到一个指向仓库 skills 目录的软链（Windows 是 junction）。

## 更新

```bash
cd ~/.codex/volcengine-skills && git pull
```

通过软链，skills 即刻生效。

## 卸载

```bash
rm ~/.agents/skills/volcengine-skills
```

可选：`rm -rf ~/.codex/volcengine-skills` 删除 clone。
