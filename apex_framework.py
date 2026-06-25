#!/usr/bin/env python3
"""
================================================================================
APEX MULTI TOOLS — INTERACTIVE CLI FRAMEWORK
================================================================================
Professional environment bootstrapper for Linux Mint live USB

Modes:
  Interactive (default)  — wizard-driven setup
  --config FILE          — pre-defined YAML/JSON selections, non-interactive
  --restore-only         — restore previous session from persistent storage
  --backup-only          — back up current session to persistent storage
  --secure-mode          — force VPN/proxy before any network operations
  --load-env NAME        — load a named saved environment profile

Architecture:
  0. Locale / Keyboard / Timezone wizard (pre-boot)
  1. Security Layer  (VPN, proxychains, macchanger)
  2. System Update   (apt update/upgrade)
  3. Base Packages
  4. GitHub Integration
  5. Tool Profiles   (Kali-style / Development)
  6. Obsidian
  7. Account Logins
  8. Google Drive Sync (rclone + local gdrive folder)
  9. Environment Save / Load
 10. Backup / Restore to removable media

Run: python3 apex_framework.py
================================================================================
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Callable, List, Optional

# ─────────────────────────────────────────────────────────────────────────────
# VERSION & RICH (TUI) SUPPORT
# ─────────────────────────────────────────────────────────────────────────────

VERSION = "2.1.0"

try:
    from rich import box
    from rich.console import Console
    from rich.table import Table
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None
    Table = None
    box = None

# ─────────────────────────────────────────────────────────────────────────────
# PATHS & CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

REPO_URL       = "https://github.com/multitools-ap-mvp/apex-multi-tools"
REPO_RAW_BASE  = "https://raw.githubusercontent.com/multitools-ap-mvp/apex-multi-tools/main"
PROXY_LIST_URL = f"{REPO_RAW_BASE}/config/proxies.txt"

FRAMEWORK_DIR      = Path.home() / "ApexMultiTools"
LOGS_DIR           = FRAMEWORK_DIR / "logs"
CONFIG_DIR         = FRAMEWORK_DIR / "config"
CACHE_DIR          = FRAMEWORK_DIR / ".cache"
ENVS_DIR           = FRAMEWORK_DIR / "environments"   # named environment profiles
BACKUP_FOLDER_NAME = "ApexMultiTools_Backup"
MANIFEST_NAME      = "apex_manifest.json"
STATE_FILE         = CACHE_DIR / "apex_state.json"
DEFAULT_GDRIVE_DEST = Path.home() / "Desktop" / "Backup-GDrive"

_USER = os.environ.get("USER", "user")
GDRIVE_SYNC_DIR = FRAMEWORK_DIR / f"{_USER}-gdrive"   # local gdrive mirror

# ─────────────────────────────────────────────────────────────────────────────
# COLOR THEME
# ─────────────────────────────────────────────────────────────────────────────

class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    RED     = "\033[91m"
    BRED    = "\033[1;91m"
    WHITE   = "\033[97m"
    GREY    = "\033[90m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    CYAN    = "\033[96m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"

# ─────────────────────────────────────────────────────────────────────────────
# LOGGING SYSTEM
# ─────────────────────────────────────────────────────────────────────────────

class ApexLogger:
    def __init__(self):
        self.session_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file     = LOGS_DIR / f"apex_{self.session_time}.log"
        self._ensure_dirs()
        self._write_header()

    def _ensure_dirs(self):
        for d in (LOGS_DIR, CONFIG_DIR, CACHE_DIR, ENVS_DIR):
            d.mkdir(parents=True, exist_ok=True)

    def _write_header(self):
        self.log_file.write_text(
            f"\n{'='*70}\n"
            f"APEX MULTI TOOLS — SESSION LOG\n"
            f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"User:    {os.environ.get('USER', 'unknown')}\n"
            f"Host:    {os.uname().nodename}\n"
            f"{'='*70}\n"
        )

    def log(self, level: str, msg: str):
        ts   = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] [{level}] {msg}"
        with open(self.log_file, "a") as f:
            f.write(line + "\n")

    def debug(self, msg): self.log("DEBUG", msg)
    def info(self, msg):  self.log("INFO",  msg)
    def warn(self, msg):  self.log("WARN",  msg)
    def error(self, msg): self.log("ERROR", msg)
    def cmd(self, cmd_list): self.log("CMD", " ".join(str(x) for x in cmd_list))


# Logger is None until main() boots it; helpers use a safe wrapper below.
logger: Optional[ApexLogger] = None

def _log(level: str, msg: str):
    """Safe logger wrapper — works before main() initialises the logger."""
    if logger:
        logger.log(level, msg)

# ─────────────────────────────────────────────────────────────────────────────
# STATE — persistent across runs
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ApexState:
    packages_selected:   List[str]     = field(default_factory=list)
    accounts_selected:   List[str]     = field(default_factory=list)
    security_selected:   List[str]     = field(default_factory=list)
    kali_tools_selected: List[str]     = field(default_factory=list)
    dev_tools_selected:  List[str]     = field(default_factory=list)
    gdrive_remote:       Optional[str] = None
    gdrive_path:         str           = ""
    gdrive_dest:         str           = ""
    gdrive_local_sync:   bool          = False   # NEW: local $user-gdrive folder
    secure_mode_enabled: bool          = False
    proxychains_configured: bool       = False
    repo_cloned:         bool          = False
    config_mode:         bool          = False
    config_file:         Optional[str] = None
    tui_mode:            bool          = False
    # locale/kb/tz remembered from last run
    last_locale:         str           = ""
    last_keyboard:       str           = ""
    last_timezone:       str           = ""

    def save(self):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(asdict(self), indent=2))
        _log("INFO", "State saved to cache")

    @classmethod
    def load(cls) -> "ApexState":
        if STATE_FILE.exists():
            try:
                data = json.loads(STATE_FILE.read_text())
                # Drop any keys that no longer exist in the dataclass
                valid = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
                return cls(**valid)
            except Exception as e:
                # Logger may not exist yet — print to stderr
                print(f"[!] Could not load state: {e}", file=sys.stderr)
        return cls()


STATE = ApexState()

# ─────────────────────────────────────────────────────────────────────────────
# UI HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def header(text: str):
    width = 70
    print(f"\n{C.BRED}{'═' * width}{C.RESET}")
    print(f"{C.BRED}{C.BOLD}  {text}{C.RESET}")
    print(f"{C.BRED}{'═' * width}{C.RESET}\n")
    _log("INFO", f"HEADER: {text}")


def banner():
    art = r"""
  ▄▄▄       ██▓███  ▓█████ ▒██   ██▒
 ▒████▄    ▓██░  ██▒▓█   ▀ ▒▒ █ █ ▒░
 ▒██  ▀█▄  ▓██░ ██▓▒▒███   ░░  █   ░
 ░██▄▄▄▄██ ▒██▄█▓▒ ▒▒▓█  ▄  ░ █ █ ▒
  ▓█   ▓██▒▒██▒ ░  ░░▒████▒▒██▒ ▒██▒
  ▒▒   ▓▒█░▒▓▒░ ░  ░░░ ▒░ ░▒▒ ░ ░▓ ░
   ▒   ▒▒ ░░▒ ░      ░ ░  ░░░   ░▒ ░
   ░   ▒   ░░          ░    ░    ░
       ░  ░            ░  ░ ░    ░
