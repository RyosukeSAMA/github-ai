# Pantheon 中文新手安装指南

[English](setup.md) | **简体中文**

这份指南假设电脑上还没有 Python、Git 或 Pantheon。请从头到尾只选择一种操作系统路径；如果版本检查没有通过，不要跳到后面的步骤。

满足下面四项才算安装完成：

- `pantheon --version` 能显示版本号。
- 浏览器能打开 <http://127.0.0.1:8000/>。
- **Settings → Setup → Test API** 对至少一个 Provider 测试成功。
- New Chat 能收到模型回答，Activity 显示任务完成。

## 一、先选择模型运行方式

Pantheon 本身免费并运行在本机，但模型执行需要以下方式之一：

| 方式 | 需要准备 | 适合用户 |
|---|---|---|
| 云端 Provider | OpenAI、Anthropic 或 DeepSeek 的 API key | 第一次安装最简单 |
| 本地 Ollama | Ollama，以及足够运行所选模型的内存和磁盘 | 希望在本地运行模型的用户 |

普通聊天账号或订阅不一定包含 API。特别是 ChatGPT 订阅不包含 OpenAI API 额度。请在所选 Provider 的官方 API 控制台创建 key，并按需要开通 API 计费。

如果还没有 API key，可以从服务商的官方入口开始：

