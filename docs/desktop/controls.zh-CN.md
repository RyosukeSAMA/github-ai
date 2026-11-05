# Pantheon Desktop：按钮与功能说明

对应本地 **0.5.0-beta.19**，核对日期：2026-11-03（Asia/Singapore）。客户端保持英文；本说明保留实际英文名称，中文解释用途。依据当前桌面界面及点击处理代码整理，不代表每项功能都已经通过真实第三方账号或所有操作系统的验收。

## 先认识界面

- **顶部工具栏**：布局、窗口、搜索、主题和桌面偏好。
- **左侧导航**：工作台、任务、产物、项目文件、定时任务和扩展能力。
- **中间工作区**：输入任务、看回复、查执行过程、审阅文件修改。
- **右侧 Task context**：当前项目、角色模型分配、用量与恢复；默认收起。
- **左下角两个图标**：模型/API 连接，以及本地服务/软件更新。

最常用路径是：**Choose project → Models & connections → Save connection → 设置新任务默认模型 → New task → 输入目标 → Run task → 查看 Result → Review and save**。只需一家的可用 API 即可开始文本任务。

## 1. 顶部工具栏

右上角从左到右排列如下；悬停或键盘聚焦可查看名称。

| 名称/外观 | 作用 | 说明 |
| --- | --- | --- |
| `Local connected` / 连接状态 | 点击展开 Connection status：项目服务、各家已保存 API 的最近测试结果和时间 | 可进入模型配置或重连服务；打开卡片不测试模型、不产生模型调用 |
| `Switch to Focus layout` / 布局图标 | 在当前窗口收起左导航和右侧上下文，让任务使用更大的宽度 | 各窗口独立；退出时恢复原上下文状态；新窗口默认标准布局 |
| `Open in new window` / 向外箭头图标 | 先保存当前任务及编辑器草稿，再另开同一项目、同一任务 | 草稿保存失败时不打开；未选项目时显示 New window，打开独立欢迎页；快捷键 `⌘/Ctrl Shift N` |
| `Search and commands` / 命令符号 | 搜索任务/产物，执行新建任务、打开文件、配置模型等导航命令 | 快捷键 `⌘/Ctrl K` |
| `Switch to dark theme` / 月亮，或 `Switch to light theme` / 太阳 | 切换植物水彩和月光花园主题 | 主题在窗口之间同步，但各自的专注布局不变 |
| `Desktop preferences` / 调节杆图标 | 打开字号、上下文宽度、通知、后台运行和全局快捷键设置 | 不用于填写模型 API |

Connection status 的 **Connected** 只表示项目服务可访问；下方 **API verified / Test failed / Not tested / Test expired / Disabled** 是显示型号的已保存测试记录，不代表所有型号都已验证。读取失败会显示 Unavailable，重连不会重新发送任务或自动测试 API。本地服务重启后，同一服务的其他窗口也会重连，并保留各自布局。

实机预览：[浅色连接卡片](toolbar-status-light.png) · [暗色连接卡片](toolbar-status-dark.png) · [窄窗口](toolbar-status-narrow.png)。图中的 API 状态来自隔离的本地测试样例。

## 2. 左侧导航与项目

| 名称/位置 | 作用 |
| --- | --- |
| `New task` / Pantheon 名称旁的笔形按钮 | 新建一条独立任务；快捷键 `⌘/Ctrl N` |
| `Workbench` | 回到当前任务的对话工作台 |
| `Task center` | 汇总任务；按标题/消息搜索，筛选运行中、需处理或已归档的任务；旁边数字为运行/停止处理中的数量 |
| `Artifact library` | 汇总产物，搜索和筛选文档/网页，并回到来源任务或审阅保存 |
| `Project files` | 浏览当前项目文件夹，打开支持的 UTF-8 文本文件并编辑 |
| `Automations` | 创建本地定时任务，暂停/启用，或立即运行一次 |
| `Capabilities` | 管理 Skills、Plugins、MCP、Memory、Messaging、Media、Git & worktrees |
| `Project` 旁的下拉箭头 | 重新选择项目文件夹；取消选择会保留当前项目 |
| 显示文件夹名称的项目卡片 | 已选项目时打开项目文件；未选择时打开文件夹选择器；悬停查看完整路径 |
| `Recent tasks` 旁的放大镜 | 打开全局搜索和命令面板 |
| 最近任务的标题 | 切换到该任务，读取其历史和保存的草稿 |
| 最近任务旁的 `…` | 打开 `Task actions` 菜单 |
| 左下角 `Models and connections` / 调节杆 | 保存各家 API 连接、测试 API、设置默认模型或进入本任务分配 |
| 左下角 `Service and updates` / 插头 | 查看连接的本地/远程服务，重连、检查更新、打开发行页或连接远程服务器 |

