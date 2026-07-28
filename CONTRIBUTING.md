# Contributing to Pantheon

感谢你有兴趣为 Pantheon 做贡献！这是一份简明的贡献指南。

## 🚀 快速开始

1. **Fork** 本仓库
2. **Clone** 你的 fork：
   ```bash
   git clone https://github.com/<your-github-username>/github-ai.git
   cd github-ai
   git remote add upstream https://github.com/RyosukeSAMA/github-ai.git
   ```
3. **创建虚拟环境并安装开发依赖**：
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install -e ".[dev]"
   ```
4. **从最新 `main` 创建分支**：
   ```bash
   git fetch upstream
   git checkout -b feat/your-feature upstream/main
   ```
5. **改代码 + 写测试**
6. **运行发布前检查**：
   ```bash
   ruff check .
   pytest
   node --check pantheon/web/static/app.js
   ```
7. **提交**（用 Conventional Commits）：
   ```bash
   git commit -m "feat: add Prometheus role for monitoring"
   ```
8. **推上去 + 提 PR**：
   ```bash
   git push origin feat/your-feature
   ```

## 🛠 贡献方式

### A. 新增一个角色 🏛️

这是最有价值的贡献。要新增一个角色（如 Ares、Aphrodite）：

1. 在 `pantheon/roles/` 下创建 `<name>.py`
2. 继承 `Role` 基类（见 `pantheon/core/base.py`）
3. 在 `pantheon/roles/__init__.py` 注册内置角色
4. 在 `config/pantheon.example.yaml` 添加示例配置
5. 在 `docs/roles/<name>.md` 写角色设定文档
6. 在 `tests/test_roles.py` 加测试

### B. 改进调度逻辑

`pantheon/core/hermes.py` 和 `pantheon/core/router.py` 是核心调度逻辑，欢迎优化：

- 更好的任务拆解
- 更智能的角色选择
- 更可靠的多步编排
- 错误恢复 / 重试机制

### C. 新增 LLM 适配器

要支持新的 LLM 提供商（如 Cohere、Mistral）：

1. 在 `pantheon/llm/` 下实现 `<provider>_client.py`
2. 继承 `BaseLLMClient`
3. 在 `pantheon/llm/__init__.py` 注册
4. 为错误处理、默认模型和自定义 Base URL 添加测试

### D. 修 bug / 改进文档

直接 PR 即可。

## 📋 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/)：

- `feat:` 新功能
- `fix:` 修 bug
- `docs:` 文档
- `refactor:` 重构（无新功能/修复）
- `test:` 加测试
- `chore:` 构建/工具/CI 改动

## ✅ 提交前检查清单

- [ ] `ruff check .` 无错误
- [ ] `pytest` 全部通过
- [ ] 修改 JavaScript 时，`node --check pantheon/web/static/app.js` 通过
- [ ] 新功能加了测试
- [ ] 公共 API 加了 docstring
- [ ] README/文档更新了（如有需要）
- [ ] 没有提交 `.env`、API Key、Token 或本地 `config/pantheon.yaml`

## 🤝 行为准则

- 友善、专业、包容
- 欢迎新手提问
- 拒绝任何形式的骚扰

## 💬 提问 / 讨论

- 提 [Issue](https://github.com/RyosukeSAMA/github-ai/issues)
- 或开 [Discussion](https://github.com/RyosukeSAMA/github-ai/discussions)

---

再次感谢 🙏
