# 核心功能补齐进度

桌面客户端开始开发之前，先完成核心能力；CLI 和 Web 共用这些能力。本文记录开发分支的进度，不表示这些改动已经进入稳定版。

## 已实现，正在验证

- 长步骤输出按来源生成上下文摘要，保留角色、交付要求、文件、来源和未解决问题。原始输出仍保留在最终步骤结果中。Web 工作区会提示摘要发生；摘要失败时明确提示节选。摘要会产生额外模型调用和费用。
- `requirements.lock` 固定运行依赖及下载哈希。一行安装脚本与 CI 使用同一份锁文件；旧版本没有锁文件时仍支持原来的安装流程。
- CLI 与 Web 使用相同的数据目录规则；`pantheon paths` 可以查看实际位置。已有 `.pantheon` 数据继续原地使用，新工作区使用系统应用数据目录，每个项目分别保存状态。项目已有的配置和 `.env` 继续优先使用。
- 同一工作区只能运行一个 Web 后台实例，避免重复调度。
- 任务状态保存在本地。`pantheon tasks` 查看最近 100 个任务，`pantheon tasks --stop <任务ID>` 请求停止；Web 的停止按钮同时请求服务端停止。已发出的同步 API 调用可能仍会完成并计费。
- 离线数据备份与恢复。停止 Web 服务并等待 CLI 任务结束后运行：

  ```sh
  pantheon backup ~/pantheon-backup.zip
  pantheon restore ~/pantheon-backup.zip
  ```

  默认备份会话、记忆、任务、用量、Skills 等工作区数据，排除 `.env`、MCP 和插件配置；也不包含 YAML 配置。需要连同配置和凭据保存时使用 `pantheon backup ~/pantheon-private.zip --include-secrets`。所有备份都可能含有私人对话内容，请保存在可信的位置。备份不包括工作区源码和其他项目文件。

  恢复会合并备份文件，覆盖的原文件另存到终端显示的恢复前目录；备份中没有的文件不会被删除。只恢复可信备份。恢复期间发生异常时自动回退本次写入。

## 仍需完成

1. 完整跨进程及跨平台回归。任务历史 Web 页面与异常退出状态恢复已经实现。
2. 新手引导进一步完善、系统凭据存储、可配置用量和费用限制。
3. 原生 Windows 安装与后台服务支持；跨平台升级、回滚和故障恢复验证。
4. 上述核心功能验收后，再设计独立桌面界面与打包。

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