`Task actions` 包含：

| 按钮 | 作用 |
| --- | --- |
| `Rename` | 修改任务名称 |
| `Pin` / `Unpin` | 置顶/取消置顶 |
| `Archive task` | 归档，移出普通任务列表；不等于删除聊天或文件 |
| `Restore task` | 恢复已归档任务 |
| `Open in a new window` | 在新窗口中打开同一任务 |

任务中心的 `Open task` 打开任务，`Stop task` 请求停止正在执行的任务；`View saved result` 查看共享核心中保存的 CLI/Web 任务结果。

## 3. 首次使用的欢迎页

| 按钮 | 作用 |
| --- | --- |
| `Choose project` | 选择本地项目文件夹；连接过程中显示进度，失败时保留原因 |
| `Choose another folder` | 项目打开失败后重选 |
| 显示项目名的文件夹图标 / `Open project files` | 进入已选项目的文件列表 |
| `Configure models` | 打开模型与 API 配置；需要先连接项目 |
| `Connect remote server` | 连接已有的 HTTPS Pantheon 服务；不是注册云账号，也不会替你部署服务器 |
| `Create first task` | 配置好后进入第一条任务 |

连接远程服务器后，文件和模型配置属于该服务器；不会自动改为本机文件或本机 API。

## 4. 花园工作台、角色与输入框

### 角色头像和运行模式

| 头像/模式 | 用途 |
| --- | --- |
| `Hermes` / `Auto route` | 由 Hermes 判断应该交给哪个角色，必要时组织协作 |
| `Multi-role council` | 明确要求多角色协作，由 Hermes 组织计划和执行 |
| `Hephaestus` | 直接交给代码、工程和修复角色 |
| `Athena` | 直接交给研究、资料整理和推理角色 |
| `Apollo` | 直接交给创作角色；媒体能力仍取决于另行配置的模型/API |
| `Chronos` | 处理定时和周期任务；自身不是需要配置模型的第五个聊天角色 |

点击头像会选择相应模式，不会立即发送任务。Hermes 头像对应 Auto route；输入框左下的模式菜单也可选择 Multi-role council。

### 输入框与起步卡片

| 按钮/状态 | 作用 | 是否立即调用模型 |
| --- | --- | --- |
| `Council mode` / 输入框左下的模式按钮 | 选择自动路由、多角色协作或指定角色 | 否 |
| `Attach images or PDF` / 回形针 | 选择并附加图片/PDF，最多五个附件；理解能力取决于配置 | 只添加附件不会发送任务 |
| `Assign role models` / 输入框旁的调节杆 | 为当前任务选择同一家或混用不同供应商/型号 | 保存分配本身不会调用模型 |
| `Run task` / 发送箭头 | 发送输入内容并开始执行；快捷键 `⌘/Ctrl Enter` | 是，按任务需要调用 |
| `Stop task` / 运行时变为停止图标 | 请求停止执行，保留已经完成的工作 | 不会撤销已发生的调用或文件操作 |
| `Saved` | 当前输入草稿已保存，可在之后继续 | 不表示任务已发送，也不表示产物已写入项目文件 |
| `Explore this project` | 填入项目探索的起步提示 | 否，只填草稿 |
| `Build something` | 填入构建功能的起步提示 | 否，只填草稿 |
| `Fix an issue` | 填入排查问题的起步提示 | 否，只填草稿 |
| `Research a topic` | 填入研究主题的起步提示 | 否，只填草稿 |

有未发送内容时，起步卡片会先确认是否替换草稿。音频转文字的入口在 `Capabilities → Media`。

## 5. 对话、结果、执行与文件修改

| 页签/按钮 | 作用 |
| --- | --- |
| `Conversation` | 查看对话、输入内容和执行时的输出 |
| `Result` | 阅读最近一次助手回复，查看当前任务产物 |
| `Activity` | 查看已记录的规划、角色执行、工具和完成事件 |
| `Changes` | 查看待审阅文件的差异；新增/删除内容有颜色区分 |
| `Council details` / 角色小头像摘要 | 展开已经记录的参与角色和执行说明 |
| `Open full activity` | 从摘要进入完整 Activity |
| `Load earlier messages` | 加载更早的对话 |
| `Copy response` / 回复复制图标 | 复制这条助手回复的文本 |
| `Copy code` | 复制对应代码块 |
| `Export full task archive` | 选择位置，将当前已执行任务的完整存档导出为 JSON |

