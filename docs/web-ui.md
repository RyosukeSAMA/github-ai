# Pantheon Web UI 更新说明

本文记录当前 Web UI 与 Workspace 的主要改动、使用方式、测试方法，以及后续发布到 GitHub 前需要检查的事项。

当前界面标识：`UI v0.2.1`

## 改动总览

### 整体界面

- 将 Web UI 调整为更接近 agent workspace 的三栏布局：左侧会话与模式，中间对话，右侧 Workspace。
- Light / Dark 主题统一使用变量与玻璃拟态风格，减少硬编码背景色。
- 背景改为低饱和蓝紫渐变网格与柔和氛围层。
- 左下角增加 `UI v0.2.1`，方便后续定位 UI 版本。
- 左下角 GitHub 按钮改为官方 GitHub mark。

### 会话

- `New Chat` 会创建一个独立会话。
- 新会话默认标题保持 `New chat`，不会自动加编号。
- 发送第一条消息后，会话标题会自动变成第一条问题的内容摘要。
- 每个会话独立保存：
  - 消息记录
  - 当前模式
  - 模型覆盖配置
  - Workspace 相关状态
- 会话数据保存在浏览器 `localStorage`。

### Agent 模式

- `Auto`：Hermes 自动判断任务应该由单个神处理，还是需要多 agent 协作。
- `Multi-role`：强制走多角色协作流程，让 Hermes 规划并协调多个角色。
- 直接点击某个神：进入该神的 direct mode，下一个任务会直接发给这个角色。
- 顶部 `Auto / Multi-role` pill 可以直接切换模式。
- 左侧 Mode 区域改为可点击的分段切换按钮。
- 切换模式后会同步更新：
  - 顶部模式按钮
  - 左侧模式按钮
  - composer 底部模式提示
  - 当前会话 metadata

### 神祇头像

- 左侧神祇列表使用生成头像，不再只显示字母。
- 对话区 agent 头像也使用对应神祇头像。
- Settings / Models 里的神祇头像与左侧、对话区保持同一套图片。
- Chronos 保留为调度角色，可以直接选择来创建本地定时任务，但不作为普通聊天 LLM agent。

### 对话区

- 用户消息使用与 Agent 卡片一致的极简实体表面，仅通过右对齐、`YOU` 和头像描边区分发送方。
- 超过六行的用户问题默认折叠，可使用 `Show more` / `Show less` 展开或收起。
- Agent 消息改为结构化响应卡片。
- Agent 消息头部会尽量显示：
  - 神祇名称
  - 当前角色类型
  - 当前模型标签
  - 状态
  - 耗时
- 模型标签会优先使用后端事件携带的 provider/model 信息；如果没有这类信息，会回退到当前会话配置里能拿到的模型名。
- 消息 hover 时显示复制按钮。
- 代码块或生成内容会被识别为 artifact card，而不是把整段代码直接铺满对话区。

### 多 Agent 实时进度

- Hermes 开始规划后立即向 Workspace 发送状态，不再等待整套多角色任务完成后一次性补发。
- Plan 会显示 Hermes 的规划理由，以及每一步对应的神和任务。
- Timeline 会在每个模型调用前显示真实的 `Step x/y`、当前神、任务、Skill 和独立耗时。
- 多角色流程会明确区分 `Preparing`、`Planning`、`Step x/y`、`Synthesizing` 和完成状态。
- 模型等待期间后端每 5 秒发送一次心跳，界面持续保留当前阶段和计时。
- 单个阶段等待 30 秒后会提示仍在等待模型；超过 90 秒会显示慢响应提醒，用户可以点击 `Stop` 后重试。
- `Model wait` 表示 Pantheon 正在等待当前 Provider 返回结果，不代表系统正在等用户选择或回复。
- 每个多角色步骤都会同时收到完整原始任务、自己的分工和前序结果，避免只凭计划里的简短标签猜测业务场景。
- 中间步骤遇到轻微、可逆的歧义时会说明采用的合理假设并继续，不会悄悄暂停整个协作。
- 如果涉及费用、外部写入、安全、不可逆操作或关键范围变化，Hermes 会在最终回答中给出 2-4 个编号方案、每项建议和明确推荐项。
- 用户可以直接回复对应的 `1`、`2`、`3` 或 `4`；界面会连同原任务与所选方案继续提交。
- 这些进度只代表 Pantheon 已实际进入的阶段，不模拟模型内部并不存在的执行细节。

### Composer 输入区

- 增加附件按钮。
- 增加语音输入按钮。
- 发送键左侧增加提示词增强按钮。明确点击后，当前草稿会发送给已配置的 Hermes 模型进行改写，但不会自动发送到对话。
- 增强后的内容会替换输入框草稿；再次点击魔杖可恢复原文。若请求期间用户已修改草稿，返回结果不会覆盖新内容。
- Settings / Display 里增加 `Voice language` 下拉。
- 支持拖拽文件到输入区。
- 文本类附件会作为上下文注入 prompt，一起发送给 agent。
- 图片、PDF、二进制等暂时只发送文件 metadata，不会假装模型已经读取了文件内容。
- 附件会在发送前显示 chip，可删除单个附件。
- 语音输入使用浏览器原生 SpeechRecognition，支持时会把语音转成文字填入输入框；不支持时会显示提示。
- 语音语言默认 `Auto` 跟随浏览器，也可以手动选择中文、英文、日文、韩文、法语、德语、西语等。

