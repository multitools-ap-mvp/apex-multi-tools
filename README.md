# Apex Multi Tools — Interactive CLI Framework

[![Version](https://img.shields.io/badge/version-0.4.0--beta-red)](https://github.com/multitools-ap-mvp/apex-multi-tools/releases)
[![Python](https://img.shields.io/badge/python-3.8+-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Build](https://github.com/multitools-ap-mvp/apex-multi-tools/actions/workflows/release.yml/badge.svg)](https://github.com/yourusername/apex-multi-tools/actions/workflows/release.yml)

> **Professional environment bootstrapper for Linux Mint live USB sessions.**

> **Security-first, config-driven, and extensible.**

> **Boot up && Setup up your perfect Enviorment in just a few click**

> **Save your current Project Enviorment .Config**

> **Use our CLi to boot up your Enviorment & Tools with 1 string**     

---

## Quick Start

### One-liner Bootstrap (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/multitools-ap-mvp/apex-multi-tools/main/bootstrap.py | python3
```

### Manual Clone & Run

```bash
git clone https://github.com/multitools-ap-mvp/apex-multi-tools.git ~/ApexMultiTools
cd ~/ApexMultiTools
python3 apex_framework.py
```

### With Config File (Non-Interactive)

```bash
python3 apex_framework.py --config apex_config.yaml
```

---

## Features

| Feature | Description |
|---------|-------------|
| **Security-First** | VPN, proxychains, macchanger, firewall setup *before* any network ops |
| **Secure Tunnel** | Auto-wraps network operations through proxychains with fetched proxy lists |
| **Rich TUI** | Beautiful interactive menus with progress bars, tables, and panels |
| **Config-Driven** | YAML/JSON config files for unattended/automated setup |
| **Tool Profiles** | Kali-style (pen-testing) & Development (coding/databases) |
| **GitHub Integration** | Clone repo, configure gh CLI, manage additional repos |
| **Session Persistence** | Backup/restore to removable storage for live USB sessions |
| **Google Drive Sync** | rclone integration with auto-configured remotes |
| **Extensible** | Easy to add new tools via the `Tool` registry |

---

## Architecture

```
┌─────────────────────────────────────────┐
│  STEP 0: SECURITY FIRST                 │
│  ├── ProtonVPN (GUI/CLI)                │
│  ├── Proxychains + proxy list fetch     │
│  ├── MAC Changer                        │
│  ├── Tor service                        │
│  └── UFW Firewall                       │
├─────────────────────────────────────────┤
│  STEP 1: SYSTEM UPDATE                  │
│  └── apt update && upgrade              │
├─────────────────────────────────────────┤
│  STEP 2: BASE PACKAGES                  │
│  └── Git, curl, vim, htop, tmux, etc.   │
├─────────────────────────────────────────┤
│  STEP 3: GITHUB INTEGRATION             │
│  ├── Clone framework repo               │
│  ├── Configure gh CLI                   │
│  └── Clone additional repos             │
├─────────────────────────────────────────┤
│  STEP 4: TOOL PROFILES                  │
│  ├── Kali-Style (nmap, metasploit, etc) │
│  └── Development (vscode, docker, etc)    │
├─────────────────────────────────────────┤
│  STEP 5: OBSIDIAN                       │
│  └── Flatpak or .deb install            │
├─────────────────────────────────────────┤
│  STEP 6: ACCOUNT LOGINS                 │
│  └── GitHub, Google, Docker, NPM, etc.│
├─────────────────────────────────────────┤
│  STEP 7: GOOGLE DRIVE SYNC              │
│  └── rclone sync/copy                   │
├─────────────────────────────────────────┤
│  STEP 8: BACKUP                         │
│  └── Persist to removable storage       │
└─────────────────────────────────────────┘
```

---

## Installation Methods

### Method 1: Bootstrap (Recommended for Live USB)

```bash
curl -fsSL https://raw.githubusercontent.com/multitools-ap-mvp/apex-multi-tools/main/bootstrap.py | python3
```

The bootstrap script:
1. Checks Python 3.8+ availability
2. Installs git if missing
3. Clones/pulls the framework repo
4. Installs Python dependencies (`rich`, `pyyaml`)
5. Launches the main framework

### Method 2: Standalone Executable

Download from [Releases](https://github.com/yourusername/apex-multi-tools/releases):

```bash
wget https://github.com/multitools-ap-mvp/apex-multi-tools/releases/download/v0.4.0-beta/apex-framework-linux-amd64.tar.gz
tar -xzf apex-framework-linux-amd64.tar.gz
./apex-framework
```

### Method 3: Docker

```bash
docker pull ghcr.io/multitools-ap-mvp/apex-multi-tools:v0.4.0-beta
docker run -it --rm ghcr.io/multitools-ap-mvp/apex-multi-tools:v0.4.0-beta
```

### Method 4: pip (Future)

```bash
pip install apex-multi-tools
apex-setup
```

---

## Configuration File

**apex_config.yaml Config**



---

## CLI Reference

```
python3 apex_framework.py [OPTIONS]

Options:
  --config FILE, -c FILE   Load selections from YAML/JSON config file
  --restore-only           Only restore from backup, then exit
  --backup-only            Only back up current state, then exit
  --secure-mode, -s        Force secure mode (VPN/proxy before network ops)
  --tui                    Force TUI mode (requires rich)
  --cli                    Force classic CLI mode (no rich)
  --no-banner              Skip banner display
  --help                   Show this message and exit
```

---

## Directory Structure

```
~/ApexMultiTools/
├── logs/                    # Timestamped session logs
│   └── apex_YYYYMMDD_HHMMSS.log
├── config/
│   └── proxies.txt          # Fetched proxy list
├── repos/                   # Cloned repositories
├── modules/                 # Future module extensions
└── .cache/
    └── apex_state.json      # Session persistence
```

---

## Tool Registry

Adding a new tool is simple:

```python
from apex_framework import Tool, ToolCategory

MY_TOOLS = {
    "MyTool": Tool(
        name="MyTool",
        category=ToolCategory.PACKAGE,  # or SPECIAL, SCRIPT
        apt_package="mytool",             # for apt installs
        check_binary="mytool",            # idempotency check
        description="What it does"
    ),
}
```

Then add to the appropriate step function.

---

## Security Notes

- **Backup contains credentials**: `rclone.conf` is backed up — treat it as sensitive
- **Proxy list**: Fetched from your repo — keep it private or rotate proxies regularly
- **MAC changer**: Requires interface name: `sudo macchanger -r eth0`
- **Tor**: Must be running for proxychains Tor routing: `sudo systemctl start tor`
- **VPN**: ProtonVPN requires account sign-in after installation

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

Please ensure:
- Code passes `flake8` linting
- Black formatting is applied
- New tools include idempotency checks
- Documentation is updated

---

## Roadmap

- [ ] v0.5.0 — Plugin system for custom tool modules
- [ ] v0.6.0 — GUI mode (Tkinter/QT) alongside TUI
- [ ] v0.7.0 — Remote management via SSH/web dashboard
- [ ] v0.8.0 — Cloud provider integrations (AWS, Azure, GCP)
- [ ] v1.0.0 — Stable release with full test coverage

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- [Rich](https://github.com/Textualize/rich) by Will McGugan for the beautiful TUI
- [PyInstaller](https://pyinstaller.org/) for standalone executable builds
- The Linux Mint team for the best live USB experience
