#!/usr/bin/env python3
"""
================================================================================
 APEX MULTI TOOLS — INTERACTIVE CLI FRAMEWORK
================================================================================
 Professional environment bootstrapper for Linux Mint live USB.

 Modes:
   Interactive (default) — wizard-driven setup
   --config FILE         — pre-defined YAML/JSON selections, non-interactive
   --restore-only        — restore previous session from persistent storage
   --backup-only         — back up current session to persistent storage
   --secure-mode         — force VPN/proxy before any network operations

 Architecture:
   1. Security Layer (VPN, proxychains, macchanger)
   2. System Foundation (update, packages)
   3. Tool Profiles (Kali-style / Development)
   4. Account Integration (GitHub, Google, etc.)
   5. Cloud Sync (rclone Google Drive)
   6. Session Persistence (backup/restore)

 Run:  python3 apex_framework.py
================================================================================
"""

import os
import re
import sys
import json
import shutil
import argparse
import subprocess
import urllib.request
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Callable
from enum import Enum, auto

# ------------------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------------------

REPO_URL = "https://github.com/multitools-ap-mvp/apex-multi-tools"
REPO_RAW_BASE = "https://raw.githubusercontent.com/multitools-ap-mvp/apex-multi-tools/main"
PROXY_LIST_URL = f"{REPO_RAW_BASE}/config/proxies.txt"

FRAMEWORK_DIR = Path.home() / "ApexMultiTools"
LOGS_DIR = FRAMEWORK_DIR / "logs"
CONFIG_DIR = FRAMEWORK_DIR / "config"
CACHE_DIR = FRAMEWORK_DIR / ".cache"

BACKUP_FOLDER_NAME = "ApexMultiTools_Backup"
MANIFEST_NAME = "apex_manifest.json"
STATE_FILE = CACHE_DIR / "apex_state.json"

DEFAULT_GDRIVE_DEST = Path.home() / "Desktop" / "Backup-GDrive"


# ------------------------------------------------------------------------
# COLOR THEME — Apex Red / Black
# ------------------------------------------------------------------------
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    RED    = "\033[91m"
    BRED   = "\033[1;91m"
    WHITE  = "\033[97m"
    GREY   = "\033[90m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    BLUE   = "\033[94m"
    MAGENTA = "\033[95m"


# ------------------------------------------------------------------------
# LOGGING SYSTEM
# ------------------------------------------------------------------------
class ApexLogger:
    def __init__(self):
        self.session_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = LOGS_DIR / f"apex_{self.session_time}.log"
        self._ensure_dirs()
        self._write_header()

    def _ensure_dirs(self):
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _write_header(self):
        header = f"""
{'='*70}
 APEX MULTI TOOLS — SESSION LOG
 Started: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
 User: {os.environ.get('USER', 'unknown')}
 Host: {os.uname().nodename}
{'='*70}
"""
        self.log_file.write_text(header)

    def log(self, level: str, msg: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] [{level}] {msg}"
        with open(self.log_file, "a") as f:
            f.write(line + "\n")

    def debug(self, msg): self.log("DEBUG", msg)
    def info(self, msg): self.log("INFO", msg)
    def warn(self, msg): self.log("WARN", msg)
    def error(self, msg): self.log("ERROR", msg)
    def cmd(self, cmd_list): self.log("CMD", " ".join(cmd_list))


logger = None  # Initialized in main()


# ------------------------------------------------------------------------
# STATE MANAGEMENT
# ------------------------------------------------------------------------
@dataclass
class ApexState:
    """Persistent state across sessions."""
    packages_selected: List[str] = field(default_factory=list)
    accounts_selected: List[str] = field(default_factory=list)
    security_selected: List[str] = field(default_factory=list)
    kali_tools_selected: List[str] = field(default_factory=list)
    dev_tools_selected: List[str] = field(default_factory=list)
    gdrive_remote: Optional[str] = None
    gdrive_path: str = ""
    gdrive_dest: str = ""
    secure_mode_enabled: bool = False
    proxychains_configured: bool = False
    repo_cloned: bool = False
    config_mode: bool = False
    config_file: Optional[str] = None

    def save(self):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(asdict(self), indent=2))
        logger.info("State saved to cache")

    @classmethod
    def load(cls) -> "ApexState":
        if STATE_FILE.exists():
            try:
                data = json.loads(STATE_FILE.read_text())
                return cls(**data)
            except Exception as e:
                logger.warn(f"Could not load state: {e}")
        return cls()


STATE = ApexState()


# ------------------------------------------------------------------------
# UI HELPERS
# ------------------------------------------------------------------------
def header(text: str):
    width = 70
    print(f"\n{C.BRED}{'═' * width}{C.RESET}")
    print(f"{C.BRED}{C.BOLD}  {text}{C.RESET}")
    print(f"{C.BRED}{'═' * width}{C.RESET}\n")
    logger.info(f"HEADER: {text}")


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
        ░  ░               ░    ░