当前边界：

- 附件不是后端多模态文件直传。
- 文件内容不会长期完整保存到会话历史，历史里只保留附件名称、大小、类型等 metadata。
- 如果要让模型真正读取 PDF、图片或多模态文件，需要后续扩展后端 request schema 和具体 LLM provider 适配。

### `/` 命令

- 在对话输入框开头输入 `/` 会打开命令菜单。
- 支持上下方向键切换候选命令。
- 支持 `Enter` 或 `Tab` 执行当前选中的命令。
- 支持鼠标点击候选命令。
- 已内置的高频命令：
  - `/new`：新建会话。
  - `/auto`：切换到 Auto routing。
  - `/multi`：切换到 Multi-role council。
  - `/workspace` / `/preview` / `/files` / `/terminal`：打开 Workspace 对应面板。
  - `/settings` / `/setup` / `/models` / `/security` / `/display` / `/info`：打开 Settings 对应面板。
  - `/memory` / `/memories`：打开长期记忆面板。
  - `/skills`：打开 Skill 管理器。
  - `/skill <skill-id> <任务>`：显式使用一个已安装 Skill。
  - `/<skill-id>`：从命令菜单选择 Skill，自动填入显式调用格式。
  - `/remember <内容>`：把这段内容保存进本地长期记忆。
  - `/memories <关键词>`：打开 Memory 并搜索相关记忆。
  - `/forget <memory id>`：删除指定记忆。
  - `/attach`：打开附件选择器。
  - `/voice`：开始或停止语音输入。
  - `/export`：导出当前聊天为 Markdown。
  - `/{god}`：直连对应 agent，例如 `/hephaestus`、`/athena`、`/apollo`、`/hermes`、`/chronos`。
- 常用短别名：
  - `/ws` 等同 `/workspace`。
  - `/term` 等同 `/terminal`。
  - `/he` 等同 `/hephaestus`。
  - `/ath` 等同 `/athena`。
  - `/apo` 等同 `/apollo`。
  - `/schedule`、`/timer` 等同 `/chronos`。

当前边界：

- 未识别的字母型 `/` 命令不会发送给 agent，会在 composer 底部显示提示。
- `/Users/...`、`/tmp/...` 这类本地路径会照常作为普通消息发送。
- 第一版不包含删除对话、执行终端命令等高风险命令。

## Settings

Settings 现在分为：

- `Setup`
- `Models`
- `Security`
- `Memory`
- `Display`
- `Info`

### Setup

Setup 是给本地安装用户准备的配置入口，适合不熟悉命令行的新手。

它支持：

- 选择 Provider：DeepSeek / OpenAI / Anthropic / Ollama。
- 自动填入常见 base URL。
- 从官方推荐模型下拉里选择默认模型。
- 支持高级用户输入 `Custom model ID`。
- 输入 API key。
- 一键保存本地配置。
- 检查当前配置是否完整，并用状态灯显示检查结果。
- 测试当前 API 连接，验证 key、base URL、网络和模型是否真的可用。
- 查看每个神当前保存的 provider、model 和 key 状态。

保存规则：

- API key 写入项目根目录的 `.env`。
- provider、base URL、默认模型写入 `config/pantheon.yaml`。
- API key 不会写入浏览器 `localStorage`。
- 后端接口不会返回完整 API key，只返回 mask 后的状态，例如 `sk-t••••1234`。
- 保存后后端会重置当前 Pantheon 实例，下一次请求会使用新的本地配置。
- Anthropic 模型目录包含 Claude Opus 5（`claude-opus-5`）。Claude Messages
  兼容网关也选择 `Anthropic`，并按服务商说明修改 Base URL。
- `Current setup` 会按 Hermes、Hephaestus、Athena、Apollo、Chronos 分行显示状态。
- 顶部摘要会显示 `DeepSeek · 4/4 ready` 或 `Mixed providers · 3/4 ready`。
- `4/4` 统计的是聊天相关 agent：Hermes、Hephaestus、Athena、Apollo。Chronos 是调度角色，不需要 API key。
- `Check setup` 只读取本地 `.env` 和 `config/pantheon.yaml`，不会保存表单改动，也不会调用真实模型 API。
- `Check setup` 不会把表单切回已保存配置；用户正在编辑的 provider/model/base URL 会保留。
- `Test API` 会发出一次极短真实请求，可能产生极小 token 消耗。
- `Test API` 不会把表单切回已保存配置；测试失败后仍保留用户当前选择的 provider/model/base URL。
- DeepSeek 下拉只提供当前可调用的 `deepseek-v4-flash` 与 `deepseek-v4-pro`，不再展示已停用的旧别名。

