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

# 自動啟動腳本路徑 (Linux)
AUTO_START_SERVICE = "/etc/systemd/system/cuda-setup.service"
AUTO_START_SCRIPT = "/usr/local/bin/cuda-setup-continue.sh"

# Windows 自動啟動路徑
WINDOWS_STARTUP_SCRIPT = os.path.join(os.environ.get('APPDATA', 'C:\\'), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup', 'cuda-setup-continue.bat')
WINDOWS_FLAG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.restart_flag')

SCRIPT_PATH = os.path.abspath(__file__)

# GPU Compute Capability 映射表 (根據常見 GPU)
GPU_COMPUTE_CAPABILITY = {
    # RTX 40 系列
    'rtx 4090': '8.9',
    'rtx 4080': '8.9',
    'rtx 4070': '8.9',
    'rtx 4060': '8.9',
    
    # RTX 30 系列  
    'rtx 3090': '8.6',
    'rtx 3080': '8.6',
    'rtx 3070': '8.6',
    'rtx 3060': '8.6',
    
    # RTX 20 系列
    'rtx 2080': '7.5',
    'rtx 2070': '7.5',
    'rtx 2060': '7.5',
    
    # GTX 10 系列
    'gtx 1080': '6.1',
    'gtx 1070': '6.1',
    'gtx 1060': '6.1',
    
    # Tesla/Professional
    'tesla v100': '7.0',
    'tesla p100': '6.0',
    'tesla k80': '3.7',
    'tesla k40': '3.5',
    'a100': '8.0',
    'a40': '8.6',
    'a30': '8.0',
    'a10': '8.6',
    
    # Quadro
    'quadro rtx': '7.5',
    
    # 預設值
    'default': '7.5'
}

# ============================================================
# 配置區域 - 在這裡設定需要的套件
# ============================================================

# Python 套件需求 (格式: '套件名': '版本')
PYTHON_PACKAGES = {
    'requests': '',
    'psutil': '',          # 本地系統資訊
    'rich': '',            # 終端機美化輸出
    'matplotlib': '',
    'packaging': '',       # 版本比較
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
    'python3-pip',         # pip 支援
]

# GPU Burn 相關配置
GPU_BURN_REPO = "https://github.com/wilicc/gpu-burn.git"
GPU_BURN_PATH = os.path.join(os.path.dirname(SCRIPT_PATH), 'gpu-burn')

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


def run_cmd(cmd: List[str], use_sudo: bool = False, check: bool = True) -> Tuple[bool, str]:
    """執行命令的通用函數"""
    if use_sudo and platform.system().lower() == 'linux':
        cmd = ['sudo'] + cmd
    
    try:
        print(f"執行: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=check)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr
    except Exception as e:
        return False, str(e)


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
        if self.os_type == 'linux':
            print(f"Python 指令: python3")
            print(f"Python 路徑: {subprocess.run(['which', 'python3'], capture_output=True, text=True).stdout.strip()}")
        else:
            print(f"Python 路徑: {sys.executable}")
        print(f"套件管理器: {self.package_manager or '未偵測到'}")
        print("=" * 70)
    
    def _detect_package_manager(self):
        """偵測系統套件管理器"""
        if self.os_type == 'linux':
            # APT: Ubuntu, Debian, Linux Mint
            # DNF: Fedora, RHEL 9+, Rocky Linux, AlmaLinux
            managers = ['apt-get', 'dnf']
            for manager in managers:
                try:
                    subprocess.run([manager, '--version'], 
                                 capture_output=True, check=True)
                    return manager
                except:
                    continue
        elif self.os_type == 'windows':
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
                print("⚠ 未安裝 Chocolatey")
                return None
        return None
    
    def update_system(self) -> bool:
        """更新系統套件列表"""
        print("\n" + "=" * 70)
        print("更新系統套件列表")
        print("=" * 70)
        
        if self.package_manager == 'apt-get':
            success, _ = run_cmd(['apt-get', 'update'], use_sudo=True)
            if success:
                print("✓ 系統更新完成 (APT)")
                return True
        elif self.package_manager == 'dnf':
            run_cmd(['dnf', 'check-update'], use_sudo=True, check=False)
            print("✓ 系統更新完成 (DNF)")
            return True
        elif self.package_manager == 'choco':
            success, _ = run_cmd(['choco', 'upgrade', 'chocolatey', '-y'])
            if success:
                print("✓ Chocolatey 更新完成")
                return True
        
        print("⚠ 無法更新系統")
        return False
    
    def install_system_tools(self, tools) -> bool:
        """安裝系統工具"""
        print("\n" + "=" * 70)
        print("安裝系統工具")
        print("=" * 70)
        
        self.update_system()
        
        if self.package_manager == 'apt-get':
            if isinstance(tools, list):
                print(f"\n安裝 {len(tools)} 個工具 (使用 APT)...")
                success, _ = run_cmd(['apt-get', 'install', '-y'] + tools, use_sudo=True)
                if success:
                    print("✓ 系統工具安裝完成")
                    run_cmd(['apt-get', 'update'], use_sudo=True)
                    return True
        
        elif self.package_manager == 'dnf':
            if isinstance(tools, list):
                print(f"\n安裝 {len(tools)} 個工具 (使用 DNF)...")
                success, _ = run_cmd(['dnf', 'install', '-y'] + tools, use_sudo=True)
                if success:
                    print("✓ 系統工具安裝完成")
                    return True
        
        elif self.package_manager == 'choco':
            if isinstance(tools, dict):
                is_server = 'server' in platform.platform().lower()
                
                print("\n安裝通用工具...")
                for tool in tools['common']:
                    print(f"  安裝 {tool}...")
                    run_cmd(['choco', 'install', tool, '-y'], check=False)
                
                if is_server:
                    print("\n安裝 Windows Server 專用工具...")
                    for tool in tools['server']:
                        print(f"  安裝 {tool}...")
                        run_cmd(['choco', 'install', tool, '-y'], check=False)
                else:
                    print("\n安裝 Windows 11 專用工具...")
                    for tool in tools['windows11']:
                        print(f"  安裝 {tool}...")
                        run_cmd(['choco', 'install', tool, '-y'], check=False)
                
                print("✓ 系統工具安裝完成")
                return True
        
        print("✗ 系統工具安裝失敗")
        return False
    
    def check_gpu(self) -> Dict:
        """檢查 NVIDIA GPU"""
        print("\n" + "=" * 70)
        print("【GPU】檢查 NVIDIA GPU 硬體")
        print("=" * 70)
        
        if self.os_type == 'linux':
            success, output = run_cmd(['lspci'], use_sudo=False, check=False)
        elif self.os_type == 'windows':
            success, output = run_cmd(['wmic', 'path', 'win32_VideoController', 'get', 'name'], 
                                     use_sudo=False, check=False)
        else:
            success = False
            output = ""
        
        result = {
            'has_gpu': False,
            'gpu_names': [],
            'compute_capabilities': []
        }
        
        if success:
            for line in output.split('\n'):
                if 'NVIDIA' in line.upper():
                    result['has_gpu'] = True
                    if self.os_type == 'linux' and ':' in line:
                        parts = line.split(':', 2)
                        if len(parts) >= 3:
                            gpu_name = parts[2].strip().replace('NVIDIA Corporation', '').strip()
                            result['gpu_names'].append(gpu_name)
                            
                            # 查找 compute capability
                            cc = self._get_compute_capability(gpu_name)
                            result['compute_capabilities'].append(cc)
                    elif self.os_type == 'windows':
                        gpu_name = line.strip()
                        if gpu_name and gpu_name != 'Name':
                            result['gpu_names'].append(gpu_name)
                            cc = self._get_compute_capability(gpu_name)
                            result['compute_capabilities'].append(cc)
        
        if result['has_gpu']:
            print(f"✓ 偵測到 {len(result['gpu_names'])} 個 NVIDIA GPU:")
            for i, (gpu_name, cc) in enumerate(zip(result['gpu_names'], result['compute_capabilities']), 1):
                print(f"  GPU {i}: {gpu_name}")
                print(f"         Compute Capability: {cc}")
        else:
            print("✗ 未偵測到 NVIDIA GPU")
        
        return result
    
    def _get_compute_capability(self, gpu_name: str) -> str:
        """根據 GPU 名稱查找 Compute Capability"""
        gpu_name_lower = gpu_name.lower()
        
        # 查找映射表
        for key, cc in GPU_COMPUTE_CAPABILITY.items():
            if key in gpu_name_lower:
                return cc
        
        # 如果找不到,使用預設值
        print(f"    ⚠ 無法確定 Compute Capability,使用預設值: {GPU_COMPUTE_CAPABILITY['default']}")
        return GPU_COMPUTE_CAPABILITY['default']
    
    def check_nvidia_driver(self) -> Dict:
        """檢查 NVIDIA 驅動"""
        print("\n" + "=" * 70)
        print("【GPU 步驟 1】檢查 NVIDIA 驅動")
        print("=" * 70)
        
        success, output = run_cmd(['nvidia-smi'], use_sudo=False, check=False)
        
        if success:
            print("✓ NVIDIA 驅動已安裝")
            for line in output.split('\n')[:10]:
                if line.strip():
                    print(f"  {line}")
            return {'installed': True}
        else:
            print("✗ NVIDIA 驅動未安裝")
            return {'installed': False}
    
    def create_auto_start_linux(self) -> bool:
        """創建 Linux 自動啟動服務"""
        print("\n設置 Linux 自動啟動服務...")
        
        work_dir = os.path.dirname(SCRIPT_PATH)
        
        # Linux 使用 python3
        script_content = f"""#!/bin/bash
        # CUDA 安裝自動繼續腳本
        sleep 10
        cd {work_dir}
        python3 {SCRIPT_PATH}
        rm -f {AUTO_START_SCRIPT}
        rm -f {AUTO_START_SERVICE}
        systemctl daemon-reload
        """
        
        try:
            with open(AUTO_START_SCRIPT, 'w') as f:
                f.write(script_content)
            os.chmod(AUTO_START_SCRIPT, 0o755)
            print(f"✓ 創建執行腳本: {AUTO_START_SCRIPT}")
            print(f"  使用: python3")
        except Exception as e:
            print(f"✗ 創建腳本失敗: {e}")
            return False
        
        service_content = f"""[Unit]
        Description=CUDA Setup Auto Continue
        After=network.target graphical.target

        [Service]
        Type=oneshot
        ExecStart={AUTO_START_SCRIPT}
        RemainAfterExit=no

        [Install]
        WantedBy=multi-user.target
        """
        
        try:
            with open(AUTO_START_SERVICE, 'w') as f:
                f.write(service_content)
        except Exception as e:
            print(f"✗ 創建服務失敗: {e}")
            return False
        
        success, _ = run_cmd(['systemctl', 'daemon-reload'], use_sudo=True)
        if not success:
            return False
        
        success, _ = run_cmd(['systemctl', 'enable', 'cuda-setup.service'], use_sudo=True)
        if success:
            print("✓ 自動啟動服務已啟用")
            return True
        return False
    
    def remove_auto_start_linux(self) -> bool:
        """移除 Linux 自動啟動服務"""
        print("\n移除 Linux 自動啟動服務...")
        
        run_cmd(['systemctl', 'disable', 'cuda-setup.service'], use_sudo=True, check=False)
        run_cmd(['systemctl', 'stop', 'cuda-setup.service'], use_sudo=True, check=False)
        
        try:
            if os.path.exists(AUTO_START_SERVICE):
                os.remove(AUTO_START_SERVICE)
            if os.path.exists(AUTO_START_SCRIPT):
                os.remove(AUTO_START_SCRIPT)
            run_cmd(['systemctl', 'daemon-reload'], use_sudo=True)
            print("✓ 自動啟動功能已移除")
            return True
        except Exception as e:
            print(f"⚠ 移除文件時出錯: {e}")
            return False
    
    def disable_nouveau(self) -> bool:
        """關閉 nouveau 驅動並更新 initramfs"""
        print("\n" + "=" * 70)
        print("關閉 Nouveau 開源驅動")
        print("=" * 70)
        
        blacklist_file = "/etc/modprobe.d/blacklist-nouveau.conf"
        blacklist_content = """# Blacklist nouveau driver
blacklist nouveau
options nouveau modeset=0
"""
        
        try:
            # 檢查是否已經設定
            if os.path.exists(blacklist_file):
                print(f"✓ {blacklist_file} 已存在")
            else:
                print(f"創建 {blacklist_file}...")
                with open(blacklist_file, 'w') as f:
                    f.write(blacklist_content)
                print(f"✓ 已創建 blacklist 設定")
            
            # 更新 initramfs
            print("\n更新 initramfs...")
            
            if self.package_manager == 'apt-get':
                # Ubuntu/Debian
                success, _ = run_cmd(['update-initramfs', '-u'], use_sudo=True)
                if success:
                    print("✓ initramfs 更新完成 (update-initramfs)")
                else:
                    print("⚠ initramfs 更新失敗")
                    
            elif self.package_manager == 'dnf':
                # RHEL/AlmaLinux
                success, _ = run_cmd(['dracut', '--force'], use_sudo=True)
                if success:
                    print("✓ initramfs 更新完成 (dracut)")
                else:
                    print("⚠ initramfs 更新失敗")
            
            print("\n⚠ 重要: 需要重啟後 nouveau 才會被停用")
            return True
            
        except Exception as e:
            print(f"✗ 關閉 nouveau 失敗: {e}")
            return False
    
    def remove_existing_nvidia_driver(self) -> bool:
        """移除現有的 NVIDIA 驅動"""
        print("\n檢查並移除舊的 NVIDIA 驅動...")
        
        if self.package_manager == 'apt-get':
            # 檢查是否有安裝
            success, output = run_cmd(['dpkg', '-l'], use_sudo=False, check=False)
            if success and 'nvidia' in output.lower():
                print("偵測到舊的 NVIDIA 套件,準備移除...")
                run_cmd(['apt-get', 'remove', '--purge', '-y', 'nvidia-*'], use_sudo=True, check=False)
                run_cmd(['apt-get', 'autoremove', '-y'], use_sudo=True, check=False)
                print("✓ 舊驅動已移除")
            else:
                print("✓ 沒有舊的 NVIDIA 驅動")
                
        elif self.package_manager == 'dnf':
            # 檢查是否有安裝
            success, output = run_cmd(['dnf', 'list', 'installed'], use_sudo=False, check=False)
            if success and 'nvidia' in output.lower():
                print("偵測到舊的 NVIDIA 套件,準備移除...")
                run_cmd(['dnf', 'remove', '-y', 'nvidia-*'], use_sudo=True, check=False)
                print("✓ 舊驅動已移除")
            else:
                print("✓ 沒有舊的 NVIDIA 驅動")
        
        return True
    
    def install_nvidia_driver_dnf(self, gpu_info: Dict) -> bool:
        """DNF: 使用 network repo 安裝 NVIDIA 驅動和 CUDA"""
        print("\n" + "=" * 70)
        print("DNF: 安裝 NVIDIA 驅動和 CUDA Toolkit")
        print("=" * 70)
        
        # 1. 添加 NVIDIA 官方 repository
        print("\n【步驟 1】添加 NVIDIA Network Repository...")
        
        nvidia_repo = "https://developer.download.nvidia.com/compute/cuda/repos/rhel9/x86_64/cuda-rhel9.repo"
        
        success, _ = run_cmd(['dnf', 'config-manager', '--add-repo', nvidia_repo], 
                            use_sudo=True, check=False)
        if success:
            print("✓ NVIDIA Repository 添加成功")
        else:
            print("⚠ Repository 添加失敗,嘗試手動下載...")
            run_cmd(['wget', '-O', '/etc/yum.repos.d/cuda-rhel9.repo', nvidia_repo], 
                   use_sudo=True, check=False)
        
        # 2. 清理並更新 cache
        print("\n【步驟 2】更新套件資料庫...")
        run_cmd(['dnf', 'clean', 'all'], use_sudo=True)
        run_cmd(['dnf', 'makecache'], use_sudo=True)
        
        # 3. 安裝 NVIDIA 驅動
        print("\n【步驟 3】安裝 NVIDIA 驅動...")
        
        driver_package = 'nvidia-driver:latest-dkms'
        
        success, _ = run_cmd(['dnf', 'module', 'install', '-y', driver_package], 
                            use_sudo=True, check=False)
        
        if not success:
            print("模組安裝失敗,嘗試直接安裝...")
            success, _ = run_cmd(['dnf', 'install', '-y', 'nvidia-driver', 'nvidia-settings'], 
                                use_sudo=True, check=False)
        
        if success:
            print("✓ NVIDIA 驅動安裝成功")
        else:
            print("✗ NVIDIA 驅動安裝失敗")
            return False
        
        # 4. 安裝 CUDA Toolkit
        print("\n【步驟 4】安裝 CUDA Toolkit...")
        
        success, _ = run_cmd(['dnf', 'install', '-y', 'cuda-toolkit'], use_sudo=True, check=False)
        
        if not success:
            print("嘗試安裝 cuda-toolkit-12-x...")
            success, _ = run_cmd(['dnf', 'install', '-y', 'cuda-toolkit-12-*'], 
                                use_sudo=True, check=False)
        
        if success:
            print("✓ CUDA Toolkit 安裝成功")
        else:
            print("✗ CUDA Toolkit 安裝失敗")
            return False
        
        # 5. 完整系統更新 (upgrade)
        print("\n【步驟 5】執行完整系統更新...")
        run_cmd(['dnf', 'upgrade', '-y'], use_sudo=True)
        print("✓ 系統更新完成 (dnf upgrade)")
        
        return True
    
    def install_nvidia_driver_apt(self, gpu_info: Dict) -> bool:
        """APT: 使用 network repo 安裝 NVIDIA 驅動和 CUDA"""
        print("\n" + "=" * 70)
        print("APT: 安裝 NVIDIA 驅動和 CUDA Toolkit")
        print("=" * 70)
        
        # 1. 添加 NVIDIA 官方 repository
        print("\n【步驟 1】添加 NVIDIA Network Repository...")
        
        run_cmd(['apt-get', 'install', '-y', 'software-properties-common', 'wget'], use_sudo=True)
        
        cuda_keyring = "cuda-keyring_1.1-1_all.deb"
        
        print("下載 CUDA Repository 設定...")
        run_cmd(['wget', 'https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb'], 
               check=False)
        
        if os.path.exists(cuda_keyring):
            run_cmd(['dpkg', '-i', cuda_keyring], use_sudo=True)
            print("✓ CUDA Repository 添加成功")
        else:
            print("⚠ Repository keyring 下載失敗,嘗試備用方案...")
            run_cmd(['add-apt-repository', '-y', 'ppa:graphics-drivers/ppa'], use_sudo=True)
        
        # 2. 更新套件資料庫
        print("\n【步驟 2】更新套件資料庫...")
        run_cmd(['apt-get', 'update'], use_sudo=True)
        
        # 3. 移除舊驅動
        print("\n【步驟 3】移除舊的 NVIDIA 驅動...")
        self.remove_existing_nvidia_driver()
        
        # 4. 安裝驅動
        print("\n【步驟 4】安裝 NVIDIA 驅動...")
        
        success, output = run_cmd(['ubuntu-drivers', 'devices'], use_sudo=True, check=False)
        
        if success and 'recommended' in output:
            print("使用 ubuntu-drivers 自動安裝推薦驅動...")
            success, _ = run_cmd(['ubuntu-drivers', 'autoinstall'], use_sudo=True, check=False)
        else:
            print("手動安裝最新驅動版本...")
            drivers = ['nvidia-driver-550', 'nvidia-driver-545', 'nvidia-driver-535']
            for driver in drivers:
                print(f"嘗試安裝 {driver}...")
                success, _ = run_cmd(['apt-get', 'install', '-y', driver], use_sudo=True, check=False)
                if success:
                    break
        
        if success:
            print("✓ NVIDIA 驅動安裝成功")
        else:
            print("✗ NVIDIA 驅動安裝失敗")
            return False
        
        # 5. 安裝 CUDA Toolkit
        print("\n【步驟 5】安裝 CUDA Toolkit...")
        
        cuda_packages = ['cuda-toolkit-12-6', 'cuda-toolkit-12-5', 'cuda-toolkit']
        
        for pkg in cuda_packages:
            print(f"嘗試安裝 {pkg}...")
            success, _ = run_cmd(['apt-get', 'install', '-y', pkg], use_sudo=True, check=False)
            if success:
                print(f"✓ {pkg} 安裝成功")
                break
        
        if not success:
            print("✗ CUDA Toolkit 安裝失敗")
            return False
        
        # 6. 完整系統更新 (update + upgrade + dist-upgrade)
        print("\n【步驟 6】執行完整系統更新...")
        run_cmd(['apt-get', 'update'], use_sudo=True)
        run_cmd(['apt-get', 'upgrade', '-y'], use_sudo=True)
        run_cmd(['apt-get', 'dist-upgrade', '-y'], use_sudo=True)
        print("✓ 系統更新完成 (apt update + upgrade + dist-upgrade)")
        
        return True
        """DNF: 使用 network repo 安裝 NVIDIA 驅動和 CUDA"""
        print("\n" + "=" * 70)
        print("DNF: 安裝 NVIDIA 驅動和 CUDA Toolkit")
        print("=" * 70)
        
        # 1. 添加 NVIDIA 官方 repository
        print("\n【步驟 1】添加 NVIDIA Network Repository...")
        
        # RHEL/AlmaLinux 8+
        nvidia_repo = "https://developer.download.nvidia.com/compute/cuda/repos/rhel9/x86_64/cuda-rhel9.repo"
        
        success, _ = run_cmd(['dnf', 'config-manager', '--add-repo', nvidia_repo], 
                            use_sudo=True, check=False)
        if success:
            print("✓ NVIDIA Repository 添加成功")
        else:
            print("⚠ Repository 添加失敗,嘗試手動下載...")
            run_cmd(['wget', '-O', '/etc/yum.repos.d/cuda-rhel9.repo', nvidia_repo], 
                   use_sudo=True, check=False)
        
        # 2. 清理並更新 cache
        print("\n【步驟 2】更新套件資料庫...")
        run_cmd(['dnf', 'clean', 'all'], use_sudo=True)
        run_cmd(['dnf', 'makecache'], use_sudo=True)
        
        # 3. 安裝 NVIDIA 驅動
        print("\n【步驟 3】安裝 NVIDIA 驅動...")
        
        # 根據 GPU 選擇驅動版本
        driver_package = 'nvidia-driver:latest-dkms'  # 使用 DKMS 版本
        
        success, _ = run_cmd(['dnf', 'module', 'install', '-y', driver_package], 
                            use_sudo=True, check=False)
        
        if not success:
            # 備用方案: 直接安裝套件
            print("模組安裝失敗,嘗試直接安裝...")
            success, _ = run_cmd(['dnf', 'install', '-y', 'nvidia-driver', 'nvidia-settings'], 
                                use_sudo=True, check=False)
        
        if success:
            print("✓ NVIDIA 驅動安裝成功")
        else:
            print("✗ NVIDIA 驅動安裝失敗")
            return False
        
        # 4. 安裝 CUDA Toolkit
        print("\n【步驟 4】安裝 CUDA Toolkit...")
        
        success, _ = run_cmd(['dnf', 'install', '-y', 'cuda-toolkit'], use_sudo=True, check=False)
        
        if not success:
            # 嘗試安裝特定版本
            print("嘗試安裝 cuda-toolkit-12-x...")
            success, _ = run_cmd(['dnf', 'install', '-y', 'cuda-toolkit-12-*'], 
                                use_sudo=True, check=False)
        
        if success:
            print("✓ CUDA Toolkit 安裝成功")
        else:
            print("✗ CUDA Toolkit 安裝失敗")
            return False
        
        # 5. 完整系統更新
        print("\n【步驟 5】執行完整系統更新...")
        run_cmd(['dnf', 'upgrade', '-y'], use_sudo=True)
        print("✓ 系統更新完成")
        
        return True
    
    def install_nvidia_driver_apt(self, gpu_info: Dict) -> bool:
        """APT: 使用 network repo 安裝 NVIDIA 驅動和 CUDA"""
        print("\n" + "=" * 70)
        print("APT: 安裝 NVIDIA 驅動和 CUDA Toolkit")
        print("=" * 70)
        
        # 1. 添加 NVIDIA 官方 repository
        print("\n【步驟 1】添加 NVIDIA Network Repository...")
        
        # 安裝必要工具
        run_cmd(['apt-get', 'install', '-y', 'software-properties-common', 'wget'], use_sudo=True)
        
        # 添加 NVIDIA CUDA Repository
        cuda_repo_pin = "/etc/apt/preferences.d/cuda-repository-pin-600"
        cuda_keyring = "cuda-keyring_1.1-1_all.deb"
        
        print("下載 CUDA Repository 設定...")
        run_cmd(['wget', 'https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb'], 
               check=False)
        
        if os.path.exists(cuda_keyring):
            run_cmd(['dpkg', '-i', cuda_keyring], use_sudo=True)
            print("✓ CUDA Repository 添加成功")
        else:
            print("⚠ Repository keyring 下載失敗,嘗試備用方案...")
            # 添加 Graphics Drivers PPA
            run_cmd(['add-apt-repository', '-y', 'ppa:graphics-drivers/ppa'], use_sudo=True)
        
        # 2. 更新套件資料庫
        print("\n【步驟 2】更新套件資料庫...")
        run_cmd(['apt-get', 'update'], use_sudo=True)
        
        # 3. 移除舊驅動
        print("\n【步驟 3】移除舊的 NVIDIA 驅動...")
        self.remove_existing_nvidia_driver()
        
        # 4. 根據 GPU 安裝對應版本的驅動
        print("\n【步驟 4】安裝 NVIDIA 驅動...")
        
        # 查詢推薦的驅動版本
        success, output = run_cmd(['ubuntu-drivers', 'devices'], use_sudo=True, check=False)
        
        if success and 'recommended' in output:
            print("使用 ubuntu-drivers 自動安裝推薦驅動...")
            success, _ = run_cmd(['ubuntu-drivers', 'autoinstall'], use_sudo=True, check=False)
        else:
            # 手動安裝最新版本
            print("手動安裝最新驅動版本...")
            drivers = ['nvidia-driver-550', 'nvidia-driver-545', 'nvidia-driver-535']
            for driver in drivers:
                print(f"嘗試安裝 {driver}...")
                success, _ = run_cmd(['apt-get', 'install', '-y', driver], use_sudo=True, check=False)
                if success:
                    break
        
        if success:
            print("✓ NVIDIA 驅動安裝成功")
        else:
            print("✗ NVIDIA 驅動安裝失敗")
            return False
        
        # 5. 安裝 CUDA Toolkit
        print("\n【步驟 5】安裝 CUDA Toolkit...")
        
        cuda_packages = ['cuda-toolkit-12-6', 'cuda-toolkit-12-5', 'cuda-toolkit']
        
        for pkg in cuda_packages:
            print(f"嘗試安裝 {pkg}...")
            success, _ = run_cmd(['apt-get', 'install', '-y', pkg], use_sudo=True, check=False)
            if success:
                print(f"✓ {pkg} 安裝成功")
                break
        
        if not success:
            print("✗ CUDA Toolkit 安裝失敗")
            return False
        
        # 6. 完整系統更新
        print("\n【步驟 6】執行完整系統更新...")
        run_cmd(['apt-get', 'update'], use_sudo=True)
        run_cmd(['apt-get', 'upgrade', '-y'], use_sudo=True)
        run_cmd(['apt-get', 'dist-upgrade', '-y'], use_sudo=True)
        print("✓ 系統更新完成")
        
        return True
    
    def install_chocolatey(self) -> bool:
        """安裝 Chocolatey 套件管理器"""
        print("\n" + "=" * 70)
        print("安裝 Chocolatey 套件管理器")
        print("=" * 70)
        
        try:
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
            print("\n⚠ 重要: 需要重新啟動 PowerShell/命令提示字元才能使用 choco")
            
            # 設置 Windows 自動重啟
            self.create_auto_start_windows()
            
            print("\n系統將在 10 秒後自動重啟...")
            import time
            for i in range(10, 0, -1):
                print(f"\r重啟倒數: {i} 秒...", end='', flush=True)
                time.sleep(1)
            print("\n")
            
            subprocess.run(['shutdown', '/r', '/t', '0'], check=False)
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"✗ Chocolatey 安裝失敗: {e.stderr}")
            return False
        except Exception as e:
            print(f"✗ 安裝過程出錯: {e}")
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
            startup_dir = os.path.dirname(WINDOWS_STARTUP_SCRIPT)
            os.makedirs(startup_dir, exist_ok=True)
            
            with open(WINDOWS_STARTUP_SCRIPT, 'w') as f:
                f.write(bat_content)
            print(f"✓ 創建啟動腳本: {WINDOWS_STARTUP_SCRIPT}")
            return True
        except Exception as e:
            print(f"✗ 創建啟動腳本失敗: {e}")
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
        
    def install_nvidia_driver_windows(self) -> bool:
        """Windows: 使用 Chocolatey 安裝 NVIDIA 顯示卡驅動"""
        print("\n" + "=" * 70)
        print("Windows: 安裝 NVIDIA 顯示卡驅動")
        print("=" * 70)

        if not self.package_manager:
            print("✗ 無法安裝：Chocolatey 未安裝")
            return False

        print("\n使用 Chocolatey 安裝 NVIDIA 顯示卡驅動...")
        success, output = run_cmd(['choco', 'install', 'nvidia-display-driver', '-y'], check=False)

        if success:
            print("✓ NVIDIA 顯示卡驅動安裝成功")
            
            # 驗證 GPU 是否啟動
            gpu_info = self.check_gpu()
            if gpu_info.get('has_gpu', False):
                print("✓ 驅動啟用成功，已偵測到 GPU：")
                print(f"  型號：{gpu_info.get('gpu_name')}")
            else:
                print("✗ 驅動安裝後仍未偵測到 GPU，可能需要重啟")
            
            return True

        else:
            print("✗ NVIDIA Driver 安裝失敗")
            print(f"錯誤：{output}")

            print("\n手動下載：")
            print("https://www.nvidia.com/Download/index.aspx")
            return False
    
    def install_nvidia_cuda_windows(self) -> bool:
        """Windows: 使用 Chocolatey 安裝 CUDA Toolkit"""
        print("\n" + "=" * 70)
        print("Windows: 安裝 CUDA Toolkit")
        print("=" * 70)
        
        if not self.package_manager:
            print("✗ Chocolatey 未安裝,無法繼續")
            return False
        
        print("\n使用 Chocolatey 安裝 CUDA...")
        success, output = run_cmd(['choco', 'install', 'cuda', '-y'], check=False)
        
        if success:
            print("✓ CUDA Toolkit 安裝成功")
            
            # 驗證安裝
            success, output = run_cmd(['nvcc', '--version'], use_sudo=False, check=False)
            if success:
                print("\n✓ CUDA 驗證成功:")
                for line in output.split('\n'):
                    if line.strip():
                        print(f"  {line}")
            return True
        else:
            print(f"✗ CUDA 安裝失敗")
            print(f"錯誤: {output}")
            
            print("\n建議手動安裝:")
            print("1. 從 NVIDIA 官網下載: https://developer.nvidia.com/cuda-downloads")
            print("2. 選擇 Windows 版本並安裝")
            return False
    
    def install_cuda(self) -> bool:
        """安裝 CUDA Toolkit"""
        print("\n" + "=" * 70)
        print("【GPU 步驟 2】安裝 CUDA Toolkit")
        print("=" * 70)
        
        self.remove_auto_start_linux()
        
        if self.package_manager == 'apt-get':
            run_cmd(['apt-get', 'update'], use_sudo=True)
            
            cuda_pkgs = ['cuda-toolkit', 'nvidia-cuda-toolkit']
            for pkg in cuda_pkgs:
                print(f"\n安裝 {pkg}...")
                success, _ = run_cmd(['apt-get', 'install', '-y', pkg], use_sudo=True, check=False)
                if success:
                    print(f"✓ {pkg} 安裝成功 (無需重啟)")
                    run_cmd(['apt-get', 'update'], use_sudo=True)
                    
                    success, output = run_cmd(['nvcc', '--version'], use_sudo=False, check=False)
                    if success:
                        print("✓ CUDA Toolkit 驗證成功:")
                        for line in output.split('\n'):
                            if line.strip():
                                print(f"  {line}")
                    return True
            
            return False
        
        elif self.package_manager == 'dnf':
            run_cmd(['dnf', 'install', '-y', 'cuda'], use_sudo=True, check=False)
            return True
        
        elif self.package_manager == 'choco':
            success, _ = run_cmd(['choco', 'install', 'cuda', '-y'])
            return success
        
        return False
    
    def install_gpu_burn(self, compute_capability: str = None) -> bool:
        """下載並編譯 GPU Burn"""
        print("\n" + "=" * 70)
        print("【GPU 步驟 3】安裝 GPU Burn 壓力測試工具")
        print("=" * 70)
        
        # 檢查是否已存在
        if os.path.exists(GPU_BURN_PATH):
            print(f"✓ GPU Burn 目錄已存在: {GPU_BURN_PATH}")
            if os.path.exists(os.path.join(GPU_BURN_PATH, 'gpu_burn')):
                print("✓ GPU Burn 已編譯")
                return True
            else:
                print("⚠ 需要重新編譯")
        else:
            # Clone repository
            print(f"\nClone GPU Burn repository...")
            print(f"來源: {GPU_BURN_REPO}")
            success, _ = run_cmd(['git', 'clone', GPU_BURN_REPO, GPU_BURN_PATH], check=False)
            
            if not success:
                print("✗ Clone 失敗")
                return False
            
            print("✓ Clone 成功")
        
        # 編譯
        print(f"\n編譯 GPU Burn...")
        
        if compute_capability:
            print(f"使用 Compute Capability: {compute_capability}")
            make_cmd = ['make', f'COMPUTE={compute_capability.replace(".", "")}']
        else:
            print("使用預設 Compute Capability")
            make_cmd = ['make']
        
        # 切換到 gpu-burn 目錄並執行 make
        original_dir = os.getcwd()
        try:
            os.chdir(GPU_BURN_PATH)
            
            # 設置 CUDA 路徑
            cuda_paths = ['/usr/local/cuda', '/usr/local/cuda-12', '/usr/local/cuda-11', '/usr']
            cuda_path = None
            for path in cuda_paths:
                nvcc_path = os.path.join(path, 'bin', 'nvcc') if path != '/usr' else '/usr/bin/nvcc'
                if os.path.exists(nvcc_path):
                    cuda_path = path
                    break
            
            if cuda_path:
                print(f"使用 CUDA 路徑: {cuda_path}")
                make_cmd.append(f'CUDAPATH={cuda_path}')
            
            success, output = run_cmd(make_cmd, check=False)
            
            if success and os.path.exists('gpu_burn'):
                print("✓ GPU Burn 編譯成功")
                print(f"\n執行檔位置: {os.path.join(GPU_BURN_PATH, 'gpu_burn')}")
                print("\n" + "=" * 70)
                print("使用方式:")
                print("=" * 70)
                print(f"cd {GPU_BURN_PATH}")
                print("./gpu_burn 60       # 測試 60 秒")
                print("./gpu_burn 3600     # 測試 1 小時")
                print("./gpu_burn -d 60    # 使用 double 精度測試")
                print("./gpu_burn -l       # 列出所有 GPU")
                print("./gpu_burn -i 0     # 只測試 GPU 0")
                print("=" * 70)
                return True
            else:
                print(f"✗ GPU Burn 編譯失敗")
                if output:
                    print(f"錯誤訊息: {output}")
                return False
                
        finally:
            os.chdir(original_dir)


class PythonPackageManager:
    """Python 套件管理器"""
    
    def __init__(self):
        # Linux 使用 python3, Windows 使用 python
        if platform.system().lower() == 'linux':
            self.python_exec = 'python3'
        else:
            self.python_exec = sys.executable
        
        self.installed = self._get_installed()
    
    def _get_installed(self) -> Dict[str, str]:
        """獲取已安裝套件"""
        packages = {}
        try:
            import json
            cmd = [self.python_exec, '-m', 'pip', 'list', '--format=json']
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            pkg_list = json.loads(result.stdout)
            for pkg in pkg_list:
                packages[pkg['name'].lower()] = pkg['version']
        except:
            pass
        return packages
    
    def install_packages(self, requirements: Dict[str, str]) -> bool:
        """安裝所有 Python 套件 (使用 --break-system-packages)"""
        print("\n" + "=" * 70)
        print("安裝 Python 套件")
        print("=" * 70)
        print(f"使用 Python: {self.python_exec}")
        
        to_install = []
        
        for pkg, ver in requirements.items():
            installed_ver = self.installed.get(pkg.lower())
            if not installed_ver:
                to_install.append((pkg, ver))
                print(f"✗ {pkg}: 未安裝")
            else:
                print(f"✓ {pkg}: {installed_ver}")
        
        if not to_install:
            print("\n✓ 所有 Python 套件都已安裝")
            return True
        
        # 安裝缺少的套件
        for pkg, ver in to_install:
            ver_str = f'>={ver}' if ver else ''
            print(f"\n安裝 {pkg} {ver_str}...")
            pkg_str = f"{pkg}{ver_str}" if ver else pkg
            
            # Linux 使用 python3 -m pip install --break-system-packages
            # Windows 使用一般的 pip install
            try:
                if platform.system().lower() == 'linux':
                    # Linux: python3 -m pip install --break-system-packages
                    subprocess.check_call([
                        self.python_exec, '-m', 'pip', 'install', 
                        '--break-system-packages', pkg_str
                    ])
                else:
                    # Windows: python -m pip install
                    subprocess.check_call([
                        self.python_exec, '-m', 'pip', 'install', pkg_str
                    ])
                print(f"✓ {pkg} 安裝成功")
            except Exception as e:
                print(f"✗ {pkg} 安裝失敗: {e}")
        
        print("\n✓ Python 套件安裝完成")
        return True


def main():
    """主程式"""
    
    print("\n" + "=" * 70)
    print(" " * 15 + "自動化環境配置工具")
    print("=" * 70)
    
    is_auto_continue = os.path.exists(AUTO_START_SERVICE)
    
    if is_auto_continue:
        print("\n🔄 偵測到重啟後自動繼續執行\n")
    
    sys_mgr = SystemManager()
    
    # ==========================================
    # 階段 1: 檢查現有安裝
    # ==========================================
    if not is_auto_continue:
        print("\n" + "█" * 70)
        print("檢查現有 NVIDIA 環境")
        print("█" * 70)
        
        # 檢查 GPU
        gpu_info = sys_mgr.check_gpu()
        
        if not gpu_info['has_gpu']:
            print("\n✗ 沒有偵測到 NVIDIA GPU")
            if sys_mgr.os_type == 'windows':
                print("   Windows 系統將繼續安裝系統工具和 Python 套件")
            else:
                print("   程式結束")
                return
        
        # 檢查驅動
        driver_status = sys_mgr.check_nvidia_driver()
        has_driver = driver_status['installed']
        
        # 檢查 CUDA
        success, _ = run_cmd(['nvcc', '--version'], use_sudo=False, check=False)
        has_cuda = success
        
        print(f"\n現狀:")
        print(f"  GPU: {'✓ 已偵測' if gpu_info['has_gpu'] else '✗ 未偵測'}")
        print(f"  驅動: {'✓ 已安裝' if has_driver else '✗ 未安裝'}")
        print(f"  CUDA: {'✓ 已安裝' if has_cuda else '✗ 未安裝'}")
        
        if has_driver and has_cuda and sys_mgr.os_type == 'linux':
            print("\n✓ Linux 驅動和 CUDA 都已安裝,跳到 GPU Burn 安裝")
            sys_mgr.check_and_install_gpu_burn_deps()
            
            if gpu_info['compute_capabilities']:
                cc = gpu_info['compute_capabilities'][0]
                sys_mgr.install_gpu_burn(compute_capability=cc)
            
            print("\n✓ 配置完成!")
            return
        
        # ==========================================
        # 階段 2: Windows Chocolatey 安裝
        # ==========================================
        if sys_mgr.os_type == 'windows' and not sys_mgr.package_manager:
            print("\n" + "█" * 70)
            print("階段 0: 安裝 Chocolatey 套件管理器")
            print("█" * 70)
            
            if sys_mgr.install_chocolatey():
                # 安裝完成會自動重啟
                return
            else:
                print("✗ Chocolatey 安裝失敗,無法繼續")
                return
        
        # ==========================================
        # 階段 2: DNF 系統完整安裝流程
        # ==========================================
        if sys_mgr.package_manager == 'dnf':
            print("\n" + "█" * 70)
            print("DNF 系統安裝流程")
            print("█" * 70)
            
            # 2.1 關閉 nouveau
            print("\n【DNF】關閉 Nouveau 驅動")
            sys_mgr.disable_nouveau()
            
            # 2.2 安裝驅動和 CUDA (使用 network repo)
            print("\n【DNF】使用 Network Repository 安裝")
            success = sys_mgr.install_nvidia_driver_dnf(gpu_info)
            
            if not success:
                print("✗ 安裝失敗")
                return
            
            # 2.3 檢查 GPU Burn 依賴
            print("\n【DNF】檢查 GPU Burn 依賴")
            sys_mgr.check_and_install_gpu_burn_deps()
            
            # 2.4 設置自動重啟
            sys_mgr.create_auto_start_linux()
            
            print("\n" + "!" * 70)
            print("DNF 系統配置完成!")
            print("系統將在 15 秒後自動重啟...")
            print("重啟後程式會自動繼續並安裝 GPU Burn")
            print("!" * 70)
            
            import time
            for i in range(15, 0, -1):
                print(f"\r重啟倒數: {i} 秒...", end='', flush=True)
                time.sleep(1)
            print("\n")
            
            run_cmd(['reboot'], use_sudo=True)
            return
        
        # ==========================================
        # 階段 2: APT 系統完整安裝流程
        # ==========================================
        elif sys_mgr.package_manager == 'apt-get':
            print("\n" + "█" * 70)
            print("APT 系統安裝流程")
            print("█" * 70)
            
            # 3.1 關閉 nouveau
            print("\n【APT】嘗試關閉 Nouveau 驅動")
            sys_mgr.disable_nouveau()
            
            # 3.2 安裝驅動和 CUDA (使用 network repo)
            print("\n【APT】使用 Network Repository 安裝")
            success = sys_mgr.install_nvidia_driver_apt(gpu_info)
            
            if not success:
                print("✗ 安裝失敗")
                return
            
            # 3.3 檢查 GPU Burn 依賴
            print("\n【APT】檢查 GPU Burn 依賴")
            sys_mgr.check_and_install_gpu_burn_deps()
            
            # 3.4 設置自動重啟
            sys_mgr.create_auto_start_linux()
            
            print("\n" + "!" * 70)
            print("APT 系統配置完成!")
            print("系統將在 15 秒後自動重啟...")
            print("重啟後程式會自動繼續並安裝 GPU Burn")
            print("!" * 70)
            
            import time
            for i in range(15, 0, -1):
                print(f"\r重啟倒數: {i} 秒...", end='', flush=True)
                time.sleep(1)
            print("\n")
            
            run_cmd(['reboot'], use_sudo=True)
            return
        
    # ==========================================
    # 階段 5: 重啟後 - 安裝 Python 套件和 GPU Burn
    # ==========================================
    if is_auto_continue:
        if sys_mgr.os_type == 'linux':
            # Linux 重啟後流程
            print("\n" + "█" * 70)
            print("重啟後繼續 - Python 套件")
            print("█" * 70)
            
            sys_mgr.remove_auto_start_linux()
            
            gpu_info = sys_mgr.check_gpu()
            
            driver_status = sys_mgr.check_nvidia_driver()
            if not driver_status['installed']:
                print("重啟後仍未偵測到驅動,安裝可能失敗")
                return
            
            # 驗證 CUDA
            success, output = run_cmd(['nvcc', '--version'], use_sudo=False, check=False)
            if success:
                print("\nCUDA Toolkit 驗證成功:")
                for line in output.split('\n'):
                    if line.strip():
                        print(f"  {line}")
            else:
                print("⚠ CUDA 命令不可用")
            
            # 安裝 Python 套件
            py_mgr = PythonPackageManager()
            py_mgr.install_packages(PYTHON_PACKAGES)
            
            # 安裝 GPU Burn
            print("\n" + "█" * 70)
            print("安裝 GPU Burn")
            print("█" * 70)
            
            if gpu_info['has_gpu'] and gpu_info['compute_capabilities']:
                cc = gpu_info['compute_capabilities'][0]
                sys_mgr.install_gpu_burn(compute_capability=cc)
            elif gpu_info['has_gpu']:
                sys_mgr.install_gpu_burn()
        
        elif sys_mgr.os_type == 'windows':
            # Windows 重啟後流程
            print("\n" + "█" * 70)
            print("Windows 重啟後繼續")
            print("█" * 70)
            
            sys_mgr.remove_auto_start_windows()
            
            # 重新偵測套件管理器
            sys_mgr.package_manager = sys_mgr._detect_package_manager()
            
            if sys_mgr.package_manager:
                print(f"✓ Chocolatey 已就緒: {sys_mgr.package_manager}")
                
                # 繼續安裝系統工具和套件
                print("\n安裝系統工具")
                sys_mgr.install_system_tools(WINDOWS_TOOLS)
                
                print("\n安裝 Python 套件")
                py_mgr = PythonPackageManager()
                py_mgr.install_packages(PYTHON_PACKAGES)

                gpu_info = sys_mgr.check_gpu()
                if gpu_info['has_gpu']:

                    # Step A：先安裝 Driver（如果沒有）
                    success, _ = run_cmd(['nvidia-smi'], check=False)
                    if not success:
                        print("\n安裝 NVIDIA 顯示卡驅動 (Driver)")
                        sys_mgr.install_nvidia_driver_windows()

                    # Step B：再檢查 CUDA
                    success, _ = run_cmd(['nvcc', '--version'], check=False)
                    if not success:
                        print("\n安裝 CUDA Toolkit")
                        sys_mgr.install_nvidia_cuda_windows()
        
                print("\n✓ Windows 配置完成!")
            else:
                print("✗ Chocolatey 仍未就緒")
                return
    
    # ==========================================
    # 完成報告
    # ==========================================
    print("\n" + "=" * 70)
    print("配置完成!")
    print("=" * 70)
    
    print("\n已安裝:")
    if sys_mgr.os_type == 'linux':
        print(f"  ✓ {len(SYSTEM_TOOLS)} 個系統工具")
    elif sys_mgr.os_type == 'windows':
        is_server = 'server' in platform.platform().lower()
        tool_count = len(WINDOWS_TOOLS['common']) + len(WINDOWS_TOOLS['server' if is_server else 'windows11'])
        print(f"  ✓ {tool_count} 個系統工具")
    
    print(f"  ✓ {len(PYTHON_PACKAGES)} 個 Python 套件")
    
    gpu_info = sys_mgr.check_gpu()
    if gpu_info['has_gpu']:
        print(f"  ✓ NVIDIA 驅動和 CUDA")
        print(f"  ✓ GPU Burn 壓力測試工具")
        print(f"\n檢測到的 GPU:")
        for i, (gpu_name, cc) in enumerate(zip(gpu_info['gpu_names'], gpu_info['compute_capabilities']), 1):
            print(f"    GPU {i}: {gpu_name} (CC: {cc})")
    
    print("\n驗證命令:")
    print("  python3 --version")
    print("  pip list")
    
    if sys_mgr.os_type == 'linux':
        print("  git --version")
        print("  gcc --version")
        print("\nGPU 相關:")
        print("  nvidia-smi              # 查看 GPU 和驅動狀態")
        print("  nvcc --version          # 查看 CUDA 版本")
        if os.path.exists(GPU_BURN_PATH):
            print(f"\nGPU 壓力測試:")
            print(f"  cd {GPU_BURN_PATH}")
            print("  ./gpu_burn 60           # 測試 60 秒")
    elif sys_mgr.os_type == 'windows':
        print("  git --version")
        print("\nGPU 相關:")
        print("  nvidia-smi              # 查看 GPU 和驅動狀態")
        print("  nvcc --version          # 查看 CUDA 版本")
    
    print("=" * 70)


if __name__ == "__main__":
    main()