"""
    print(f"{C.RED}{art}{C.RESET}")
    print(f"{C.WHITE}{C.BOLD}  APEX MULTI TOOLS — INTERACTIVE CLI FRAMEWORK{C.RESET}")
    print(f"{C.GREY}  Linux Mint Live USB Environment Bootstrapper{C.RESET}")
    print(f"{C.GREY}  v{VERSION} — Security-First | Config-Driven | Extensible{C.RESET}\n")


def info(msg: str):
    print(f"{C.CYAN}[*]{C.RESET} {msg}")
    _log("INFO", msg)

def ok(msg: str):
    print(f"{C.GREEN}[OK]{C.RESET} {msg}")
    _log("INFO", f"OK: {msg}")

def warn(msg: str):
    print(f"{C.YELLOW}[!]{C.RESET} {msg}")
    _log("WARN", msg)

def err(msg: str):
    print(f"{C.RED}[ERROR]{C.RESET} {msg}")
    _log("ERROR", msg)

def success(msg: str):
    print(f"{C.GREEN}{C.BOLD}[✓]{C.RESET} {msg}")
    _log("INFO", f"SUCCESS: {msg}")


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        ans = input(f"{C.WHITE}{prompt} {C.GREY}{suffix}{C.RESET} ").strip().lower()
        if ans == "":
            return default
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        warn("Please answer y or n.")


def ask_input(prompt: str, default: str = "") -> str:
    suffix = f" {C.GREY}[{default}]{C.RESET}" if default else ""
    result = input(f"{C.WHITE}{prompt}{suffix}{C.RESET}\n> ").strip()
    return result if result else default


def toggle_select(
    title: str,
    names: List[str],
    preselected=None,
    all_default: bool = True,
    descriptions: Optional[dict] = None,
) -> List[str]:
    """
    Interactive toggle-select menu.

    HOW TO USE:
      • Type a number (e.g. 2) and press Enter  → toggle that item
      • Separate multiple numbers with spaces or commas (e.g. 2 5 7)
      • Type 'a' → select all
      • Type 'd' → deselect all
      • Type 'c' → confirm and continue
    """
    if preselected is not None:
        pre      = set(preselected)
        selected = {n: (n in pre) for n in names}
    else:
        selected = {n: all_default for n in names}

    while True:
        print(f"\n{C.WHITE}{C.BOLD}{title}{C.RESET}")

        # ── Usage guide ─────────────────────────────────────────────────────
        print(
            f"{C.GREY}  Guide: type a number → toggle │ '2 5' or '2,5' → multi-toggle{C.RESET}\n"
            f"{C.GREY}         'a' = select all │ 'd' = deselect all │ 'c' = confirm{C.RESET}"
        )
        print()

        for i, name in enumerate(names, 1):
            mark  = f"{C.GREEN}[x]{C.RESET}" if selected[name] else f"{C.GREY}[ ]{C.RESET}"
            extra = (
                f"  {C.GREY}— {descriptions[name]}{C.RESET}"
                if descriptions and name in descriptions
                else ""
            )
            print(f"  {C.RED}{i:2d}{C.RESET}. {mark} {name}{extra}")

        print()
        choice = input(f"{C.WHITE}> {C.RESET}").strip().lower()

        if choice == "c":
            break
        elif choice == "a":
            selected = {n: True  for n in names}
        elif choice == "d":
            selected = {n: False for n in names}
        else:
            # Accept "2 5 7" or "2,5,7" or "2, 5, 7"
            raw = choice.replace(",", " ").split()
            try:
                idxs = [int(x) for x in raw if x]
                for i in idxs:
                    if 1 <= i <= len(names):
                        n = names[i - 1]
                        selected[n] = not selected[n]
                    else:
                        warn(f"No item #{i}")
            except ValueError:
                warn("Couldn't parse that — try a number, 'a', 'd', or 'c'.")

    return [n for n in names if selected[n]]

# ─────────────────────────────────────────────────────────────────────────────
# COMMAND RUNNER
# ─────────────────────────────────────────────────────────────────────────────

def run(
    cmd: List[str],
    sudo: bool    = False,
    capture: bool = False,
    check: bool   = True,
    retries: int  = 0,
    retry_delay: int = 3,
    shell: bool   = False,
):
    """
    Run a command list (or shell string) with logging, optional sudo, retries.

    FIX: Commands that contain pipe operators must be passed as a shell string
    with shell=True — NOT as a list, because subprocess does not support '|'
    in list form.
    """
    if not shell and sudo and os.geteuid() != 0:
        cmd = ["sudo"] + list(cmd)

    log_target = cmd if isinstance(cmd, str) else " ".join(str(x) for x in cmd)
    _log("CMD", log_target)

    attempt = 0
    while True:
        attempt += 1
        try:
            kwargs = dict(check=check, text=True, shell=shell)
            if capture:
                kwargs.update(stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            result = subprocess.run(cmd, **kwargs)
            if capture and result.stdout:
                _log("DEBUG", f"Output: {result.stdout[:500]}")
            return result
        except subprocess.CalledProcessError as e:
            _log("ERROR", f"Command failed (attempt {attempt}): {log_target} — {e}")
            if attempt <= retries:
                warn(f"Retrying in {retry_delay}s… (attempt {attempt}/{retries + 1})")
                time.sleep(retry_delay)
            else:
                if check:
                    raise
                return e


def run_shell(cmd_str: str, sudo: bool = False, capture: bool = False, check: bool = True):
    """Convenience: run a shell string (supports pipes, redirects, etc.)."""
    if sudo and os.geteuid() != 0:
        cmd_str = f"sudo {cmd_str}"
    return run(cmd_str, capture=capture, check=check, shell=True)


def sudo_keepalive():
    info("Requesting sudo access for system operations…")
    subprocess.run(["sudo", "-v"], check=False)
    ok("Sudo access granted")


def check_installed(binary: str) -> bool:
    return shutil.which(binary) is not None


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path

# ─────────────────────────────────────────────────────────────────────────────
# TOOL REGISTRY
# ─────────────────────────────────────────────────────────────────────────────

class ToolCategory(Enum):
    PACKAGE = auto()
    SPECIAL = auto()
    SCRIPT  = auto()


@dataclass
class Tool:
    name:         str
    category:     ToolCategory
    install_cmd:  Optional[List] = None
    check_binary: Optional[str]  = None
    description:  str            = ""
    pre_install:  Optional[Callable] = None
    post_install: Optional[Callable] = None
    apt_package:  Optional[str]  = None

    def is_installed(self) -> bool:
        if self.check_binary:
            return check_installed(self.check_binary)
        if self.apt_package:
            result = run(["dpkg", "-l", self.apt_package], capture=True, check=False)
            return result.returncode == 0 and "ii" in (result.stdout or "")
        return False

    def install(self):
        if self.is_installed():
            ok(f"{self.name} already installed — skipping")
            return

        info(f"Installing {self.name}…")
        if self.pre_install:
            self.pre_install()

        if self.category == ToolCategory.PACKAGE and self.apt_package:
            run(["apt-get", "install", "-y", self.apt_package], sudo=True)

        elif self.category in (ToolCategory.SPECIAL, ToolCategory.SCRIPT) and self.install_cmd:
            for step in self.install_cmd:
                if isinstance(step, str):
                    # Shell string — supports pipes, redirects
                    run_shell(step, check=True)
                else:
                    # Plain list — no pipe support; use run() with logging
                    run(list(step), sudo=(os.geteuid() != 0), check=True)

        if self.post_install:
            self.post_install()

        ok(f"{self.name} installed")

# ─────────────────────────────────────────────────────────────────────────────
# TOOL DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────

BASE_PACKAGES = {
    "Git":             Tool("Git",             ToolCategory.PACKAGE, apt_package="git",            check_binary="git",      description="Version control"),
    "Curl":            Tool("Curl",            ToolCategory.PACKAGE, apt_package="curl",           check_binary="curl",     description="HTTP client"),
    "Wget":            Tool("Wget",            ToolCategory.PACKAGE, apt_package="wget",           check_binary="wget",     description="File downloader"),
    "Build Essentials":Tool("Build Essentials",ToolCategory.PACKAGE, apt_package="build-essential",                        description="Compilers & make"),
    "Python3 & pip":   Tool("Python3 & pip",   ToolCategory.PACKAGE, apt_package="python3-pip",    check_binary="pip3",    description="Python package manager"),
    "Python venv":     Tool("Python venv",     ToolCategory.PACKAGE, apt_package="python3-venv",                           description="Virtual environments"),
    "Vim":             Tool("Vim",             ToolCategory.PACKAGE, apt_package="vim",            check_binary="vim",      description="Text editor"),
    "htop":            Tool("htop",            ToolCategory.PACKAGE, apt_package="htop",           check_binary="htop",     description="Process viewer"),
    "Net-tools":       Tool("Net-tools",       ToolCategory.PACKAGE, apt_package="net-tools",      check_binary="ifconfig", description="Network utilities"),
    "OpenSSH":         Tool("OpenSSH",         ToolCategory.PACKAGE, apt_package="openssh-client", check_binary="ssh",      description="SSH client"),
    "Flatpak":         Tool("Flatpak",         ToolCategory.PACKAGE, apt_package="flatpak",        check_binary="flatpak",  description="App sandboxing"),
    "Unzip":           Tool("Unzip",           ToolCategory.PACKAGE, apt_package="unzip",          check_binary="unzip",    description="Archive extractor"),
    "jq":              Tool("jq",              ToolCategory.PACKAGE, apt_package="jq",             check_binary="jq",       description="JSON processor"),
    "Tree":            Tool("Tree",            ToolCategory.PACKAGE, apt_package="tree",           check_binary="tree",     description="Directory tree viewer"),
    "Tmux":            Tool("Tmux",            ToolCategory.PACKAGE, apt_package="tmux",           check_binary="tmux",     description="Terminal multiplexer"),
    "Neofetch":        Tool("Neofetch",        ToolCategory.PACKAGE, apt_package="neofetch",       check_binary="neofetch", description="System info display"),
}

SECURITY_TOOLS = {
    "ProtonVPN (GUI)":  Tool("ProtonVPN (GUI)",  ToolCategory.SPECIAL, description="VPN client — GUI",      check_binary="protonvpn-app"),
    "ProtonVPN (CLI)":  Tool("ProtonVPN (CLI)",  ToolCategory.SPECIAL, description="VPN client — CLI",      check_binary="protonvpn-cli"),
    "Proxychains4":     Tool("Proxychains4",     ToolCategory.PACKAGE, apt_package="proxychains4", check_binary="proxychains4", description="Proxy routing"),
    "MAC Changer":      Tool("MAC Changer",      ToolCategory.PACKAGE, apt_package="macchanger",   check_binary="macchanger",  description="MAC address spoofing"),
    "Tor":              Tool("Tor",              ToolCategory.PACKAGE, apt_package="tor",           check_binary="tor",         description="Anonymity network"),
    "UFW Firewall":     Tool("UFW Firewall",     ToolCategory.PACKAGE, apt_package="ufw",           check_binary="ufw",         description="Uncomplicated firewall"),
    "KeePassXC":        Tool("KeePassXC",        ToolCategory.PACKAGE, apt_package="keepassxc",     check_binary="keepassxc",   description="Password manager"),
    "WireGuard":        Tool("WireGuard",        ToolCategory.PACKAGE, apt_package="wireguard",     check_binary="wg",          description="VPN protocol"),
    "Nmap":             Tool("Nmap",             ToolCategory.PACKAGE, apt_package="nmap",           check_binary="nmap",        description="Network scanner"),
    "Wireshark":        Tool("Wireshark",        ToolCategory.PACKAGE, apt_package="wireshark",     check_binary="wireshark",   description="Packet analyser"),
    "Aircrack-ng":      Tool("Aircrack-ng",      ToolCategory.PACKAGE, apt_package="aircrack-ng",   check_binary="aircrack-ng", description="WiFi security auditing"),
    "Hydra":            Tool("Hydra",            ToolCategory.PACKAGE, apt_package="hydra",          check_binary="hydra",       description="Password cracker"),
    "SQLMap":           Tool("SQLMap",           ToolCategory.PACKAGE, apt_package="sqlmap",         check_binary="sqlmap",      description="SQL injection tool"),
    "John the Ripper":  Tool("John the Ripper",  ToolCategory.PACKAGE, apt_package="john",           check_binary="john",        description="Password hash cracker"),
    "Hashcat":          Tool("Hashcat",          ToolCategory.PACKAGE, apt_package="hashcat",        check_binary="hashcat",     description="GPU password cracker"),
    # SPECIAL tools — install_cmd uses shell strings (supports pipes)
    "Metasploit": Tool(
        "Metasploit", ToolCategory.SPECIAL, check_binary="msfconsole",
        description="Penetration testing framework",
        install_cmd=[
            "curl https://raw.githubusercontent.com/rapid7/metasploit-omnibus/master/config/templates/metasploit-framework-wrappers/msfupdate.erb -o /tmp/msfinstall",
            "chmod 755 /tmp/msfinstall",
            "/tmp/msfinstall",
        ],
    ),
    "Burp Suite": Tool(
        "Burp Suite", ToolCategory.SPECIAL, check_binary="burpsuite",
        description="Web security testing",
        install_cmd=[
            "wget -q -O /tmp/burpsuite.sh 'https://portswigger.net/burp/releases/download?product=community&version=2024.1.1&type=Linux'",
            "chmod +x /tmp/burpsuite.sh",
            "/tmp/burpsuite.sh -q -dir /opt/BurpSuiteCommunity",
        ],
    ),
}

DEV_TOOLS = {
    # FIX: removed trailing colon from key and name
    "VS Code": Tool(
        "VS Code", ToolCategory.SPECIAL, check_binary="code",
        description="Code editor",
        install_cmd=[
            # FIX: pipe commands must be shell strings
            "wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /tmp/packages.microsoft.gpg",
            "sudo install -D -o root -g root -m 644 /tmp/packages.microsoft.gpg /etc/apt/keyrings/packages.microsoft.gpg",
            "sudo sh -c 'echo \"deb [arch=amd64,arm64,armhf signed-by=/etc/apt/keyrings/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main\" > /etc/apt/sources.list.d/vscode.list'",
            "rm -f /tmp/packages.microsoft.gpg",
            "sudo apt-get update",
            "sudo apt-get install -y code",
        ],
    ),
    "Docker": Tool(
        "Docker", ToolCategory.SPECIAL, check_binary="docker",
        description="Container platform",
        install_cmd=[
            "sudo apt-get install -y ca-certificates curl gnupg",
            "sudo install -m 0755 -d /etc/apt/keyrings",
            # FIX: pipe — shell string
            "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg",
            "sudo chmod a+r /etc/apt/keyrings/docker.gpg",
            "bash -c 'echo \"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable\" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null'",
            "sudo apt-get update",
            "sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin",
            f"sudo usermod -aG docker {_USER}",
        ],
    ),
    "Node.js (LTS)": Tool(
        "Node.js (LTS)", ToolCategory.SCRIPT, check_binary="node",
        description="JavaScript runtime",
        install_cmd=[
            "curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash - && sudo apt-get install -y nodejs",
        ],
    ),
    "NPM":        Tool("NPM",       ToolCategory.PACKAGE, apt_package="npm",          check_binary="npm",          description="Node package manager"),
    "Yarn":       Tool("Yarn",      ToolCategory.SCRIPT,  check_binary="yarn",        description="Package manager",    install_cmd=["npm install -g yarn"]),
    "PostgreSQL": Tool("PostgreSQL",ToolCategory.PACKAGE, apt_package="postgresql",   check_binary="psql",         description="Relational database"),
    "MySQL":      Tool("MySQL",     ToolCategory.PACKAGE, apt_package="mysql-server", check_binary="mysql",        description="Relational database"),
    "MongoDB": Tool(
        "MongoDB", ToolCategory.SPECIAL, check_binary="mongod",
        description="NoSQL database",
        install_cmd=[
            # FIX: pipe — shell strings
            "wget -qO- https://www.mongodb.org/static/pgp/server-7.0.asc | sudo gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg",
            "echo 'deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse' | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list",
            "sudo apt-get update",
            "sudo apt-get install -y mongodb-org",
            "sudo systemctl start mongod",
            "sudo systemctl enable mongod",
        ],
    ),
    "Redis":   Tool("Redis",   ToolCategory.PACKAGE, apt_package="redis-server", check_binary="redis-server", description="In-memory database"),
    "SQLite3": Tool("SQLite3", ToolCategory.PACKAGE, apt_package="sqlite3",      check_binary="sqlite3",      description="Embedded database"),
    "Go": Tool(
        "Go", ToolCategory.SPECIAL, check_binary="go",
        description="Go programming language",
        install_cmd=[
            "wget -q https://go.dev/dl/go1.21.5.linux-amd64.tar.gz -O /tmp/go.tar.gz",
            "sudo rm -rf /usr/local/go",
            "sudo tar -C /usr/local -xzf /tmp/go.tar.gz",
        ],
    ),
    "Rust": Tool(
        "Rust", ToolCategory.SCRIPT, check_binary="rustc",
        description="Rust programming language",
        install_cmd=["curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y"],
    ),
    "DBeaver": Tool("DBeaver", ToolCategory.PACKAGE, apt_package="dbeaver-ce", check_binary="dbeaver", description="Database GUI"),
    "Postman": Tool(
        "Postman", ToolCategory.SPECIAL, check_binary="postman",
        description="API testing",
        install_cmd=[
            "wget -q https://dl.pstmn.io/download/latest/linux64 -O /tmp/postman.tar.gz",
            "sudo tar -xzf /tmp/postman.tar.gz -C /opt/",
            "sudo ln -sf /opt/Postman/Postman /usr/local/bin/postman",
        ],
    ),
    "Insomnia": Tool(
        "Insomnia", ToolCategory.SPECIAL, check_binary="insomnia",
        description="API testing",
        install_cmd=[
            "wget -q 'https://updates.insomnia.rest/downloads/ubuntu/latest?app=com.insomnia.app&source=website' -O /tmp/insomnia.deb",
            "sudo dpkg -i /tmp/insomnia.deb",
            "sudo apt-get install -f -y",
        ],
    ),
}

ACCOUNTS = {
    "GitHub (gh CLI)": {
        "type": "cli", "check": "gh",
        "login_cmd": ["gh", "auth", "login"],
        "install": lambda: install_gh_cli(),
    },
    "Google Account (browser)": {
        "type": "browser", "url": "https://accounts.google.com/",
    },
    "Google Cloud (gcloud)": {
        "type": "cli", "check": "gcloud",
        "login_cmd": ["gcloud", "auth", "login"],
        "install": lambda: warn("Install gcloud from https://cloud.google.com/sdk/docs/install"),
    },
    "Docker Hub": {
        "type": "cli", "check": "docker",
        "login_cmd": ["docker", "login"],
    },
    "NPM": {
        "type": "cli", "check": "npm",
        "login_cmd": ["npm", "login"],
    },
    "Heroku": {
        "type": "cli", "check": "heroku",
        "login_cmd": ["heroku", "login"],
        "install": lambda: run(["npm", "install", "-g", "heroku"]),
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# INSTALLER HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def install_gh_cli():
    if check_installed("gh"):
        return
    info("Installing GitHub CLI…")
    run(["apt-get", "install", "-y", "gh"], sudo=True, check=False)
    if not check_installed("gh"):
        for cmd in [
            "curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg",
            "sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg",
            "echo \"deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages focal main\" | sudo tee /etc/apt/sources.list.d/github-cli.list",
            "sudo apt-get update",
            "sudo apt-get install -y gh",
        ]:
            run_shell(cmd, check=False)
    ok("GitHub CLI installed")


def install_protonvpn(gui: bool = True):
    fallback    = "https://repo.protonvpn.com/debian/dists/stable/main/binary-all/protonvpn-stable-release_1.0.8_all.deb"
    listing_url = "https://repo.protonvpn.com/debian/dists/stable/main/binary-all/"
    try:
        req = urllib.request.Request(listing_url, headers={"User-Agent": "apex-framework"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html    = resp.read().decode(errors="ignore")
            matches = re.findall(r"protonvpn-stable-release_[\d.]+_all\.deb", html)
            url     = listing_url + sorted(set(matches))[-1] if matches else fallback
    except Exception:
        url = fallback

    deb_path = Path("/tmp/protonvpn-repo.deb")
    info("Downloading ProtonVPN repo package…")
    try:
        urllib.request.urlretrieve(url, deb_path)
    except Exception as e:
        err(f"Download failed: {e}")
        return

    run(["dpkg", "-i", str(deb_path)], sudo=True, check=False)
    run(["apt-get", "update"], sudo=True, check=False)
    pkg = "proton-vpn-gnome-desktop" if gui else "protonvpn-cli"
    run(["apt-get", "install", "-y", pkg], sudo=True, check=False)
    ok(f"ProtonVPN ({'GUI' if gui else 'CLI'}) installed")


def install_obsidian_flatpak():
    if not check_installed("flatpak"):
        run(["apt-get", "install", "-y", "flatpak"], sudo=True)
    run(["flatpak", "remote-add", "--if-not-exists", "flathub",
         "https://flathub.org/repo/flathub.flatpakrepo"], sudo=True)
    run(["flatpak", "install", "-y", "flathub", "md.obsidian.Obsidian"], sudo=True)
    ok("Obsidian installed via Flatpak")


def install_obsidian_deb() -> bool:
    api_url = "https://api.github.com/repos/obsidianmd/obsidian-releases/releases/latest"
    try:
        req = urllib.request.Request(api_url, headers={"User-Agent": "apex-framework"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        err(f"Couldn't reach GitHub API: {e}")
        return False

    asset_url = next(
        (a["browser_download_url"] for a in data.get("assets", [])
         if a.get("name", "").endswith(".deb") and "amd64" in a.get("name", "")),
        None,
    )
    if not asset_url:
        err("Couldn't find a .deb asset for Obsidian")
        return False

    deb_path = Path("/tmp/obsidian-latest.deb")
    urllib.request.urlretrieve(asset_url, deb_path)
    run(["dpkg", "-i", str(deb_path)], sudo=True, check=False)
    run(["apt-get", "install", "-f", "-y"], sudo=True)
    ok("Obsidian installed from .deb")
    return True

# ─────────────────────────────────────────────────────────────────────────────
# PROXY MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

def fetch_proxy_list() -> Path:
    info("Fetching proxy list from repository…")
    proxy_file = CONFIG_DIR / "proxies.txt"
    try:
        urllib.request.urlretrieve(PROXY_LIST_URL, proxy_file)
        ok(f"Proxy list downloaded → {proxy_file}")
    except Exception as e:
        warn(f"Could not fetch proxy list: {e}")
        proxy_file.write_text(
            "# Default proxy list\n"
            "# Format: type host port [user pass]\n"
            "socks5 127.0.0.1 9050\n"
        )
        info("Created default proxy list (Tor 127.0.0.1:9050)")
    return proxy_file


def configure_proxychains(proxy_file: Path):
    conf = Path("/etc/proxychains4.conf")
    if not conf.exists():
        conf = Path("/etc/proxychains.conf")
    if not conf.exists():
        warn("proxychains config not found — skipping configuration")
        return

    info("Configuring proxychains with fetched proxies…")
    try:
        existing = conf.read_text()
    except PermissionError:
        warn("Need sudo to read proxychains config")
        return

    new_lines    = []
    in_list      = False
    proxy_entries = [
        p.strip() for p in proxy_file.read_text().splitlines()
        if p.strip() and not p.startswith("#")
    ]

    for line in existing.splitlines():
        if line.strip() == "[ProxyList]":
            in_list = True
            new_lines.append(line)
            new_lines.extend(proxy_entries)
            continue
        if in_list and line.strip() and not line.strip().startswith("#"):
            continue   # drop old proxy entries
        new_lines.append(line)

    tmp = Path("/tmp/proxychains_new.conf")
    tmp.write_text("\n".join(new_lines))
    run(["cp", str(tmp), str(conf)], sudo=True)
    ok("Proxychains configured")
    STATE.proxychains_configured = True

# ─────────────────────────────────────────────────────────────────────────────
# GITHUB REPO INTEGRATION
# ─────────────────────────────────────────────────────────────────────────────

def clone_framework_repo():
    if FRAMEWORK_DIR.exists() and (FRAMEWORK_DIR / ".git").exists():
        info("Framework repo exists — pulling latest…")
        run(["git", "-C", str(FRAMEWORK_DIR), "pull", "--ff-only"])
        ok("Repo updated")
    else:
        info(f"Cloning framework → {FRAMEWORK_DIR}…")
        FRAMEWORK_DIR.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", REPO_URL, str(FRAMEWORK_DIR)])
        ok("Framework cloned")
    STATE.repo_cloned = True


def setup_github_cli_from_repo():
    if not check_installed("gh"):
        install_gh_cli()
    info("Configuring GitHub CLI…")
    run(["gh", "config", "set", "git_protocol", "ssh"])
    ok("GitHub CLI configured")

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG FILE MODE
# ─────────────────────────────────────────────────────────────────────────────

def load_config_file(path: str) -> dict:
    p = Path(path).expanduser()
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    text = p.read_text()
    if p.suffix in (".yaml", ".yml"):
        import yaml
        return yaml.safe_load(text)
    return json.loads(text)


def apply_config(config: dict):
    info("Applying configuration from file…")
    sec = config.get("security", {})
    if sec.get("enabled", False):
        STATE.secure_mode_enabled = True
        STATE.security_selected   = sec.get("tools", [])

    STATE.packages_selected   = config.get("packages", {}).get("selected", [])
    STATE.kali_tools_selected = config.get("tools", {}).get("kali", [])
    STATE.dev_tools_selected  = config.get("tools", {}).get("development", [])
    STATE.accounts_selected   = config.get("accounts", {}).get("login", [])

    gdrive = config.get("gdrive", {})
    STATE.gdrive_remote     = gdrive.get("remote")
    STATE.gdrive_path       = gdrive.get("path", "")
    STATE.gdrive_dest       = gdrive.get("dest", str(DEFAULT_GDRIVE_DEST))
    STATE.gdrive_local_sync = gdrive.get("local_sync", False)
    ok("Configuration applied")

# ─────────────────────────────────────────────────────────────────────────────
# ENVIRONMENT SAVE / LOAD  (new feature)
# ─────────────────────────────────────────────────────────────────────────────

ENV_FIELDS = [
    "packages_selected", "accounts_selected", "security_selected",
    "kali_tools_selected", "dev_tools_selected",
    "gdrive_remote", "gdrive_path", "gdrive_dest", "gdrive_local_sync",
    "secure_mode_enabled", "last_locale", "last_keyboard", "last_timezone",
]


def _env_snapshot() -> dict:
    """Capture the current STATE into a saveable dict."""
    return {k: getattr(STATE, k) for k in ENV_FIELDS}


def save_environment():
    """
    Prompt the user for a name and write a named environment YAML/JSON profile
    to ENVS_DIR.  This profile can be loaded later with --load-env <name> or
    at the end-of-session prompt.
    """
    header("SAVE ENVIRONMENT PROFILE")

    name = ask_input(
        "Name for this environment profile",
        default=datetime.now().strftime("env_%Y%m%d_%H%M%S"),
    ).strip()

    if not name:
        warn("No name entered — skipping save.")
        return

    # Sanitise: allow only letters, digits, dash, underscore
    safe_name = re.sub(r"[^\w\-]", "_", name)
    if safe_name != name:
        info(f"Name sanitised to: {safe_name}")

    ENVS_DIR.mkdir(parents=True, exist_ok=True)
    env_path = ENVS_DIR / f"{safe_name}.json"

    snapshot = _env_snapshot()
    snapshot["_saved_at"]  = datetime.now().isoformat()
    snapshot["_apex_version"] = VERSION

    env_path.write_text(json.dumps(snapshot, indent=2))
    success(f"Environment saved → {env_path}")

    # Also generate a ready-to-use YAML config so the user can do
    # `python3 apex_framework.py --config environments/<name>.yaml`
    try:
        import yaml
        yaml_path = ENVS_DIR / f"{safe_name}.yaml"
        yaml.safe_dump(snapshot, yaml_path.open("w"), default_flow_style=False)
        ok(f"YAML config also written → {yaml_path}")
    except ImportError:
        pass  # pyyaml not available — JSON only is fine

    print(
        f"\n{C.GREY}  Load it next time with:{C.RESET}\n"
        f"  {C.CYAN}python3 apex_framework.py --load-env {safe_name}{C.RESET}\n"
        f"  {C.CYAN}python3 apex_framework.py --config {env_path}{C.RESET}\n"
    )


def load_environment(name: str) -> bool:
    """
    Load a named environment profile from ENVS_DIR and apply it to STATE.
    Returns True on success.
    """
    # Accept bare name OR full path
    candidate = Path(name)
    if not candidate.exists():
        candidate = ENVS_DIR / f"{name}.json"
    if not candidate.exists():
        candidate = ENVS_DIR / f"{name}.yaml"
    if not candidate.exists():
        err(f"Environment profile not found: {name}")
        _list_environments()
        return False

    try:
        if candidate.suffix in (".yaml", ".yml"):
            import yaml
            data = yaml.safe_load(candidate.read_text())
        else:
            data = json.loads(candidate.read_text())
    except Exception as e:
        err(f"Could not read environment profile: {e}")
        return False

    for k in ENV_FIELDS:
        if k in data and hasattr(STATE, k):
            setattr(STATE, k, data[k])

    saved_at = data.get("_saved_at", "unknown")
    success(f"Loaded environment '{name}' (saved {saved_at})")
    STATE.config_mode = True
    return True


def _list_environments():
    """Print all saved environment profiles."""
    ENVS_DIR.mkdir(parents=True, exist_ok=True)
    profiles = sorted(ENVS_DIR.glob("*.json")) + sorted(ENVS_DIR.glob("*.yaml"))
    seen     = set()
    unique   = [p for p in profiles if p.stem not in seen and not seen.add(p.stem)]

    if not unique:
        info("No saved environments found in " + str(ENVS_DIR))
        return

    print(f"\n{C.WHITE}{C.BOLD}Saved environment profiles:{C.RESET}")
    for p in unique:
        try:
            data     = json.loads(p.read_text()) if p.suffix == ".json" else {}
            saved_at = data.get("_saved_at", "")
        except Exception:
            saved_at = ""
        ts = f"  {C.GREY}({saved_at[:19]}){C.RESET}" if saved_at else ""
        print(f"  {C.RED}•{C.RESET} {p.stem}{ts}")
    print()


def list_and_pick_environment() -> Optional[str]:
    """Show saved environments and let user choose one."""
    ENVS_DIR.mkdir(parents=True, exist_ok=True)
    profiles = sorted({p.stem for p in ENVS_DIR.glob("*.json")} |
                       {p.stem for p in ENVS_DIR.glob("*.yaml")})

    if not profiles:
        warn("No saved environment profiles found.")
        return None

    print(f"\n{C.WHITE}{C.BOLD}Available environment profiles:{C.RESET}")
    for i, name in enumerate(profiles, 1):
        print(f"  {C.RED}{i}{C.RESET}. {name}")
    print(f"  {C.RED}0{C.RESET}. Cancel")

    choice = input(f"{C.WHITE}> {C.RESET}").strip()
    if choice == "0" or not choice:
        return None
    if choice.isdigit() and 1 <= int(choice) <= len(profiles):
        return profiles[int(choice) - 1]
    warn("Invalid selection.")
    return None

# ─────────────────────────────────────────────────────────────────────────────
# BACKUP / RESTORE to removable media
# ─────────────────────────────────────────────────────────────────────────────

def find_media_roots() -> List[Path]:
    user  = _USER
    roots = []
    for base in (f"/media/{user}", f"/run/media/{user}", "/media"):
        p = Path(base)
        if p.exists():
            roots += [d for d in p.iterdir() if d.is_dir()]
    seen, uniq = set(), []
    for r in roots:
        if str(r) not in seen:
            uniq.append(r)
            seen.add(str(r))
    return uniq


def pick_backup_location(prompt_label: str) -> Optional[Path]:
    roots      = find_media_roots()
    candidates = [r / BACKUP_FOLDER_NAME for r in roots]
    existing   = [c for c in candidates if c.exists()]
    options    = existing if existing else candidates

    print(f"\n{C.WHITE}{prompt_label}{C.RESET}")

    if not options:
        warn("No removable drives detected.")

    for i, c in enumerate(options, 1):
        tag = f"  {C.GREEN}(backup found){C.RESET}" if c in existing else ""
        print(f"  {C.RED}{i}{C.RESET}. {c}{tag}")
    print(f"  {C.RED}0{C.RESET}. Enter a custom path")
    print(f"  {C.RED}s{C.RESET}. Skip")

    while True:
        choice = input(f"{C.WHITE}> {C.RESET}").strip().lower()
        if choice in ("s", ""):
            return None
        if choice == "0" or not options:
            custom = input(f"{C.WHITE}Enter full path: {C.RESET}").strip()
            return Path(custom).expanduser() / BACKUP_FOLDER_NAME if custom else None
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice) - 1]
        warn("Invalid choice — try again or type 's' to skip.")


def backup_session():
    header("BACKUP SESSION")
    if not ask_yes_no("Back up rclone config + selections to persistent storage?", default=True):
        warn("Skipped backup.")
        return

    loc = pick_backup_location("Where should the backup be saved?")
    if loc is None:
        warn("Skipped backup.")
        return

    loc.mkdir(parents=True, exist_ok=True)

    rclone_conf = Path.home() / ".config" / "rclone" / "rclone.conf"
    if rclone_conf.exists():
        shutil.copy(rclone_conf, loc / "rclone.conf")
        ok("rclone.conf copied")
    else:
        info("No rclone.conf found to back up.")

    manifest = {k: getattr(STATE, k) for k in ENV_FIELDS}
    manifest["_saved_at"]     = datetime.now().isoformat()
    manifest["_apex_version"] = VERSION
    (loc / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2))
    ok(f"Backup written → {loc}")
    warn("This backup contains credentials — treat it as sensitive.")


def restore_session():
    header("RESTORE PREVIOUS SESSION")
    if not ask_yes_no("Restore from a previous backup?", default=True):
        info("Starting fresh.")
        return

    loc = pick_backup_location("Looking for previous Apex backup…")
    if loc is None or not loc.exists():
        warn("No backup found — starting fresh.")
        return

    manifest_path = loc / MANIFEST_NAME
    if manifest_path.exists():
        try:
            data = json.loads(manifest_path.read_text())
            for k in ENV_FIELDS:
                if k in data and hasattr(STATE, k):
                    setattr(STATE, k, data[k])
            ok("Restored previous selections.")
        except Exception as e:
            warn(f"Couldn't read manifest: {e}")

    rclone_backup = loc / "rclone.conf"
    if rclone_backup.exists():
        dest = Path.home() / ".config" / "rclone"
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy(rclone_backup, dest / "rclone.conf")
        ok("Restored rclone.conf")
    else:
        info("No rclone.conf in backup.")

# ─────────────────────────────────────────────────────────────────────────────
# LOCALE / KEYBOARD / TIMEZONE WIZARD  (pre-boot)
# ─────────────────────────────────────────────────────────────────────────────

def step_locale_wizard():
    """
    Runs before the main setup steps.
    Lets the user quickly set language/locale, keyboard layout, and timezone.
    Pre-fills from last run (STATE.last_locale etc.) so it's instant to skip.
    """
    header("LOCALE / KEYBOARD / TIMEZONE")

    print(
        f"  {C.GREY}Set system locale, keyboard layout, and timezone before setup.{C.RESET}\n"
        f"  {C.GREY}Press Enter to keep the current value, or type a new one.{C.RESET}\n"
    )

    # ── Current values (from system) ─────────────────────────────────────
    def _sys(cmd: str, fallback: str = "") -> str:
        try:
            r = subprocess.run(cmd.split(), capture_output=True, text=True)
            return r.stdout.strip()
        except Exception:
            return fallback

    cur_locale = _sys("localectl status", "")
    cur_tz     = _sys("timedatectl show --property=Timezone --value", "")

    # Extract locale string from localectl output e.g. "System Locale: LANG=en_US.UTF-8"
    m = re.search(r"LANG=(\S+)", cur_locale)
    cur_locale_str = m.group(1) if m else "en_US.UTF-8"

    # Extract keyboard layout from localectl output e.g. "VC Keymap: se"
    km = re.search(r"VC Keymap:\s+(\S+)", cur_locale)
    cur_kb = km.group(1) if km else "us"

    # Suggest last-used values, falling back to system values
    suggest_locale = STATE.last_locale   or cur_locale_str
    suggest_kb     = STATE.last_keyboard or cur_kb
    suggest_tz     = STATE.last_timezone or cur_tz

    print(f"  Current locale:   {C.CYAN}{cur_locale_str}{C.RESET}")
    print(f"  Current keyboard: {C.CYAN}{cur_kb}{C.RESET}")
    print(f"  Current timezone: {C.CYAN}{cur_tz}{C.RESET}\n")

    if not ask_yes_no("Change locale / keyboard / timezone?", default=False):
        info("Skipping locale wizard.")
        return

    # ── Locale ────────────────────────────────────────────────────────────
    new_locale = ask_input("Locale (e.g. en_US.UTF-8, sv_SE.UTF-8)", default=suggest_locale)
    if new_locale and new_locale != cur_locale_str:
        info(f"Setting locale to {new_locale}…")
        run_shell(f"sudo localectl set-locale LANG={new_locale}", check=False)
        ok(f"Locale set to {new_locale}")
    STATE.last_locale = new_locale

    # ── Keyboard ──────────────────────────────────────────────────────────
    new_kb = ask_input("Keyboard layout (e.g. us, se, de, gb)", default=suggest_kb)
    if new_kb and new_kb != cur_kb:
        info(f"Setting keyboard to {new_kb}…")
        run_shell(f"sudo localectl set-keymap {new_kb}", check=False)
        # Also set X11 keymap for GUI sessions
        run_shell(f"sudo localectl set-x11-keymap {new_kb}", check=False)
        ok(f"Keyboard set to {new_kb}")
    STATE.last_keyboard = new_kb

    # ── Timezone ──────────────────────────────────────────────────────────
    print(f"\n  {C.GREY}Tip: run `timedatectl list-timezones` to see all options.{C.RESET}")
    new_tz = ask_input("Timezone (e.g. Europe/Stockholm, UTC, US/Eastern)", default=suggest_tz)
    if new_tz and new_tz != cur_tz:
        info(f"Setting timezone to {new_tz}…")
        run_shell(f"sudo timedatectl set-timezone {new_tz}", check=False)
        ok(f"Timezone set to {new_tz}")
    STATE.last_timezone = new_tz

    success("Locale / keyboard / timezone configured.")

# ─────────────────────────────────────────────────────────────────────────────
# SETUP STEPS
# ─────────────────────────────────────────────────────────────────────────────

def step_security_first():
    header("STEP 0 — SECURITY FIRST")

    if STATE.config_mode:
        info("Secure mode: " + ("ENABLED via config" if STATE.secure_mode_enabled else "not enabled"))
    else:
        STATE.secure_mode_enabled = ask_yes_no(
            "Enable secure mode? (VPN/proxy before network operations)", default=False
        )

    if not STATE.secure_mode_enabled:
        warn("Secure mode disabled — proceeding without VPN/proxy wrapper")
        return

    sec_names = list(SECURITY_TOOLS.keys())
    chosen = (
        STATE.security_selected
        if STATE.config_mode and STATE.security_selected
        else toggle_select(
            "Select security tools to install",
            sec_names,
            preselected=STATE.security_selected or None,
            all_default=False,
            descriptions={k: v.description for k, v in SECURITY_TOOLS.items()},
        )
    )
    STATE.security_selected = chosen

    for name in chosen:
        # ProtonVPN is handled via dedicated installer
        if name in ("ProtonVPN (GUI)", "ProtonVPN (CLI)"):
            continue
        tool = SECURITY_TOOLS[name]
        try:
            tool.install()
        except Exception as e:
            err(f"Failed to install {name}: {e}")

    # ProtonVPN dedicated installers (fixed: names now match SECURITY_TOOLS keys)
    if "ProtonVPN (GUI)" in chosen:
        install_protonvpn(gui=True)
    if "ProtonVPN (CLI)" in chosen:
        install_protonvpn(gui=False)

    if "Proxychains4" in chosen:
        proxy_file = fetch_proxy_list()
        configure_proxychains(proxy_file)

    if "MAC Changer" in chosen:
        info("MAC Changer ready — run: sudo macchanger -r <interface>")

    ok("Security layer configured")


def step_system_update():
    header("STEP 1 — SYSTEM UPDATE & UPGRADE")
    if not ask_yes_no("Run apt update + upgrade?", default=True):
        warn("Skipping system update.")
        return
    run(["apt-get", "update"], sudo=True)
    run(["apt-get", "upgrade", "-y"], sudo=True)
    ok("System updated")


def step_base_packages():
    header("STEP 2 — BASE PACKAGES")
    pkg_names = list(BASE_PACKAGES.keys())

    chosen = (
        STATE.packages_selected
        if STATE.config_mode and STATE.packages_selected
        else toggle_select(
            "Select base packages to install",
            pkg_names,
            preselected=STATE.packages_selected or None,
            all_default=True,
            descriptions={k: v.description for k, v in BASE_PACKAGES.items()},
        )
    )
    STATE.packages_selected = chosen

    for name in chosen:
        try:
            BASE_PACKAGES[name].install()
        except Exception as e:
            err(f"Failed to install {name}: {e}")


def step_github():
    header("STEP 3 — GITHUB INTEGRATION")
    if not ask_yes_no("Clone/update framework repo & configure gh CLI?", default=True):
        warn("Skipping GitHub integration.")
        return
    clone_framework_repo()
    setup_github_cli_from_repo()


def step_tool_profiles():
    header("STEP 4 — TOOL PROFILES")

    # Kali / pen-testing tools
    kali_names = [
        k for k in SECURITY_TOOLS
        if k not in ("ProtonVPN (GUI)", "ProtonVPN (CLI)", "Proxychains4",
                     "MAC Changer", "Tor", "UFW Firewall", "KeePassXC", "WireGuard")
    ]
    if ask_yes_no("Install Kali-style pen-testing tools?", default=False):
        chosen_kali = (
            STATE.kali_tools_selected
            if STATE.config_mode and STATE.kali_tools_selected
            else toggle_select(
                "Kali-style tools",
                kali_names,
                preselected=STATE.kali_tools_selected or None,
                all_default=False,
                descriptions={k: SECURITY_TOOLS[k].description for k in kali_names},
            )
        )
        STATE.kali_tools_selected = chosen_kali
        for name in chosen_kali:
            try:
                SECURITY_TOOLS[name].install()
            except Exception as e:
                err(f"Failed to install {name}: {e}")

    # Development tools
    dev_names = list(DEV_TOOLS.keys())
    if ask_yes_no("Install development tools?", default=True):
        chosen_dev = (
            STATE.dev_tools_selected
            if STATE.config_mode and STATE.dev_tools_selected
            else toggle_select(
                "Development tools",
                dev_names,
                preselected=STATE.dev_tools_selected or None,
                all_default=False,
                descriptions={k: DEV_TOOLS[k].description for k in dev_names},
            )
        )
        STATE.dev_tools_selected = chosen_dev
        for name in chosen_dev:
            try:
                DEV_TOOLS[name].install()
            except Exception as e:
                err(f"Failed to install {name}: {e}")


def step_obsidian():
    header("STEP 5 — OBSIDIAN")
    if not ask_yes_no("Install Obsidian?", default=False):
        warn("Skipping Obsidian.")
        return

    method_names = ["Flatpak (recommended)", ".deb (direct download)"]
    method = toggle_select("Install method", method_names, all_default=False)

    if "Flatpak (recommended)" in method:
        install_obsidian_flatpak()
    elif ".deb (direct download)" in method:
        install_obsidian_deb()


def step_account_logins():
    header("STEP 6 — ACCOUNT LOGINS")
    acct_names = list(ACCOUNTS.keys())

    chosen = (
        STATE.accounts_selected
        if STATE.config_mode and STATE.accounts_selected
        else toggle_select(
            "Select accounts to log in to",
            acct_names,
            preselected=STATE.accounts_selected or None,
            all_default=False,
        )
    )
    STATE.accounts_selected = chosen

    for name in chosen:
        acct = ACCOUNTS[name]
        info(f"Setting up: {name}")

        if acct["type"] == "browser":
            info(f"Opening browser → {acct['url']}")
            subprocess.Popen(["xdg-open", acct["url"]], start_new_session=True)

        elif acct["type"] == "cli":
            if not check_installed(acct["check"]):
                warn(f"{acct['check']} not installed — attempting install…")
                install_fn = acct.get("install")
                if install_fn:
                    install_fn()

            if check_installed(acct["check"]):
                try:
                    subprocess.run(acct["login_cmd"], check=False)
                except Exception as e:
                    err(f"Login failed for {name}: {e}")
            else:
                warn(f"Skipping {name} — binary not available")


def step_gdrive_sync():
    header("STEP 7 — GOOGLE DRIVE SYNC")

    if not check_installed("rclone"):
        info("rclone not found — installing…")
        run_shell("curl https://rclone.org/install.sh | sudo bash", check=False)

    if not check_installed("rclone"):
        warn("rclone could not be installed — skipping GDrive sync")
        return

    # ── Remote configuration ──────────────────────────────────────────────
    existing_conf = Path.home() / ".config" / "rclone" / "rclone.conf"
    if not STATE.gdrive_remote:
        if existing_conf.exists():
            # Try to read existing remote name from rclone.conf
            try:
                for line in existing_conf.read_text().splitlines():
                    m = re.match(r"^\[(.+)\]$", line.strip())
                    if m:
                        STATE.gdrive_remote = m.group(1)
                        info(f"Found existing rclone remote: {STATE.gdrive_remote}")
                        break
            except Exception:
                pass

        if not STATE.gdrive_remote:
            if ask_yes_no("Configure a new Google Drive remote in rclone?", default=True):
                info("Launching rclone config — follow the prompts to add a 'drive' remote.")
                subprocess.run(["rclone", "config"], check=False)
                STATE.gdrive_remote = ask_input("Remote name you just configured", default="gdrive")
            else:
                warn("Skipping GDrive remote configuration.")
                return

    # ── Cloud sync path ───────────────────────────────────────────────────
    if not STATE.gdrive_dest:
        STATE.gdrive_dest = str(DEFAULT_GDRIVE_DEST)
    STATE.gdrive_path = ask_input(
        f"Google Drive folder to sync (leave blank for root)",
        default=STATE.gdrive_path or "",
    )
    remote_target = (
        f"{STATE.gdrive_remote}:{STATE.gdrive_path}"
        if STATE.gdrive_path
        else f"{STATE.gdrive_remote}:"
    )
    dest_path = Path(ask_input("Local destination folder", default=STATE.gdrive_dest))
    STATE.gdrive_dest = str(dest_path)
    ensure_dir(dest_path)

    info(f"Syncing {remote_target} → {dest_path} …")
    run(["rclone", "copy", remote_target, str(dest_path), "--progress"], check=False)
    ok("Google Drive sync complete")

    # ── Local $USER-gdrive folder (new feature) ────────────────────────────
    if ask_yes_no(
        f"Also create a local gdrive mirror at {GDRIVE_SYNC_DIR} (auto-syncs to Drive)?",
        default=False,
    ):
        ensure_dir(GDRIVE_SYNC_DIR)
        STATE.gdrive_local_sync = True
        info(f"Created {GDRIVE_SYNC_DIR}")

        # Optionally sync it now
        if ask_yes_no("Sync to Google Drive now?", default=True):
            run(
                ["rclone", "sync", str(GDRIVE_SYNC_DIR), remote_target, "--progress"],
                check=False,
            )
            ok("Synced local gdrive folder to Drive")

        # Write a convenience sync script into the repo folder
        sync_script = FRAMEWORK_DIR / "gdrive_sync.sh"
        sync_script.write_text(
            "#!/usr/bin/env bash\n"
            f"# Auto-generated by Apex Multi Tools v{VERSION}\n"
            f"# Syncs {GDRIVE_SYNC_DIR} ↔ {remote_target}\n\n"
            f'echo "[*] Syncing {GDRIVE_SYNC_DIR} → {remote_target}…"\n'
            f"rclone sync \"{GDRIVE_SYNC_DIR}\" \"{remote_target}\" --progress\n"
            f'echo "[*] Pulling {remote_target} → {GDRIVE_SYNC_DIR}…"\n'
            f"rclone copy \"{remote_target}\" \"{GDRIVE_SYNC_DIR}\" --progress\n"
            f'echo "[✓] Done"\n'
        )
        sync_script.chmod(0o755)
        ok(f"Sync helper script written → {sync_script}")
        info(f"Run it anytime: bash {sync_script}")

    else:
        STATE.gdrive_local_sync = False


def step_save_environment():
    """End-of-run prompt: offer to save the current environment profile."""
    header("STEP 8 — SAVE ENVIRONMENT PROFILE")

    print(
        f"  {C.GREY}Save your current tool selections, accounts, and settings as a named{C.RESET}\n"
        f"  {C.GREY}profile.  Load it on any future run with:{C.RESET}\n"
        f"  {C.CYAN}  python3 apex_framework.py --load-env <name>{C.RESET}\n"
    )

    if ask_yes_no("Save this environment profile now?", default=True):
        save_environment()
    else:
        warn("Skipping environment save.")


def step_backup():
    backup_session()


def step_restore():
    restore_session()

# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def print_summary():
    header("SESSION SUMMARY")

    sections = [
        ("Base packages",    STATE.packages_selected),
        ("Security tools",   STATE.security_selected),
        ("Kali tools",       STATE.kali_tools_selected),
        ("Dev tools",        STATE.dev_tools_selected),
        ("Accounts",         STATE.accounts_selected),
    ]

    for label, items in sections:
        if items:
            print(f"  {C.WHITE}{label}:{C.RESET}")
            for it in items:
                print(f"    {C.GREEN}✓{C.RESET} {it}")

    if STATE.gdrive_remote:
        print(f"\n  {C.WHITE}Google Drive:{C.RESET} {STATE.gdrive_remote}:{STATE.gdrive_path}")
    if STATE.gdrive_local_sync:
        print(f"  {C.WHITE}GDrive local folder:{C.RESET} {GDRIVE_SYNC_DIR}")
    if STATE.last_timezone:
        print(f"  {C.WHITE}Timezone:{C.RESET} {STATE.last_timezone}")

    print(f"\n  {C.GREY}Full log: {LOGS_DIR}{C.RESET}\n")
    success("Apex Multi Tools setup complete.")

# ─────────────────────────────────────────────────────────────────────────────
# ARGUMENT PARSER
# ─────────────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="apex_framework.py",
        description="Apex Multi Tools — Linux Mint live USB bootstrapper",
    )
    p.add_argument("--config",      "-c", metavar="FILE",  help="Load selections from YAML/JSON config file")
    p.add_argument("--load-env",          metavar="NAME",  help="Load a named saved environment profile")
    p.add_argument("--list-envs",         action="store_true", help="List all saved environment profiles and exit")
    p.add_argument("--save-env",          action="store_true", help="Save current state as a named profile and exit")
    p.add_argument("--restore-only",      action="store_true", help="Only restore from backup, then exit")
    p.add_argument("--backup-only",       action="store_true", help="Only back up current state, then exit")
    p.add_argument("--secure-mode", "-s", action="store_true", help="Force secure mode")
    p.add_argument("--no-banner",         action="store_true", help="Skip banner display")
    p.add_argument("--version",           action="version",    version=f"Apex Multi Tools v{VERSION}")
    return p

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    global logger, STATE

    # ── Boot logger first ────────────────────────────────────────────────
    logger = ApexLogger()

    # ── Load last state ──────────────────────────────────────────────────
    STATE = ApexState.load()

    # ── Parse args ───────────────────────────────────────────────────────
    args = build_parser().parse_args()

    # ── Quick-exit commands ───────────────────────────────────────────────
    if args.list_envs:
        _list_environments()
        sys.exit(0)

    if args.save_env:
        save_environment()
        sys.exit(0)

    # ── Banner ────────────────────────────────────────────────────────────
    if not args.no_banner:
        banner()

    # ── Config file / named environment ───────────────────────────────────
    if args.load_env:
        if not load_environment(args.load_env):
            sys.exit(1)

    if args.config:
        try:
            cfg = load_config_file(args.config)
            apply_config(cfg)
            STATE.config_mode = True
            STATE.config_file = args.config
        except FileNotFoundError as e:
            err(str(e))
            sys.exit(1)

    if args.secure_mode:
        STATE.secure_mode_enabled = True

    # ── --restore-only ─────────────────────────────────────────────────
    if args.restore_only:
        sudo_keepalive()
        step_restore()
        sys.exit(0)

    # ── --backup-only ──────────────────────────────────────────────────
    if args.backup_only:
        step_backup()
        sys.exit(0)

    # ─────────────────────────────────────────────────────────────────────
    # FULL INTERACTIVE FLOW
    # ─────────────────────────────────────────────────────────────────────
    try:
        sudo_keepalive()

        # Restore previous session (optional)
        step_restore()

        # PRE-BOOT: locale / keyboard / timezone
        step_locale_wizard()

        # Main setup pipeline
        step_security_first()
        step_system_update()
        step_base_packages()
        step_github()
        step_tool_profiles()
        step_obsidian()
        step_account_logins()
        step_gdrive_sync()

        # Save environment profile
        step_save_environment()

        # Physical backup to removable media
        step_backup()

        # Persist cache state
        STATE.save()

        print_summary()

    except KeyboardInterrupt:
        print(f"\n\n{C.YELLOW}[ABORT]{C.RESET} Interrupted by user.")
        STATE.save()
        sys.exit(130)
    except Exception as e:
        err(f"Unexpected error: {e}")
        logger.error(f"Fatal: {e}")
        STATE.save()
        sys.exit(1)


if __name__ == "__main__":
    main()