### Security

Security 是一个可选的本地登录锁，适合用户把服务开放到局域网、远程机器、NAS 或服务器时使用。

它支持：

- 首次在 UI 里开启 `Require login for this UI`。
- 设置本地登录用户名和密码。
- 用户名、启用状态和密码哈希写入项目根目录 `.env`。
- 登录成功后写入 HttpOnly session cookie。
- 保护聊天、Setup、Workspace、Files、Preview、Terminal 等敏感 API。
- 默认不开启；不开启时保持原来的本地免登录体验。
- 登录页使用 Hermes 头像、玻璃卡片和主界面一致的柔和背景，避免只显示单字母 logo。
- 登录锁不再把右上角模型状态临时改成 `login required`；右上角只显示模型/连接状态。

保存规则：

- `PANTHEON_UI_AUTH_ENABLED=true/false` 控制是否开启登录锁。
- `PANTHEON_UI_USERNAME` 保存用户名。
- `PANTHEON_UI_PASSWORD_HASH` 保存 PBKDF2 哈希，不保存明文密码。
- `PANTHEON_UI_SESSION_SECRET` 用于签名本地登录 cookie。
- 关闭登录锁会写入 `PANTHEON_UI_AUTH_ENABLED=false`，不会删除已有密码哈希。

### Memory

Memory 是本地长期记忆模块，用来保存用户明确希望 Pantheon 以后记住的偏好、项目背景、agent 规则或任务经验。

它支持：

- 在 Settings / Memory 手动保存记忆。
- 用 `/remember <内容>` 快速保存一条记忆。
- 用 `/memories <关键词>` 搜索已有记忆。
- 用 `/forget <memory id>` 删除指定记忆。
- 用户自然说“帮我记住……”“以后……”“我的偏好是……”时自动保存。
- 普通对话中出现项目背景、技术栈、规范、风格等长期信息时，生成 `Suggested` 候选，等待用户 Save / Ignore。
- 为记忆选择 `Role scope`：Global、Hermes、Hephaestus、Athena、Apollo、Chronos。
- 开关 `Use memory in agent context`，控制是否把相关记忆注入后续 agent prompt。
- 开关 `Auto capture agent results`，自动把任务和回答摘要存成记忆。该项默认关闭，避免记忆库变脏。
- 根据当前问题做轻量关键词检索，命中后把 `Global + 当前角色` 的少量相关记忆注入上下文。

保存规则：

- 记忆保存在项目根目录 `.pantheon/memory.sqlite`。
- 当前版本不依赖 embedding、向量数据库或额外 API key。
- `.pantheon/` 不提交到 Git，属于用户本机私有数据。
- 记忆不会自动同步到 GitHub。
- 如果登录锁开启，Memory API 也会受登录保护。

当前边界：

- 检索是关键词匹配，不是语义向量搜索。
- 记忆只在本地 Web 服务工作区内生效。
- Suggestion 需要用户确认后才会进入长期记忆。

### Display

Display 偏好保存在浏览器本地，刷新后会保留。

- `Theme`：切换 Dark / Light。
- `Font size`：切换 Small / Medium / Large，影响聊天正文、输入框、侧栏、Settings、Workspace、按钮、元信息和代码块字号。
- `Voice language`：控制语音输入识别语言。

### Info

Info 是轻量只读诊断页，不放完整说明书。

- `About`：显示 UI / Backend / Python 版本。
- `Local paths`：显示 Workspace、`config/pantheon.yaml` 和 `.env` 路径。
- `Current setup`：显示当前 provider、model 和聊天 agent ready 摘要。
- `Support`：提供 `Copy diagnostics`、GitHub 和 Setup Guide。
- `Copy diagnostics` 不会复制完整 API key。
- 顶栏 `Export` 按钮改为下载图标 + Markdown 标识，更明确表示导出当前聊天。

当前 DeepSeek 的处理方式：

- DeepSeek 走 OpenAI-compatible API。
- Setup 里选择 DeepSeek 时，会把 `llm_providers.openai.base_url` 写成 `https://api.deepseek.com`。
- 角色配置里的 provider 仍然是 `openai`，默认模型是 `deepseek-v4-flash`。
- API key 写入 `.env` 的 `DEEPSEEK_API_KEY`。

### Models

Models 用来做当前会话内的临时模型覆盖。

注意：

- 这里的改动会跟随当前聊天会话保存到浏览器本地历史里。
- 它不会写入 `.env` 或 `config/pantheon.yaml`。
- 如果要让配置长期生效，应该使用 `Setup`。

### Artifact 卡片

Assistant 输出的常见文件会被识别成卡片。

目前常见支持类型：

- HTML
- Python
- JSON
- Markdown
- CSS
- JavaScript / TypeScript
- Shell
- Text

卡片操作：

- `Preview`：HTML 可以直接预览。
- `Copy`：复制代码内容。
- `Save to Files`：保存到工作区文件。
- `Show source`：展开原始代码。