产物卡片：

| 按钮/状态 | 作用 |
| --- | --- |
| `Preview` | 在客户端预览产物；HTML 为隔离的静态预览，不执行网页脚本 |
| `Source task` | 回到产生该产物的任务 |
| `Review and save` | 选择项目内的目标路径，生成差异并进入 Changes；此时还没写文件 |
| `Ready to review` | 产物已经生成，仍待审阅保存 |
| `Saved to …` | 产物已经保存到显示的路径 |
| `Accept and save` | 接受当前差异并写入文件；文件若已被其他程序修改，会阻止直接覆盖 |
| `Discard changes` | 放弃这次待审阅修改；不会回滚之前已经保存的文件 |

项目文件编辑：`Open folder` 在系统文件管理器打开项目；`Parent folder` 返回上级；`Reload file` 从磁盘重新读取；`Review changes` 将编辑草稿送去审阅，仍需 `Accept and save` 才写入。

## 6. 右侧 Task context

| 区域/按钮 | 作用 |
| --- | --- |
| `Show context` / 工作区右上分栏图标 | 展开右侧上下文；`Hide context` 或 × 收起 |
| `Workspace` / `Project location` | 显示项目名称和本地/远程位置，展开可查看完整路径 |
| `Open project folder` / 向外箭头 | 在连接主机允许的本地项目场景打开项目文件夹 |
| `This council` | 显示当前任务的角色、职责和配置的供应商标识 |
| 角色下面的供应商小按钮 | 打开角色模型分配；悬停可查看完整模型 ID |
| `Edit assignment` | 同样进入本任务模型分配 |
| `Usage and budgets` | 查看记录的模型调用、token、费用估算，查看/编辑工作区预算策略 |
| `Review recovery` | 任务失败、中断或停止后，先审阅已完成工作，再确认是否继续 |

角色旁的品牌图标表示配置来源，不代表已经验证 API 或该角色已经执行。费用为估算而非账单；`Cost unknown` 表示缺少价格，不能理解成免费。恢复可能重新调用供应商，不会自动发生。

## 7. Models & connections：连接与 API

### 第一步：保存连接

| 控件/按钮 | 作用 |
| --- | --- |
| 顶部供应商小卡片 | 展示已经保存的连接及其测试状态；目前是摘要，不是切换按钮 |
| `Provider` | 选择当前正在编辑的供应商，各家连接分别保存 |
| `Test model` | 选择测试/连接参考型号，可搜索或直接填模型 ID；切换型号不会自动测试 |
| `API base URL` | API 地址；通常保留默认，兼容网关按其提供的地址填写 |
| `API key` | 第一次输入密钥；已保存时显示固定掩码，不回显真实密钥 |
| `Change` | 输入替换密钥；仍需 Save connection 才保存 |
| `Cancel change` | 取消替换，继续保留原密钥，不清除其他字段的草稿 |
| `Storage & streaming` | 展开凭据存储、流式输出和刷新模型等高级选项 |
| `Credential storage` | 选择私有本地 `.env`，或可用的系统凭据存储 |
| `Stream incremental output` | 配置增量输出方式；此选项跟随连接保存 |
| `Test API` | 确认后向所选模型发出小请求，检查实际访问；可能产生使用量，测试不等于保存 |
| `Refresh models` | 获取当前连接的模型目录；不会自动替换已保存的角色模型 |
| `Save connection` | 保存当前供应商的连接信息，解锁第二步；不改变现有角色分配 |

### 第二步：决定用在哪里

| 按钮 | 实际影响范围 |
| --- | --- |
| `Use this provider for new tasks` | 确认后，将四个 AI 角色的新任务默认值设为当前供应商/型号；现有任务和 Chronos 不变 |
| `Assign this task` | 打开当前任务的角色分配窗口；还需点击 Apply to this task 才应用 |
| `Enable / disable connection` | 查看哪些角色/任务引用此连接，并进入启用、停用或移除操作 |
| `Done` | 保存连接后结束配置；只关闭配置，不额外改变角色模型 |
| `Add another provider` | 在完成提示里进入另一家尚未保存的连接，不会购买或测试 API |

应用新任务默认值或本任务模型成功后，配置窗口会关闭，工作台显示绿色提示并说明影响范围。

### Assign role models：当前任务分配

