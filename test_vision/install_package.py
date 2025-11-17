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
    'python3-tkinter'
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
        print(f"Python 路徑: {sys.executable}")
        print(f"套件管理器: {self.package_manager or '未偵測到'}")
        print("=" * 70)
    
    def _detect_package_manager(self):
        """偵測系統套件管理器"""
        if self.os_type == 'linux':
            # APT: Ubuntu, Debian, Linux Mint
            # DNF: Fedora, RHEL 8+, Rocky Linux, AlmaLinux
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
        print("【GPU 步驟 0】檢查 NVIDIA GPU 硬體")
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
        
        script_content = f"""#!/bin/bash
# CUDA 安裝自動繼續腳本
sleep 10
cd {work_dir}
{sys.executable} {SCRIPT_PATH}
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
    
    def install_nvidia_driver(self) -> Dict:
        """安裝 NVIDIA 驅動 (伺服器用最新版本)"""
        print("\n開始安裝 NVIDIA 驅動...")
        print("伺服器環境: 自動選擇最新穩定版驅動")
        print("-" * 70)
        
        if self.package_manager == 'apt-get':
            run_cmd(['apt-get', 'update'], use_sudo=True)
            
            print("\n添加 NVIDIA 官方驅動源...")
            run_cmd(['apt-get', 'install', '-y', 'software-properties-common'], use_sudo=True)
            run_cmd(['add-apt-repository', '-y', 'ppa:graphics-drivers/ppa'], use_sudo=True)
            run_cmd(['apt-get', 'update'], use_sudo=True)
            
            print("\n安裝最新推薦驅動...")
            success, _ = run_cmd(['ubuntu-drivers', 'autoinstall'], use_sudo=True, check=False)
            
            if not success:
                print("⚠ 自動安裝失敗,嘗試手動指定版本...")
                drivers = ['nvidia-driver-550', 'nvidia-driver-545', 'nvidia-driver-535']
                for driver in drivers:
                    print(f"\n嘗試安裝 {driver}...")
                    success, _ = run_cmd(['apt-get', 'install', '-y', driver], use_sudo=True, check=False)
                    if success:
                        break
            
            if success:
                print("✓ NVIDIA 驅動安裝成功")
                run_cmd(['apt-get', 'update'], use_sudo=True)
                
                if self.create_auto_start_linux():
                    print("\n" + "!" * 70)
                    print("系統將在 10 秒後自動重啟...")
                    print("重啟後程式會自動繼續執行")
                    print("!" * 70)
                    
                    import time
                    for i in range(10, 0, -1):
                        print(f"\r重啟倒數: {i} 秒...", end='', flush=True)
                        time.sleep(1)
                    print("\n")
                    
                    run_cmd(['reboot'], use_sudo=True)
                
                return {'success': True, 'needs_reboot': True}
            
            return {'success': False, 'needs_reboot': False}
        
        elif self.package_manager == 'dnf':
            print("為 RHEL/AlmaLinux 安裝最新驅動...")
            run_cmd(['dnf', 'install', '-y', 'epel-release'], use_sudo=True)
            success, _ = run_cmd(['dnf', 'install', '-y', 'nvidia-driver', 'nvidia-driver-cuda'], 
                                use_sudo=True, check=False)
            if success:
                if self.create_auto_start_linux():
                    import time
                    for i in range(10, 0, -1):
                        print(f"\r重啟倒數: {i} 秒...", end='', flush=True)
                        time.sleep(1)
                    print("\n")
                    run_cmd(['reboot'], use_sudo=True)
                return {'success': True, 'needs_reboot': True}
            return {'success': False, 'needs_reboot': False}
        
        return {'success': False, 'needs_reboot': False}
    
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
            
            # 使用 --break-system-packages 繞過 externally-managed 限制
            try:
                subprocess.check_call([
                    self.python_exec, '-m', 'pip', 'install', 
                    '--break-system-packages', pkg_str
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
    # 階段 1: 系統基礎工具
    # ==========================================
    if not is_auto_continue:
        print("\n" + "█" * 70)
        print("階段 1: 安裝系統基礎工具")
        print("█" * 70)
        
        sys_mgr.update_system()
        
        if sys_mgr.os_type == 'linux':
            sys_mgr.install_system_tools(SYSTEM_TOOLS)
        elif sys_mgr.os_type == 'windows':
            sys_mgr.install_system_tools(WINDOWS_TOOLS)
        
        # ==========================================
        # 階段 2: Python 套件
        # ==========================================
        print("\n" + "█" * 70)
        print("階段 2: 安裝 Python 套件")
        print("█" * 70)
        
        py_mgr = PythonPackageManager()
        py_mgr.install_packages(PYTHON_PACKAGES)
        
        # ==========================================
        # 階段 3: GPU 驅動
        # ==========================================
        print("\n" + "█" * 70)
        print("階段 3: 配置 GPU 環境")
        print("█" * 70)
        
        gpu_info = sys_mgr.check_gpu()
        
        if gpu_info['has_gpu']:
            driver_status = sys_mgr.check_nvidia_driver()
            
            if not driver_status['installed']:
                print("\n需要安裝 NVIDIA 驅動...")
                install_result = sys_mgr.install_nvidia_driver()
                if install_result['needs_reboot']:
                    return  # 自動重啟
    
    # ==========================================
    # 階段 4: CUDA Toolkit (重啟後執行)
    # ==========================================
    if is_auto_continue:
        print("\n" + "█" * 70)
        print("階段 4: 安裝 CUDA Toolkit")
        print("█" * 70)
        
        gpu_info = sys_mgr.check_gpu()
        
        success, _ = run_cmd(['nvcc', '--version'], use_sudo=False, check=False)
        if not success:
            sys_mgr.install_cuda()
        else:
            print("✓ CUDA Toolkit 已安裝")
            sys_mgr.remove_auto_start_linux()
    
    # ==========================================
    # 階段 5: GPU Burn (最後安裝)
    # ==========================================
    if is_auto_continue or (not is_auto_continue and sys_mgr.check_nvidia_driver()['installed']):
        print("\n" + "█" * 70)
        print("階段 5: 安裝 GPU Burn 壓力測試工具 (最後)")
        print("█" * 70)
        
        # 重新獲取 GPU 資訊
        gpu_info = sys_mgr.check_gpu()
        
        if gpu_info['has_gpu'] and gpu_info['compute_capabilities']:
            # 使用第一個 GPU 的 compute capability
            cc = gpu_info['compute_capabilities'][0]
            sys_mgr.install_gpu_burn(compute_capability=cc)
        elif gpu_info['has_gpu']:
            # 沒有 compute capability 就用預設值
            sys_mgr.install_gpu_burn()
        else:
            print("✗ 沒有 GPU,跳過 GPU Burn 安裝")
    
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