"""
    print(f"{C.RED}{art}{C.RESET}")
    print(f"{C.WHITE}{C.BOLD}        MULTI TOOLS — INTERACTIVE CLI FRAMEWORK{C.RESET}")
    print(f"{C.GREY}        Linux Mint Live USB Environment Bootstrapper{C.RESET}")
    print(f"{C.GREY}        v2.0 — Security-First | Config-Driven | Extensible{C.RESET}\n")


def info(msg):  
    print(f"{C.CYAN}[*]{C.RESET} {msg}")
    logger.info(msg)


def ok(msg):    
    print(f"{C.GREEN}[OK]{C.RESET} {msg}")
    logger.info(f"OK: {msg}")


def warn(msg):  
    print(f"{C.YELLOW}[!]{C.RESET} {msg}")
    logger.warn(msg)


def err(msg):   
    print(f"{C.RED}[ERROR]{C.RESET} {msg}")
    logger.error(msg)


def success(msg):
    print(f"{C.GREEN}{C.BOLD}[✓]{C.RESET} {msg}")
    logger.info(f"SUCCESS: {msg}")


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        ans = input(f"{C.WHITE}{prompt} {C.GREY}{suffix} {C.RESET}").strip().lower()
        if ans == "":
            return default
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        warn("Please answer y or n.")


def ask_input(prompt: str, default: str = "") -> str:
    suffix = f" {C.GREY}[default: {default}]{C.RESET}" if default else ""
    result = input(f"{C.WHITE}{prompt}{suffix}{C.RESET}\n> ").strip()
    return result if result else default


def toggle_select(title, names, preselected=None, all_default=True, descriptions=None):
    if preselected is not None:
        pre = set(preselected)
        selected = {n: (n in pre) for n in names}
    else:
        selected = {n: all_default for n in names}

    while True:
        print(f"\n{C.WHITE}{C.BOLD}{title}:{C.RESET}")
        for i, name in enumerate(names, 1):
            mark = f"{C.GREEN}[x]{C.RESET}" if selected[name] else f"{C.GREY}[ ]{C.RESET}"
            extra = f" {C.GREY}({descriptions[name]}){C.RESET}" if descriptions and name in descriptions else ""
            print(f"  {C.RED}{i:2d}{C.RESET}. {mark} {name}{extra}")
        print(f"\n{C.GREY}Type numbers to toggle (e.g. 2,5,7), 'a' = all, 'd' = none, 'c' = confirm{C.RESET}")
        choice = input(f"{C.WHITE}> {C.RESET}").strip().lower()

        if choice == "c":
            break
        elif choice == "a":
            selected = {n: True for n in names}
        elif choice == "d":
            selected = {n: False for n in names}
        else:
            try:
                idxs = [int(x.strip()) for x in choice.split(",") if x.strip()]
                for i in idxs:
                    if 1 <= i <= len(names):
                        n = names[i - 1]
                        selected[n] = not selected[n]
            except ValueError:
                warn("Couldn't parse that input, try again.")

    return [n for n in names if selected[n]]


# ------------------------------------------------------------------------
# COMMAND RUNNER — Robust with retry & logging
# ------------------------------------------------------------------------
def run(cmd, sudo=False, capture=False, check=True, retries=0, retry_delay=3):
    """
    Run a shell command with logging, optional sudo, and retry logic.
    """
    if sudo and os.geteuid() != 0:
        cmd = ["sudo"] + cmd

    logger.cmd(cmd)

    attempt = 0
    while True:
        attempt += 1
        try:
            if capture:
                result = subprocess.run(
                    cmd, check=check, text=True,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT
                )
                logger.debug(f"Output: {result.stdout[:500] if result.stdout else 'none'}")
                return result
            return subprocess.run(cmd, check=check)
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed (attempt {attempt}): {' '.join(cmd)} — {e}")
            if attempt <= retries:
                warn(f"Retrying in {retry_delay}s... (attempt {attempt}/{retries+1})")
                import time
                time.sleep(retry_delay)
            else:
                if check:
                    raise
                return e


def sudo_keepalive():
    info("Requesting sudo access for system operations...")
    subprocess.run(["sudo", "-v"])
    ok("Sudo access granted")


def check_installed(binary: str) -> bool:
    """Check if a binary is available in PATH."""
    return shutil.which(binary) is not None


def ensure_dir(path: Path):
    """Ensure directory exists."""
    path.mkdir(parents=True, exist_ok=True)
    return path


# ------------------------------------------------------------------------
# TOOL REGISTRY — Extensible tool definitions
# ------------------------------------------------------------------------
class ToolCategory(Enum):
    PACKAGE = auto()
    SPECIAL = auto()
    SCRIPT = auto()


@dataclass
class Tool:
    name: str
    category: ToolCategory
    install_cmd: Optional[List[str]] = None
    check_binary: Optional[str] = None
    description: str = ""
    pre_install: Optional[Callable] = None
    post_install: Optional[Callable] = None
    apt_package: Optional[str] = None

    def is_installed(self) -> bool:
        if self.check_binary:
            return check_installed(self.check_binary)
        if self.apt_package:
            result = run(["dpkg", "-l", self.apt_package], capture=True, check=False)
            return result.returncode == 0 and "ii" in result.stdout
        return False

    def install(self):
        if self.is_installed():
            ok(f"{self.name} already installed, skipping")
            return

        info(f"Installing {self.name}...")
        if self.pre_install:
            self.pre_install()

        if self.category == ToolCategory.PACKAGE and self.apt_package:
            run(["apt-get", "install", "-y", self.apt_package], sudo=True)
        elif self.category == ToolCategory.SPECIAL and self.install_cmd:
            for cmd in self.install_cmd:
                if isinstance(cmd, str):
                    subprocess.run(cmd, shell=True, check=True)
                else:
                    run(cmd, sudo=True)
        elif self.category == ToolCategory.SCRIPT and self.install_cmd:
            for cmd in self.install_cmd:
                subprocess.run(cmd, shell=True, check=True)

        if self.post_install:
            self.post_install()

        ok(f"{self.name} installed")


# ------------------------------------------------------------------------
# TOOL DEFINITIONS
# ------------------------------------------------------------------------

# Base packages
BASE_PACKAGES = {
    "Git": Tool("Git", ToolCategory.PACKAGE, apt_package="git", check_binary="git", description="Version control"),
    "Curl": Tool("Curl", ToolCategory.PACKAGE, apt_package="curl", check_binary="curl", description="HTTP client"),
    "Wget": Tool("Wget", ToolCategory.PACKAGE, apt_package="wget", check_binary="wget", description="File downloader"),
    "Build Essentials": Tool("Build Essentials", ToolCategory.PACKAGE, apt_package="build-essential", description="Compilers & make"),
    "Python3 & pip": Tool("Python3 & pip", ToolCategory.PACKAGE, apt_package="python3-pip", check_binary="pip3", description="Python package manager"),
    "Python venv": Tool("Python venv", ToolCategory.PACKAGE, apt_package="python3-venv", description="Virtual environments"),
    "Vim": Tool("Vim", ToolCategory.PACKAGE, apt_package="vim", check_binary="vim", description="Text editor"),
    "htop": Tool("htop", ToolCategory.PACKAGE, apt_package="htop", check_binary="htop", description="Process viewer"),
    "Net-tools": Tool("Net-tools", ToolCategory.PACKAGE, apt_package="net-tools", check_binary="ifconfig", description="Network utilities"),
    "OpenSSH": Tool("OpenSSH", ToolCategory.PACKAGE, apt_package="openssh-client", check_binary="ssh", description="SSH client"),
    "Flatpak": Tool("Flatpak", ToolCategory.PACKAGE, apt_package="flatpak", check_binary="flatpak", description="App sandboxing"),
    "Unzip": Tool("Unzip", ToolCategory.PACKAGE, apt_package="unzip", check_binary="unzip", description="Archive extractor"),
    "jq": Tool("jq", ToolCategory.PACKAGE, apt_package="jq", check_binary="jq", description="JSON processor"),
    "Tree": Tool("Tree", ToolCategory.PACKAGE, apt_package="tree", check_binary="tree", description="Directory tree viewer"),
    "Tmux": Tool("Tmux", ToolCategory.PACKAGE, apt_package="tmux", check_binary="tmux", description="Terminal multiplexer"),
    "Neofetch": Tool("Neofetch", ToolCategory.PACKAGE, apt_package="neofetch", check_binary="neofetch", description="System info display"),
}

# Security / Kali-style tools
SECURITY_TOOLS = {
    "Proxychains4": Tool("Proxychains4", ToolCategory.PACKAGE, apt_package="proxychains4", check_binary="proxychains4", description="Proxy routing"),
    "MAC Changer": Tool("MAC Changer", ToolCategory.PACKAGE, apt_package="macchanger", check_binary="macchanger", description="MAC address spoofing"),
    "Tor": Tool("Tor", ToolCategory.PACKAGE, apt_package="tor", check_binary="tor", description="Anonymity network"),
    "UFW Firewall": Tool("UFW Firewall", ToolCategory.PACKAGE, apt_package="ufw", check_binary="ufw", description="Uncomplicated firewall"),
    "KeePassXC": Tool("KeePassXC", ToolCategory.PACKAGE, apt_package="keepassxc", check_binary="keepassxc", description="Password manager"),
    "WireGuard": Tool("WireGuard", ToolCategory.PACKAGE, apt_package="wireguard", check_binary="wg", description="VPN protocol"),
    "Nmap": Tool("Nmap", ToolCategory.PACKAGE, apt_package="nmap", check_binary="nmap", description="Network scanner"),
    "Wireshark": Tool("Wireshark", ToolCategory.PACKAGE, apt_package="wireshark", check_binary="wireshark", description="Packet analyzer"),
    "Aircrack-ng": Tool("Aircrack-ng", ToolCategory.PACKAGE, apt_package="aircrack-ng", check_binary="aircrack-ng", description="WiFi security auditing"),
    "Hydra": Tool("Hydra", ToolCategory.PACKAGE, apt_package="hydra", check_binary="hydra", description="Password cracker"),
    "SQLMap": Tool("SQLMap", ToolCategory.PACKAGE, apt_package="sqlmap", check_binary="sqlmap", description="SQL injection tool"),
    "John the Ripper": Tool("John the Ripper", ToolCategory.PACKAGE, apt_package="john", check_binary="john", description="Password hash cracker"),
    "Hashcat": Tool("Hashcat", ToolCategory.PACKAGE, apt_package="hashcat", check_binary="hashcat", description="GPU password cracker"),
    "Metasploit": Tool("Metasploit", ToolCategory.SPECIAL, description="Penetration testing framework", install_cmd=[
        ["curl", "https://raw.githubusercontent.com/rapid7/metasploit-omnibus/master/config/templates/metasploit-framework-wrappers/msfupdate.erb", "-o", "/tmp/msfinstall"],
        ["chmod", "755", "/tmp/msfinstall"],
        ["/tmp/msfinstall"]
    ], check_binary="msfconsole"),
    "Burp Suite": Tool("Burp Suite", ToolCategory.SPECIAL, description="Web security testing", install_cmd=[
        ["wget", "-q", "-O", "/tmp/burpsuite.sh", "https://portswigger.net/burp/releases/download?product=community&version=2024.1.1&type=Linux"],
        ["chmod", "+x", "/tmp/burpsuite.sh"],
        ["/tmp/burpsuite.sh", "-q", "-dir", "/opt/BurpSuiteCommunity"]
    ], check_binary="burpsuite"),
}

# Development tools
DEV_TOOLS = {
    "VS Code:": Tool("VS Code:", ToolCategory.SPECIAL, description="Code editor", check_binary="code", install_cmd=[
        ["wget", "-qO-", "https://packages.microsoft.com/keys/microsoft.asc", "|", "gpg", "--dearmor", ">", "/tmp/packages.microsoft.gpg"],
        ["sudo", "install", "-D", "-o", "root", "-g", "root", "-m", "644", "/tmp/packages.microsoft.gpg", "/etc/apt/keyrings/packages.microsoft.gpg"],
        ["sudo", "sh", "-c", 'echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/keyrings/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" > /etc/apt/sources.list.d/vscode.list'],
        ["rm", "-f", "/tmp/packages.microsoft.gpg"],
        ["sudo", "apt-get", "update"],
        ["sudo", "apt-get", "install", "-y", "code"],
    ]),
    "Docker": Tool("Docker", ToolCategory.SPECIAL, description="Container platform", check_binary="docker", install_cmd=[
        ["sudo", "apt-get", "install", "-y", "ca-certificates", "curl", "gnupg"],
        ["sudo", "install", "-m", "0755", "-d", "/etc/apt/keyrings"],
        ["curl", "-fsSL", "https://download.docker.com/linux/ubuntu/gpg", "|", "sudo", "gpg", "--dearmor", "-o", "/etc/apt/keyrings/docker.gpg"],
        ["sudo", "chmod", "a+r", "/etc/apt/keyrings/docker.gpg"],
        ["bash", "-c", 'echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null'],
        ["sudo", "apt-get", "update"],
        ["sudo", "apt-get", "install", "-y", "docker-ce", "docker-ce-cli", "containerd.io", "docker-buildx-plugin", "docker-compose-plugin"],
        ["sudo", "usermod", "-aG", "docker", os.environ.get("USER", "")],
    ]),
    "Node.js (LTS)": Tool("Node.js (LTS)", ToolCategory.SCRIPT, description="JavaScript runtime", check_binary="node", install_cmd=[
        "curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash - && sudo apt-get install -y nodejs"
    ]),
    "NPM": Tool("NPM", ToolCategory.PACKAGE, apt_package="npm", check_binary="npm", description="Node package manager"),
    "Yarn": Tool("Yarn", ToolCategory.SCRIPT, description="Package manager", check_binary="yarn", install_cmd=[
        "npm install -g yarn"
    ]),
    "PostgreSQL": Tool("PostgreSQL", ToolCategory.PACKAGE, apt_package="postgresql", check_binary="psql", description="Relational database"),
    "MySQL": Tool("MySQL", ToolCategory.PACKAGE, apt_package="mysql-server", check_binary="mysql", description="Relational database"),
    "MongoDB": Tool("MongoDB", ToolCategory.SPECIAL, description="NoSQL database", check_binary="mongod", install_cmd=[
        ["wget", "-qO-", "https://www.mongodb.org/static/pgp/server-7.0.asc", "|", "sudo", "gpg", "--dearmor", "-o", "/usr/share/keyrings/mongodb-server-7.0.gpg"],
        ["echo", "\"deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse\"", "|", "sudo", "tee", "/etc/apt/sources.list.d/mongodb-org-7.0.list"],
        ["sudo", "apt-get", "update"],
        ["sudo", "apt-get", "install", "-y", "mongodb-org"],
        ["sudo", "systemctl", "start", "mongod"],
        ["sudo", "systemctl", "enable", "mongod"],
    ]),
    "Redis": Tool("Redis", ToolCategory.PACKAGE, apt_package="redis-server", check_binary="redis-server", description="In-memory database"),
    "SQLite3": Tool("SQLite3", ToolCategory.PACKAGE, apt_package="sqlite3", check_binary="sqlite3", description="Embedded database"),
    "Go": Tool("Go", ToolCategory.SPECIAL, description="Go programming language", check_binary="go", install_cmd=[
        ["wget", "-q", "https://go.dev/dl/go1.21.5.linux-amd64.tar.gz", "-O", "/tmp/go.tar.gz"],
        ["sudo", "rm", "-rf", "/usr/local/go"],
        ["sudo", "tar", "-C", "/usr/local", "-xzf", "/tmp/go.tar.gz"],
    ]),
    "Rust": Tool("Rust", ToolCategory.SCRIPT, description="Rust programming language", check_binary="rustc", install_cmd=[
        "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y"
    ]),
    "DBeaver": Tool("DBeaver", ToolCategory.PACKAGE, apt_package="dbeaver-ce", check_binary="dbeaver", description="Database GUI"),
    "Postman": Tool("Postman", ToolCategory.SPECIAL, description="API testing", check_binary="postman", install_cmd=[
        ["wget", "-q", "https://dl.pstmn.io/download/latest/linux64", "-O", "/tmp/postman.tar.gz"],
        ["sudo", "tar", "-xzf", "/tmp/postman.tar.gz", "-C", "/opt/"],
        ["sudo", "ln", "-s", "/opt/Postman/Postman", "/usr/local/bin/postman"],
    ]),
    "Insomnia": Tool("Insomnia", ToolCategory.SPECIAL, description="API testing", check_binary="insomnia", install_cmd=[
        ["wget", "-q", "https://updates.insomnia.rest/downloads/ubuntu/latest?&app=com.insomnia.app&source=website", "-O", "/tmp/insomnia.deb"],
        ["sudo", "dpkg", "-i", "/tmp/insomnia.deb"],
        ["sudo", "apt-get", "install", "-f", "-y"],
    ]),
}

# Account configurations
ACCOUNTS = {
    "GitHub (gh CLI)": {
        "type": "cli",
        "check": "gh",
        "login_cmd": ["gh", "auth", "login"],
        "install": lambda: install_gh_cli(),
    },
    "Google Account (browser)": {
        "type": "browser",
        "url": "https://accounts.google.com/",
    },
    "Google Cloud (gcloud)": {
        "type": "cli",
        "check": "gcloud",
        "login_cmd": ["gcloud", "auth", "login"],
        "install": lambda: warn("Install gcloud from https://cloud.google.com/sdk/docs/install"),
    },
    "Docker Hub": {
        "type": "cli",
        "check": "docker",
        "login_cmd": ["docker", "login"],
    },
    "NPM": {
        "type": "cli",
        "check": "npm",
        "login_cmd": ["npm", "login"],
    },
    "Heroku": {
        "type": "cli",
        "check": "heroku",
        "login_cmd": ["heroku", "login"],
        "install": lambda: run(["npm", "install", "-g", "heroku"]),
    },
}


# ------------------------------------------------------------------------
# INSTALLER HELPERS
# ------------------------------------------------------------------------
def install_gh_cli():
    if check_installed("gh"):
        return
    info("Installing GitHub CLI...")
    run(["apt-get", "install", "-y", "gh"], sudo=True, check=False)
    if not check_installed("gh"):
        cmds = [
            "curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg",
            "sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg",
        ["bash", "-c", 'echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null'],
            "sudo apt-get update",
            "sudo apt-get install -y gh",
        ]
        for c in cmds:
            subprocess.run(c, shell=True)
    ok("GitHub CLI installed")


def install_protonvpn(gui=True):
    fallback = ("https://repo.protonvpn.com/debian/dists/stable/main/binary-all/"
                "protonvpn-stable-release_1.0.8_all.deb")
    listing_url = "https://repo.protonvpn.com/debian/dists/stable/main/binary-all/"

    try:
        req = urllib.request.Request(listing_url, headers={"User-Agent": "apex-framework"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode(errors="ignore")
        matches = re.findall(r'protonvpn-stable-release_[\d.]+_all\.deb', html)
        if matches:
            latest = sorted(set(matches))[-1]
            url = listing_url + latest
        else:
            url = fallback
    except Exception:
        url = fallback

    deb_path = Path("/tmp/protonvpn-repo.deb")
    info(f"Downloading ProtonVPN repo package...")
    try:
        urllib.request.urlretrieve(url, deb_path)
    except Exception as e:
        err(f"Download failed: {e}")
        return

    run(["dpkg", "-i", str(deb_path)], sudo=True, check=False)
    run(["apt-get", "update"], sudo=True, check=False)
    pkg = "proton-vpn-gnome-desktop" if gui else "protonvpn-cli"
    run(["apt-get", "install", "-y", pkg], sudo=True, check=False)
    ok(f"Proton VPN ({'GUI' if gui else 'CLI'}) installed")


def install_obsidian_flatpak():
    if not check_installed("flatpak"):
        run(["apt-get", "install", "-y", "flatpak"], sudo=True)
    run(["flatpak", "remote-add", "--if-not-exists", "flathub",
         "https://flathub.org/repo/flathub.flatpakrepo"], sudo=True)
    run(["flatpak", "install", "-y", "flathub", "md.obsidian.Obsidian"], sudo=True)
    ok("Obsidian installed via Flatpak")


def install_obsidian_deb():
    api_url = "https://api.github.com/repos/obsidianmd/obsidian-releases/releases/latest"
    try:
        req = urllib.request.Request(api_url, headers={"User-Agent": "apex-framework"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        err(f"Couldn't reach GitHub API: {e}")
        return False

    asset_url = None
    for asset in data.get("assets", []):
        name = asset.get("name", "")
        if name.endswith(".deb") and "amd64" in name:
            asset_url = asset["browser_download_url"]
            break

    if not asset_url:
        err("Couldn't find a .deb asset")
        return False

    deb_path = Path("/tmp/obsidian-latest.deb")
    urllib.request.urlretrieve(asset_url, deb_path)
    run(["dpkg", "-i", str(deb_path)], sudo=True, check=False)
    run(["apt-get", "install", "-f", "-y"], sudo=True)
    ok("Obsidian installed from .deb")
    return True


# ------------------------------------------------------------------------
# PROXY MANAGEMENT
# ------------------------------------------------------------------------
def fetch_proxy_list():
    info("Fetching proxy list from repository...")
    proxy_file = CONFIG_DIR / "proxies.txt"

    try:
        urllib.request.urlretrieve(PROXY_LIST_URL, proxy_file)
        ok(f"Proxy list downloaded ({proxy_file})")
    except Exception as e:
        warn(f"Could not fetch proxy list: {e}")
        proxy_file.write_text("# Default proxy list\n# Format: type host port [user pass]\nsocks5 127.0.0.1 9050\n")
        info("Created default proxy list with Tor (127.0.0.1:9050)")

    return proxy_file


def configure_proxychains(proxy_file: Path):
    config_path = Path("/etc/proxychains4.conf")
    if not config_path.exists():
        config_path = Path("/etc/proxychains.conf")

    if not config_path.exists():
        warn("proxychains config not found, skipping configuration")
        return

    info("Configuring proxychains with fetched proxies...")

    try:
        existing = config_path.read_text()
    except PermissionError:
        warn("Need sudo to edit proxychains config")
        return

    lines = existing.split("\n")
    new_lines = []
    in_proxy_list = False
    for line in lines:
        if line.strip().startswith("[ProxyList]"):
            in_proxy_list = True
            new_lines.append(line)
            proxies = proxy_file.read_text().strip().split("\n")
            for p in proxies:
                if not p.startswith("#") and p.strip():
                    new_lines.append(f"{p.strip()}")
            continue
        if in_proxy_list and line.strip() and not line.strip().startswith("#"):
            continue
        new_lines.append(line)

    temp_config = Path("/tmp/proxychains_new.conf")
    temp_config.write_text("\n".join(new_lines))
    run(["cp", str(temp_config), str(config_path)], sudo=True)
    ok("Proxychains configured with fetched proxies")
    STATE.proxychains_configured = True


# ------------------------------------------------------------------------
# GITHUB REPO INTEGRATION
# ------------------------------------------------------------------------
def clone_framework_repo():
    if FRAMEWORK_DIR.exists() and (FRAMEWORK_DIR / ".git").exists():
        info("Framework repo already cloned, pulling latest changes...")
        run(["git", "-C", str(FRAMEWORK_DIR), "pull"])
        ok("Repo updated")
        STATE.repo_cloned = True
        return

    info(f"Cloning framework repository to {FRAMEWORK_DIR}...")
    FRAMEWORK_DIR.parent.mkdir(parents=True, exist_ok=True)
    run(["git", "clone", REPO_URL, str(FRAMEWORK_DIR)])
    ok("Framework repository cloned")
    STATE.repo_cloned = True


def setup_github_cli_from_repo():
    if not check_installed("gh"):
        install_gh_cli()

    info("Configuring GitHub CLI context...")
    run(["gh", "config", "set", "git_protocol", "ssh"])
    ok("GitHub CLI configured")


# ------------------------------------------------------------------------
# CONFIG FILE MODE
# ------------------------------------------------------------------------
def load_config_file(path: str) -> dict:
    config_path = Path(path).expanduser()
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    content = config_path.read_text()

    if config_path.suffix in ('.yaml', '.yml'):
        import yaml
        return yaml.safe_load(content)
    elif config_path.suffix == '.json':
        return json.loads(content)
    else:
        try:
            import yaml
            return yaml.safe_load(content)
        except Exception:
            return json.loads(content)


def apply_config(config: dict):
    info("Applying configuration from file...")

    if config.get("security", {}).get("enabled", False):
        STATE.secure_mode_enabled = True
        STATE.security_selected = config["security"].get("tools", [])

    STATE.packages_selected = config.get("packages", {}).get("selected", [])
    STATE.kali_tools_selected = config.get("tools", {}).get("kali", [])
    STATE.dev_tools_selected = config.get("tools", {}).get("development", [])
    STATE.accounts_selected = config.get("accounts", {}).get("login", [])

    gdrive = config.get("gdrive", {})
    STATE.gdrive_remote = gdrive.get("remote")
    STATE.gdrive_path = gdrive.get("path", "")
    STATE.gdrive_dest = gdrive.get("dest", str(DEFAULT_GDRIVE_DEST))

    ok("Configuration applied")


# ------------------------------------------------------------------------
# BACKUP / RESTORE
# ------------------------------------------------------------------------
def find_media_roots():
    user = os.environ.get("USER", "")
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


def pick_backup_location(prompt_label):
    roots = find_media_roots()
    candidates = [r / BACKUP_FOLDER_NAME for r in roots]
    existing = [c for c in candidates if c.exists()]
    options = existing if existing else candidates

    print(f"\n{C.WHITE}{prompt_label}{C.RESET}")
    if not options:
        warn("No removable drives detected.")
    for i, c in enumerate(options, 1):
        tag = f"{C.GREEN}(existing backup found){C.RESET}" if c in existing else ""
        print(f"  {C.RED}{i}{C.RESET}. {c} {tag}")
    print(f"  {C.RED}0{C.RESET}. Enter a custom path")
    print(f"  {C.RED}s{C.RESET}. Skip")

    choice = input(f"{C.WHITE}> {C.RESET}").strip().lower()
    if choice in ("s", ""):
        return None
    if choice == "0" or not options:
        custom = input(f"{C.WHITE}Enter full path to use: {C.RESET}").strip()
        return Path(custom).expanduser() / BACKUP_FOLDER_NAME if custom else None
    if choice.isdigit() and 1 <= int(choice) <= len(options):
        return options[int(choice) - 1]
    warn("Invalid choice.")
    return None


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
    else:
        info("No rclone.conf found to back up.")

    manifest = {
        "packages_selected": STATE.packages_selected,
        "accounts_selected": STATE.accounts_selected,
        "security_selected": STATE.security_selected,
        "kali_tools_selected": STATE.kali_tools_selected,
        "dev_tools_selected": STATE.dev_tools_selected,
        "gdrive_remote": STATE.gdrive_remote,
        "gdrive_path": STATE.gdrive_path,
        "gdrive_dest": STATE.gdrive_dest,
        "secure_mode_enabled": STATE.secure_mode_enabled,
    }
    (loc / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2))
    ok(f"Backed up to {loc}")
    warn("This backup contains your rclone.conf — treat it as a credential.")


def restore_session():
    header("RESTORE PREVIOUS SESSION")
    if not ask_yes_no("Restore from a previous backup?", default=True):
        info("Starting fresh.")
        return

    loc = pick_backup_location("Looking for previous Apex backup...")
    if loc is None or not loc.exists():
        warn("No backup restored, starting fresh.")
        return

    manifest_path = loc / MANIFEST_NAME
    if manifest_path.exists():
        try:
            data = json.loads(manifest_path.read_text())
            for key, value in data.items():
                if hasattr(STATE, key):
                    setattr(STATE, key, value)
            ok("Restored previous selections.")
        except Exception as e:
            warn(f"Couldn't read manifest: {e}")

    rclone_backup = loc / "rclone.conf"
    if rclone_backup.exists():
        dest_dir = Path.home() / ".config" / "rclone"
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(rclone_backup, dest_dir / "rclone.conf")
        ok("Restored rclone.conf")
    else:
        info("No rclone.conf found in backup.")


# ------------------------------------------------------------------------
# SETUP STEPS
# ------------------------------------------------------------------------
def step_security_first():
    header("STEP 0 — SECURITY FIRST")

    if STATE.config_mode:
        if STATE.secure_mode_enabled:
            info("Secure mode enabled via config file")
        else:
            info("Secure mode not enabled in config")
    else:
        STATE.secure_mode_enabled = ask_yes_no(
            "Enable secure mode? (VPN/proxy before network operations)", default=False
        )

    if not STATE.secure_mode_enabled:
        warn("Secure mode disabled — proceeding without VPN/proxy wrapper")
        return

    sec_names = list(SECURITY_TOOLS.keys())
    if STATE.config_mode and STATE.security_selected:
        chosen = STATE.security_selected
    else:
        chosen = toggle_select(
            "Select security tools to install",
            sec_names,
            preselected=STATE.security_selected or None,
            all_default=False,
            descriptions={k: v.description for k, v in SECURITY_TOOLS.items()},
        )

    STATE.security_selected = chosen

    for name in chosen:
        tool = SECURITY_TOOLS[name]
        try:
            tool.install()
        except Exception as e:
            err(f"Failed to install {name}: {e}")
            logger.error(f"Security tool install failed: {name} — {e}")

    if "Proton VPN (GUI)" in chosen:
        install_protonvpn(gui=True)
    if "Proton VPN (CLI)" in chosen:
        install_protonvpn(gui=False)

    if "Proxychains4" in chosen:
        proxy_file = fetch_proxy_list()
        configure_proxychains(proxy_file)

    if "MAC Changer" in chosen:
        info("MAC Changer ready — use: sudo macchanger -r <interface>")

    ok("Security layer configured")


def step_system_update():
    header("STEP 1 — SYSTEM UPDATE & UPGRADE")
    if STATE.config_mode:
        if not ask_yes_no("Config mode: Run system update?", default=True):
            return
    else:
        if not ask_yes_no("Run apt update && apt upgrade?", default=True):
            warn("Skipped system update")
            return

    info("Updating package index...")
    run(["apt-get", "update"], sudo=True)
    info("Upgrading packages...")
    run(["apt-get", "upgrade", "-y"], sudo=True)
    ok("System updated")


def step_base_packages():
    header("STEP 2 — BASE PACKAGES")
    names = list(BASE_PACKAGES.keys())

    if STATE.config_mode and STATE.packages_selected:
        chosen = STATE.packages_selected
    else:
        chosen = toggle_select(
            "Select base packages",
            names,
            preselected=STATE.packages_selected or None,
            all_default=True,
            descriptions={k: v.description for k, v in BASE_PACKAGES.items()},
        )

    STATE.packages_selected = chosen

    for name in chosen:
        tool = BASE_PACKAGES[name]
        try:
            tool.install()
        except Exception as e:
            err(f"Failed to install {name}: {e}")


def step_github_integration():
    header("STEP 3 — GITHUB INTEGRATION")

    if not ask_yes_no("Clone framework repository and configure GitHub CLI?", default=True):
        return

    clone_framework_repo()
    setup_github_cli_from_repo()

    if ask_yes_no("Clone additional repositories?", default=False):
        while True:
            repo_url = ask_input("Enter repository URL (or 'done' to finish)")
            if repo_url.lower() == 'done':
                break
            dest_name = repo_url.split('/')[-1].replace('.git', '')
            dest = FRAMEWORK_DIR / "repos" / dest_name
            info(f"Cloning {repo_url}...")
            run(["git", "clone", repo_url, str(dest)], check=False)

    ok("GitHub integration complete")


def step_tool_profiles():
    header("STEP 4 — TOOL PROFILES")

    print(f"\n{C.WHITE}{C.BOLD}Choose profile:{C.RESET}")
    print(f"  {C.RED}1{C.RESET}. Kali-style (penetration testing)")
    print(f"  {C.RED}2{C.RESET}. Development (coding & databases)")
    print(f"  {C.RED}3{C.RESET}. Both")
    print(f"  {C.RED}4{C.RESET}. Custom selection")
    print(f"  {C.RED}s{C.RESET}. Skip")

    if STATE.config_mode:
        choice = "3" if (STATE.kali_tools_selected and STATE.dev_tools_selected) else "1" if STATE.kali_tools_selected else "2" if STATE.dev_tools_selected else "s"
    else:
        choice = input(f"{C.WHITE}> {C.RESET}").strip().lower()

    if choice == "s" or choice == "":
        warn("Skipped tool profiles")
        return

    if choice in ("1", "3", "4"):
        kali_names = list(SECURITY_TOOLS.keys())
        if choice == "4":
            kali_chosen = toggle_select(
                "Select Kali-style tools",
                kali_names,
                preselected=STATE.kali_tools_selected or None,
                all_default=False,
                descriptions={k: v.description for k, v in SECURITY_TOOLS.items()},
            )
        elif STATE.config_mode:
            kali_chosen = STATE.kali_tools_selected
        else:
            kali_chosen = kali_names

        STATE.kali_tools_selected = kali_chosen
        for name in kali_chosen:
            if name in SECURITY_TOOLS:
                try:
                    SECURITY_TOOLS[name].install()
                except Exception as e:
                    err(f"Failed to install {name}: {e}")

    if choice in ("2", "3", "4"):
        dev_names = list(DEV_TOOLS.keys())
        if choice == "4":
            dev_chosen = toggle_select(
                "Select development tools",
                dev_names,
                preselected=STATE.dev_tools_selected or None,
                all_default=False,
                descriptions={k: v.description for k, v in DEV_TOOLS.items()},
            )
        elif STATE.config_mode:
            dev_chosen = STATE.dev_tools_selected
        else:
            dev_chosen = dev_names

        STATE.dev_tools_selected = dev_chosen
        for name in dev_chosen:
            if name in DEV_TOOLS:
                try:
                    DEV_TOOLS[name].install()
                except Exception as e:
                    err(f"Failed to install {name}: {e}")

    ok("Tool profiles installed")


def step_obsidian():
    header("STEP 5 — OBSIDIAN")
    if not ask_yes_no("Install Obsidian?", default=True):
        return

    print(f"{C.GREY}  1) Flatpak (recommended){C.RESET}")
    print(f"{C.GREY}  2) Direct .deb from GitHub{C.RESET}")
    print(f"{C.GREY}  3) Skip{C.RESET}")
    choice = input(f"{C.WHITE}Choose [1/2/3]: {C.RESET}").strip()

    if choice == "1":
        install_obsidian_flatpak()
    elif choice == "2":
        install_obsidian_deb()


def step_accounts():
    header("STEP 6 — ACCOUNT LOGINS")

    if STATE.config_mode and STATE.accounts_selected:
        chosen = STATE.accounts_selected
    else:
        if not ask_yes_no("Log into accounts now?", default=False):
            return
        chosen = toggle_select(
            "Select accounts",
            list(ACCOUNTS.keys()),
            preselected=STATE.accounts_selected or None,
            all_default=False,
        )

    STATE.accounts_selected = chosen

    for name in chosen:
        cfg = ACCOUNTS[name]

        if cfg["type"] == "browser":
            info(f"Opening browser for {name}...")
            try:
                subprocess.run(["xdg-open", cfg["url"]], check=False)
            except FileNotFoundError:
                warn(f"Visit manually: {cfg['url']}")
            input(f"{C.GREY}Press Enter once signed in...{C.RESET}")
            continue

        check_bin = cfg.get("check")
        if check_bin and not check_installed(check_bin):
            if "install" in cfg:
                cfg["install"]()

        if check_bin and not check_installed(check_bin):
            err(f"{check_bin} not available, skipping {name}")
            continue

        info(f"Launching login for {name}...")
        subprocess.run(cfg["login_cmd"])

    ok("Account logins complete")


    if STATE.config_mode:
        if not STATE.gdrive_remote:
            tui_warn("No Google Drive config in file, skipping")
            return
    else:
        if not tui_ask_yes_no("Set up Google Drive sync?", default=True):
            return

    if not check_installed("rclone"):
        tui_info("Installing rclone...")
        run(["apt-get", "install", "-y", "rclone"], sudo=True, check=False)
        if not check_installed("rclone"):
            subprocess.run("curl https://rclone.org/install.sh | sudo bash", shell=True, check=False)

    remotes = []
    result = subprocess.run(["rclone", "listremotes"], text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    remotes = [r.strip().rstrip(":") for r in result.stdout.splitlines() if r.strip()]

    remote_name = STATE.gdrive_remote

    if remotes and not remote_name:
        if RICH_AVAILABLE and STATE.tui_mode:
            console.print("\n[bold white]Existing remotes:[/bold white]")
            for i, r in enumerate(remotes, 1):
                console.print(f"  [red]{i}[/red]. {r}")
            console.print(f"  [red]0[/red]. Create new remote")
            choice = IntPrompt.ask("Pick remote", default=0)
            if 1 <= choice <= len(remotes):
                remote_name = remotes[choice - 1]
        else:
            print(f"\n{C.WHITE}Existing remotes:{C.RESET}")
            for i, r in enumerate(remotes, 1):
                print(f"  {C.RED}{i}{C.RESET}. {r}")
            print(f"  {C.RED}0{C.RESET}. Create new remote")
            choice = input(f"{C.WHITE}> {C.RESET}").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(remotes):
                remote_name = remotes[int(choice) - 1]

    if not remote_name:
        tui_warn("Launching rclone config...")
        tui_info("Choose 'New remote' -> type 'drive' -> follow browser auth")
        subprocess.run(["rclone", "config"])
        result = subprocess.run(["rclone", "listremotes"], text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        remotes = [r.strip().rstrip(":") for r in result.stdout.splitlines() if r.strip()]
        if not remotes:
            tui_err("No remote created, aborting")
            return
        if RICH_AVAILABLE and STATE.tui_mode:
            console.print("\n[bold white]Available remotes:[/bold white]")
            for i, r in enumerate(remotes, 1):
                console.print(f"  [red]{i}[/red]. {r}")
            choice = IntPrompt.ask("Pick remote", default=1)
            if 1 <= choice <= len(remotes):
                remote_name = remotes[choice - 1]
        else:
            print(f"\n{C.WHITE}Available remotes:{C.RESET}")
            for i, r in enumerate(remotes, 1):
                print(f"  {C.RED}{i}{C.RESET}. {r}")
            choice = input(f"{C.WHITE}> {C.RESET}").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(remotes):
                remote_name = remotes[int(choice) - 1]
            else:
                tui_err("Invalid choice, aborting")
                return

    drive_path = STATE.gdrive_path or tui_ask_input("Drive source path (blank = root)", default="")
    source = f"{remote_name}:{drive_path}" if drive_path else f"{remote_name}:"

    dest = Path(STATE.gdrive_dest) if STATE.gdrive_dest else DEFAULT_GDRIVE_DEST
    if not STATE.gdrive_dest:
        dest_input = tui_ask_input("Local destination", default=str(dest))
        if dest_input:
            dest = Path(dest_input).expanduser()
    dest.mkdir(parents=True, exist_ok=True)

    mode = "sync" if tui_ask_yes_no("Use sync (mirror) instead of copy?", default=False) else "copy"

    tui_info(f"Running rclone {mode}...")
    subprocess.run(["rclone", mode, source, str(dest), "--progress"])
    tui_ok(f"Synced to {dest}")

    STATE.gdrive_remote = remote_name
    STATE.gdrive_path = drive_path
    STATE.gdrive_dest = str(dest)

    tui_warn("On live USB, files will be wiped on reboot unless backed up")


# ------------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(
        description=f"Apex Multi Tools v{VERSION} — Interactive CLI Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  python3 apex_framework.py                    # Interactive TUI wizard
  python3 apex_framework.py --config setup.yaml  # Unattended setup
  python3 apex_framework.py --secure-mode        # Force secure mode
  python3 apex_framework.py --cli                # Classic CLI mode
  python3 apex_framework.py --restore-only       # Just restore backup
  python3 apex_framework.py --backup-only        # Just create backup
        """
    )
    parser.add_argument("--config", "-c", metavar="FILE",
                        help="Load selections from YAML/JSON config file")
    parser.add_argument("--restore-only", action="store_true",
                        help="Only restore from backup, then exit")
    parser.add_argument("--backup-only", action="store_true",
                        help="Only back up current state, then exit")
    parser.add_argument("--secure-mode", "-s", action="store_true",
                        help="Force secure mode (VPN/proxy before network ops)")
    parser.add_argument("--tui", action="store_true",
                        help="Force TUI mode (requires rich)")
    parser.add_argument("--cli", action="store_true",
                        help="Force classic CLI mode (no rich)")
    parser.add_argument("--no-banner", action="store_true",
                        help="Skip banner display")
    return parser.parse_args()