保存的 artifact 默认写入：

```text
pantheon-artifacts/
```

## Workspace

右侧 Workspace 现在分为四个工具：

- `Activity`
- `Preview`
- `Files`
- `Terminal`

### Activity

Activity 用来看 agent 正在做什么，适合观察任务流。

它会显示：

- 当前任务摘要
- Hermes plan
- 各个角色的执行步骤，以及 Work / Question / Review / Revision 类型
- 步骤依赖、预期交付物与验收条件
- Agent 之间的 Handoff、Question、Review Request、Revision Request 和 Result 消息
- 状态、耗时、完成情况
- 检测到 HTML 时的快速 Preview 操作

典型用途：

- 判断 Multi-role 是否真的触发了多 agent 协作。
- 看当前任务是 Hermes 在规划，还是某个角色在执行。
- 看上一个角色把什么结果交给了谁，以及下一个角色按什么条件完成。
- 发现步骤卡住、状态未结束等问题。

这些消息由 Hermes 根据计划生成并记录。Agent 不会绕过 Hermes 自由群聊，
因此协作过程可观察、可停止，也不会形成无限反馈循环。当前 Question、Review
和 Revision 属于计划阶段确定的步骤，执行中暂时不会自动追加新的循环。

### Preview

Preview 用来预览生成的 HTML 页面。

支持：

- 对话里的 HTML artifact 直接预览。
- Files 里的 HTML 文件预览。
- Desktop / Mobile 视口切换。
- 缩放比例切换。
- Reload。
- Download。
- Open 新窗口打开。
- 外部链接点击跳转。

补充说明：

- 如果 HTML 本身没有 CSS，Preview 会提示 `unstyled HTML`。这不是界面 bug，而是生成的 HTML 没有样式。
- 如果只输出 HTML 片段，不是完整 `<!doctype html>` 文档，Preview 会用 Pantheon 的浅色 shell 包一层，避免全白空白感太强。
- 如果用户希望页面更美观，需要在 prompt 里明确要求输出完整 HTML + CSS。

### Files

Files 用来浏览和检查项目文件。

支持：

- 文件列表
- 面包屑路径
- 文件详情
- 复制路径
- 复制内容
- HTML 文件预览
- 保存 artifact 后自动定位文件

安全限制：

- 只能访问 workspace root 内部文件。
- 会阻止路径逃逸。
- 默认隐藏 `.git`、`.venv`、`node_modules`、`.env` 等目录或敏感文件。

### Terminal

Terminal 用来在 Web UI 里运行简单命令。

支持：

- 多行输入
- `Enter` 执行命令
- `Shift+Enter` 换行
- `Up / Down` 查看命令历史
- 复制输出
- 清空输出
- 创建 HTML 文件后提示可预览

风险命令保护：

- `rm -rf`
- `git reset --hard`
- `git clean -f`
- `git checkout -f`

这类命令会先要求确认，避免误删或误回滚。

### Integrations

Settings 里新增 `Integrations` 扩展中心，参考 Hermes 设置模块的信息架构，但保留 Pantheon 当前的右侧抽屉体验。

现在的 `Integrations` 是可操作的本地扩展中心：

- `MCP`：连接标准 MCP server，测试连接并读取工具目录；可按工具指定 Hephaestus / Athena / Apollo / Chronos、启停工具，并设置自动执行或每次审批。
- `Plugins`：创建、编辑、启停本地 prompt pack。启用后，它的规则会注入指定神的任务上下文；当前插件是数据型扩展，不执行任意 Python 代码。
- `Skills`：加载标准 `SKILL.md` 工作流，支持内置与本地 Skill、角色归属、自动匹配、显式调用和启停。内置 Skill 只读，本地 Skill 可编辑删除。
- `Channels`：启用 token 保护的 Webhook，把脚本或其他服务提交的任务送进同一个 Pantheon runtime。

所有状态都来自本地运行时，而不是静态文案。MCP server 配置和 Plugin pack 会保存到项目的 `.pantheon/` 目录；MCP/API 密钥与 Webhook token 保存到 `.env`，注册表只保存环境变量名；本地 Skill 使用 `.pantheon/skills/<skill-id>/SKILL.md` 标准目录，旧 `.pantheon/skills.json` 首次启动时自动迁移。

内置 Skill：

- `plan-multi-agent-task`：Hermes，多角色编排。
- `fix-and-verify`：Hephaestus，修复并验证代码。
- `research-with-sources`：Athena，有来源的研究与查证。
- `build-web-preview`：Apollo + Hephaestus，设计并输出可预览 HTML。
- `review-code-change`：Athena + Hephaestus，代码变更审查。
- `schedule-and-deliver`：Chronos，创建持久化本地定时任务。

Skill 自动匹配每个角色最多选择一个符合任务的工作流，不会把所有启用 Skill 全量注入。显式 `/skill` 优先于自动匹配，执行消息和 Workspace Activity 会显示实际使用的 Skill。

