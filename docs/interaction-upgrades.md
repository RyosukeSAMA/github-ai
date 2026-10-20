# 交互增强与验证边界（v0.4.0）

这些能力共用 CLI、Web、SDK 的模型连接、预算、任务归档和工作区数据。真实 OpenAI/Anthropic、多模态和三个聊天平台的账号验收仍保留为验证缺口，本轮不替用户购买 API 或发送外部平台消息。

## 真正增量输出

Web 角色执行和最终汇总随供应商文本事件逐段显示。规划 JSON、上下文压缩、恢复计划和提示词优化仍使用完整响应，内部输出不混入聊天。前端合并高频事件后渲染 Markdown；完成时用完整结果校正显示，避免重复追加。

OpenAI 官方模型沿用 Responses API，兼容网关/DeepSeek/Ollama 沿用 Chat Completions，Anthropic 使用 Messages 流。协议实现依据 [OpenAI streaming](https://developers.openai.com/api/docs/guides/streaming-responses)、[Chat streaming events](https://developers.openai.com/api/reference/resources/chat/subresources/completions/streaming-events) 和 [Anthropic streaming](https://platform.claude.com/docs/en/build-with-claude/streaming)。模拟 SDK 事件验收不代表任何真实账户已获得模型访问权限。

Connections → 编辑连接可关闭 **Show incremental output**，用于不支持流式的网关。关闭后保留阶段进度，完成时显示完整文本；不会因流式失败自动重发收费请求。停止会关闭当前流并阻止后续调用，已被接受的请求可能计费。缺少最终用量时保留保守预算预留。

## 用量与费用

Web Settings → Info 显示按任务、角色、阶段汇总的近期调用。`pantheon usage --task TASK_ID --limit 100` 和 `GET /api/usage/details?task_id=...&limit=100` 查看明细，最多返回 500 条；记录不包含提示词、答案、文件内容和密钥。

阶段包括 planning、execution、synthesis、context、recovery、enhancement、probe、vision、image、transcription。每次真实模型请求单独记账，失败尝试也可见。服务商未返回 token 的调用显示未知，未填写单价的费用显示未知；估算不等于账单，失败/中断不意味着免费。旧数据库自动增加字段，旧记录标为 legacy，不猜测历史角色和阶段。

## 连接停用、恢复与删除

在 Setup 的连接卡片选择 Disable / Enable / Remove connection。确认框列出引用此连接的默认角色、会话数量和媒体用途。操作不替换角色模型、不删除聊天；停用后相关请求明确失败，不偷偷切换其他服务商。进行中的请求不因配置更改自动撤销。

Remove connection 默认保留保存的 key，方便以后重新保存连接。勾选 **Also delete the saved API key** 才删除本机 `.env` 或系统存储中的 key。父进程环境变量不受修改。移除状态会阻止旧 YAML/环境配置自动复活连接；恢复需重新保存连接。移除或停用不向服务商撤销 key，若要撤销，请在服务商账户操作。

## CLI 连续会话

```sh
pantheon chat --session my-project
pantheon chat --session my-project --role hephaestus
pantheon chat --session my-project --no-stream
pantheon chat --list
pantheon ask --stream "Explain this project"
pantheon usage --task TASK_ID
```

同一个 session ID 续接该终端历史；不同 ID 隔离。不会读取或覆盖 Web 会话。文件保存于工作区数据目录的 `cli-sessions/`，权限为私有；文件锁覆盖单次交互任务，防止两个终端同时覆盖同一会话。CLI 使用已保存的工作区模型配置，每次启动重新读取；不会套用 Web 当前会话的模型覆盖。

输入 `/exit` 退出，`/help` 查看命令，`/mode auto`、`/mode multi`、`/mode role:athena` 改变后续模式，`/clear` 明确确认后清空此 CLI 历史。后续请求使用与 Web 相同的最近 16 条 / 24,000 字符历史边界；原文仍保留在本地记录。`ask` 和 `--raw` 行为保持独立，`--raw` 与 `--stream` 不同时使用。

## 长聊天与键盘

保存的聊天默认渲染最近 80 条消息，点击 Show earlier messages 每次再加载 80 条；超长旧回复先显示节选，Show full reply 展开全文。完整记录、导出、复制和后续模型上下文均以原文为准。240 条记录的浏览器回归验证初始 DOM 为 80 条、加载后为 160 条、切换/保存后首尾原文仍完整；不承诺不同电脑上的固定耗时。

- 会话列表：↑ / ↓、Home / End 移动焦点，Enter 打开。
- Cmd/Ctrl + Shift + O：新会话并聚焦输入框。
- Cmd/Ctrl + Shift + L：聚焦输入框。
- Cmd/Ctrl + ,：设置；Esc 关闭并恢复原焦点。
- Cmd/Ctrl + /：工作区；Cmd/Ctrl + Shift + E：导出聊天。

## 保留的边界

这不是桌面安装包。桌面端后续共用这些核心协议，另行处理进程生命周期、显式工作区、系统菜单、通知、签名打包和升级回退。验收不会把模拟的云端接口结果标成真实账号通过。
