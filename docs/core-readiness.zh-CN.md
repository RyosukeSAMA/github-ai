# 核心功能补齐进度

桌面客户端开始开发之前，先完成核心能力；CLI 和 Web 共用这些能力。本文记录 v0.2.6 的核心功能与后续顺序，发布状态以 GitHub Release 为准。

## 本批核心功能

- 长步骤输出按来源生成上下文摘要，保留角色、交付要求、文件、来源和未解决问题。原始输出仍保留在最终步骤结果中。Web 工作区会提示摘要发生；摘要失败时明确提示节选。摘要会产生额外模型调用和费用。
- `requirements.lock` 固定运行依赖及下载哈希。一行安装脚本与 CI 使用同一份锁文件；旧版本没有锁文件时仍支持原来的安装流程。
- CLI 与 Web 使用相同的数据目录规则；`pantheon paths` 可以查看实际位置。已有 `.pantheon` 数据继续原地使用，新工作区使用系统应用数据目录，每个项目分别保存状态。项目已有的配置和 `.env` 继续优先使用。
- 同一工作区只能运行一个 Web 后台实例，避免重复调度。
- 任务状态保存在本地。`pantheon tasks` 查看最近 100 个任务，`pantheon tasks --stop <任务ID>` 请求停止；Web 的停止按钮同时请求服务端停止。`pantheon tasks --show <任务ID>` 和 Web 设置 → Info → View result 查看已保存的结果；最多保存 200,000 字符，超出时明确标记为节选。已发出的同步 API 调用可能仍会完成并计费。
- 离线数据备份与恢复。停止 Web 服务并等待 CLI 任务结束后运行：

  ```sh
  pantheon backup ~/pantheon-backup.zip
  pantheon restore ~/pantheon-backup.zip
  ```

  默认备份会话、记忆、任务、用量、Skills 等工作区数据，排除 `.env`、MCP 和插件配置；也不包含 YAML 配置。需要连同配置和凭据保存时使用 `pantheon backup ~/pantheon-private.zip --include-secrets`。所有备份都可能含有私人对话内容，请保存在可信的位置。备份不包括工作区源码和其他项目文件。

  恢复会合并备份文件，覆盖的原文件另存到终端显示的恢复前目录；备份中没有的文件不会被删除。只恢复可信备份。恢复期间发生异常时自动回退本次写入。备份及恢复期间会阻止新 CLI 任务启动；运行中的任务或 Web 服务会阻止备份及恢复。

## 按顺序继续

1. 新手首次启动引导：选择工作区、配置服务商、测试 API，再完成第一次任务。
2. 系统凭据存储，保留已有 `.env` 的兼容与迁移路径。
3. 可配置用量、费用提醒与任务限制；不将估算费用当作供应商账单。
4. 原生 Windows 安装与后台服务支持；跨平台升级、回滚和故障恢复验证。
5. 上述核心功能完成并验收后，再设计独立桌面界面与打包。

本批回归包含跨进程停止、崩溃后恢复锁与任务状态、恢复失败后的数据回退。CI 另行验证 Linux、macOS、Windows 的运行基础；这些测试不代表原生 Windows 安装及服务管理已经完成。

## 数据路径

- macOS：`~/Library/Application Support/Pantheon`
- Linux：`${XDG_DATA_HOME:-~/.local/share}/pantheon`
- Windows 数据路径：`%LOCALAPPDATA%\Pantheon`（这不表示原生 Windows 全部功能已支持）
- `PANTHEON_DATA_DIR` 可以覆盖应用目录；`PANTHEON_STATE_MODE=workspace` 可以显式选择项目内 `.pantheon`。
- 从其他目录操作指定项目：`pantheon --workspace /完整/项目路径 paths`。同样适用于 `ask`、`tasks`、`backup`、`restore` 和 `web`。

## 更新依赖锁

维护者在项目根目录执行以下命令，重新生成适用于 Python 3.10 及以上的通用锁文件，并在全新环境运行测试：

```sh
uv pip compile pyproject.toml --python-version 3.10 --universal --generate-hashes --constraint constraints-runtime.txt --output-file requirements.lock
python -m venv /tmp/pantheon-verify
/tmp/pantheon-verify/bin/pip install --require-hashes -r requirements.lock
/tmp/pantheon-verify/bin/pip install -e '.[dev]'
/tmp/pantheon-verify/bin/pip check
/tmp/pantheon-verify/bin/pytest
```

开发和浏览器测试工具属于可选依赖，不在运行依赖锁中。