MCP agent 调用默认关闭。使用顺序是：保存 server、`Test connection`、检查发现的工具、设置每个工具可用的神与审批策略，最后打开 `Let agents use approved tools`。用户仍然在普通对话中描述任务，Agent 在需要时自动选择其获准的 MCP 工具；写入或高风险工具默认弹出 `Allow once` 审批。Workspace Activity 会显示调用、等待审批、完成或失败。远程 MCP server 使用 Streamable HTTP，本地 server 使用 stdio；stdio 子进程只继承安全基础变量和显式配置的变量，不继承整个 Pantheon 环境。

GitHub、Context7、Figma Desktop 是连接表单预设，并不是 Pantheon 内置的第三方服务。GitHub 需要有效 token；Context7 通过本机 `npx` 启动；Figma Desktop 需要先在 Figma 桌面端开启本地 MCP server。也可以使用 `Custom` 连接其他 stdio 或 Streamable HTTP server。

## 后端 API 新增

Workspace 相关 API：

- `GET /api/auth/status`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `POST /api/security/save`
- `GET /api/setup/status`
- `GET /api/integrations`
- `GET/POST/PUT/DELETE /api/skills`
- `GET/POST/PUT/DELETE /api/plugins`
- `GET/POST/PUT/DELETE /api/mcp/servers`
- `POST /api/mcp/servers/{server_id}/test`
- `PUT /api/mcp/servers/{server_id}/tools/{tool_name}/policy`
- `POST /api/mcp/servers/{server_id}/call`
- `POST /api/mcp/approvals/{approval_id}`
- `GET /api/channels`
- `POST /api/channels/webhook/config`
- `POST /api/channels/webhook`
- `POST /api/setup/check`
- `POST /api/setup/save`
- `GET /api/workspace`
- `GET /api/workspace/files`
- `GET /api/workspace/file`
- `POST /api/workspace/file`
- `GET /api/workspace/preview`
- `POST /api/workspace/terminal/stream`
- `GET /api/chronos/jobs`
- `POST /api/chronos/jobs`
- `POST /api/chronos/jobs/{job_id}/pause`
- `POST /api/chronos/jobs/{job_id}/resume`
- `POST /api/chronos/jobs/{job_id}/run`
- `DELETE /api/chronos/jobs/{job_id}`

其中：

- `POST /api/setup/save` 用来把 Settings / Setup 的 provider、model、API key 保存到本地 `.env` 和 `config/pantheon.yaml`。
- `POST /api/security/save` 用来开启或关闭本地 UI 登录锁，并把用户名、密码哈希和 session secret 保存到 `.env`。
- `POST /api/workspace/file` 用来把前端 artifact 保存到 workspace 文件系统，会做路径保护和重名处理。
- `POST /api/chronos/jobs` 用来创建本地定时任务，任务会保存到 `.pantheon/chronos_jobs.json`。
- `GET /api/integrations` 返回扩展中心的运行时汇总与本地状态路径。
- `/api/skills` 管理标准目录式 Skill；`/api/plugins` 管理数据型 prompt pack。
- `/api/mcp/servers` 管理真实 MCP server；`test` 会启动/连接 server 并读取工具目录；`policy` 保存工具级神职和审批权限；`call` 只用于手动诊断已发现的工具；`approvals` 处理流式对话中的一次性授权。
- `/api/channels/webhook` 是实际任务入口，不依赖浏览器 cookie，只接受配置的 Webhook token。

## 前端本地存储

主要 localStorage key：

```js
pantheon:display-prefs
pantheon:chat-sessions
pantheon:chat-history
```

说明：

- `pantheon:display-prefs` 保存主题、字号和语音识别语言等显示偏好。
- `pantheon:chat-sessions` 保存多会话数据。
- `pantheon:chat-history` 是旧聊天历史 key，目前保留兼容。

## 快捷键

- `Cmd/Ctrl + K`：切换 Auto / Multi-role。
- `Cmd/Ctrl + ,`：打开 Settings。
- `Cmd/Ctrl + /`：打开 Workspace。
- `Cmd/Ctrl + Shift + E`：导出聊天为 Markdown。
- `Esc`：关闭面板或让输入框失焦。

## 本地运行

从项目根目录启动：

```bash
source .venv/bin/activate
pantheon web --host 127.0.0.1 --port 8000
```

浏览器打开：

```text
http://127.0.0.1:8000/
```

默认监听地址只允许本机访问。Web UI 提供文件写入与终端执行能力；如需改为
`--host 0.0.0.0` 或通过局域网、NAS、服务器访问，请先在 `Settings -> Security`
开启登录锁，并在网络层限制可访问来源。

静态文件改动后，浏览器硬刷新：

```text
Cmd+Shift+R
```

后端 `pantheon/web/app.py` 改动后，需要重启服务。

### 电脑重启后自动运行

macOS 和 Linux 用户可以在项目根目录安装当前用户服务：

```bash
pantheon service install
pantheon service status
```

常用维护命令：

