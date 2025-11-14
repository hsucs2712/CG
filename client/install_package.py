#!/usr/bin/env python3
"""
自動化環境配置工具
支援: Windows, Linux (Ubuntu, RHEL)
功能: 自動安裝 Python 套件、系統工具、NVIDIA 驅動和 CUDA Toolkit
特性: 驅動安裝後自動重啟並繼續執行
"""

import subprocess
import sys
import os
import platform
from typing import Dict, List, Tuple
import pkg_resources

# 自動啟動腳本路徑 (Linux)
AUTO_START_SERVICE = "/etc/systemd/system/cuda-setup.service"
AUTO_START_SCRIPT = "/usr/local/bin/cuda-setup-continue.sh"

# Windows 自動啟動路徑
WINDOWS_STARTUP_SCRIPT = os.path.join(os.environ.get('APPDATA', 'C:\\'), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup', 'cuda-setup-continue.bat')
WINDOWS_FLAG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.restart_flag')

SCRIPT_PATH = os.path.abspath(__file__)

# ============================================================
# 配置區域 - 在這裡設定需要的套件
# ============================================================

# Python 套件需求 (格式: '套件名': '版本')
PYTHON_PACKAGES = {
    'pip': '', 
    'requests': '',
    'psutil': '',          # 本地系統資訊
    'rich': '',            # 終端機美化輸出
    'matplotlib': '',
}

# 系統工具需求 (Linux)
SYSTEM_TOOLS = [
    'git',
    'gcc',
    'g++',
    'make',
    'cmake',
    'wget',
    'curl',
    'build-essential',
]

# Windows 系統工具 (區分 11 和 Server)
WINDOWS_TOOLS = {
    'common': [
        'git',
        'cmake',
        'wget',
        'curl',
        '7zip',
    ],
    'windows11': [
        'powershell-core',
        'windows-terminal',
    ],
    'server': [
        'openssh',
        'sysinternals',
    ]
}

# ============================================================


class SystemManager:
    """系統管理器 - 處理系統級別的安裝"""
    
    def __init__(self):
        self.os_type = platform.system().lower()
        self.package_manager = self._detect_package_manager()
        
        print("=" * 70)
        print("系統資訊")
        print("=" * 70)
        print(f"作業系統: {platform.system()} {platform.release()}")
        print(f"Python 版本: {sys.version.split()[0]}")
        print(f"套件管理器: {self.package_manager or '未偵測到'}")
        print("=" * 70)
    
    def _detect_package_manager(self):
        """偵測系統套件管理器"""
        if self.os_type == 'linux':
            managers = ['apt-get', 'dnf']
            for manager in managers:
                try:
                    subprocess.run([manager, '--version'], 
                                 capture_output=True, check=True)
                    return manager
                except:
                    continue
        elif self.os_type == 'windows':
            # 檢測 Windows 版本
            is_server = 'server' in platform.platform().lower()
            
            print(f"Windows 版本: {platform.platform()}")
            if is_server:
                print("檢測到 Windows Server")
            else:
                print("檢測到 Windows 11/10")
            
            try:
                subprocess.run(['choco', '--version'], 
                             capture_output=True, check=True)
                return 'choco'
            except:
                print("⚠ 未安裝 Chocolatey,準備安裝...")
                return None
        return None
    
    def install_chocolatey(self) -> bool:
        """安裝 Chocolatey"""
        print("\n" + "=" * 70)
        print("安裝 Chocolatey 套件管理器")
        print("=" * 70)
        
        try:
            # PowerShell 安裝命令
            cmd = (
                "Set-ExecutionPolicy Bypass -Scope Process -Force; "
                "[System.Net.ServicePointManager]::SecurityProtocol = "
                "[System.Net.ServicePointManager]::SecurityProtocol -bor 3072; "
                "iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))"
            )
            
            print("執行 Chocolatey 安裝腳本...")
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
                capture_output=True,
                text=True,
                check=True
            )
            
            print("✓ Chocolatey 安裝成功")
            print("\n⚠ 重要: 需要重新啟動以完成安裝")
            
            # 設置自動重啟
            self.create_auto_start_windows()
            
            # 倒數重啟
            import time
            print("\n系統將在 10 秒後自動重啟...")
            for i in range(10, 0, -1):
                print(f"\r重啟倒數: {i} 秒...", end='', flush=True)
                time.sleep(1)
            print("\n")
            
            # 執行重啟
            subprocess.run(['shutdown', '/r', '/t', '0'], check=False)
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"✗ Chocolatey 安裝失敗: {e.stderr}")
            return False
        except Exception as e:
            print(f"✗ 安裝過程出錯: {e}")
            return False
    
    def _run_cmd(self, cmd: List[str], use_sudo: bool = False) -> Tuple[bool, str]:
        """執行命令"""
        if use_sudo and self.os_type == 'linux':
            cmd = ['sudo'] + cmd
        
        try:
            print(f"執行: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, e.stderr
        except Exception as e:
            return False, str(e)
    
    def update_system(self) -> bool:
        """更新系統套件列表"""
        print("\n" + "=" * 70)
        print("更新系統套件列表")
        print("=" * 70)
        
        if self.package_manager == 'apt-get':
            success, _ = self._run_cmd(['apt-get', 'update'], use_sudo=True)
            if success:
                print("✓ 系統更新完成")
                return True
        elif self.package_manager == 'dnf':
            self._run_cmd(['dnf', 'check-update'], use_sudo=True)
            print("✓ 系統更新完成")
            return True
        elif self.package_manager == 'choco':
            success, _ = self._run_cmd(['choco', 'upgrade', 'chocolatey', '-y'])
            if success:
                print("✓ Chocolatey 更新完成")
                return True
        
        print("⚠ 無法更新系統")
        return False
    
    def check_gpu(self) -> Dict:
        """檢查 NVIDIA GPU 並獲取詳細資訊"""
        print("\n" + "=" * 70)
        print("【GPU 步驟 0】檢查 NVIDIA GPU 硬體")
        print("=" * 70)
        
        if self.os_type == 'linux':
            success, output = self._run_cmd(['lspci'], use_sudo=False)
        elif self.os_type == 'windows':
            # Windows 使用 wmic 查詢 GPU
            success, output = self._run_cmd(['wmic', 'path', 'win32_VideoController', 'get', 'name'], use_sudo=False)
        else:
            success = False
            output = ""
        
        result = {
            'has_gpu': False,
            'gpu_list': [],
            'gpu_names': []
        }
        
        if success:
            lines = output.split('\n')
            for line in lines:
                if 'NVIDIA' in line.upper():
                    result['has_gpu'] = True
                    result['gpu_list'].append(line.strip())
                    
                    # 提取 GPU 名稱
                    if self.os_type == 'linux' and ':' in line:
                        parts = line.split(':', 2)
                        if len(parts) >= 3:
                            gpu_name = parts[2].strip()
                            gpu_name = gpu_name.replace('NVIDIA Corporation', '').strip()
                            result['gpu_names'].append(gpu_name)
                    elif self.os_type == 'windows':
                        gpu_name = line.strip()
                        if gpu_name and gpu_name != 'Name':
                            result['gpu_names'].append(gpu_name)
        
        if result['has_gpu']:
            print(f"✓ 偵測到 {len(result['gpu_names'])} 個 NVIDIA GPU:")
            for i, gpu_name in enumerate(result['gpu_names'], 1):
                print(f"  GPU {i}: {gpu_name}")
        else:
            print("✗ 未偵測到 NVIDIA GPU")
            print("  跳過 GPU 驅動和 CUDA 安裝")
        
        return result
    
    def check_nvidia_driver(self) -> Dict:
        """檢查 NVIDIA 驅動"""
        print("\n" + "=" * 70)
        print("【GPU 步驟 1】檢查 NVIDIA 驅動")
        print("=" * 70)
        
        success, output = self._run_cmd(['nvidia-smi'], use_sudo=False)
        
        if success:
            print("✓ NVIDIA 驅動已安裝")
            for line in output.split('\n')[:10]:
                if line.strip():
                    print(f"  {line}")
            return {'installed': True, 'needs_reboot': False}
        else:
            print("✗ NVIDIA 驅動未安裝")
            return {'installed': False, 'needs_reboot': False}
    
    def create_auto_start_linux(self) -> bool:
        """創建 Linux 自動啟動服務"""
        print("\n設置 Linux 自動啟動服務...")
        
        work_dir = os.path.dirname(SCRIPT_PATH)
        
        # 創建執行腳本
        script_content = f"""#!/bin/bash
# CUDA 安裝自動繼續腳本
sleep 10  # 等待系統完全啟動

# 切換到原始工作目錄
cd {work_dir}

# 執行 Python 腳本
{sys.executable} {SCRIPT_PATH}

# 腳本執行完成後自我刪除
rm -f {AUTO_START_SCRIPT}
rm -f {AUTO_START_SERVICE}
systemctl daemon-reload
"""
        
        try:
            with open(AUTO_START_SCRIPT, 'w') as f:
                f.write(script_content)
            os.chmod(AUTO_START_SCRIPT, 0o755)
            print(f"✓ 創建執行腳本: {AUTO_START_SCRIPT}")
        except Exception as e:
            print(f"✗ 創建腳本失敗: {e}")
            return False
        
        # 創建 systemd 服務
        service_content = f"""[Unit]
Description=CUDA Setup Auto Continue
After=network.target graphical.target

[Service]
Type=oneshot
ExecStart={AUTO_START_SCRIPT}
RemainAfterExit=no
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""
        
        try:
            with open(AUTO_START_SERVICE, 'w') as f:
                f.write(service_content)
            print(f"✓ 創建服務文件: {AUTO_START_SERVICE}")
        except Exception as e:
            print(f"✗ 創建服務失敗: {e}")
            return False
        
        # 啟用服務
        success, _ = self._run_cmd(['systemctl', 'daemon-reload'], use_sudo=True)
        if not success:
            return False
        
        success, _ = self._run_cmd(['systemctl', 'enable', 'cuda-setup.service'], 
                                   use_sudo=True)
        if success:
            print("✓ 自動啟動服務已啟用")
            return True
        else:
            print("✗ 啟用服務失敗")
            return False
    
    def create_auto_start_windows(self) -> bool:
        """創建 Windows 自動啟動腳本"""
        print("\n設置 Windows 自動啟動...")
        
        work_dir = os.path.dirname(SCRIPT_PATH)
        
        # 創建標記文件
        try:
            with open(WINDOWS_FLAG_FILE, 'w') as f:
                f.write('restart')
            print(f"✓ 創建標記文件: {WINDOWS_FLAG_FILE}")
        except Exception as e:
            print(f"✗ 創建標記文件失敗: {e}")
            return False
        
        # 創建啟動批次檔
        bat_content = f"""@echo off
timeout /t 10 /nobreak
cd /d "{work_dir}"
"{sys.executable}" "{SCRIPT_PATH}"
del "%~f0"
"""
        
        try:
            # 確保啟動資料夾存在
            startup_dir = os.path.dirname(WINDOWS_STARTUP_SCRIPT)
            os.makedirs(startup_dir, exist_ok=True)
            
            with open(WINDOWS_STARTUP_SCRIPT, 'w') as f:
                f.write(bat_content)
            print(f"✓ 創建啟動腳本: {WINDOWS_STARTUP_SCRIPT}")
            return True
        except Exception as e:
            print(f"✗ 創建啟動腳本失敗: {e}")
            return False
    
    def remove_auto_start_linux(self) -> bool:
        """移除 Linux 自動啟動服務"""
        print("\n移除 Linux 自動啟動服務...")
        
        self._run_cmd(['systemctl', 'disable', 'cuda-setup.service'], use_sudo=True)
        self._run_cmd(['systemctl', 'stop', 'cuda-setup.service'], use_sudo=True)
        
        try:
            if os.path.exists(AUTO_START_SERVICE):
                os.remove(AUTO_START_SERVICE)
                print(f"✓ 刪除服務文件: {AUTO_START_SERVICE}")
            
            if os.path.exists(AUTO_START_SCRIPT):
                os.remove(AUTO_START_SCRIPT)
                print(f"✓ 刪除執行腳本: {AUTO_START_SCRIPT}")
            
            self._run_cmd(['systemctl', 'daemon-reload'], use_sudo=True)
            print("✓ 自動啟動功能已移除")
            return True
        except Exception as e:
            print(f"⚠ 移除文件時出錯: {e}")
            return False
    
    def remove_auto_start_windows(self) -> bool:
        """移除 Windows 自動啟動"""
        print("\n移除 Windows 自動啟動...")
        
        try:
            if os.path.exists(WINDOWS_STARTUP_SCRIPT):
                os.remove(WINDOWS_STARTUP_SCRIPT)
                print(f"✓ 刪除啟動腳本: {WINDOWS_STARTUP_SCRIPT}")
            
            if os.path.exists(WINDOWS_FLAG_FILE):
                os.remove(WINDOWS_FLAG_FILE)
                print(f"✓ 刪除標記文件: {WINDOWS_FLAG_FILE}")
            
            print("✓ 自動啟動功能已移除")
            return True
        except Exception as e:
            print(f"⚠ 移除文件時出錯: {e}")
            return False
    
    def install_nvidia_driver(self) -> Dict:
        """安裝 NVIDIA 驅動 (伺服器用最新版本)"""
        print("\n開始安裝 NVIDIA 驅動...")
        print("伺服器環境: 自動選擇最新穩定版驅動")
        print("-" * 70)
        
        if self.package_manager == 'apt-get':
            # 更新系統
            self._run_cmd(['apt-get', 'update'], use_sudo=True)
            
            # 添加 NVIDIA 官方 PPA
            print("\n添加 NVIDIA 官方驅動源...")
            self._run_cmd(['apt-get', 'install', '-y', 'software-properties-common'], 
                         use_sudo=True)
            self._run_cmd(['add-apt-repository', '-y', 'ppa:graphics-drivers/ppa'], 
                         use_sudo=True)
            self._run_cmd(['apt-get', 'update'], use_sudo=True)
            
            # 使用 ubuntu-drivers 自動安裝
            print("\n安裝最新推薦驅動...")
            success, _ = self._run_cmd(['ubuntu-drivers', 'autoinstall'], use_sudo=True)
            
            if not success:
                print("⚠ 自動安裝失敗,嘗試手動指定版本...")
                drivers = ['nvidia-driver-550', 'nvidia-driver-545', 'nvidia-driver-535']
                for driver in drivers:
                    print(f"\n嘗試安裝 {driver}...")
                    success, _ = self._run_cmd(['apt-get', 'install', '-y', driver], 
                                              use_sudo=True)
                    if success:
                        break
            
            if success:
                print("✓ NVIDIA 驅動安裝成功")
                self._run_cmd(['apt-get', 'update'], use_sudo=True)
                
                # 設置自動啟動並重啟
                if self.create_auto_start_linux():
                    print("\n" + "!" * 70)
                    print("NVIDIA 驅動安裝完成!")
                    print("系統將在 10 秒後自動重啟...")
                    print("重啟後程式會自動繼續執行並安裝 CUDA Toolkit")
                    print("!" * 70)
                    
                    import time
                    for i in range(10, 0, -1):
                        print(f"\r重啟倒數: {i} 秒...", end='', flush=True)
                        time.sleep(1)
                    print("\n")
                    
                    self._run_cmd(['reboot'], use_sudo=True)
                
                return {'success': True, 'needs_reboot': True}
            else:
                print("✗ 驅動安裝失敗")
                return {'success': False, 'needs_reboot': False}
        
        elif self.package_manager == 'dnf':
            # RHEL/AlmaLinux
            print("為 RHEL/AlmaLinux 安裝最新驅動...")
            self._run_cmd(['dnf', 'install', '-y', 'epel-release'], use_sudo=True)
            success, _ = self._run_cmd(['dnf', 'install', '-y', 'nvidia-driver', 'nvidia-driver-cuda'], 
                                      use_sudo=True)
            if success:
                if self.create_auto_start_linux():
                    import time
                    for i in range(10, 0, -1):
                        print(f"\r重啟倒數: {i} 秒...", end='', flush=True)
                        time.sleep(1)
                    print("\n")
                    self._run_cmd(['reboot'], use_sudo=True)
                return {'success': True, 'needs_reboot': True}
            return {'success': False, 'needs_reboot': False}
        
        return {'success': False, 'needs_reboot': False}
    
    def install_cuda(self) -> bool:
        """安裝 CUDA Toolkit (不需要重啟)"""
        print("\n" + "=" * 70)
        print("【GPU 步驟 2】安裝 CUDA Toolkit")
        print("=" * 70)
        
        # 移除自動啟動服務
        if self.os_type == 'linux':
            self.remove_auto_start_linux()
        elif self.os_type == 'windows':
            self.remove_auto_start_windows()
        
        if self.package_manager == 'apt-get':
            print("更新系統套件列表...")
            self._run_cmd(['apt-get', 'update'], use_sudo=True)
            
            cuda_pkgs = ['cuda-toolkit', 'nvidia-cuda-toolkit']
            for pkg in cuda_pkgs:
                print(f"\n安裝 {pkg}...")
                success, _ = self._run_cmd(['apt-get', 'install', '-y', pkg], 
                                          use_sudo=True)
                if success:
                    print(f"✓ {pkg} 安裝成功 (無需重啟)")
                    self._run_cmd(['apt-get', 'update'], use_sudo=True)
                    
                    # 驗證
                    print("\n驗證 CUDA 安裝...")
                    success, output = self._run_cmd(['nvcc', '--version'], use_sudo=False)
                    if success:
                        print("✓ CUDA Toolkit 驗證成功:")
                        for line in output.split('\n'):
                            if line.strip():
                                print(f"  {line}")
                    else:
                        print("⚠ nvcc 命令不可用,可能需要設置環境變數")
                        print("  export PATH=/usr/local/cuda/bin:$PATH")
                    return True
            
            print("✗ CUDA 安裝失敗")
            return False
        
        elif self.package_manager == 'dnf':
            self._run_cmd(['dnf', 'install', '-y', 'cuda'], use_sudo=True)
            return True
        
        elif self.package_manager == 'choco':
            # Windows CUDA 安裝
            print("使用 Chocolatey 安裝 CUDA...")
            success, _ = self._run_cmd(['choco', 'install', 'cuda', '-y'])
            if success:
                print("✓ CUDA Toolkit 安裝成功")
                return True
            else:
                print("✗ CUDA 安裝失敗")
                return False
        
        return False
    
    def install_system_tools(self, tools) -> bool:
        """安裝系統工具"""
        print("\n" + "=" * 70)
        print("安裝系統工具")
        print("=" * 70)
        
        self.update_system()
        
        if self.package_manager == 'apt-get':
            if isinstance(tools, list):
                print(f"\n安裝 {len(tools)} 個工具...")
                success, _ = self._run_cmd(['apt-get', 'install', '-y'] + tools, 
                                          use_sudo=True)
                if success:
                    print("✓ 系統工具安裝完成")
                    self._run_cmd(['apt-get', 'update'], use_sudo=True)
                    return True
        
        elif self.package_manager == 'dnf':
            if isinstance(tools, list):
                success, _ = self._run_cmd(['dnf', 'install', '-y'] + tools, 
                                          use_sudo=True)
                if success:
                    print("✓ 系統工具安裝完成")
                    return True
        
        elif self.package_manager == 'choco':
            if isinstance(tools, dict):
                is_server = 'server' in platform.platform().lower()
                
                # 安裝通用工具
                print(f"\n安裝通用工具...")
                for tool in tools['common']:
                    print(f"  安裝 {tool}...")
                    self._run_cmd(['choco', 'install', tool, '-y'])
                
                # 安裝特定版本工具
                if is_server:
                    print(f"\n安裝 Windows Server 專用工具...")
                    for tool in tools['server']:
                        print(f"  安裝 {tool}...")
                        self._run_cmd(['choco', 'install', tool, '-y'])
                else:
                    print(f"\n安裝 Windows 11 專用工具...")
                    for tool in tools['windows11']:
                        print(f"  安裝 {tool}...")
                        self._run_cmd(['choco', 'install', tool, '-y'])
                
                print("✓ 系統工具安裝完成")
                return True
        
        print("✗ 系統工具安裝失敗")
        return False


class PythonPackageManager:
    """Python 套件管理器"""
    
    def __init__(self):
        self.installed = self._get_installed()
    
    def _get_installed(self) -> Dict[str, str]:
        """獲取已安裝套件"""
        packages = {}
        for dist in pkg_resources.working_set:
            packages[dist.project_name.lower()] = dist.version
        return packages
    
    def check_packages(self, requirements: Dict[str, str]) -> Dict:
        """檢查套件狀態"""
        result = {
            'to_install': [],
            'to_upgrade': [],
            'ok': []
        }
        
        print("\n" + "=" * 70)
        print("檢查 Python 套件")
        print("=" * 70)
        
        for pkg, req_ver in requirements.items():
            installed_ver = self.installed.get(pkg.lower())
            
            if not req_ver:  # 空版本表示任意版本
                if not installed_ver:
                    result['to_install'].append((pkg, ''))
                    print(f"✗ {pkg}: 未安裝")
                else:
                    result['ok'].append(pkg)
                    print(f"✓ {pkg}: {installed_ver}")
            else:
                if not installed_ver:
                    result['to_install'].append((pkg, req_ver))
                    print(f"✗ {pkg}: 未安裝 (需要 >={req_ver})")
                elif version.parse(installed_ver) < version.parse(req_ver):
                    result['to_upgrade'].append((pkg, req_ver))
                    print(f"⚠ {pkg}: {installed_ver} → 需要升級到 >={req_ver}")
                else:
                    result['ok'].append(pkg)
                    print(f"✓ {pkg}: {installed_ver}")
        
        return result
    
    def install_packages(self, requirements: Dict[str, str]) -> bool:
        """安裝所有 Python 套件"""
        print("\n" + "=" * 70)
        print("安裝 Python 套件")
        print("=" * 70)
        
        status = self.check_packages(requirements)
        
        if not status['to_install'] and not status['to_upgrade']:
            print("\n✓ 所有 Python 套件都已安裝且版本正確")
            return True
        
        # 安裝缺少的套件
        for pkg, ver in status['to_install']:
            ver_str = f'>={ver}' if ver else ''
            print(f"\n安裝 {pkg} {ver_str}...")
            pkg_str = f"{pkg}{ver_str}" if ver else pkg
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg_str])
                print(f"✓ {pkg} 安裝成功")
            except:
                print(f"✗ {pkg} 安裝失敗")
        
        # 升級舊版本
        for pkg, ver in status['to_upgrade']:
            print(f"\n升級 {pkg} 到 >={ver}...")
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', f"{pkg}>={ver}"])
                print(f"✓ {pkg} 升級成功")
            except:
                print(f"✗ {pkg} 升級失敗")
        
        print("\n✓ Python 套件安裝完成")
        return True


def main():
    """主程式 - 優化安裝順序"""
    
    print("\n")
    print("=" * 70)
    print(" " * 20 + "自動化環境配置工具")
    print("=" * 70)
    
    sys_mgr = SystemManager()
    py_mgr = PythonPackageManager()
    
    # 檢查是否為重啟後自動執行
    is_auto_continue = (os.path.exists(AUTO_START_SERVICE) or 
                       os.path.exists(WINDOWS_FLAG_FILE))
    
    if is_auto_continue:
        print("\n🔄 偵測到這是重啟後的自動繼續執行")
        print("   跳過已完成的步驟...\n")
    
    # ========================================
    # 階段 0: 檢查並安裝 Chocolatey (Windows)
    # ========================================
    if sys_mgr.os_type == 'windows' and not sys_mgr.package_manager and not is_auto_continue:
        print("\n" + "█" * 70)
        print("階段 0: 安裝 Chocolatey 套件管理器")
        print("█" * 70)
        
        if sys_mgr.install_chocolatey():
            # 安裝完成會自動重啟,這裡不會執行到
            return
        else:
            print("✗ Chocolatey 安裝失敗,無法繼續")
            return
    
    # ========================================
    # 階段 1: 系統基礎環境
    # ========================================
    if not is_auto_continue:
        print("\n" + "█" * 70)
        print("階段 1: 安裝系統基礎工具")
        print("█" * 70)
        
        # 1.1 更新系統
        sys_mgr.update_system()
        
        # 1.2 安裝系統工具
        if sys_mgr.os_type == 'linux':
            sys_mgr.install_system_tools(SYSTEM_TOOLS)
        elif sys_mgr.os_type == 'windows':
            sys_mgr.install_system_tools(WINDOWS_TOOLS)
        
        # ========================================
        # 階段 2: Python 套件 (優先安裝)
        # ========================================
        print("\n" + "█" * 70)
        print("階段 2: 安裝 Python 套件 (在 GPU 套件之前)")
        print("█" * 70)
        
        py_mgr.install_packages(PYTHON_PACKAGES)
    
    # ========================================
    # 階段 3: GPU 環境 (NVIDIA 驅動 + CUDA)
    # ========================================
    print("\n" + "█" * 70)
    print("階段 3: 配置 GPU 環境")
    print("█" * 70)
    
    # 3.1 檢查 GPU 硬體
    gpu_info = sys_mgr.check_gpu()
    
    if gpu_info['has_gpu']:
        # 3.2 檢查驅動
        driver_status = sys_mgr.check_nvidia_driver()
        
        if not driver_status['installed']:
            if not is_auto_continue:
                # 需要安裝驅動
                print("\n需要安裝 NVIDIA 驅動...")
                print(f"為以下 GPU 安裝驅動:")
                for i, gpu_name in enumerate(gpu_info['gpu_names'], 1):
                    print(f"  GPU {i}: {gpu_name}")
                
                if sys_mgr.os_type == 'linux':
                    install_result = sys_mgr.install_nvidia_driver()
                    if install_result['needs_reboot']:
                        # 程式會自動重啟,這裡不會執行到
                        return
                elif sys_mgr.os_type == 'windows':
                    print("\nWindows 系統請手動安裝 NVIDIA 驅動:")
                    print("https://www.nvidia.com/Download/index.aspx")
            else:
                print("⚠ 重啟後仍未偵測到驅動,可能安裝失敗")
                if sys_mgr.os_type == 'linux':
                    sys_mgr.remove_auto_start_linux()
                elif sys_mgr.os_type == 'windows':
                    sys_mgr.remove_auto_start_windows()
                return
        else:
            # 驅動已安裝
            if is_auto_continue:
                print("\n✓ 驅動重啟後已生效")
                print(f"繼續為以下 GPU 安裝 CUDA:")
                for i, gpu_name in enumerate(gpu_info['gpu_names'], 1):
                    print(f"  GPU {i}: {gpu_name}")
            
            # 檢查並安裝 CUDA
            success, _ = sys_mgr._run_cmd(['nvcc', '--version'], use_sudo=False)
            if not success:
                print("\n驅動已就緒,現在安裝 CUDA Toolkit...")
                sys_mgr.install_cuda()
            else:
                print("\n✓ CUDA Toolkit 已安裝,跳過")
                # 確保移除自動啟動
                if is_auto_continue:
                    if sys_mgr.os_type == 'linux':
                        sys_mgr.remove_auto_start_linux()
                    elif sys_mgr.os_type == 'windows':
                        sys_mgr.remove_auto_start_windows()
    else:
        print("\n✓ 無 GPU,跳過 GPU 相關安裝")
        # 清理可能殘留的自動啟動
        if is_auto_continue:
            if sys_mgr.os_type == 'linux':
                sys_mgr.remove_auto_start_linux()
            elif sys_mgr.os_type == 'windows':
                sys_mgr.remove_auto_start_windows()
    
    # ========================================
    # 完成報告
    # ========================================
    print("\n" + "=" * 70)
    print("配置完成!")
    print("=" * 70)
    print("\n已安裝:")
    
    if sys_mgr.os_type == 'linux':
        print(f"  ✓ {len(SYSTEM_TOOLS)} 個系統工具")
    elif sys_mgr.os_type == 'windows':
        is_server = 'server' in platform.platform().lower()
        tool_count = len(WINDOWS_TOOLS['common']) + len(WINDOWS_TOOLS['server' if is_server else 'windows11'])
        print(f"  ✓ {tool_count} 個系統工具 ({'Windows Server' if is_server else 'Windows 11'})")
    
    print(f"  ✓ {len(PYTHON_PACKAGES)} 個 Python 套件")
    
    if gpu_info['has_gpu']:
        print(f"  ✓ NVIDIA 驅動和 CUDA")
        print(f"\n檢測到的 GPU:")
        for i, gpu_name in enumerate(gpu_info['gpu_names'], 1):
            print(f"    GPU {i}: {gpu_name}")
    
    print("\n驗證命令:")
    print("  python --version")
    print("  pip list")
    
    if sys_mgr.os_type == 'linux':
        print("  git --version")
        print("  gcc --version")
        print("\nGPU 相關:")
        print("  nvidia-smi        # 查看 GPU 和驅動狀態")
        print("  nvcc --version    # 查看 CUDA 版本")
    elif sys_mgr.os_type == 'windows':
        print("  git --version")
        print("\nGPU 相關:")
        print("  nvidia-smi        # 查看 GPU 和驅動狀態")
        print("  nvcc --version    # 查看 CUDA 版本")
    
    print("=" * 70)


if __name__ == "__main__":
    # 確保有必要套件
    try:
        import pkg_resources
        from packaging import version
    except ImportError:
        print("安裝必要套件...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "packaging"])
        import pkg_resources
        from packaging import version
    
    main()