#!/usr/bin/env python3
"""
================================================================================
 APEX MULTI TOOLS — BOOTSTRAP LAUNCHER
================================================================================
 One-liner bootstrap for Linux Mint live USB.

 Usage:
   curl -fsSL https://raw.githubusercontent.com/yourusername/apex-multi-tools/main/bootstrap.py | python3

 What it does:
   1. Checks Python 3.8+ is available
   2. Clones/pulls the framework repo to ~/ApexMultiTools
   3. Installs required dependencies (pip packages if needed)
   4. Launches the main framework

 This file stays tiny (~3KB) so it downloads fast even on slow connections.
================================================================================
"""

import os
import sys
import subprocess
import urllib.request
from pathlib import Path

REPO_URL = "https://github.com/yourusername/apex-multi-tools.git"
REPO_RAW = "https://raw.githubusercontent.com/yourusername/apex-multi-tools/main"
FRAMEWORK_DIR = Path.home() / "ApexMultiTools"
FRAMEWORK_SCRIPT = FRAMEWORK_DIR / "apex_framework.py"

MIN_PYTHON = (3, 8)


def check_python():
    """Ensure Python 3.8+ is available."""
    if sys.version_info < MIN_PYTHON:
        print(f"[ERROR] Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required, found {sys.version_info.major}.{sys.version_info.minor}")
        sys.exit(1)
    print(f"[*] Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} OK")


def check_git():
    """Ensure git is available."""
    result = subprocess.run(["which", "git"], capture_output=True)
    if result.returncode != 0:
        print("[*] Git not found, installing...")
        subprocess.run(["sudo", "apt-get", "update"], check=False)
        subprocess.run(["sudo", "apt-get", "install", "-y", "git"], check=False)
    else:
        print("[*] Git OK")


def clone_or_update_repo():
    """Clone the framework repo or pull latest if already exists."""
    if FRAMEWORK_DIR.exists() and (FRAMEWORK_DIR / ".git").exists():
        print(f"[*] Framework found at {FRAMEWORK_DIR}, pulling updates...")
        result = subprocess.run(
            ["git", "-C", str(FRAMEWORK_DIR), "pull", "--ff-only"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print("[OK] Framework updated")
        else:
            print(f"[!] Pull failed: {result.stderr.strip()}")
            print("[*] Attempting force reset...")
            subprocess.run(["git", "-C", str(FRAMEWORK_DIR), "fetch", "origin"], check=False)
            subprocess.run(["git", "-C", str(FRAMEWORK_DIR), "reset", "--hard", "origin/main"], check=False)
    else:
        print(f"[*] Cloning framework to {FRAMEWORK_DIR}...")
        FRAMEWORK_DIR.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["git", "clone", "--depth=1", REPO_URL, str(FRAMEWORK_DIR)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"[ERROR] Clone failed: {result.stderr.strip()}")
            # Fallback: download raw framework script
            print("[*] Falling back to raw download...")
            FRAMEWORK_DIR.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(
                f"{REPO_RAW}/apex_framework.py",
                FRAMEWORK_SCRIPT
            )
            print("[OK] Framework downloaded (raw)")
        else:
            print("[OK] Framework cloned")


def install_deps():
    """Install Python dependencies if needed."""
    deps = ["rich", "pyyaml"]
    try:
        import rich
        import yaml
        print("[*] Dependencies already satisfied")
        return
    except ImportError:
        pass

    print("[*] Installing Python dependencies...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--user"] + deps,
        check=False
    )
    print("[OK] Dependencies installed")


def launch_framework():
    """Run the main framework."""
    print("\n" + "="*60)
    print("  LAUNCHING APEX MULTI TOOLS FRAMEWORK")
    print("="*60 + "\n")

    # Pass through any CLI args
    args = " ".join(sys.argv[1:])
    cmd = f"{sys.executable} {FRAMEWORK_SCRIPT} {args}"
    os.system(cmd)


def main():
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

        APEX MULTI TOOLS — BOOTSTRAP v0.4.0-beta
    """)

    check_python()
    check_git()
    clone_or_update_repo()
    install_deps()
    launch_framework()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[ABORT] Bootstrap interrupted by user.")
        sys.exit(1)