```bash
pantheon service restart
pantheon service logs
pantheon service stop
pantheon service uninstall
```

服务默认只监听 `127.0.0.1:8000`。如需使用非回环地址，必须先开启
Settings / Security，并显式传入 `--allow-network`。Chronos 仍依赖该服务运行，
但安装服务后会在用户登录时自动恢复。

## 手动测试清单

### 基础界面

1. 打开 `http://127.0.0.1:8000/`。
2. 确认左下角显示 `UI v0.2.1`。
3. 确认 GitHub 按钮使用 GitHub mark。
4. 打开 Settings 切换 Light / Dark，刷新后确认主题保留。

### Setup 本地配置

1. 打开 Settings。
2. 进入 `Setup`。
3. 选择 `DeepSeek`。
4. 确认 Default model 是 `deepseek-v4-flash`。
5. 确认 Base URL 是 `https://api.deepseek.com`。
6. 粘贴一次 DeepSeek API key。
7. 点击 `Save local config`。
8. 确认状态变成 `ready`。
9. 确认 `Current setup` 显示 `DeepSeek · 4/4 ready`，并列出 Hermes、Hephaestus、Athena、Apollo、Chronos 的状态。
10. 检查项目根目录 `.env` 里出现 `DEEPSEEK_API_KEY=...`。
11. 检查 `config/pantheon.yaml` 里 `llm_providers.openai.base_url` 是 DeepSeek endpoint。
12. 点击 `Check`，确认没有报错。
13. 点击 `Refresh models`，确认状态显示供应商返回的模型数量，模型下拉更新为当前 API key 可见的模型。
14. 切换到一个新发现的模型，确认只有点击 `Save local config` 后才会修改本地配置。
15. 暂时断网后再次点击 `Refresh models`，确认界面保留当前模型，并回退到 `.pantheon/model_catalog.json` 中的缓存目录。
16. 重启 Web 服务，确认已配置的官方供应商会自动建立模型缓存；24 小时内再次重启不会重复请求供应商。
17. 将 Base URL 改为第三方兼容网关，确认后台不会自动探测；仅点击 `Refresh models` 时才访问该网关。

### `/` 命令菜单

1. 在输入框输入 `/`，确认命令菜单从 composer 上方弹出。
2. 输入 `/pre`，确认只保留 Preview 相关命令。
3. 按上下方向键，确认高亮项移动。
4. 按 `Enter`，确认打开 Workspace Preview。
5. 输入 `/models`，确认打开 Settings / Models。
6. 输入 `/he`，确认切换到 Hephaestus direct mode。
7. 输入 `/schedule`，确认切换到 Chronos scheduling。
8. 输入 `/memory`，确认打开 Settings / Memory。
9. 输入 `/integrations`，确认打开 Settings / Integrations。
10. 输入 `/skills`，确认打开 Integrations 并切到 Skills。
11. 输入 `/fix`，确认能筛选出 `Fix and Verify` Skill。
12. 选择后补充任务并发送，确认输入被转换为 `/skill fix-and-verify <任务>`。
13. 输入 `/remember 这个项目偏好简洁的玻璃拟态 UI`，确认保存一条本地记忆。
14. 输入 `/unknown` 并回车，确认不会发送给 agent，并出现未知命令提示。

### Integrations 扩展中心

1. 打开 Settings -> Integrations。
2. 分别点击 `MCP`、`Plugins`、`Skills`、`Channels`，确认每个区域都有真实操作按钮。
3. 在 `Skills` 中确认显示 6 个内置 Skill，且每项显示归属神、触发词和 `built-in`。
4. 点击 `Fix and Verify` 的 `Use`，补充“修复这个 Python 函数的空值错误”，发送后确认 Hephaestus 消息头与 Activity 显示该 Skill。
5. 新建一个本地 Skill，选择 `Hephaestus`，填写触发词和工作方法，确认 `.pantheon/skills/<id>/SKILL.md` 被创建，再停用/启用各一次。
6. 新建一个 Plugin pack，选择 `Global`，写入一条项目规则；回到对话发送任务，确认该规则会进入 agent 上下文。
7. 在 `Channels` 中启用 Webhook 并生成 Token。使用下面的本地测试命令：

```bash
curl -X POST http://127.0.0.1:8000/api/channels/webhook \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"task":"让 Athena 简要比较 SQLite 和 PostgreSQL","mode":"auto"}'
```

8. 在 `MCP` 中点击 `New server`，选择预设或填写一个 stdio server，保存后点击 `Test connection`，确认能看到工具列表、描述和风险标签。

可以直接使用仓库内的 demo server：`Command` 填 `python`，`Arguments` 填 `examples/mcp_demo_server.py`，`Working directory` 填 Pantheon 项目根目录。

