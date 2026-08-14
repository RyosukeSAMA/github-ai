<p align="center">
  <img src="docs/images/pantheon-banner.jpg" alt="Pantheon local multi-agent workspace" width="100%">
</p>

<p align="center">
  <img src="docs/images/pantheon-mark.png" alt="Pantheon 品牌徽记" width="112">
</p>

<h1 align="center">Pantheon</h1>

<p align="center">
  <strong>一个本地多 Agent 工作区</strong><br>
  Hermes 负责规划与编排，专业神祇分工执行。
</p>

<div align="center">

[![Version](https://img.shields.io/badge/version-0.2.1-6366f1.svg)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776ab.svg)](https://www.python.org)
[![CI](https://github.com/RyosukeSAMA/github-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/RyosukeSAMA/github-ai/actions)
[![License](https://img.shields.io/badge/license-MIT-24292f.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-alpha-d6a84b.svg)](#current-boundaries)

[English](README.md) | **简体中文**

[快速开始](#quick-start) · [神祇角色](#agent-roles) · [扩展中心](#integrations) · [架构](#architecture) · [文档](#documentation)

</div>

![Pantheon Web UI](docs/images/pantheon-web-ui.jpg)

<p align="center"><sub>Pantheon Web UI：对话、Agent 编排、Workspace、文件、终端与网页预览集中在同一个本地工作区。</sub></p>

Pantheon 把一个需求变成可观察、可控制的本地协作流程。使用 **Auto** 让 Hermes 自动选择合适的神，切换到 **Multi-role** 发起明确的多角色协作，也可以直接与某位神对话。同一套运行时同时支持 Web UI、CLI 和 Python SDK。

## 当前能力

| 模块 | 当前实现 |
|---|---|
| 多 Agent 调度 | Auto 自动路由、指定角色和强制 Multi-role 计划 |
| Agent 工作区 | 实时 Activity、HTML Preview、文件浏览/编辑和 Terminal |
| 会话 | 多会话、首条消息自动命名、Markdown 导出、附件和 `/` 命令 |
| Memory | 本地 SQLite、角色范围、自然语言记忆识别和保存建议 |
| Chronos | 持久化的单次/周期任务和运行记录 |
| 扩展 | 6 个内置 Skills、本地 Skills、Plugin prompt packs、MCP 工具和 Webhook |
| 本地配置 | Provider/模型向导、配置检查、API 测试、登录锁和可选自动启动服务 |

Pantheon 以本地为中心：配置、Memory、定时任务和扩展状态保存在所选工作区，会话和显示偏好保存在当前浏览器。只有在执行任务时，相关内容才会发送给你启用的模型 Provider 或外部集成。

<a id="quick-start"></a>

## 快速开始

### 环境要求

- Python 3.10 或更高版本
- Git
- 至少一个支持的模型 Provider，或正在运行的 Ollama
- 推荐 macOS 或 Linux；Windows 用户目前建议使用 WSL

### 安装并启动

```bash
git clone https://github.com/RyosukeSAMA/github-ai.git
cd github-ai

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .

pantheon web
```

如需电脑重启后继续自动运行 Pantheon，可在项目根目录安装当前用户服务：

```bash
pantheon service install
pantheon service status
```

它会在用户登录后启动，并继续只监听 `127.0.0.1:8000`。维护时可使用
`pantheon service logs` 和 `pantheon service restart`。macOS 的服务日志位于
`~/Library/Logs/Pantheon/`。

打开 <http://127.0.0.1:8000/>，进入 **Settings → Setup**：

1. 选择 DeepSeek、OpenAI、Anthropic 或 Ollama。
2. 选择模型，并在需要时输入 API key。
3. 依次运行 **Check setup** 和 **Test API**。
4. 点击 **Save local config**。

Web UI 会把 API key 保存到本地 `.env`，把 Provider、Base URL 和模型选择写入 `config/pantheon.yaml`。修改后端配置后，如需完整重载运行时，请重启 `pantheon web`。

Anthropic 模型目录已包含 Claude Opus 5（`claude-opus-5`）。Claude 兼容网关
也继续使用 **Anthropic**，并按服务商要求修改 Base URL。

<details>
<summary>手动配置文件</summary>

```bash
cp config/pantheon.example.yaml config/pantheon.yaml
cp .env.example .env
```

在 `.env` 中填写所需密钥，并在 `config/pantheon.yaml` 中设置匹配的 Provider、模型和 Base URL。不要提交这两个本地文件。

</details>

### 第一次使用

1. 点击 **New Chat**，保持 **Auto** 模式。
2. 输入一个具体任务，例如：`制作一个响应式个人主页，并输出完整 HTML`。
3. 打开 **Workspace** 查看 Hermes 计划、当前 Agent 和执行步骤。
4. 在 **Preview** 预览 HTML，在 **Files** 查看保存的产物，在 **Terminal** 执行本地命令。
5. 在输入框键入 `/`，可以使用 `/multi`、`/schedule`、`/memory`、`/skills`、`/preview` 等命令。

<a id="agent-roles"></a>

## 神祇角色

Pantheon 用神祇身份表达清晰的职责边界：Hermes 负责编排，Hephaestus 负责构建，Athena 负责研究，Apollo 负责创意，Chronos 负责时间与调度。

<p align="center">
  <a href="docs/images/posters/pantheon.webp">
    <img src="docs/images/posters/pantheon.webp" alt="Pantheon multi-agent system concept poster" width="420">
  </a>
</p>

<p align="center"><sub>Pantheon 品牌概念图。README 顶部的 Web UI 截图展示当前真实产品界面。</sub></p>

### 五神概念海报

<p align="center">
  <a href="docs/images/posters/hermes.webp"><img src="docs/images/posters/hermes.webp" alt="Hermes — orchestration and routing" width="30%"></a>
  <a href="docs/images/posters/hephaestus.webp"><img src="docs/images/posters/hephaestus.webp" alt="Hephaestus — engineering and building" width="30%"></a>
  <a href="docs/images/posters/athena.webp"><img src="docs/images/posters/athena.webp" alt="Athena — research and reasoning" width="30%"></a>
</p>

<p align="center">
  <a href="docs/images/posters/apollo.webp"><img src="docs/images/posters/apollo.webp" alt="Apollo — creative direction" width="30%"></a>
  <a href="docs/images/posters/chronos.webp"><img src="docs/images/posters/chronos.webp" alt="Chronos — scheduling and time" width="30%"></a>
</p>

<p align="center"><sub>点击海报查看大图。角色图用于表达产品定位；实际模型、联网能力和媒体生成能力取决于用户配置的 Provider、Skills 与 MCP 工具。</sub></p>

Hermes、Hephaestus、Athena 和 Apollo 都可以在 Settings 中分别设置不同 Provider 和模型。`config/pantheon.example.yaml` 中的值仅用于展示混合 Provider 配置方式，并不是强制默认值。

| 神祇 | 专长 | 模型 | 可执行工具边界 |
|---|---|---|---|
| **Hermes** | 规划、路由、协调和结果汇总 | 独立配置 | 调度已配置的 Agent 和获准扩展 |
| **Hephaestus** | 代码生成、调试、重构和审查 | 按角色配置 | 文件或终端改动通过 Workspace 或已授权 MCP 完成 |
| **Athena** | 调研整理、对比、事实核查和摘要 | 按角色配置 | 实时联网需要已授权的 MCP 或 Provider 工具 |
| **Apollo** | 创意策划、写作、图片提示词和分镜 | 按角色配置 | 真正生成图片、音频或视频需要外部工具 |
| **Chronos** | 单次和周期本地任务 | 无 LLM | 仅在 Pantheon Web 服务运行时执行 |

角色 Prompt 本身不会自动获得外部工具。第三方工具必须先连接，再分配给对应神，并通过 MCP 策略授权后，Pantheon 才会执行。

## Workspace

右侧 Workspace 是任务的操作视图：

- **Activity**：显示当前任务、Hermes 计划、执行中的神、耗时、Skills、Memory 命中、MCP 调用、审批和完成状态。
- **Preview**：在沙箱 iframe 中渲染完整 HTML 和消息产物，支持桌面/移动视图与缩放。
- **Files**：在工作区根目录内浏览、打开、编辑、保存、下载和预览文件。
- **Terminal**：流式显示本地命令输出，保留命令历史，支持取消，并在识别到风险命令时要求确认。

生成的代码默认只是消息 Artifact。只有用户点击 **Save to Files**，或获准工具执行写入后，代码才会变成本地文件。这可以避免普通聊天输出意外修改项目。

## Memory 与定时任务

### Memory

Memory 保存在 `.pantheon/memory.sqlite`，可以设为全局，或只作用于 Hermes、Hephaestus、Athena、Apollo、Chronos 中的某个角色。

- 说“记住……”或使用 `/remember` 可以明确保存记忆。
- Pantheon 可以从普通对话中提出记忆建议，由用户一键确认。
- 可选的自动捕获会保存简短的任务/结果摘要；默认关闭，避免记忆库被噪声污染。
- 使用 `/memories <关键词>` 或 **Settings → Memory** 搜索、编辑、置顶和删除记忆。

### Chronos

Chronos 会把支持的自然语言时间表达转换为持久化任务，并保存到 `.pantheon/chronos_jobs.json`。选择 Chronos 或使用 `/schedule`，可以创建、查看、暂停、恢复、立即运行和删除任务。

定时任务会在重启后恢复，但它是本地调度器：Pantheon Web 服务停止期间不会执行任务。

<a id="integrations"></a>

## Integrations 扩展中心

Integrations 提供的是真实本地能力，不是静态展示开关。

| 模块 | 状态 | 当前作用 |
|---|---|---|
| **Skills** | 可用 | 加载标准 `SKILL.md`；支持自动匹配、显式 `/skill` 调用、6 个内置 Skill 和可编辑本地 Skill |
| **MCP** | 可用 | 连接 stdio 或 Streamable HTTP server，发现工具、分配神祇，并设置自动执行/每次审批策略 |
| **Plugins** | 可用 | 把启用的本地 Prompt Pack 注入指定 Agent 上下文；不会执行任意 Python 插件代码 |
| **Channels** | Webhook 可用 | 通过 `/api/channels/webhook` 接收带 Token 的脚本或服务任务 |

### 内置 Skills

- `plan-multi-agent-task`：Hermes 把复杂需求拆成有顺序的多神计划。
- `fix-and-verify`：Hephaestus 定位、修复并验证一个具体缺陷。
- `research-with-sources`：Athena 区分证据与推断，并给出可追踪来源。
- `build-web-preview`：Apollo 与 Hephaestus 设计并实现可预览网页。
- `review-code-change`：Athena 与 Hephaestus 审查代码改动中的具体风险。
- `schedule-and-deliver`：Chronos 把时间要求转换为持久化本地任务。

### MCP 使用流程

1. 打开 **Settings → Integrations → MCP**，添加一个 Server。
2. 点击 **Test connection** 发现工具。
3. 只启用需要的工具，并指定允许使用它们的神。
4. 选择自动执行或每次调用审批。
5. 开启 **Let agents use approved tools**，然后在普通对话中描述任务。

GitHub、Context7 和 Figma Desktop 是连接表单预设，不是 Pantheon 内置账号或托管 MCP 服务。用户仍需提供凭据，并准备对应的本地或远程 Server。

Channels 当前只提供 Webhook 入口。钉钉、企业微信、微信、QQ、Slack、Teams 等原生适配器属于后续计划，目前尚未内置。

## CLI 与 Python SDK

### CLI

```bash
# 让 Hermes 自动决定路由
pantheon ask "调研一个主题并整理可靠证据"

# 直接交给指定神
pantheon ask --role hephaestus "写一个 Python 回文检查器"

# 强制执行有顺序的多 Agent 计划
pantheon ask --multi "调研一个 AI 产品、设计页面并生成 HTML"

# 查看并显式调用 Skill
pantheon skills
pantheon ask --skill fix-and-verify "修复空值处理回归"
```

### Python SDK

```python
from pantheon import Pantheon

pantheon = Pantheon()

result = pantheon.ask("设计并实现一个响应式个人主页", mode="multi")
print(result["content"])

for step in result["steps"]:
    print(step.role, step.duration_ms, step.success)
```

## 本地数据与安全

| 位置 | 保存内容 |
|---|---|
| 浏览器 `localStorage` | 会话历史、显示偏好和部分 UI 状态 |
| `.env` | API key、Webhook Token 和本地登录配置 |
| `config/pantheon.yaml` | Provider、模型、角色、Web 和日志配置 |
| `.pantheon/memory.sqlite` | 长期记忆和记忆建议 |
| `.pantheon/chronos_jobs.json` | Chronos 任务和运行状态 |
| `.pantheon/mcp_servers.json` | MCP Server 与策略；密钥只保存环境变量名引用 |
| `.pantheon/plugins.json` | 本地 Plugin Prompt Packs |
| `.pantheon/skills/` | 本地标准 Skills |

仓库内的这些本地文件均已加入 `.gitignore`，应继续保留在本机。

> [!IMPORTANT]
> Pantheon 包含文件写入和终端执行 API，默认只监听 `127.0.0.1`。使用 `0.0.0.0`、局域网地址、NAS、远程服务器或反向代理前，请先在 **Settings → Security** 开启登录锁，并增加防火墙或代理访问控制。当前登录锁面向单个本地操作者，不是公网多用户鉴权系统。

<a id="current-boundaries"></a>

## 当前边界

Pantheon v0.2.1 仍是 Alpha 阶段的本地工作区，部署前需要了解以下限制：

- Chat Agent 为同步执行；Multi-role 会按计划顺序执行步骤，而不是并行运行。
- 附件会在支持时转换为文本上下文，并不是通用的多模态模型文件上传。
- 语音输入依赖浏览器 SpeechRecognition，不同浏览器和语言的支持程度不同。
- HTML Preview 使用沙箱，但仍应把生成页面视为不可信内容。
- Plugin Pack 是 Prompt 型扩展，不包含任意可执行插件或插件市场。
- Security 登录锁是本地单用户保护，不是生产级身份管理。

<a id="architecture"></a>

## 架构

```text
                    CLI · Web UI · Python SDK
                              │
                       Pantheon 统一入口
                              │
                  Hermes 路由与任务编排
              ┌───────────────┼────────────────┐
              │               │                │
       Skills / Memory   Plugin 上下文    已授权 MCP 工具
              │               │                │
              └───────────────┼────────────────┘
                              │
       Hephaestus · Athena · Apollo · Chronos
                              │
                    已配置的 LLM Provider

Web 运行时：SSE Activity · Workspace · Preview · Files · Terminal
本地状态：.env · pantheon.yaml · .pantheon/ · 浏览器会话
```

运行时负责路由、角色执行、Memory/Skill 上下文注入、MCP 审批与调用、结果汇总和 SSE 进度事件。详细流程见 [docs/architecture.md](docs/architecture.md)。

## 项目结构

```text
pantheon/
├── cli.py                 # Typer CLI
├── core/
│   ├── pantheon.py        # CLI / Web / SDK 共用入口
│   ├── hermes.py          # 编排与流式事件
│   ├── router.py          # Auto 与 Multi-role 计划
│   ├── extensions.py      # Skills、Plugins 与 MCP
│   ├── memory.py          # SQLite Memory
│   └── scheduler.py       # 持久化 Chronos 任务
├── llm/                   # OpenAI-compatible、Anthropic、Ollama 客户端
├── roles/                 # Hermes、Hephaestus、Athena、Apollo、Chronos
├── skills/                # 6 个内置标准 Skills
└── web/
    ├── app.py             # FastAPI、SSE、Setup、Auth 与本地 API
    └── static/            # Web UI 与神祇头像
```

## 测试

普通使用不需要安装开发依赖：

```bash
python -m pip install -e ".[dev]"
ruff check .
pytest
```

浏览器回归测试使用单独的可选依赖，不会调用模型：

```bash
python -m pip install -e ".[e2e]"
playwright install chromium
pytest e2e --browser chromium
```

真实 Provider 诊断必须显式开启，因为它会发出真实请求，并可能产生极小费用：

```bash
pantheon provider-test --role hermes --live
PANTHEON_LIVE_TEST=1 pytest tests/live -m live
```

GitHub Actions 覆盖 Python 3.10、3.11、3.12，并单独运行 Chromium E2E；
CI 不会获取或测试真实 Provider 密钥。

<a id="documentation"></a>

## 文档

| 文档 | 内容 |
|---|---|
| [安装配置](docs/setup.md) | Provider 配置与常见问题排查 |
| [Web UI 指南](docs/web-ui.md) | Workspace、Memory、Integrations、测试和快捷键 |
| [架构说明](docs/architecture.md) | 路由、执行流程与组件设计 |
| [角色说明](docs/roles/) | 各神祇 Prompt 与职责 |
| [FAQ](docs/faq.md) | 常见配置和行为问题 |
| [Changelog](CHANGELOG.md) | 版本更新记录 |
| [贡献指南](CONTRIBUTING.md) | 开发与贡献流程 |

## Roadmap

- [x] **v0.1**：5 个角色、Hermes 调度、CLI、Web UI 和 SDK
- [x] **v0.2**：多会话工作区、实时 Activity、Chronos、Memory、Skills、MCP、Webhook 和本地登录锁
- [x] **v0.2.1**：自动启动服务、Playwright 回归、Provider smoke test 和 FastAPI lifespan 迁移
- [ ] **v0.3**：原生频道适配器、MCP resources/prompts 和可视化任务编排
- [ ] **v0.4**：可安装扩展目录、语义记忆检索和可观测性
- [ ] **v1.0**：多用户身份、审计日志、限流和分布式执行

## 贡献

欢迎贡献角色、Skills、Integrations、测试、文档和无障碍改进。详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## License

MIT © 2024–2026 RyosukeSAMA
