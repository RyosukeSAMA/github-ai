# 媒体、工作流与任务恢复

先完成[新手安装](setup.zh-CN.md)，打开 Settings → Setup 保存至少一个聊天供应商。下面的设置按工作区保存，CLI、Web、SDK 共用；会话内的模型覆盖不会改动其他聊天或全局默认值。

Web 普通追问会携带当前聊天的近期文字，最多 16 条用户/助手消息、合计 24,000 字符，单条最多 12,000 字符。长消息使用带标记的首尾摘录，完整记录保留在聊天中。多角色任务只带上每轮最终回复，不重复携带所有中间步骤。这会增加下一次请求的输入 token，但不会额外调用模型做摘要。上下文与工作区记忆分开，恢复任务时保留，也不会自动读取其他聊天。SDK 可向 `ask()` 显式传入 `history=[{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]`。

提示词优化使用当前聊天分配给 Hermes 的模型。Models 中可以选择已保存的自定义模型，也可为单个角色或全部 AI 角色输入精确模型 ID。目录未列出不代表模型不可用，可用 Test this role 验证访问权限。回复标签保存本次调用的模型，切换模型或刷新后保持原记录；旧消息缺少来源时显示 “Model not recorded”，不会推测其使用了哪个模型。

每次 `pantheon ask` CLI 命令仍是独立任务，不会自动续接网页聊天或上一条 CLI 命令。CLI 从同一个工作区读取已保存的角色默认模型与供应商连接。网页选择 “Current chat only” 不影响 CLI；保存 “New chat defaults” 也会更新后续 CLI 任务使用的工作区默认模型，可统一使用一家或按角色混用。v0.3.2 不改变 CLI 命令语法或神殿布局。

## 图片和 PDF 理解

1. 在 Setup 保存 OpenAI 或 Anthropic 的 API key；聊天用 DeepSeek 时，也要单独配置视觉供应商的 key。
2. 打开 Settings → Media，选择视觉供应商和有图片/PDF 能力的模型 ID，点击 Save media models。保存表示配置完成，不保证账号已有该模型权限。
3. 回到对话，使用回形针或拖拽上传 PNG、JPEG、WebP、PDF。每个最大 8 MiB，合计最大 20 MiB，最多六个；文件扩展名和签名需要匹配。
4. 输入“总结关键证据”或具体问题并发送。上传阶段不调用模型；发送后文件会交给视觉供应商识别，再由 Pantheon 执行任务。
5. 缺少 key、文件类型不支持、模型无权限或预算不足会明确失败，不会把文件名当成已读内容。

上传文件私有保存在工作区状态目录的 `media/`，会话只记录文件 ID 和 metadata。识别结果进入任务检查点，恢复任务时不会重复调用已成功的视觉识别。

CLI 与 SDK：

```sh
pantheon ask --file report.pdf --file chart.png "比较报告和图表中的数据"
```

```python
from pathlib import Path
from pantheon import Pantheon
p = Pantheon()
result = p.ask("解释这个图表", attachments=[Path("chart.png")])
```

## 生成图片和转写音频

在 Media 设置 OpenAI 的图片和音频模型。默认值来自本版核对的官方文档，供应商模型更新后可填写新 ID；模型访问和账单以你的 API 账号为准。

- 图片：填写描述，选择尺寸，点击 Generate。生成一张 PNG，可预览并下载。也可明确让 Apollo “生成一张实际图片”；原生工具成功后才显示图片链接。
- 音频：上传 WAV、MP3、M4A、MP4 或 WebM，最大 24 MiB，点击 Transcribe。转写结果可以下载，也可点击 Use transcript in composer，核对后自行发送，不会自动发出聊天。
- 图片、PDF、音频发送给所选供应商，可能产生费用。不会将 DeepSeek key 发给 OpenAI。音频生成、视频生成、图片编辑不属于本版内置能力。

```sh
pantheon image "星空下的蓝色玻璃神殿"
pantheon transcribe recording.wav
pantheon media
```

```python
artifact = p.services.media.generate_image("星空下的蓝色玻璃神殿")
metadata, image_path = p.services.media.get(artifact["id"])
audio = p.services.media.upload_path("recording.wav")
transcript = p.services.media.transcribe(audio["id"])
```

## 并行执行与有限恢复

在 Settings → Info → Workflow 设置独立步骤数（1–4，默认 3）和失败恢复轮数（0–2，默认 1）。仅无依赖且安全的步骤可以同时运行，依赖结果只传给相关步骤。调度、图片生成、有写入/审批工具的角色保守串行。

恢复只能修复原计划里失败的指令，保留已完成步骤，不改变角色、依赖或扩大任务。API key/额度/审批错误不会通过重复调用自动修复；发生外部操作的失败步骤不自动重跑。

```sh
pantheon workflow --parallel 3 --recovery 1
```

## 预算

Info → Budgets 可以设置每任务请求数、24 小时请求数、输出 token 上限、任务/日费用估算。0 表示不限。规划、摘要、恢复、媒体请求和失败尝试都会计入；并发请求先预留额度。

文本按你提供的每百万 token 单价估算；媒体有额外图像/音频计费，使用你提供的每次请求估算，不把 base64 当作文本 token 定价。开启金额上限时，未定价的模型会在发送前被拒绝。估算不是服务商账单，失败和缺少用量的请求保留预留值。

```json
{
  "task_requests": 12,
  "daily_requests": 100,
  "prices": {},
  "operation_prices": {}
}
```

把自己的价格写入 JSON 后，运行 `pantheon budgets --policy policy.json`。价格键为 `供应商/模型ID`；文本值为 `{"input":输入单价,"output":输出单价}`，媒体值为每次请求的美元估算。

## 恢复与完整归档

在 Info → Task history 查看结果、Resume failed steps 或 Download full archive。CLI：

```sh
pantheon tasks
pantheon tasks --show TASK_ID
pantheon tasks --resume TASK_ID
pantheon tasks --archive TASK_ID > result.json
```

恢复使用当前保存的模型配置和原计划，成功步骤不再执行。未完成步骤曾尝试外部操作时，先检查实际结果，再通过 UI 确认或 `--acknowledge-effects` 明确重试。已继续的源任务不能再创建第二个重试；应查看或恢复其后继任务。

旧任务没有检查点时，从保存的请求新建。结果详情最多显示 200,000 字符，完整 JSON 归档不截断。停止任务会阻止后续调用，已被供应商接受的同步请求可能仍会完成并计费。

离线备份包含媒体和任务数据，恢复合并文件但不删除备份之外的文件。恢复后平台入口关闭、排队事件标为中断，不自动重发。见[备份说明](core-readiness.zh-CN.md)。


当前 Media 页（未配置密钥，不表示调用成功）：

![Pantheon Media](images/pantheon-media.jpg)