9. 给一个只读工具只勾选 `Athena`，选择 `Run automatically` 并保存；给一个写入工具选择 `Ask every time`，再打开 `Let agents use approved tools`。
10. 在普通对话中让 Athena 完成需要该工具的任务，确认 Workspace Activity 出现 MCP 子步骤。
11. 触发 `Ask every time` 工具，确认出现参数审批弹窗；分别测试 `Deny` 和 `Allow once`。
12. 展开 `Schema and manual diagnostic`，填写合法 JSON 并点击 `Run diagnostic`，确认能看到真实返回值。这里是排障入口，不是日常调用方式。
13. 确认 `.env` 只在本地保存密钥，`.pantheon/mcp_servers.json` 只保存环境变量名；同时确认 `.pantheon/skills/`、`.pantheon/plugins.json` 和 `.pantheon/mcp_servers.json` 被创建。

### Memory 长期记忆

1. 打开 Settings -> Memory。
2. 确认状态为 `manual` 或 `auto`，Store 指向 `.pantheon/memory.sqlite`。
3. 在 `New memory` 输入：

```text
用户偏好中文回答，UI 风格偏简洁高级，不要夸张霓虹。
```

4. 点击 `Save memory`。
5. 确认列表出现新记忆，并显示 memory id，role 为 `global`。
6. 在搜索框输入 `中文`，确认列表能筛出这条记忆。
7. 回到对话框，发送：

```text
/remember 当前项目叫 Pantheon，是神殿多 agent 协作系统。
```

8. 再发送：

```text
帮我记住，我喜欢中文回答，解释尽量简洁。
```

9. 确认 Workspace 日志出现 `Memory saved from user message`，Settings -> Memory 里出现新保存的记忆。
10. 再发送：

```text
这个项目的 UI 风格偏简洁高级，不要夸张霓虹。
```

11. 确认 Settings -> Memory 的 `Suggested` 区域出现候选记忆。
12. 点击 `Save`，确认它进入 `Saved memories`；点击 `Ignore`，确认候选消失且不会进入长期记忆。
13. 在 `Role scope` 选择 `Hephaestus`，保存：

```text
Hephaestus 写代码时优先保持现有架构。
```

14. 切换到 Hephaestus direct mode，发送和代码相关的问题，打开 Workspace -> Terminal，确认日志里出现 `Memory matched` 或 `Memory context injected`。
15. 复制某条记忆的 id，输入 `/forget <id>`，确认列表删除该记忆。

### Chronos 真定时任务

1. 点击左侧 `Chronos`，或输入 `/schedule` 切到 Chronos scheduling。
2. 发送：

```text
every 10 seconds remind me to stretch
```

3. 打开 Workspace -> Activity。
4. 确认 `Chronos Jobs` 里出现新任务，状态为 `scheduled`，并显示下一次运行时间。
5. 等待约 10 秒，点击 `Refresh`，确认运行次数增加或状态更新。
6. 点击 `Pause`，确认状态变成 `paused`。
7. 点击 `Resume`，确认任务恢复。
8. 点击 `Run now`，确认任务立即执行一次。
9. 点击 `Delete`，确认任务从列表移除。

说明：

- Chronos 任务保存在 `.pantheon/chronos_jobs.json`。
- Web 服务停止时，后台调度循环也会停止；重启服务后会继续读取本地任务。
- 任务真正执行时会再次调用 Pantheon，所以如果任务需要模型回答，仍然要有对应 API key。

### Security 登录锁

1. 打开 Settings。
2. 进入 `Security`。
3. 勾选 `Require login for this UI`。
4. 输入用户名，例如 `admin`。
5. 输入至少 8 位密码。
6. 点击 `Save security`。
7. 确认状态显示 `Local login enabled`。
8. 刷新页面，确认出现登录页。
9. 输入用户名和密码，确认可以进入 UI。
10. 退出登录后，确认 Workspace / Setup 等 API 不能在未登录状态下使用。

注意：

- 前端不会保存完整 API key。
- 之后再次打开 Setup，只会显示 mask 后的 key 状态。
- 如果后端 `pantheon/web/app.py` 已经改动，保存配置后仍建议重启一次 Web 服务确认完整流程。

### 会话标题

1. 点击 `New Chat`。
2. 不发送消息时，确认标题仍然是 `New chat`。
3. 发送第一条问题。
4. 确认左侧标题变成第一条问题摘要。
5. 再点一次 `New Chat`。
6. 确认第二个新会话仍然显示 `New chat`。

### Auto / Multi-role 切换

1. 点击顶部 `Auto` pill。
2. 确认它变成 `Multi-role`。
3. 确认左侧 Mode 分段按钮同步变化。
4. 刷新浏览器。
5. 确认当前会话仍保留刚才选择的模式。

### Multi-agent 协作

切换到 `Multi-role` 后发送：

```text
必须用多 agent 协作：Athena 负责调研，Hephaestus 负责代码实现，Apollo 负责表达和文档。请设计一个 FastAPI + SQLite 的 agent memory demo。
```

预期结果：

- Activity 出现 Hermes plan。
- Timeline 出现多个角色步骤。
- 对话区出现多个 agent 响应卡片，或至少出现明确的多步骤协作结果。

### 附件输入