| Provider | 官方入口 |
|---|---|
| OpenAI | [API 入门指南](https://platform.openai.com/docs/quickstart/make-your-first-api-request) |
| Anthropic | [Claude API key 说明](https://platform.claude.com/docs/en/manage-claude/authentication) |
| DeepSeek | [DeepSeek 开放平台](https://platform.deepseek.com/) |
| Ollama | [官方下载页面](https://ollama.com/download)（本地模型不需要云端 API key） |

创建普通的项目或个人 API key，复制后在第六步的 Pantheon **Settings → Setup** 页面粘贴。计费方式和可用模型取决于对应服务商账户。

第一次只配置一个 Provider 即可。成功运行后，再为不同 Agent 分配不同 Provider。

## 二、确认电脑是否支持

| 系统 | 支持方式 | Python |
|---|---|---|
| macOS 13 或更新版本 | Terminal + Homebrew | 推荐 3.11 或 3.12 |
| Ubuntu 22.04 或 24.04 | 原生终端 | 3.10-3.12 |
| Windows 11 | 原生 PowerShell | 3.11 或 3.12 |
| Windows + WSL2 | 可选 Ubuntu 环境 | 3.10–3.12 |

Pantheon 的 GitHub CI 会在 Ubuntu 上测试 Python 3.10、3.11 和 3.12。Python 3.13 或更新版本可能可以运行，但目前不属于已测试范围。

完成下方对应系统的基础组件准备后，一行安装并启动：

**macOS / Ubuntu：**

```bash
curl -fsSL https://raw.githubusercontent.com/RyosukeSAMA/github-ai/main/scripts/install.sh | bash
```

**Windows 11 原生 PowerShell：**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/RyosukeSAMA/github-ai/main/scripts/install.ps1 | iex"
```

安装后打开新的终端，运行 `pantheon web`，再进入第六节。Windows 无需安装 WSL，也无需执行虚拟环境的激活脚本。默认安装目录是 `%LOCALAPPDATA%\Pantheon\app`；macOS/Ubuntu 为 `~/github-ai`。安装器下载最新稳定 Release，在单独的永久环境中安装并验证依赖，之后切换代码和 `.venv` 入口；不会直接修改失败前的环境。终端启动器加入当前用户 PATH。


## 三、准备操作系统

只执行与你电脑对应的小节。

### macOS 13 或更新版本

1. 从“应用程序 → 实用工具”打开**终端**。
2. 安装 Apple 命令行工具：

   ```bash
   xcode-select --install
   ```

   系统可能弹出安装窗口，请完成安装后再继续。如果系统提示已经安装，可以直接继续。

3. 检查 Homebrew：

   ```bash
   brew --version
   ```

4. 如果提示找不到 `brew`，安装 Homebrew：

   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

   如果安装结束时提示需要把 `brew` 添加到 shell 环境，请复制执行它给出的命令，然后关闭并重新打开终端。

5. 安装 Python 和 Git：

   ```bash
   brew install python@3.12 git
   python3.12 --version
   git --version
   ```

只有 `python3.12` 显示 Python 3.12，并且 Git 显示版本号时，才继续下一步。

### Ubuntu 22.04 或 24.04

1. 打开**终端**。
2. 安装 Git、Python、pip 和虚拟环境组件：

   ```bash
   sudo apt update
   sudo apt install -y git curl python3 python3-venv python3-pip
   python3 --version
   git --version
   ```

只有 Python 显示 3.10-3.12，并且 Git 显示版本号时，才继续下一步。

### Windows 11 原生 PowerShell

打开普通 PowerShell，准备基础组件：

```powershell
winget install --id Git.Git -e --source winget
winget install --id Python.Python.3.12 -e --scope user
```

完成安装提示后，关闭并重新打开 PowerShell，确认：

```powershell
git --version
py -3.12 --version
```

然后执行第二节的 PowerShell 一行安装，打开新窗口后执行 `pantheon --version` 和 `pantheon web`，直接进入第六节。无需 `source .venv/bin/activate`。如果没有 WinGet，可从 [Git for Windows](https://git-scm.com/install/windows) 和 [Python Windows 下载](https://www.python.org/downloads/windows/) 安装相应组件；Python 安装时启用 launcher。

### Windows + WSL2（可选）

此路径仅用于主动选择 WSL 的用户。以下 Linux 命令在 Ubuntu 窗口执行；原生 Windows 用户使用上方 PowerShell 安装即可。

1. 以管理员身份打开 **PowerShell**。
2. 安装 WSL2 和 Ubuntu：

   ```powershell
   wsl --install -d Ubuntu-24.04
   ```

3. 按提示重启 Windows。
4. 从开始菜单打开 **Ubuntu 24.04**，按提示创建 Linux 用户名和密码。输入密码时屏幕不会显示字符，这是正常现象。
5. 在 Ubuntu 窗口中执行：

   ```bash
   sudo apt update
   sudo apt install -y git curl python3 python3-venv python3-pip
   python3 --version
   git --version
   ```

请把项目放在 Linux 主目录，例如 `/home/你的用户名/github-ai`。不要放在 `/mnt/c/...`，否则速度较慢，也更容易遇到文件权限问题。

如果 PowerShell 提示没有 `Ubuntu-24.04`，执行 `wsl --list --online`，从列表中选择 Ubuntu 22.04 或 24.04。Windows 安装错误可参照 [Microsoft 的 WSL 安装指南](https://learn.microsoft.com/en-us/windows/wsl/install)。

## 四、下载并安装 Pantheon

本节是 macOS、Ubuntu 和 WSL 的手动源码安装。使用一行安装的用户已完成依赖配置，直接进入第五节。

1. 回到用户主目录并下载项目：

   ```bash
   cd ~
   git clone https://github.com/RyosukeSAMA/github-ai.git
   cd github-ai
   ```

2. 创建独立 Python 环境。

   macOS 用户执行：

   ```bash
   python3.12 -m venv .venv
   ```

   Ubuntu 或 WSL 用户执行：

   ```bash
   python3 -m venv .venv
   ```

   然后进入虚拟环境：

   ```bash
   source .venv/bin/activate
   ```

   命令提示符前面应该出现 `(.venv)`。这表示 Pantheon 的依赖与电脑上其他 Python 项目相互隔离。

3. 安装 Pantheon：

   ```bash
   python -m pip install --upgrade pip
   python -m pip install -e .
   pantheon --version
   ```

预期结果：

```text
pantheon 0.3.1
```

显示更高版本也正常。不要使用 `sudo pip install`。

## 五、启动 Web UI

一行安装用户打开新终端即可；手动源码安装用户保持 `(.venv)`，执行：

```bash
pantheon web
```

启动成功时会出现类似内容：

```text
Uvicorn running on http://127.0.0.1:8000
```

保持这个终端窗口打开。使用最新版 Chrome、Edge、Firefox 或 Safari 打开 <http://127.0.0.1:8000/>。

`127.0.0.1` 表示只有当前电脑可以访问 Pantheon。第一次安装时不要把 Host 改成 `0.0.0.0`。

## 六、配置连接并分配角色模型

1. 打开 **Settings → Setup**，选择 DeepSeek、OpenAI、Anthropic，或本机已运行的 Ollama。
2. 填写该供应商的 API key，保留官方 Base URL，选择用于连接测试的模型。
3. 点击 **Test API**，确认出现 **API connected**。测试会发送一次短请求，可能产生少量费用，验证结果绑定这组密钥、地址和模型。
4. 选择私有 `.env` 或可用的 **System credential storage**，点击 **Save provider connection**。这一步不会改变任何角色模型，也不会再次调用 API。
5. 打开 **Models → New chat defaults**。在 **Use one model for all AI roles** 中选择同一供应商和模型，点击 **Apply to all AI roles → Save new chat defaults**。
6. 创建 **New Chat**，四个 AI 角色就可共用这一家连接，Chronos 不需要模型。

多家混用是可选功能，不要求拥有三家密钥。分别在 Setup 添加连接，再在 Models 逐个角色选择供应商和模型即可。**Current chat only** 自动保存当前聊天的选择；**New chat defaults** 需要显式保存，只影响以后创建的聊天，旧聊天保留自己的模型。角色技能不与供应商绑定。费用主要取决于模型价格、token 数和调用次数，可以在 Info 查看用量和设置预算。

每个角色有 **Test this role**，用来验证所选模型。测试一个模型不代表该供应商所有模型都可用。验证结果有效期为 24 小时，模型列表提醒与验证结果分别显示。**Check setup** 仅检查本地配置。

Setup 底部显示实际配置和凭据路径。旧源码安装继续使用项目 `.env` 和 `config/pantheon.yaml`；新工作区默认使用系统用户数据目录。系统凭据选项使用受支持的 OS 密钥环，`pantheon credentials --migrate` 可显式迁移已保存的 API key 和平台 token。迁移先保存并核验，再移除文件中的原值。不要把密钥粘贴到 GitHub Issue、截图或聊天消息中。

如果 Test API 失败，先不要保存，请查看下面与错误对应的排错步骤。

## 七、完成第一个任务

1. 点击 **New Chat**。
2. 保持 **Auto** 模式。
3. 发送：

   ```text
   写一个 Python hello world 示例，并说明如何运行。
   ```

出现以下结果代表安装成功：

- 页面显示模型回答；
- Activity 显示 Hermes 和执行任务的 Agent；
- 任务正常完成，没有 API 错误。

在终端按 `Control-C` 可以停止 Pantheon。

## 八、以后再次启动 Pantheon

打开终端；Windows 用户打开 Ubuntu，然后执行：

```bash
cd ~/github-ai
source .venv/bin/activate
pantheon web
```

再打开 <http://127.0.0.1:8000/>。如果之前把项目下载到其他目录，请在 `cd` 后使用实际路径。

## 九、可选：登录电脑后自动启动

先确认手动启动和首次任务已经成功。然后 macOS 和原生 Linux 用户可以执行：

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

服务使用选定工作区和当前安装。macOS 使用 LaunchAgent，Linux 使用 user systemd，Windows 使用当前用户 Startup 快捷方式与 windowless runner，不需要管理员权限。Windows 的后台任务在登录后运行；WSL 需要启用 systemd 才使用后台服务。先停止手动运行的 Web，再安装服务，避免同一工作区重复启动。

## 十、可选：使用 Ollama，不配置云端 API key

1. 从 [Ollama 官方网站](https://ollama.com/download)安装并启动 Ollama。WSL 用户应在运行 Pantheon 的同一个 Ubuntu 环境中安装 Linux 版 Ollama。
2. 下载模型：

   ```bash
   ollama pull llama3.1
   ollama list
   ```

3. 启动 Pantheon，打开 **Settings → Setup**。
4. 选择 **Ollama**，保留 `http://localhost:11434` 作为 Base URL。
5. 选择或输入 `ollama list` 显示的模型 ID。
6. 点击 **Test API → Save provider connection**。在 **Models → New chat defaults** 选择 Ollama 和已下载的模型，点击 **Apply to all AI roles → Save new chat defaults**，然后新建聊天。

Ollama 模型可能需要下载数 GB 文件，运行速度取决于模型大小和电脑硬件。

## 十一、更新 Pantheon

等待任务完成，停止手动运行的 Web，然后执行：

```text
pantheon update
pantheon update --rollback
```

第二条仅在确实需要恢复上一安装时使用。更新器先下载并校验新环境，再离线备份本地数据并切换；属于当前安装的后台服务会暂停并重启。新服务启动或健康检查失败时会恢复旧代码与环境。存在未提交源码或运行中任务时会拒绝切换。配置和最新工作区数据保留；回退只切换程序版本，不会自动恢复旧数据格式。若跨越不兼容的数据格式版本，请使用离线备份恢复，并保留原始数据。

旧版本没有 `update` 命令时，macOS/Ubuntu 使用：

```bash
curl -fsSL https://raw.githubusercontent.com/RyosukeSAMA/github-ai/main/scripts/install.sh | PANTHEON_UPDATE=1 bash
```

Windows 使用原生安装命令前设置 `$env:PANTHEON_UPDATE='1'`。开发分支源码安装可继续使用 `git pull --ff-only` 与 `python -m pip install -e .`；不应对含未提交修改的源码运行发布版更新器。

Web 约每六小时检查 GitHub 正式 Release，有新版时显示升级提示。Settings → Info 提供手动检查、Release 链接和 `pantheon update` 提示。仅合并代码、没有发布 Release 时不会提示；页面不会在后台自动安装版本。

`pantheon doctor` 显示实际工作区、状态、配置与凭据路径。`pantheon backup export /path/to/backup.zip` 导出离线工作区备份（先停止服务并等待 CLI 任务完成）；`pantheon backup restore /path/to/backup.zip` 恢复并保留回退副本。系统钥匙串中的密钥不包含在普通备份中，换电脑需重新配置。Info 页的 Export backup/Import backup 导出的是会话 JSON，不等同于完整工作区备份。

Settings → Info 的 API usage 显示服务商报告的 token。Budgets 设置每任务、24 小时请求数和输出 token 限制；0 表示不限。填写当前模型单价后可限制本地费用估算；未定价调用显示未知，不冒充账单。CLI 使用 `pantheon budgets`，SDK 使用 `p.services.budget`。

## 十二、常见问题排查

### `python3: command not found`

返回“准备操作系统”一节安装 Python。安装后关闭并重新打开终端。macOS 执行 `python3.12 --version`，Ubuntu 或 WSL 执行 `python3 --version`。

### Python 版本低于 3.10

不要继续使用这个 Python。macOS 执行 `brew install python@3.12`。Ubuntu 请使用 22.04/24.04，或先安装受支持的 Python，再创建 `.venv`。

### Ubuntu 提示 `No module named venv` 或无法创建虚拟环境

```bash
sudo apt update
sudo apt install -y python3-venv
python3 -m venv .venv
```

### `source: no such file or directory: .venv/bin/activate`

确认当前位于项目目录。macOS 使用：

```bash
cd ~/github-ai
python3.12 -m venv .venv
source .venv/bin/activate
```

Ubuntu 或 WSL 使用：

```bash
cd ~/github-ai
python3 -m venv .venv
source .venv/bin/activate
```

### `pantheon: command not found`

重新进入虚拟环境并安装：

```bash
cd ~/github-ai
source .venv/bin/activate
python -m pip install -e .
pantheon --version
```

### 端口 8000 已被占用

换一个端口启动：

```bash
pantheon web --port 8001
```

然后打开 <http://127.0.0.1:8001/>。

### 浏览器无法打开 Pantheon

确认启动 Pantheon 的终端仍在运行，并且没有显示 traceback。使用 Uvicorn 实际打印的 URL。新版 Windows 通常会自动转发 WSL 的 `127.0.0.1`；如果没有，在 PowerShell 中执行 `wsl --shutdown`，重新打开 Ubuntu，再启动 Pantheon。

### 出现 `401`、`authentication` 或 `invalid API key`

API key 缺失、过期、复制不完整，或者属于其他 Provider。到当前所选 Provider 的官方 API 控制台重新创建 key，粘贴后再次运行 **Test API**。普通聊天订阅不是 API key。

### 出现 `404` 或 `model not found`

当前账户无法使用该模型，或者模型与 Provider 不匹配。点击 **Refresh models**，选择可用模型，再运行 **Test API**。除非有意使用兼容网关，否则不要修改官方 Base URL。

### 出现 `429`、rate limit 或 quota 错误

Provider 因为账户额度、计费或频率限制拒绝请求。检查该 Provider 的 API 控制台，或者选择另一个已配置 Provider。

### Web UI 可以打开，但任务提示其他 Agent 没有 key

Setup 需要配置所有启用的聊天 Agent，或者禁用不使用的角色。返回 **Settings → Setup**，检查 Agent 状态列表，为所有启用角色保存能够使用的 Provider 和模型。

### 重置本地配置

先停止 Pantheon，并备份文件。然后重命名配置：

```bash
cd ~/github-ai
mv .env .env.backup 2>/dev/null || true
mv config/pantheon.yaml config/pantheon.yaml.backup 2>/dev/null || true
pantheon web
```

打开 Setup，重新配置 Provider。

### 收集可用的诊断信息

在 Web UI 打开 **Settings → Info → Copy diagnostics**。它会隐藏已保存 API key。使用后台服务时可以运行 `pantheon service logs`。

问题仍未解决时，可以创建 GitHub Issue，并提供操作系统、`python3 --version`、`pantheon --version`、失败命令和去除敏感信息后的错误。不要提供 API key。

## 十三、卸载

先停止并卸载可选后台服务：

```bash
cd ~/github-ai
source .venv/bin/activate
pantheon service uninstall
```

如果需要保留设置、定时任务或 Memory，请先备份 `.env`、`config/pantheon.yaml` 和 `.pantheon/`。然后离开项目目录，通过文件管理器删除 `github-ai` 文件夹。删除项目目录也会删除其中的虚拟环境和本地 Pantheon 数据。

## 十四、高级手动配置

新手推荐使用浏览器 Setup。需要手动配置时执行：

```bash
cd ~/github-ai
cp .env.example .env
cp config/pantheon.example.yaml config/pantheon.yaml
```

在 `.env` 中填写 key，然后在 `config/pantheon.yaml` 中设置匹配的 Provider、模型和 Base URL。不要提交这两个文件。

Pantheon 会在后台刷新已配置的官方模型目录，并把结果缓存在 `.pantheon/model_catalog.json`。成功刷新后，模型菜单只显示该 API key 的模型列表返回的模型。若已保存的模型未出现在列表中，它仍会保留并显示提示，方便你测试或手动更换；刷新不会自动改写已保存的配置。仅出现在模型列表中不代表生成请求一定成功，选择新模型后请先点击 **Test API**。如果刷新失败，Pantheon 会保留缓存列表或内置推荐项。

默认在启动时同步，然后每小时更新官方 API 账号目录，失败时每五分钟重试；已打开的网页每分钟及回到前台时同步下拉框。即使没有 OpenAI、Anthropic 密钥，官方公开文档推荐项也会每六小时更新。这些推荐项不表示账号已有调用权限；添加对应 API key 后才会查询账号目录。设置区会显示更新时间及失败状态。需要离线运行时可以设置 `PANTHEON_MODEL_DOCS_SYNC=0`，关闭公开文档同步。

## 十五、贡献者安装

普通用户只需要安装 `-e .`。参与开发时再安装开发或浏览器测试依赖：

```bash
python -m pip install -e ".[dev]"
python -m pip install -e ".[e2e]"
playwright install chromium
pytest
pytest e2e --browser chromium
```

普通自动化测试使用 Mock Client，不需要 API key。实时 Provider 诊断需要用户主动开启，并可能产生 Provider 费用。

### 远程访问与终端权限

先在本机启动并开启 **Settings → Security**，再使用 `--host 0.0.0.0`。未配置登录时，远程绑定会拒绝启动。通过 `PANTHEON_ALLOWED_HOSTS` 设置浏览器访问使用的 IP 或域名，多个值用逗号分隔；跨来源 UI 请求会被拒绝。远程终端默认关闭，确有需要时在启动前设置 `PANTHEON_TERMINAL_ENABLED=true`；本机也可设置为 `false` 禁用。修改这些服务设置后需重启。

停止 Web 任务后，不会再启动后续角色、工具或汇总。供应商已接受的同步模型请求可能继续完成并计费。模型请求超时为 120 秒，预算管理下关闭 SDK 内部重试；Web 任务总执行预算为 10 分钟。计划最多八步，可配置有限恢复；长上下文按来源摘要，失败时明确使用节选，大任务可拆成多个请求。


安装后可继续阅读[媒体、预算和任务恢复](workflows.zh-CN.md)及[聊天平台配置](channels.zh-CN.md)。