def main():
    global logger, STATE

    args = parse_args()

    # Initialize logging
    logger = ApexLogger()
    STATE = ApexState.load()

    # Determine TUI mode
    if args.cli:
        STATE.tui_mode = False
    elif args.tui:
        STATE.tui_mode = True
    else:
        STATE.tui_mode = RICH_AVAILABLE

    # Handle config file
    if args.config:
        STATE.config_mode = True
        STATE.config_file = args.config
        try:
            config = load_config_file(args.config)
            apply_config(config)
            tui_info(f"Loaded config from {args.config}")
        except Exception as e:
            tui_err(f"Failed to load config: {e}")
            sys.exit(1)

    if args.secure_mode:
        STATE.secure_mode_enabled = True

    # Display banner
    if not args.no_banner:
        if STATE.tui_mode and RICH_AVAILABLE:
            tui_banner()
        else:
            os.system("clear")
            print("""
   ▄▄▄       ██▓███  ▓█████ ▒██   ██▒
  ▒████▄    ▓██░  ██▒▓█   ▀ ▒▒ █ █ ▒░
  ▒██  ▀█▄  ▓██░ ██▓▒▒███   ░░  █   ░
  ░██▄▄▄▄██ ▒██▄█▓▒ ▒▒▓█  ▄  ░ █ █ ▒
   ▓█   ▓██▒▒██▒ ░  ░░▒████▒▒██▒ ▒██▒
   ▒▒   ▓▒█░▒▓▒░ ░  ░░░ ▒░ ░▒▒ ░ ░▓ ░
    ▒   ▒▒ ░░▒ ░      ░ ░  ░░░   ░▒ ░
    ░   ▒   ░░          ░    ░    ░
        ░  ░               ░    ░

        APEX MULTI TOOLS v""" + VERSION + """
            """)

    logger.info(f"=== Apex Framework v{VERSION} started ===")
    tui_info(f"Session log: {logger.log_file}")
    tui_info(f"Framework directory: {FRAMEWORK_DIR}")
    if STATE.tui_mode:
        tui_info("TUI mode active (Rich)")
    else:
        tui_info("CLI mode (classic)")

    # Standalone modes
    if args.restore_only:
        restore_session()
        STATE.save()
        tui_header("RESTORE COMPLETE")
        tui_ok("Restore finished — run without flags for full setup")
        return

    if args.backup_only:
        backup_session()
        STATE.save()
        tui_header("BACKUP COMPLETE")
        tui_ok("Backup finished")
        return

    # Main wizard flow
    restore_session()
    sudo_keepalive()

    step_security_first()
    step_system_update()
    step_base_packages()
    step_github_integration()
    step_tool_profiles()
    step_obsidian()
    step_accounts()
    step_gdrive_sync()
    backup_session()
    STATE.save()

    tui_header("SETUP COMPLETE")
    tui_success("Apex Multi Tools environment is ready!")
    tui_info(f"Session log: {logger.log_file}")
    tui_info(f"Framework directory: {FRAMEWORK_DIR}")

    if STATE.secure_mode_enabled:
        tui_info("Secure mode was active — review proxychains/VPN status")

    # Summary table
    if RICH_AVAILABLE and STATE.tui_mode:
        summary = Table(title="Installation Summary", box=box.ROUNDED, border_style="green")
        summary.add_column("Category", style="cyan")
        summary.add_column("Count", style="white")
        summary.add_row("Base Packages", str(len(STATE.packages_selected)))
        summary.add_row("Security Tools", str(len(STATE.security_selected)))
        summary.add_row("Kali Tools", str(len(STATE.kali_tools_selected)))
        summary.add_row("Dev Tools", str(len(STATE.dev_tools_selected)))
        summary.add_row("Accounts", str(len(STATE.accounts_selected)))
        summary.add_row("Google Drive", STATE.gdrive_remote or "Not configured")
        console.print(summary)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{C.RED}Setup interrupted by user.{C.RESET}")
        if STATE:
            STATE.save()
        sys.exit(1)
    except Exception as e:
        print(f"\n{C.RED}Fatal error: {e}{C.RESET}")
        if logger:
            logger.error(f"Fatal error: {e}")
        if STATE:
            STATE.save()
        sys.exit(1)