1. 点击输入框左侧的附件按钮。
2. 选择一个 `.txt`、`.md`、`.py` 或 `.json` 文件。
3. 确认输入框下方出现附件 chip。
4. 发送问题，例如：

```text
请总结我上传的文件内容，并指出里面最重要的三点。
```

预期结果：

- 用户消息里显示附件 chip。
- Agent 能根据文本附件内容回答。
- 刷新后历史消息仍显示附件 metadata。

二进制文件测试：

1. 上传一张图片或 PDF。
2. 发送“请分析这个附件”。

预期结果：

- 附件 chip 显示 metadata。
- Agent 应该知道当前 UI 只能提供 metadata，不能直接读取二进制内部内容。

### 语音输入

1. 点击输入框左侧的麦克风按钮。
2. 如果浏览器请求麦克风权限，允许后说一句测试任务。
3. 确认语音内容被填入输入框。
4. 再次点击麦克风按钮停止，或直接发送。

说明：

- Chrome 系浏览器通常支持 SpeechRecognition。
- 如果浏览器不支持，会在 composer 底部显示提示。

### HTML Preview

发送：

```text
用 HTML 写一个极简个人主页，包含一个指向 https://github.com/RyosukeSAMA/github-ai 的 GitHub 链接，输出完整 HTML 代码块。
```

预期结果：

- 对话区出现 HTML artifact 卡片。
- 点击 `Preview` 后，Workspace Preview 渲染页面。
- 点击页面里的 GitHub 链接可以跳转外部网页。
- 点击 `Open` 可以在新窗口打开预览。

### Artifact 保存

发送：

```text
写一个 Python hello world、一个 JSON 配置示例、一个 HTML 页面，分别用代码块输出。
```

预期结果：

- 对话区出现多个 artifact 卡片。
- 点击 `Save to Files` 后文件保存到 `pantheon-artifacts/`。
- Files 自动打开保存的文件。
- HTML artifact 可以继续 Preview。

### Terminal 创建文件

在 Terminal 输入：

```sh
cat > demo.html <<'EOF'
<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Demo</title>
  </head>
  <body>
    <h1>Hello from Pantheon</h1>
    <a href="https://github.com/RyosukeSAMA/github-ai">GitHub</a>
  </body>
</html>
EOF
```

预期结果：

- Terminal 输出执行结果和退出码。
- Files 可以看到并打开 `demo.html`。
- Preview 可以渲染这个页面。
- 因为示例 HTML 没有 CSS，Preview 会显示 `unstyled HTML` 提示。

删除测试文件：

```sh
rm demo.html
```

## 这次改动涉及的主要文件

后续写 release note 或 commit message 时，可以重点提这些文件：

- `pantheon/web/app.py`
- `pantheon/web/static/index.html`
- `pantheon/web/static/app.css`
- `pantheon/web/static/app.js`
- `pantheon/web/static/avatars/`
- `pantheon/core/memory.py`
- `pantheon/core/extensions.py`
- `pantheon/core/hermes.py`
- `pantheon/core/router.py`
- `pantheon/skills/`
- `tests/test_web_workspace.py`
- `tests/test_web_integrations_runtime.py`
- `tests/test_memory.py`
- `tests/test_web_memory.py`
- `tests/test_hermes.py`
- `pyproject.toml`
- `README.md`
- `docs/web-ui.md`

## 发布前检查

建议提交前运行：

```bash
.venv/bin/ruff check . --no-cache
.venv/bin/pytest -q
node --check pantheon/web/static/app.js
```

查看 git 状态：

```bash
git status --short
```

如果本地生成过测试 artifact，并且不打算提交它们，可以删除：

```bash
rm -r pantheon-artifacts
```

如果要正式发新版本，建议同步更新：

- `pyproject.toml`
- `pantheon/__init__.py`
- `pantheon/web/static/index.html` 里的 UI 版本号
- GitHub release note

## Release Note 草稿

可以按下面方向整理 GitHub 更新说明：

```markdown
## Web UI / Workspace Update

- Added multi-session chat with automatic first-prompt titles.
- Added Auto / Multi-role mode switching in the topbar and sidebar.
- Added generated god avatars across sidebar and chat messages.
- Added Workspace tools: Activity, Preview, Files, and Terminal.
- Added HTML artifact preview, file saving, and terminal-created preview flow.
- Improved chat cards, artifact cards, model/status metadata, and copy actions.
- Improved Light/Dark visual style with glass panels, soft grid background, and cleaner spacing.
- Added workspace API endpoints and regression tests.
- Added local long-term Memory with Settings UI, slash commands, SQLite storage, and tests.
- Added standard SKILL.md workflows with role ownership, automatic matching, explicit invocation, built-in Skills, and local Skill management.
- Added real MCP server connections with tool discovery, role policies, approval prompts, and Workspace activity traces.
- Added token-protected Webhook tasks, local Plugin prompt packs, Chronos jobs, and an optional local login lock.
- Fixed authenticated Streamable HTTP MCP connections by passing a configured HTTP client to the MCP SDK.
```
