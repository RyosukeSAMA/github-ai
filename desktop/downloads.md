# Download and install Pantheon Desktop

Desktop is a separate native app. The stable `pantheon` one-line installer installs Web/CLI; it does not install Desktop. Desktop bundles its Python runtime: no Python, Node, Ubuntu or WSL installation is required to use its packaged app.

## Choose the installer for your computer

Open the [official Desktop beta releases](https://github.com/RyosukeSAMA/github-ai/releases) and select the highest Desktop `v0.5.0-beta.*` version containing your platform. The release's asset list and `SHA256SUMS.txt` are authoritative; do not select an installer by the screenshot's version.

| Computer | Installer filename ends with | Installation |
| --- | --- | --- |
| macOS 13+ on Apple Silicon (M1 or later) | `mac-arm64.dmg` | Open the DMG, then drag Pantheon into Applications. |
| Windows 11 on Intel/AMD 64-bit | `win-x64.exe` | Run the installer; choose the installation location when prompted. No WSL is needed. |
| Ubuntu 24.04 on Intel/AMD 64-bit | `linux-amd64.deb` | Open the package manager, or run `sudo apt install ./Pantheon-*-linux-amd64.deb` from the download directory. |
| Linux 64-bit with AppImage support | `linux-x86_64.AppImage` | Mark the file executable, then open it. This format requires the desktop's AppImage/FUSE support. |

macOS Intel, Windows ARM64 and Linux ARM64 installers are not currently published or established by the release matrix. Automated packaging on the three listed CI hosts does not establish every desktop environment or native permission behavior. These preview builds are not Apple notarized or Windows Authenticode signed. Software signing/notarization is outside the current delivery.

For macOS, **Apple menu → About This Mac** shows the chip. On Windows, **Settings → System → About → System type** shows the CPU architecture. On Linux, `uname -m` should show `x86_64` for these Linux builds.

## Continue a project in beta.22

Use **Project overview** to keep decisions, output files and next steps. For a small static website, **Delivery checks** records what was observed in a real browser before you accept the result. Follow the [website workflow](delivery-checks.md) or [three-session trial guide](website-trial.md).

A separately installed stable Web/CLI service stays on its own version. To try the beta workflows in standalone Web/CLI, use the beta.22 source and follow the [checker setup](delivery-checks.md#browser-availability).

## Start your first task

1. Launch Pantheon and choose a local project folder. Wait for the folder name and connected confirmation. The app does not copy that folder into the installer.
2. Open **Models & connections**, choose a provider and enter your API key. One provider is enough; multiple providers are optional. **Test API** makes a small provider request and can incur usage. **Save connection** stores the connection; testing alone does not save it.
3. Choose **Use this provider for new tasks**, or assign models only to the current task. Check the green confirmation's scope. Other tasks keep their models.
4. Describe a task and send it. Review generated file changes before saving. See the [controls guide](../docs/desktop/controls.zh-CN.md) for the complete English-button reference.

Your API keys, conversations and project state live outside the application bundle. Installing the same release on another person's computer does not transfer your configuration. Upgrading on your own computer intentionally retains your existing data.

## Upgrade and recover

1. Open **Service & updates**. Choose **Beta + Stable** to receive Desktop preview releases, or **Stable** to receive stable releases. Check the release notes.
2. Download the matching installer. Progress, cancellation and errors remain visible. A checksum failure removes the partial file; retry rather than opening it manually.
3. Select **Back up & open installer**. Wait for running tasks to finish. Desktop creates a data-only backup of each idle local workspace it owns, then opens the verified installer.
4. Quit Pantheon and install/replace the app using the platform steps above. Relaunch and confirm the version in **Service & updates**. Your workspace data remains in place.
5. If recovery is needed, choose a compatible earlier installer under **Version recovery**. Application rollback and data restoration are separate deliberate operations. To restore data, use **Backups & recovery → Inspect backup**, review its summary, then confirm. Restored schedules and pending work remain paused; inspect them before enabling or resuming.

Default backups contain workspace state and history, not project source files, provider credentials or configuration. Use Git or a file backup for project files. Secret-inclusive backup is optional and explicitly confirmed. Keep such archives private. Remote/reused services require backups and upgrades on the host that owns them.

## Verify a manual download

Download `SHA256SUMS.txt` alongside the installer. In the same directory:

```sh
# macOS
shasum -a 256 -c SHA256SUMS.txt --ignore-missing
# Linux
sha256sum -c SHA256SUMS.txt --ignore-missing
```

On Windows PowerShell, run `Get-FileHash .\Pantheon-*-win-x64.exe -Algorithm SHA256` and compare its full hash to the matching filename in `SHA256SUMS.txt`. Checksums establish file integrity; they are separate from publisher signing.
