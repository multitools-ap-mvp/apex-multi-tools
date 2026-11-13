# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

## [0.4.0-beta] — 2026-06-18

### Added
- **Security-First Architecture**: VPN, proxychains, macchanger, firewall setup *before* any network operations
- **Secure Tunnel Wrapper**: `SecureTunnel` class auto-wraps network ops through proxychains
- **Proxy List Fetching**: Auto-fetches proxy list from repo and configures proxychains
- **Rich TUI**: Beautiful interactive menus with panels, tables, progress bars, and styled prompts
- **Config File Mode**: Full YAML/JSON config support for unattended setup (`--config`)
- **Bootstrap Script**: Tiny (~3KB) launcher that clones framework and auto-installs deps
- **GitHub Actions Workflow**: Auto-build, lint, test, and release on tag push
- **Docker Support**: Dockerfile + GitHub Container Registry integration
- **Tool Registry**: Extensible `Tool` dataclass with idempotency, categories, and custom installers
- **Kali-Style Profile**: 20+ pen-testing tools (nmap, metasploit, burpsuite, aircrack-ng, etc.)
- **Development Profile**: 20+ dev tools (vscode, docker, nodejs, go, rust, databases, etc.)
- **GitHub Integration**: Clone repo, configure gh CLI, manage additional repos
- **Session Summary**: Rich table showing installation summary at end
- **Retry Logic**: Command runner with configurable retries and delays
- **Structured Logging**: Timestamped logs in `~/ApexMultiTools/logs/`

### Changed
- Complete rewrite from original `apex_setup.py` to modular framework
- State management upgraded to `dataclass` with full serialization
- Command runner now supports capture, retry, and sudo wrapping
- Backup manifest now includes version field for migration support

### Removed
- Legacy `PACKAGES`, `ACCOUNTS`, `SECURITY_TOOLS` flat dictionaries
- Old `STATE` global dict replaced with typed `ApexState` dataclass

---

## [0.3.0] — 2026-05-15

### Added
- Google Drive sync via rclone
- Backup/restore to removable storage
- Obsidian install (Flatpak + .deb)
- Account login helpers (GitHub, Google, Docker, NPM)

### Fixed
- Proxychains config path detection
- ProtonVPN deb URL discovery

---

## [0.2.0] — 2026-04-20

### Added
- System update/upgrade step
- Custom package selection with toggle menu
- Security tools (proxychains, macchanger, tor, ufw)
- Color theme (Apex red/black)

---

## [0.1.0] — 2026-04-01

### Added
- Initial prototype
- Basic apt package installer
- Simple yes/no prompts
- Log file output
