# 🏛️ Pantheon

> **A multi-AI-role collaboration framework.** Each god has a specialty; Hermes orchestrates.

<div align="center">

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org)
[![CI](https://github.com/RyosukeSAMA/github-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/RyosukeSAMA/github-ai/actions)
[![Status](https://img.shields.io/badge/status-alpha-yellow)]()
[![GitHub release](https://img.shields.io/github/v/release/RyosukeSAMA/github-ai)](https://github.com/RyosukeSAMA/github-ai/releases)
[![GitHub stars](https://img.shields.io/github/stars/RyosukeSAMA/github-ai)](https://github.com/RyosukeSAMA/github-ai/stargazers)

[角色一览](#-角色一览) · [快速开始](#-快速开始) · [架构](docs/architecture.md) · [贡献](CONTRIBUTING.md)

</div>

---

## ✨ 它能做什么

把"找一个 AI 干活"变成"调用一支虚拟团队"：

- 🔨 **专业化分工**：写代码、调研、出图、定时任务——每个角色用最擅长的模型和工具
- 📨 **智能调度**：Hermes 主神理解你的任务，自动决定派给谁
- 🧩 **多角色协作**：复杂任务会被拆解，多个角色依次执行，最后汇总
- 🧰 **真实工作区**：在 Web UI 中查看实时 Activity、预览 HTML、管理文件并运行终端命令
- 🧠 **可控扩展**：本地长期记忆、标准 Skills、MCP 工具审批、Plugin prompt packs 与 Webhook
- 🎯 **三种入口**：命令行、Web UI、Python SDK，随你挑
- 🔌 **可扩展**：新增一个角色只需要写一个 Python 文件 + 在 YAML 注册

## 👥 角色一览

| 角色 | 神祇 | 职责 | 默认模型 | 工具 |
|------|------|------|----------|------|
| 📨 **Hermes** | 信使之神 | 总协调、任务理解、结果汇总 | Claude Opus 4.8 | 调度 |
| 🔨 **Hephaestus** | 锻造之神 | 写代码、改 bug、重构 | Claude Sonnet 4.6 | terminal, file, patch |
| 🦉 **Athena** | 智慧之神 | 联网调研、文献综述、问答 | GPT-5.5 | web_search, web_extract |
| 🎵 **Apollo** | 光明/艺术之神 | 出图、视频、音乐 | GPT-5.4 mini | image_gen, video_gen, tts |
| ⏰ **Chronos** | 时间之神 | 定时任务、周期执行 | (无 LLM) | cronjob |

📖 每个角色的详细设定见 [`docs/roles/`](docs/roles/)。

## 🚀 快速开始

### 安装

```bash
git clone https://github.com/RyosukeSAMA/github-ai.git
cd github-ai
pip install -e ".[dev]"
```

### 配置

方式 A：用 Web UI 配置（推荐新手）

```bash
pantheon web
```

打开 `http://127.0.0.1:8000/`，进入 `Settings → Setup`：

- 选择 DeepSeek / OpenAI / Anthropic / Ollama
- 填入默认模型和 API key
- 点击 `Save local config`

Web UI 会把 API key 写入本地 `.env`，把 provider、base URL、模型写入 `config/pantheon.yaml`。

方式 B：手动配置文件

```bash
# 1. 复制配置模板
cp config/pantheon.example.yaml config/pantheon.yaml

# 2. 复制环境变量模板并填入 API key
cp .env.example .env
# 编辑 .env，填入你的 API key（DEEPSEEK_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY）
```

### 🎭 默认配置展示（理想样貌）

`pantheon.example.yaml` 展示的是**理想配置**——每个神用各自最合适的模型：

| 角色 | 任务 | 示例模型 |
|------|------|----------|
| 📨 Hermes | 调度/规划 | `claude-opus-4-8` |
| 🔨 Hephaestus | 写代码 | `claude-sonnet-4-6` |
| 🦉 Athena | 调研 | `gpt-5.5` |
| 🎵 Apollo | 创意/表达 | `gpt-5.4-mini` |
| ⏰ Chronos | 定时 | (无 LLM) |

**但你需要根据自己持有的 API key 修改**。常见快速方案（只用一家）：

- **只用 DeepSeek**（推荐入门）：把所有 `provider: openai` + `model: deepseek-v4-flash`，加 `base_url: https://api.deepseek.com`
- **只用 OpenAI**：把模型都改成 `gpt-5.5`，用 OpenAI key
- **只用 Anthropic**：把模型都改成 `claude-sonnet-4-6`，用 Anthropic key
- **只用 Ollama**（完全免费）：本地跑 `llama3.1`，见 [`docs/setup.md`](docs/setup.md)

### 三种用法

**命令行（CLI）**

```bash
# 单角色模式：把任务派给指定角色
pantheon ask --role hephaestus "写一个 Python 快速排序"

# 自动模式：让 Hermes 决定派给谁
pantheon ask "调研 2025 年 LLM 发展趋势"

# 多角色协作：强制串行多步
pantheon ask --multi "调研 LLM 趋势并出一份报告（含图表）"

# 查看并显式使用标准 Skill
pantheon skills
pantheon ask --skill fix-and-verify "修复空值错误并给出验证结果"

# 启动 Web UI
pantheon web
# 然后访问 http://127.0.0.1:8000
```

**Python SDK**

```python
from pantheon import Pantheon

p = Pantheon()

# 自动派单
result = p.ask("写一个装饰器")
print(result["content"])

# 指定角色
result = p.ask("写代码", mode="role:hephaestus")
print(result["content"])

# 多角色协作
result = p.ask("调研趋势并出报告", mode="multi")
for step in result["steps"]:
    print(f"[{step.role}] {step.content}")

# 显式使用一个内置或本地 Skill
result = p.ask("修复空值错误并验证", skill="fix-and-verify")
print(result["skill_matches"])
```

**Web UI**

```bash
pantheon web
```

打开浏览器访问 `http://127.0.0.1:8000`，会有一个聊天界面：左侧角色列表，右侧对话窗口。输入 `/` 可以选择命令；输入 `/skill <id> <任务>`，或在 `Settings -> Integrations -> Skills` 点击 `Use`，可以显式调用工作流。

Web UI 的 Workspace、Preview、Files、Terminal、会话模式切换和测试说明见 [`docs/web-ui.md`](docs/web-ui.md)。

> [!IMPORTANT]
> Web UI 内含文件写入和终端执行能力。默认只监听 `127.0.0.1`；如果改用
> `0.0.0.0` 或对外暴露端口，请先在 `Settings -> Security` 开启本地登录锁，
> 并使用防火墙或反向代理限制访问。

## 🏛️ 架构总览

```
┌──────────────────────────────────────────────────┐
│              用户交互层（3 入口共享逻辑）           │
├──────────────────────────────────────────────────┤
│   CLI (Typer)   │   Web UI (FastAPI)   │   SDK   │
└────────┬────────┴──────────┬───────────┴────┬────┘
         └───────────────────┼─────────────────┘
                  ┌─────────▼─────────┐
                  │ Pantheon (统一门面) │
                  └─────────┬─────────┘
                  ┌─────────▼─────────┐
                  │ Hermes (主协调器)  │
                  │ - 任务理解          │
                  │ - Skill 选择         │
                  │ - 角色选派          │
                  │ - 多步编排          │
                  │ - 结果汇总          │
                  └─────────┬─────────┘
        ┌──────────┬────────┼────────┬──────────┐
        ▼          ▼        ▼        ▼          ▼
     🔨 Hephae  🦉 Athena 🎵 Apollo ⏰ Chronos  ...
        │          │        │        │
        └──────────┴────────┴────────┘
                  │
       ┌──────────▼──────────┐
       │ LLM 适配层          │
       │ (OpenAI/Anthropic/  │
       │  Ollama)            │
       └─────────────────────┘
```

完整架构说明见 [`docs/architecture.md`](docs/architecture.md)。

## 🛠 自定义 / 新增角色

1. 在 `pantheon/roles/` 下新建 `<name>.py`：

```python
from pantheon.core.base import Role

class Ares(Role):
    name = "ares"
    description = "Security auditor god"
    system_prompt = """You are a security expert..."""
    # 在 pantheon.yaml 里覆盖 model/tools
```

2. 在 `config/pantheon.yaml` 注册：

```yaml
pantheon:
  roles:
    ares:
      model: claude-sonnet-4-6
      provider: anthropic
      tools: [terminal, file]
```

3. 在 `pantheon/roles/__init__.py` 导出。

## 📦 项目结构

```
github-ai/
├── README.md
├── LICENSE                       # MIT
├── CONTRIBUTING.md
├── pyproject.toml
├── requirements.txt
├── .gitignore
├── .env.example
│
├── pantheon/                     # 核心代码包
│   ├── __init__.py
│   ├── sdk.py                    # Python SDK
│   ├── cli.py                    # CLI (Typer)
│   ├── core/                     # 调度核心
│   │   ├── pantheon.py
│   │   ├── hermes.py
│   │   ├── router.py
│   │   ├── base.py
│   │   ├── extensions.py        # Skills / Plugins / MCP
│   │   ├── memory.py            # 本地长期记忆
│   │   └── scheduler.py         # Chronos 持久化任务
│   ├── llm/                      # LLM 适配层
│   │   ├── base.py
│   │   ├── openai_client.py
│   │   ├── anthropic_client.py
│   │   └── ollama_client.py
│   ├── roles/                    # 各角色
│   │   ├── hermes.py
│   │   ├── hephaestus.py
│   │   ├── athena.py
│   │   ├── apollo.py
│   │   └── chronos.py
│   ├── skills/                   # 内置标准 SKILL.md 工作流
│   └── web/
│       ├── app.py                # FastAPI + SSE + 本地 API
│       └── static/               # HTML / CSS / JS / 神祇头像
│
├── config/
│   └── pantheon.example.yaml     # 配置模板
│
├── docs/                         # 文档
│   ├── architecture.md
│   ├── setup.md
│   ├── web-ui.md
│   ├── faq.md
│   └── roles/
│       ├── hermes.md
│       ├── hephaestus.md
│       ├── athena.md
│       ├── apollo.md
│       └── chronos.md
│
├── tests/                        # 测试
│   ├── test_hermes.py
│   ├── test_memory.py
│   ├── test_scheduler.py
│   └── test_web_*.py
│
└── .github/
    └── workflows/
        └── ci.yml                # CI
```

## 🧪 测试

```bash
pytest                          # 跑全部测试
pytest --cov=pantheon           # 带覆盖率
pytest tests/test_hermes.py     # 单个文件
```

## 📖 文档导航

| 文档 | 内容 |
|------|------|
| [docs/setup.md](docs/setup.md) | 详细安装配置手册、踩坑记录 |
| [docs/architecture.md](docs/architecture.md) | 架构设计、调度逻辑详解 |
| [docs/web-ui.md](docs/web-ui.md) | Web UI、Workspace、Memory 与 Integrations 使用说明 |
| [docs/faq.md](docs/faq.md) | 常见问题 |
| [docs/roles/](docs/roles/) | 每个角色的详细人设 |
| [CHANGELOG.md](CHANGELOG.md) | 版本更新记录 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 贡献指南 |

## 🗺 Roadmap

- [x] v0.1：5 个基础角色 + Hermes 调度 + CLI/Web/SDK
- [x] v0.2：多会话 Web 工作区、实时协作进度、Chronos、Memory、Skills、MCP、Webhook 与本地登录锁
- [ ] v0.3：第三方频道适配、MCP resources/prompts 与可视化任务编排
- [ ] v0.4：可安装扩展市场、语义记忆检索与可观测性
- [ ] v1.0：多用户鉴权、审计、限流与分布式执行

## 🤝 贡献

欢迎贡献角色、修复 bug、改进文档。详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 📄 许可证

MIT © 2024 RyosukeSAMA
