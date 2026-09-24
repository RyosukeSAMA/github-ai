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
| Windows 11 | WSL2 + Ubuntu 22.04/24.04 | 使用 Ubuntu 的 Python |
| Windows 原生 PowerShell | 当前不支持 | — |

Pantheon 的 GitHub CI 会在 Ubuntu 上测试 Python 3.10、3.11 和 3.12。Python 3.13 或更新版本可能可以运行，但目前不属于已测试范围。

如果已经安装 Git、`curl`、受支持的 Python 和 `venv`，可以在 macOS、Ubuntu 或 WSL Ubuntu 中使用[一行安装脚本](../scripts/install.sh)：

```bash
curl -fsSL https://raw.githubusercontent.com/RyosukeSAMA/github-ai/main/scripts/install.sh | bash
cd ~/github-ai && .venv/bin/pantheon web
```

第一行在新的 `~/github-ai` 目录中安装，第二行启动 Pantheon。脚本不会覆盖已有目录，也不会自动安装系统软件。Windows 用户先完成第三节的 WSL2 和 Ubuntu 准备，再在 Ubuntu 中执行；也可以在 PowerShell 中运行 `wsl -d Ubuntu-24.04 -- bash -lc "curl -fsSL https://raw.githubusercontent.com/RyosukeSAMA/github-ai/main/scripts/install.sh | bash"`。Pantheon 仍在 WSL 中运行。之后跳到第六节配置 Provider。如果提示缺少依赖，请先按下方第三至第五节补齐。

如果使用云端 Provider，4 GB 内存和约 1 GB 可用磁盘通常足够运行 Pantheon 及其 Python 环境。本地 Ollama 需要更多内存和磁盘，具体取决于下载的模型。

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

### Windows 11 + WSL2

Pantheon 当前在 Windows 上使用 Linux 命令。后面的安装命令不要在 PowerShell 中执行。

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

macOS、Ubuntu 和 Windows 的 Ubuntu 窗口都执行相同命令。

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
pantheon 0.2.1
```

显示更高版本也正常。不要使用 `sudo pip install`。

## 五、启动 Web UI

确认终端仍显示 `(.venv)`，然后执行：

```bash
pantheon web
```

启动成功时会出现类似内容：

```text
Uvicorn running on http://127.0.0.1:8000
```

保持这个终端窗口打开。使用最新版 Chrome、Edge、Firefox 或 Safari 打开 <http://127.0.0.1:8000/>。

`127.0.0.1` 表示只有当前电脑可以访问 Pantheon。第一次安装时不要把 Host 改成 `0.0.0.0`。

## 六、在浏览器中配置一个 Provider

1. 打开 **Settings**。
2. 打开 **Setup**。
3. 选择你拥有 API key 的 Provider：DeepSeek、OpenAI 或 Anthropic。只有本机已经运行 Ollama 时才选择 Ollama。
4. 保留 Pantheon 显示的官方 Base URL。
5. 粘贴从该 Provider 官方 API 控制台创建的 API key。
6. 选择一个模型。
   首次配置请保持 **Use this model for all chat agents** 已勾选。
7. 点击 **Test API**。它会检查表单中当前填写的内容，并发送一次很小的真实请求，可能产生少量 Provider 费用。
8. 测试成功后点击 **Save local config**。
9. 点击 **Check setup**。它会检查已经保存到本地的配置；确认所有已启用 Agent 均已就绪。

Pantheon 会把 key 保存在项目本地 `.env` 文件，把 Provider 和模型设置保存在 `config/pantheon.yaml`。Git 会忽略这两个文件。不要把 API key 粘贴到 GitHub Issue、截图或聊天消息中。

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

服务使用当前项目目录和虚拟环境。macOS 使用当前用户的 LaunchAgent，Linux 使用 user systemd。WSL 用户应继续手动启动，除非 WSL 已经启用 systemd。

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
6. 保持 **Use this model for all chat agents** 已勾选。依次点击 **Test API**、**Save local config**、**Check setup**。最后一次检查应显示所有已启用 Agent 均已就绪。

Ollama 模型可能需要下载数 GB 文件，运行速度取决于模型大小和电脑硬件。

## 十一、更新 Pantheon

先在终端按 `Control-C` 停止 Pantheon，然后执行：

```bash
cd ~/github-ai
source .venv/bin/activate
git pull --ff-only
python -m pip install -e .
pantheon --version
```

如果更新涉及后端配置，更新后重新执行 `pantheon web`。

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

在 Web UI 打开 **Settings → Support → Copy diagnostics**。它会隐藏已保存 API key。使用后台服务时可以运行 `pantheon service logs`。

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
