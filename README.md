<div align="center">

```
▄▄▄       ██▓███  ▓█████ ▒██   ██▒
▒████▄    ▓██░  ██▒▓█   ▀ ▒▒ █ █ ▒░
▒██  ▀█▄  ▓██░ ██▓▒▒███   ░░  █   ░
░██▄▄▄▄██ ▒██▄█▓▒ ▒▒▓█  ▄  ░ █ █ ▒
 ▓█   ▓██▒▒██▒ ░  ░░▒████▒▒██▒ ▒██▒
 ▒▒   ▓▒█░▒▓▒░ ░  ░░░ ▒░ ░▒▒ ░ ░▓ ░
  ▒   ▒▒ ░░▒ ░      ░ ░  ░░░   ░▒ ░
  ░   ▒   ░░          ░    ░    ░
      ░  ░            ░  ░ ░    ░
```

# APEX MULTI TOOLS

**Linux Mint Live USB Environment Bootstrapper**

*Security-First · Config-Driven · Extensible*

[![Version](https://img.shields.io/badge/version-2.1.0-red?style=flat-square)](https://github.com/multitools-ap-mvp/apex-multi-tools/releases)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue?style=flat-square)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Linux%20Mint%20%7C%20Ubuntu%20%7C%20Debian-lightgrey?style=flat-square)](https://linuxmint.com/)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

</div>

---

## ⬇️ Download

> Pick the option that fits your workflow. All options run the same script.

| Option | Command | Notes |
|--------|---------|-------|
| **[⬇ Download v2.1.0 (zip)](https://github.com/multitools-ap-mvp/apex-multi-tools/archive/refs/tags/v2.1.0.zip)** | — | Full repo as ZIP |
| **[⬇ Download apex_framework.py](https://github.com/multitools-ap-mvp/apex-multi-tools/releases/latest/download/apex_framework.py)** | — | Single-file download |
| **Clone via Git** | `git clone https://github.com/multitools-ap-mvp/apex-multi-tools.git` | Recommended |
| **Run directly** | `curl -fsSL https://raw.githubusercontent.com/multitools-ap-mvp/apex-multi-tools/main/apex_framework.py -o apex_framework.py` | Quick one-liner |

---

## What is Apex Multi Tools?

Apex Multi Tools is an **interactive CLI bootstrapper** for setting up a fully customized Linux environment on a live USB or fresh install — in one guided session. It handles everything from system hardening and tool installation to account logins, Google Drive sync, and session persistence.

Built for developers, security researchers, and power users who want their environment ready fast, every time.

**What it does in one run:**
- Sets your locale, keyboard, and timezone
- Enables a security layer (VPN, Tor, proxychains, MAC spoofing)
- Installs and configures base packages, dev tools, and pen-testing tools
- Logs in to GitHub, Docker, NPM, Google Cloud, and more
- Syncs Google Drive via rclone
- Saves your entire environment as a named profile you can reload later
- Backs up your config to a USB drive for next time

---

## ✨ Features

### 🔐 Security First
- ProtonVPN (GUI & CLI installer)
- Tor + Proxychains4 with auto-fetched proxy list
- MAC address randomisation via macchanger
- UFW firewall, WireGuard, KeePassXC
- Full Kali-style toolkit: Nmap, Wireshark, Metasploit, Burp Suite, Hydra, SQLMap, Hashcat, Aircrack-ng, John the Ripper

### 🛠️ Dev Environment
- VS Code, Docker, Node.js LTS, Go, Rust
- PostgreSQL, MySQL, MongoDB, Redis, SQLite3
- DBeaver, Postman, Insomnia
- Git, GitHub CLI (gh), build essentials, Python3 + venv

### 🌐 Account Integration
- GitHub (gh CLI — SSH key upload + auth)
- Google Account (browser launch)
- Google Cloud (gcloud)
- Docker Hub, NPM, Heroku

### ☁️ Google Drive Sync
- rclone-powered sync to any GDrive folder
- Creates a local `$USER-gdrive/` mirror folder in the repo
- Auto-generates a `gdrive_sync.sh` helper script

### 💾 Environment Profiles
- Save your entire setup as a named JSON/YAML profile
- Load it on any future machine with one flag: `--load-env <name>`
- Profiles live in `~/ApexMultiTools/environments/`

### 🔄 Session Persistence
- Backup rclone config + selections to a removable USB drive
- Restore on the next live session automatically
- YAML config file support for non-interactive runs

---

## 📋 Requirements

- Linux Mint 21+ / Ubuntu 22.04+ / Debian 12+
- Python 3.8 or newer
- `sudo` access
- Internet connection (for tool installation)

Optional but recommended:
```bash
pip3 install rich       # enables the Rich TUI (colours, tables)
pip3 install pyyaml     # enables YAML config file support
```

---

## 🚀 Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/multitools-ap-mvp/apex-multi-tools.git
cd apex-multi-tools

# 2. Run
python3 apex_framework.py
```

That's it. The wizard takes you through every step interactively.

---

## 🖥️ CLI Screenshots

### Boot screen

```
  ▄▄▄       ██▓███  ▓█████ ▒██   ██▒
 ▒████▄    ▓██░  ██▒▓█   ▀ ▒▒ █ █ ▒░
 ▒██  ▀█▄  ▓██░ ██▓▒▒███   ░░  █   ░
 ░██▄▄▄▄██ ▒██▄█▓▒ ▒▒▓█  ▄  ░ █ █ ▒
  ▓█   ▓██▒▒██▒ ░  ░░▒████▒▒██▒ ▒██▒

  APEX MULTI TOOLS — INTERACTIVE CLI FRAMEWORK
  Linux Mint Live USB Environment Bootstrapper
  v2.1.0 — Security-First | Config-Driven | Extensible
```

---

### Locale / Keyboard / Timezone wizard

```
══════════════════════════════════════════════════════════════════════
  LOCALE / KEYBOARD / TIMEZONE
══════════════════════════════════════════════════════════════════════

  Set system locale, keyboard layout, and timezone before setup.
  Press Enter to keep the current value, or type a new one.

  Current locale:   en_US.UTF-8
  Current keyboard: us
  Current timezone: Europe/Stockholm

Change locale / keyboard / timezone? [y/N] y

Locale (e.g. en_US.UTF-8, sv_SE.UTF-8) [en_US.UTF-8]
> sv_SE.UTF-8
[OK] Locale set to sv_SE.UTF-8

Keyboard layout (e.g. us, se, de, gb) [us]
> se
[OK] Keyboard set to se

Timezone (e.g. Europe/Stockholm, UTC, US/Eastern) [Europe/Stockholm]
>
[✓] Locale / keyboard / timezone configured.
```

---

### Toggle-select menu (tool picker)

```
══════════════════════════════════════════════════════════════════════
  STEP 0 — SECURITY FIRST
══════════════════════════════════════════════════════════════════════

Select security tools to install:
  Guide: type a number → toggle │ '2 5' or '2,5' → multi-toggle
         'a' = select all │ 'd' = deselect all │ 'c' = confirm

   1. [ ] ProtonVPN (GUI)    — VPN client — GUI
   2. [ ] ProtonVPN (CLI)    — VPN client — CLI
   3. [x] Proxychains4       — Proxy routing
   4. [x] MAC Changer        — MAC address spoofing
   5. [x] Tor                — Anonymity network
   6. [ ] UFW Firewall       — Uncomplicated firewall
   7. [ ] KeePassXC          — Password manager
   8. [ ] WireGuard          — VPN protocol
   9. [ ] Nmap               — Network scanner
  10. [ ] Wireshark          — Packet analyser
  11. [ ] Aircrack-ng        — WiFi security auditing
  12. [ ] Metasploit         — Penetration testing framework
  13. [ ] Burp Suite         — Web security testing

> 3 5 9
> c
```

---

### Environment save / load

```
══════════════════════════════════════════════════════════════════════
  SAVE ENVIRONMENT PROFILE
══════════════════════════════════════════════════════════════════════

  Save your current tool selections, accounts, and settings as a
  named profile. Load it on any future run with:
    python3 apex_framework.py --load-env <name>

Save this environment profile now? [Y/n] y

Name for this environment profile [env_20250625_143201]
> my-pentest-setup

[✓] Environment saved → ~/ApexMultiTools/environments/my-pentest-setup.json

  Load it next time with:
  python3 apex_framework.py --load-env my-pentest-setup
  python3 apex_framework.py --config ~/ApexMultiTools/environments/my-pentest-setup.json
```

---

### Session summary

```
══════════════════════════════════════════════════════════════════════
  SESSION SUMMARY
══════════════════════════════════════════════════════════════════════

  Base packages:
    ✓ Git          ✓ Curl       ✓ Wget
    ✓ Python3      ✓ Tmux       ✓ Neofetch

  Security tools:
    ✓ Proxychains4   ✓ MAC Changer   ✓ Tor   ✓ Nmap

  Dev tools:
    ✓ VS Code   ✓ Docker   ✓ Node.js (LTS)   ✓ Go

  Accounts:
    ✓ GitHub (gh CLI)   ✓ Docker Hub

  Google Drive:  gdrive:Backup
  GDrive local:  ~/ApexMultiTools/jack-gdrive
  Timezone:      Europe/Stockholm

  Full log: ~/ApexMultiTools/logs/

[✓] Apex Multi Tools setup complete.
```

---

## 📖 How It Works

The framework runs as a **linear wizard** — each step can be accepted, skipped, or customised. Your choices are saved to a state cache so if something fails mid-run, you can resume from where you left off.

### Step 0 — Restore Previous Session
Looks for an existing backup on any mounted USB drive. If found, offers to restore your previous selections and rclone config before anything else runs.

### Step 0.5 — Locale / Keyboard / Timezone
Sets system locale (`localectl`), keyboard layout (console + X11), and timezone (`timedatectl`). Remembers your last values so on repeat runs you just press Enter to confirm.

### Step 1 — Security First
Optionally enables **secure mode** — installs your chosen VPN/proxy/anonymity tools before any network operations run. Includes ProtonVPN, Tor, Proxychains4, MAC Changer, WireGuard, UFW, and more.

### Step 2 — System Update
Runs `apt update` + `apt upgrade` to bring the system fully current.

### Step 3 — Base Packages
Toggle-select from 16 essential packages: Git, Curl, Wget, Python3, Vim, Tmux, Neofetch, htop, OpenSSH, Flatpak, and more.

### Step 4 — GitHub Integration
Clones or updates the Apex repo to `~/ApexMultiTools`, installs and configures the `gh` CLI with SSH protocol.

### Step 5 — Tool Profiles
Two separate menus — one for **Kali-style pen-testing tools** and one for **development tools**. Pick exactly what you need.

### Step 6 — Obsidian
Install Obsidian via Flatpak (recommended) or direct `.deb` download.

### Step 7 — Account Logins
Log in to GitHub, Google Cloud, Docker Hub, NPM, and Heroku interactively. The framework installs any missing CLI tools first.

### Step 8 — Google Drive Sync
Configures rclone with your Google Drive remote, runs an initial sync to a local folder, and optionally creates a `$USER-gdrive/` mirror directory in the repo that you can sync anytime with the generated `gdrive_sync.sh` script.

### Step 9 — Save Environment Profile
Saves the entire session — tool selections, accounts, locale, GDrive config — as a named JSON/YAML profile in `~/ApexMultiTools/environments/`. Reload it on any machine.

### Step 10 — Backup to USB
Copies your rclone config + session manifest to any detected removable drive for physical backup. Survives reboots and live USB resets.

---

## ⚙️ CLI Reference

```bash
# Interactive wizard (default)
python3 apex_framework.py

# Load a named environment profile
python3 apex_framework.py --load-env my-pentest-setup

# Run from a YAML/JSON config (non-interactive)
python3 apex_framework.py --config environments/my-pentest-setup.yaml

# List all saved environment profiles
python3 apex_framework.py --list-envs

# Save current state and exit
python3 apex_framework.py --save-env

# Only restore from backup, then exit
python3 apex_framework.py --restore-only

# Only back up current session, then exit
python3 apex_framework.py --backup-only

# Force secure mode (VPN/proxy first)
python3 apex_framework.py --secure-mode

# Suppress banner
python3 apex_framework.py --no-banner

# Show version
python3 apex_framework.py --version
```

---

## 📁 Directory Structure

After first run, Apex creates the following layout:

```
~/ApexMultiTools/
├── logs/
│   └── apex_20250625_143201.log    # Per-session log
├── config/
│   └── proxies.txt                  # Fetched proxy list
├── environments/
│   ├── my-pentest-setup.json        # Saved environment profiles
│   └── my-pentest-setup.yaml
├── .cache/
│   └── apex_state.json              # Session state cache
├── jack-gdrive/                     # Local GDrive mirror ($USER-gdrive)
└── gdrive_sync.sh                   # Rclone sync helper script
```

---

## 🔧 Config File Format

You can drive the entire setup non-interactively with a YAML or JSON config file:

```yaml
# apex_config.yaml
security:
  enabled: true
  tools:
    - Proxychains4
    - MAC Changer
    - Tor
    - Nmap

packages:
  selected:
    - Git
    - Curl
    - Python3 & pip
    - Tmux

tools:
  kali:
    - Nmap
    - Wireshark
  development:
    - VS Code
    - Docker
    - Node.js (LTS)

accounts:
  login:
    - GitHub (gh CLI)
    - Docker Hub

gdrive:
  remote: gdrive
  path: Backup
  dest: ~/Desktop/GDrive-Backup
  local_sync: true
```

Run it:
```bash
python3 apex_framework.py --config apex_config.yaml
```

---

## 🔄 Changelog

### v2.1.0 — 2025-06-25
- **New:** Locale / keyboard / timezone wizard (pre-boot, remembers last values)
- **New:** `toggle_select` inline usage guide on every menu
- **New:** Environment save/load — `--save-env`, `--load-env <name>`, `--list-envs`
- **New:** `$USER-gdrive/` local GDrive mirror folder + `gdrive_sync.sh` helper
- **Fix:** VS Code key had trailing colon — broken manifest serialisation
- **Fix:** Pipe operators in subprocess lists (`|` passed as literal arg) — all install_cmd entries converted to shell strings
- **Fix:** ProtonVPN keys missing from `SECURITY_TOOLS` — wizard checks were dead code
- **Fix:** `logger` used before init — safe `_log()` wrapper added
- **Fix:** `pick_backup_location()` silently returned `None` on bad input — now loops

### v2.0.0
- Full rewrite: dataclass state, Rich TUI support, retry logic, config file mode
- Added Kali-style tool profiles, account login automation
- rclone Google Drive sync

---

## 📜 License

MIT — see [LICENSE](LICENSE)

---

<div align="center">

**[apexmultitools.se](https://apexmultitools.se)** · Built by ApexMultiTools

</div>
