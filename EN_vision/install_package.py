#!/usr/bin/env python3

"""
Automated Environment Configuration Tool
Supported Platforms: Windows, Linux (Ubuntu, RHEL/CentOS)
Functionality: Automated installation of Python packages, system utilities, NVIDIA drivers, and CUDA Toolkit
Features: Automatic system restart and continued operation following driver installation
"""

import subprocess
import sys
import os
import platform
from typing import Dict, List, Tuple
import pkg_resources
from packaging import version

# Auto-start script path
AUTO_START_SERVICE = "/etc/systemd/system/cuda-setup.service"
AUTO_START_SCRIPT = "/usr/local/bin/cuda-setup-continue.sh"
SCRIPT_PATH = os.path.abspath(__file__)


# ============================================================
# Configuration Zone - Specify required packages here
# ============================================================

# Python Package Requirements (Format: 'Package Name': 'Version')
PYTHON_PACKAGES = {
    'pip' : '', 
    "requests": "",
    "psutil": "",          # Local system information
    "rich": "",            # Enhanced terminal output
    'matplotlib': '',
    'tk' : '',
}

# System Tool Requirements (Linux)
SYSTEM_TOOLS = [
    'git',
    'gcc',
    'g++',
    'make',
    'cmake',
    'wget',
    'curl',
]

# Windows System Tools (using Chocolatey)
WINDOWS_TOOLS = [
    'git',
    'cmake',
    'wget',
    'cuda',
]

# ============================================================


class SystemManager:
    """System Manager - Handling System-Level Installations"""

    def __init__(self):
        self.os_type = platform.system().lower()
        self.package_manager = self._detect_package_manager()
        
        print("=" * 70)
        print("System Information")
        print("=" * 70)
        print(f"Operating System: {platform.system()} {platform.release()}")
        print(f"Python version: {sys.version.split()[0]}")
        print(f"Package Manager: {self.package_manager or '未偵測到'}")
        print("=" * 70)

    def _detect_package_manager(self):
        """Detection System Package Manager"""
        if self.os_type == 'linux':
            managers = ['apt-get', 'dnf']       #apt-get: Ubuntu, dnf: Red Hat/AlmaLinux
            for manager in managers:
                try:
                    subprocess.run([manager, '--version'], 
                                 capture_output=True, check=True)
                    return manager
                except:
                    continue
        elif self.os_type == 'windows':
            # Detect Windows version
            win_version = platform.version()
            is_server = 'server' in platform.platform().lower()
            
            print(f"Windows version: {platform.platform()}")
            if is_server:
                print("Windows Server detected")
            else:
                print("Windows 11/10 detected")
            
            try:
                subprocess.run(['choco', '--version'],  # choco: windows servers
                             capture_output=True, check=True)
                return 'choco'
            except:
                print("⚠ Chocolatey not installed")
                print("Recomenda-se instalar o Chocolatey: https://chocolatey.org/install")
                return None
        return None
    
    def detect_package_manager(self):
        if os.path.exists("/usr/bin/apt") or os.path.exists("/usr/bin/apt-get"):
            return "apt"
        if os.path.exists("/usr/bin/dnf"):
            return "dnf"
        if os.name == "nt":
            return "choco"
        return None

    def run_cmd(self, cmd: List[str], use_sudo=True):
        if use_sudo and self.os_type == "linux":
            cmd = ["sudo"] + cmd
        try:
            print(f"Running: {' '.join(cmd)}")
            subprocess.check_call(cmd)
            return True
        except subprocess.CalledProcessError:
            print(f"Command failed: {' '.join(cmd)}")
            return False

    # ---------------------------------------------------------
    # System Update (Lightweight)
    # ---------------------------------------------------------
    def update_system(self):
        if self.package_manager == "apt":
            print("\nUpdating APT package list...")
            return self.run_cmd(["apt-get", "update"])

        elif self.package_manager in ["dnf", "yum"]:
            print("\nSkipping system update for RHEL-based OS (dnf/yum).")
            return True

        elif self.package_manager == "choco":
            print("\nUpdating Chocolatey...")
            return self.run_cmd(["choco", "upgrade", "chocolatey", "-y"], use_sudo=False)

        print("Unknown package manager; skipping update.")
        return False

    # ---------------------------------------------------------
    # System Tools Installation
    # ---------------------------------------------------------
    def install_system_tools(self, tools: List[str]):
        print("\nInstalling required system tools...")

        if not self.package_manager:
            print("No valid package manager detected.")
            return False

        for tool in tools:
            print(f"Installing {tool} ...")

            if self.package_manager == "apt":
                self.run_cmd(["apt-get", "install", "-y", tool])

            elif self.package_manager in ["dnf", "yum"]:
                self.run_cmd([self.package_manager, "install", "-y", tool])

            elif self.package_manager == "choco":
                self.run_cmd(["choco", "install", tool, "-y"], use_sudo=False)

        print("\n✓ System tools installation completed.")
        return True


# ---------------------------------------------------------
# Python Package Manager
# ---------------------------------------------------------

class PythonPackageManager:

    def __init__(self):
        pass

    def check_packages(self, requirements: Dict[str, str]):
        installed = {}
        try:
            import pkg_resources
            for pkg in pkg_resources.working_set:
                installed[pkg.project_name.lower()] = pkg.version
        except Exception:
            pass

        to_install = []
        to_upgrade = []

        for pkg, req_ver in requirements.items():
            pkg_lower = pkg.lower()

            if pkg_lower not in installed:
                to_install.append((pkg, req_ver))
            else:
                from packaging import version
                if version.parse(installed[pkg_lower]) < version.parse(req_ver):
                    to_upgrade.append((pkg, req_ver))

        return {"to_install": to_install, "to_upgrade": to_upgrade}

    def install_packages(self, requirements: Dict[str, str]):
        print("\n===================================================")
        print("Installing Python Packages")
        print("===================================================")

        status = self.check_packages(requirements)

        # Install missing packages
        for pkg, ver in status["to_install"]:
            print(f"\nInstalling {pkg}>={ver} ...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", f"{pkg}>={ver}"])
                print(f"✓ {pkg} installed successfully.")
            except:
                print(f"✗ Failed to install {pkg}")

        # Upgrade older packages
        for pkg, ver in status["to_upgrade"]:
            print(f"\nUpgrading {pkg} to >={ver} ...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", f"{pkg}>={ver}"])
                print(f"✓ {pkg} upgraded successfully.")
            except:
                print(f"✗ Failed to upgrade {pkg}")

        print("\n✓ Python package installation completed.")
        return True


# ---------------------------------------------------------
# MAIN EXECUTION LOGIC
# ---------------------------------------------------------

SYSTEM_TOOLS = [
    "git",
    "gcc",
    "g++",
    "make",
    "cmake",
    "wget",
    "curl"
]

PYTHON_PACKAGES = {
    "packaging": "24.0"
}

def main():

    sys_mgr = SystemManager()
    py_mgr = PythonPackageManager()

    print("\n===============================================")
    print("Lightweight GPU Burn Environment Installer")
    print("===============================================")

    # 1. Update system (APT only, skip yum/dnf)
    sys_mgr.update_system()

    # 2. Install system tools
    sys_mgr.install_system_tools(SYSTEM_TOOLS)

    # 3. Install Python packages
    py_mgr.install_packages(PYTHON_PACKAGES)

    print("\n===============================================")
    print("Installation Complete!")
    print("===============================================")

if __name__ == "__main__":
    main()
