# Telegram、Slack、Discord 接入

这三个平台默认关闭。Pantheon 必须运行 `pantheon web` 或后台服务；平台配置完成后，通过已验证回调接收文本任务并调用同一套 Hermes/预算/任务归档。没有配置时显示 `not_connected`，保存 key 后显示 `configured`，收到验证成功的回调后才显示 `receiving`。

## 先准备回调地址

平台无法访问你电脑的 `127.0.0.1`。需要你控制的公网 HTTPS 地址，通过反向代理转发到 Pantheon。公网侧建议只开放 `/api/channels/telegram/callback`、`/api/channels/slack/callback`、`/api/channels/discord/callback`，管理 UI 留在本地。

如果代理保留公网 Host，在启动进程环境中设置 `PANTHEON_ALLOWED_HOSTS=你的域名`，多个域名用逗号分隔，再重启。直接绑定远程地址还需要先在 Security 配置登录。平台回调不需要浏览器登录，但每次必须通过各自验证；配置页面仍受 UI 登录保护。该版本不会替用户申请域名、证书或部署公网服务器。

所有平台都必须填写允许的用户和聊天/频道 ID。空白名单不允许启用。保存配置不会自动向平台发送消息；只有选中“Reply to allowed incoming tasks”后，才回复允许的传入任务。

## Telegram

1. 在 Telegram 的官方 `@BotFather` 创建自己的 Bot，取得 Bot token。
2. 在与 Bot 的私聊发送一条消息。尚未设置 webhook 时，可使用 Telegram `getUpdates` 查看 `message.from.id` 和 `message.chat.id`。填的是数字 ID，不是用户名；群聊 ID 可能带负号。
3. 打开 Settings → Integrations → Channels → Telegram。填写用户 ID、chat ID、Bot token 和自己生成的回调 secret token（仅字母、数字、下划线、短横线）。选择凭据保存方式，启用并保存。
4. 用 Telegram `setWebhook` 注册公网地址与同一个 secret。例如将占位符替换为自己的值：

   ```sh
   curl -X POST 'https://api.telegram.org/bot<BOT_TOKEN>/setWebhook' \
     -H 'Content-Type: application/json' \
     -d '{"url":"https://<DOMAIN>/api/channels/telegram/callback","secret_token":"<SAME_SECRET>"}'
   ```

5. 从白名单用户/chat 向 Bot 发一个明确任务。Channels 会显示最近事件状态，Info → Task history 可以查看结果。启用回复时，答案回到原 chat，并引用原消息。

只处理文本消息，不接收 Telegram 文件或其他 Bot 的消息。回调 header 的 secret 必须匹配，重复 `update_id` 不重复执行。

参考：[Telegram Bot API](https://core.telegram.org/bots/api#setwebhook)。

## Slack

1. 创建 Slack App，添加 Bot scopes `app_mentions:read`、`chat:write`，安装到自己的 workspace，取得 Bot token；Basic Information 中取得 Signing Secret。
2. 邀请 Bot 加入目标频道。准备 workspace 的 team ID（`T...`）、用户 ID（`U...`）和频道 ID（`C...` 等）；使用平台复制 ID 或管理 API 获取，不能填显示名称。
3. Channels → Slack 填写这些 ID、Bot token、Signing Secret，启用并保存。
4. 在 Slack App 的 Event Subscriptions 填 `https://<DOMAIN>/api/channels/slack/callback`。验证通过后订阅 Bot event `app_mention`；修改 scopes 后按 Slack 提示重新安装。
5. 从白名单用户在白名单频道 `@你的Bot 具体任务`。启用回复时，答案在原消息的 thread 中返回。

签名使用原始请求体和时间戳，过期或伪造请求会拒绝；workspace、用户和频道均需匹配。Bot/编辑消息不触发任务，Slack 重试同一 `event_id` 只确认一次。普通频道聊天、DM 和文件事件不属于本版入口。

参考：[签名验证](https://docs.slack.dev/authentication/verifying-requests-from-slack/)、[Events API](https://docs.slack.dev/apis/events-api/)。

## Discord

1. 在 Developer Portal 创建 Application，取得 Application ID 和 Public Key（64 个十六进制字符）。将应用安装到目标服务器并授权 `applications.commands`。
2. 开启 Discord Developer Mode，复制允许的 User ID 和 Channel ID。
3. Channels → Discord 填写 application ID、public key 与白名单，启用并保存。无需将 Bot token 保存在 Pantheon；它使用经签名的 interaction 和临时回复 token。
4. 在 Developer Portal 将 Interactions Endpoint URL 设置为 `https://<DOMAIN>/api/channels/discord/callback`。Pantheon 验证 Ed25519 签名并回复 PING。
5. 为应用注册 `/pantheon` 命令，添加名为 `task` 的必填 string 参数。例如通过 Discord Commands API 注册：

   ```sh
   curl -X POST 'https://discord.com/api/v10/applications/<APPLICATION_ID>/commands' \
     -H 'Authorization: Bot <YOUR_BOT_TOKEN>' \
     -H 'Content-Type: application/json' \
     -d '{"name":"pantheon","description":"Run a Pantheon task","options":[{"name":"task","description":"What should Pantheon do?","type":3,"required":true}]}'
   ```

6. 从允许的用户/频道运行 `/pantheon task:你的具体需求`。收到命令后立即确认、后台执行；回复只对发起者可见。Discord 临时 token 有效期有限，队列过旧会标记 `expired`。

不监听服务器全部消息，不接收平台附件。签名、application ID、用户和频道必须同时通过检查，生成回复关闭 mentions，避免意外群体通知。

参考：[Interactions 验签](https://github.com/discord/discord-api-docs/blob/main/developers/interactions/overview.mdx)、[接收与回复](https://docs.discord.com/developers/interactions/receiving-and-responding)。

## 状态、失败和边界

- `queued` / `running`：已保存/正在执行；重复回调不生成第二个任务。
- `processed`：结果已归档，没有启用回复。
- `delivered`：平台确认接收回复，任务本身的成功/失败见 Task history。
- `reply_failed`：回复失败或超时，可能已经送达；不会自动重发。
- `failed` / `interrupted` / `cancelled` / `expired`：查看本地任务及配置。中断事件不会静默重跑，需要用户核对后从请求创建新任务。

每用户每分钟最多 10 个任务，队列最多 100 个。自动处理文本，独立任务之间不共享平台聊天历史；不执行需要交互审批的 MCP 工具。回复长度按平台限制截短，完整结果保存在 Pantheon。Web/后台服务停止时无法接收或执行消息。

凭据可保存到 `.env` 或支持的系统存储；页面只显示是否配置，不回显 token。HTTP 日志隐藏 Telegram/Discord URL 中的 token。备份不导出临时 Discord 回复 token，恢复后入口关闭、待执行事件不重放。

CLI 可查看 `pantheon channels`。通过 `pantheon channels --platform telegram --config channel.json` 保存 JSON；其结构是 `{"config":{"enabled":true,"users":["ID"],"channels":["ID"],"auto_reply":false},"secrets":{"bot_token":"...","secret_token":"..."},"storage":"env"}`。含凭据的配置文件不要提交到 Git。


当前平台设置页（未连接）：

![Pantheon Channels](images/pantheon-channels.jpg)
