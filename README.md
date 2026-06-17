# 🏛️ Pantheon

> **A multi-AI-role collaboration framework.** Each god has a specialty; Hermes orchestrates.

<div align="center">

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org)
[![CI](https://img.shields.io/badge/CI-passing-brightgreen)](.github/workflows/ci.yml)
[![Status](https://img.shields.io/badge/status-alpha-yellow)]()

[角色一览](#-角色一览) · [快速开始](#-快速开始) · [架构](docs/architecture.md) · [贡献](CONTRIBUTING.md)

</div>

---

## ✨ 它能做什么

把"找一个 AI 干活"变成"调用一支虚拟团队"：

- 🔨 **专业化分工**：写代码、调研、出图、定时任务——每个角色用最擅长的模型和工具
- 📨 **智能调度**：Hermes 主神理解你的任务，自动决定派给谁
- 🧩 **多角色协作**：复杂任务会被拆解，多个角色依次执行，最后汇总
- 🎯 **三种入口**：命令行、Web UI、Python SDK，随你挑
- 🔌 **可扩展**：新增一个角色只需要写一个 Python 文件 + 在 YAML 注册

## 👥 角色一览

| 角色 | 神祇 | 职责 | 默认模型 | 工具 |
|------|------|------|----------|------|
| 📨 **Hermes** | 信使之神 | 总协调、任务理解、结果汇总 | Claude Sonnet | 调度 |
| 🔨 **Hephaestus** | 锻造之神 | 写代码、改 bug、重构 | Claude Sonnet | terminal, file, patch |
| 🦉 **Athena** | 智慧之神 | 联网调研、文献综述、问答 | GPT-4o | web_search, web_extract |
| 🎵 **Apollo** | 光明/艺术之神 | 出图、视频、音乐 | GPT-4o | image_gen, video_gen, tts |
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

```bash
# 1. 复制配置模板
cp config/pantheon.example.yaml config/pantheon.yaml

# 2. 复制环境变量模板并填入 API key
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY 和 ANTHROPIC_API_KEY
```

### 三种用法

**命令行（CLI）**

```bash
# 单角色模式：把任务派给指定角色
pantheon ask --role hephaestus "写一个 Python 快速排序"

# 自动模式：让 Hermes 决定派给谁
pantheon ask "调研 2025 年 LLM 发展趋势"

# 多角色协作：强制串行多步
pantheon ask --multi "调研 LLM 趋势并出一份报告（含图表）"

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
    print(f"[{step['role']}] {step['result']}")
print("---")
print(result["summary"])
```

**Web UI**

```bash
pantheon web
```

打开浏览器访问 `http://127.0.0.1:8000`，会有一个聊天界面：左侧角色列表，右侧对话窗口。

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
      model: claude-sonnet-4-20250514
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
│   ├── web.py                    # Web UI (FastAPI)
│   ├── core/                     # 调度核心
│   │   ├── pantheon.py
│   │   ├── hermes.py
│   │   ├── router.py
│   │   └── base.py
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
│   └── web/static/               # Web 资源
│
├── config/
│   └── pantheon.example.yaml     # 配置模板
│
├── docs/                         # 文档
│   ├── architecture.md
│   ├── setup.md
│   ├── faq.md
│   └── roles/
│       ├── hermes.md
│       ├── hephaestus.md
│       ├── athena.md
│       ├── apollo.md
│       └── chronos.md
│
├── tests/                        # 测试
│   ├── test_pantheon.py
│   ├── test_hermes.py
│   └── test_roles.py
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
| [docs/faq.md](docs/faq.md) | 常见问题 |
| [docs/roles/](docs/roles/) | 每个角色的详细人设 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 贡献指南 |

## 🗺 Roadmap

- [x] v0.1：5 个基础角色 + Hermes 调度 + CLI/Web/SDK
- [ ] v0.2：增加消息总线，支持角色间异步通信
- [ ] v0.3：可视化编排（拖拽定义多角色流程）
- [ ] v0.4：工具市场（社区贡献工具）
- [ ] v1.0：生产级特性（鉴权、监控、分布式）

## 🤝 贡献

欢迎贡献角色、修复 bug、改进文档。详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 📄 许可证

MIT © 2024 RyosukeSAMA