| 按钮/控件 | 作用 |
| --- | --- |
| `One provider` | 当前界面让四个 AI 角色统一使用相同供应商和型号 |
| `Mix by role` | 为 Hermes、Hephaestus、Athena、Apollo 分别选择供应商和型号；可以都是一家，也可以混用 |
| 每行 `Connection` | 选择该角色使用的连接 |
| 每行 `Model` | 搜索/选择型号，或输入自定义 ID；方向键移动、Enter 选择、Escape 收起、Tab 继续填写 |
| `Apply to this task` | 保存到当前对话；其他任务和新任务默认值不变 |
| `Cancel` / × | 关闭，不应用本次分配修改 |

### 状态与连接管理

| 名称/按钮 | 含义 |
| --- | --- |
| `API verified` | 显示的那组模型/地址/密钥通过过 API 测试；修改关键配置后需重新验证 |
| `Connection saved` | 配置已保存；不保证该 API 已经测试成功 |
| `Not tested` | 没有对应的成功测试记录；不直接等于不可用 |
| `Test failed` | 最近一次测试失败，应查看原因 |
| `Disabled` | 连接已停用 |
| `Disable connection` / `Enable connection` | 暂停/恢复连接；原角色引用会保留 |
| `Remove saved connection` | 移除保存的连接配置；不会替角色自动选另一家 |
| `Also delete the saved API key when removing` | 选中后，在移除时一并删除保存的密钥 |

DeepSeek/OpenAI/Anthropic 图标用于识别连接；Ollama 图标识别运行平台，只有明确的本机回环地址才标记 Local endpoint。

## 8. Desktop preferences 与软件服务

桌面偏好需要点击 `Save preferences` 才保存：

| 选项/按钮 | 作用 |
| --- | --- |
| `Text size` | 调整阅读字号，当前范围为 13–20 px |
| `Context panel width` | 调整右侧上下文宽度，当前范围为 260–460 px |
| `Task notifications` | 启用任务完成或待审批通知；实际显示取决于系统通知能力和权限 |
| `Keep working in the background` | 启用后关闭最后一个窗口可保留托盘中的服务；电脑睡眠仍可能影响执行 |
| `Global shortcut` | 启用 `⌘/Ctrl Shift Space` 呼出/聚焦应用；依赖系统允许注册该快捷键 |
| `Save preferences` | 保存并应用界面/桌面设置 |
| `Cancel` / × | 关闭偏好窗口，不保存本次表单改动 |

`Service and updates`：

| 按钮 | 作用 |
| --- | --- |
| `Reconnect current host` | 尝试重连当前本地服务或已登录远程服务器，不重新发送任务 |
| `Check for updates` | 检查兼容平台的稳定桌面发行版；不会自动下载安装，Beta 之间不保证自动提示 |
| `Open official releases` | 打开 GitHub 发行页，手动查看和下载版本 |
| `Connect remote server` | 填写 HTTPS 地址、账号和密码，连接已有 Pantheon 服务 |
| `Remember using system-backed encryption` | 在系统加密能力可用时记住远程登录凭据；不是模型 API 密钥的存储开关 |
| `Connect` | 提交远程连接信息 |

托盘菜单中的 `Open Pantheon` 打开窗口，`New window` 新开窗口，`Quit Pantheon` 退出程序。退出会停止客户端自己启动的本地服务；不会停止复用的已有服务或远程服务器。有活动任务时会先提示。

## 9. Terminal：项目终端

| 按钮 | 作用 |
| --- | --- |
| `Open terminal` / 页签右侧终端图标 | 展开命令面板 |
| `Run once` | 确认后，在连接主机的项目环境执行输入的命令；这是真实执行 |
| `Stop command` | 请求中止当前命令 |
| `Close terminal` / × | 收起面板；不应当用它代替 Stop command |

## 10. Automations 与 Capabilities

### Automations

| 按钮 | 作用 |
| --- | --- |
| `Create schedule` | 根据输入的时间/任务描述创建本地定时任务 |
| `Pause` | 暂停该计划 |
| `Enable` | 恢复已暂停的计划 |
| `Run once` | 确认后立即执行一次，可能调用配置的模型和工具 |

本地计划要求服务运行且电脑醒着，不是独立的云端定时服务。

### Capabilities

| 页签/按钮 | 作用 |
| --- | --- |
| `Skills` | 查看技能提示词；`Add skill` 添加，`Edit` 编辑非内置项，`Enable/Disable` 切换启用状态 |
| `Plugins` | 查看/添加/编辑插件指令；当前不是任意桌面应用的一键安装商店 |
| `MCP` | 添加/编辑 MCP 服务；`Inspect tools` 确认后连接服务并发现工具；本地 stdio 服务会启动相应程序 |
| `Tool policies` / `Save tool policy` | 配置各工具的启用状态、允许角色以及逐次审批/自动允许策略 |
| `Memory` / `Add memory` | 查看并添加持久项目记忆；与单条聊天记录不同 |
| `Messaging` / `Configure Telegram/Slack/Discord` | 保存平台连接、允许用户/频道和回复选项；保存本身不发送测试消息，接收真实消息仍需可达 HTTPS 回调 |
| `Configure webhook` / `Save webhook` | 配置通用回调；首次启用生成令牌，按弹窗提示保管 |
| `Media` / `Save media models` | 保存图片/PDF 理解、图像生成和音频转写的专用模型选择 |
| `Generate image` | 确认后调用配置的 OpenAI 图像模型；不会因为已有 DeepSeek 连接就自动具备图像生成能力 |
| `Choose audio to transcribe` | 选择音频，确认后调用配置的 OpenAI 转写模型 |
| `Use in task draft` | 将转写文字放入任务草稿，不自动发送 |
| `Save output…` | 选择位置，保存生成的媒体文件 |
| `Git & worktrees` | 查看项目 Git 分支、状态和差异；需要连接主机已安装 Git |
| `Create isolated worktree` | 从指定分支/提交创建隔离工作目录；不复制当前未提交修改 |
| `Open isolated project` | 打开刚创建的工作目录，使用其独立工作区 |
| `View details` | 查看对应能力的配置详情 |

执行中需要工具审批时，`Allow once` 只批准当前请求，`Deny` 拒绝当前请求。

## 三种“保存”不要混淆

1. **输入框 Saved**：保存的是未发送草稿。
2. **Save connection**：保存 API 连接；再决定新任务默认值或本任务分配。
3. **Accept and save**：确认文件差异，真正把内容写入项目文件。

本说明只解释现有界面；没有新增按钮、调整布局、调用付费 API、上传 GitHub 或合并分支。


## 更新与备份恢复（beta.17）

打开 **Service & updates**，在 Updates 选择 Stable 或 Beta + Stable。下载显示进度，支持取消/重试；必须通过 SHA-256 校验才能打开。**Back up & open installer** 先备份空闲且由 Desktop 管理的本地工作区，再打开系统安装器，随后退出应用并安装。它不会静默替换应用或自动降级。

**Backups & recovery** 创建/检查/恢复归档。默认不包含项目源文件、API 凭证和配置；勾选包含凭证时还需要系统确认。恢复必须在空闲本地工作区进行，恢复后的定时任务保持暂停，运行中任务、待发消息和审批不会自动重放。远程或复用服务需要在拥有服务的主机上维护。完整步骤见[下载与恢复说明](../../desktop/downloads.md)。


## beta.18 新入口

- **Help and diagnostics**：新手步骤、快捷键、版本和本地诊断导出。诊断文件不含密钥、聊天、项目名/路径、地址或原始日志，也不会自动上传。
- **Desktop preferences → Appearance**：System 跟随系统；Light/Dark 固定主题，同时切换花园。
- **Usage and budgets**：表单设置请求上限、每次输出 Token 上限、估算费用上限与自填单价；空值表示不设上限。未知费用不会当作免费。
- **Project files / 已保存成果 → Version history**：比较真实文本快照；Review restoration 只准备差异，再点接受才写入，并检查文件是否又被外部修改。
- **Assign role models → Compare model plans**：按自填单价/评分比较费用优先、均衡、质量偏好。先填入分配界面审阅，再 Apply to this task。比较本身不测试 API 或切换模型。


## beta.19 离线草稿与操作区

**Service & updates → Offline drafts**：对同一 HTTPS 主机/账号/工作区启用本地私有缓存。断网时可以编辑草稿、新建未发送任务及搜索已缓存内容，状态为 Saved locally。重新连接不自动同步；点击 Sync drafts 后，如另一台设备或网页端改过草稿，会展示两端文本供选择。选择保留本机草稿后仍需再次 Sync drafts；选择服务器稿件会保留一份本机恢复副本。Export local drafts 导出私有文本。主机需升级到支持该修订协议的当前源码；工作区 ZIP 不含本设备尚未同步的应用缓存。

**Operation sessions**：先明确批准浏览器来源或 macOS 应用，再添加步骤并 Review & run steps。浏览器在单独窗口运行，可填写/点击/截图；跨来源导航、下载和弹窗受限，不共享 Pantheon 登录 Cookie。Stop 取消剩余步骤，已经发出的请求可能继续完成。macOS 应用控制需要实际辅助功能与自动化权限，支持范围以内置应用列表为准；Windows/Linux 目前只有浏览器适配器。该入口不会给模型授予无需审阅的桌面权限。详见[完整步骤与验证边界](../../desktop/offline-and-operations.md)。
