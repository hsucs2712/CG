#!/usr/bin/env python3
"""
自動化環境構成ツール
サポート: Windows, Linux (Ubuntu, RHEL)
機能: 自動インストール Python パッケージ、システムツール、NVIDIAドライバとCUDA Toolkit
特性: ドライバインストール後自動再起動して継続実行
"""

import subprocess
import sys
import os
import platform
import time
import json
from typing import Dict

# モジュールインポート
from run_cmd import run_cmd
from gpu_detect import check_gpu, check_nvidia_driver
from list import (
    PYTHON_PACKAGES, SYSTEM_TOOLS, WINDOWS_TOOLS,
    AUTO_START_SERVICE, WINDOWS_FLAG_FILE, GPU_BURN_PATH
)


class PythonPackageManager:
    """Python パッケージマネージャー"""
    
    def __init__(self):
        if platform.system().lower() == 'linux':
            self.python_exec = 'python3'
        else:
            self.python_exec = sys.executable
        
        self.installed = self._get_installed()
    
    def _get_installed(self) -> Dict[str, str]:
        """インストール済みパッケージを取得"""
        packages = {}
        try:
            cmd = [self.python_exec, '-m', 'pip', 'list', '--format=json']
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            pkg_list = json.loads(result.stdout)
            for pkg in pkg_list:
                packages[pkg['name'].lower()] = pkg['version']
        except:
            pass
        return packages
    
    def install_packages(self, requirements: Dict[str, str]) -> bool:
        """Pythonパッケージをインストール(既存のものは更新)"""
        print("\n" + "=" * 70)
        print("Python パッケージをチェック・インストール")
        print("=" * 70)
        print(f"Python を使用: {self.python_exec}")
        
        to_install = []
        to_upgrade = []
        
        for pkg, ver in requirements.items():
            installed_ver = self.installed.get(pkg.lower())
            if not installed_ver:
                to_install.append((pkg, ver))
            else:
                to_upgrade.append((pkg, installed_ver))
        
        # 既存パッケージを表示
        if to_upgrade:
            print(f"\n✓ 既にインストール済み ({len(to_upgrade)} 個):")
            for pkg, ver in to_upgrade[:5]:  # 最初の5個だけ表示
                print(f"  • {pkg}: {ver}")
            if len(to_upgrade) > 5:
                print(f"  ... 他 {len(to_upgrade) - 5} 個")
        
        # 新規インストールが必要なパッケージ
        if to_install:
            print(f"\n📥 新規インストールが必要 ({len(to_install)} 個):")
            for pkg, ver in to_install:
                ver_str = f'>={ver}' if ver else ''
                print(f"  • {pkg} {ver_str}")
            
            print("\n新規パッケージをインストール中...")
            for pkg, ver in to_install:
                ver_str = f'>={ver}' if ver else ''
                pkg_str = f"{pkg}{ver_str}" if ver else pkg
                
                try:
                    if platform.system().lower() == 'linux':
                        subprocess.check_call([
                            self.python_exec, '-m', 'pip', 'install', 
                            '--break-system-packages', pkg_str
                        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        subprocess.check_call([
                            self.python_exec, '-m', 'pip', 'install', pkg_str
                        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    print(f"  ✓ {pkg} インストール成功")
                except Exception as e:
                    print(f"  ✗ {pkg} インストール失敗: {e}")
        else:
            print("\n✓ すべてのPythonパッケージがインストール済み")
        
        print("\n✓ Pythonパッケージのセットアップ完了")
        return True


def run_linux_setup():
    """Linux完全セットアップフロー"""
    from linux_install import LinuxInstaller
    
    print("\n" + "=" * 70)
    print(" " * 20 + "Linux セットアップ")
    print("=" * 70)
    
    # パッケージマネージャーを検出
    managers = ['apt-get', 'dnf']
    package_manager = None
    for manager in managers:
        try:
            subprocess.run([manager, '--version'], capture_output=True, check=True)
            package_manager = manager
            break
        except:
            continue
    
    if not package_manager:
        print("✗ サポートされているパッケージマネージャーが見つかりません (apt-get/dnf)")
        return
    
    print(f"✓ パッケージマネージャー: {package_manager}")
    
    # 再起動後の継続実行かチェック
    is_auto_continue = os.path.exists(AUTO_START_SERVICE)
    
    if is_auto_continue:
        print("\n🔄 再起動後の自動継続を検出\n")
    
    linux_installer = LinuxInstaller(package_manager)
    
    # ==========================================
    # 初回実行: GPUチェックとドライバインストール
    # ==========================================
    if not is_auto_continue:
        print("\n" + "█" * 70)
        print("ステップ 1: GPU環境をチェック")
        print("█" * 70)
        
        gpu_info = check_gpu()
        
        if not gpu_info['has_gpu']:
            print("\n✗ NVIDIA GPUが検出されませんでした")
            print("   GPUなしでシステムツールとPythonパッケージのみインストールします")
            
            # GPUなしでもツールをインストール
            linux_installer.install_system_tools(SYSTEM_TOOLS)
            
            py_mgr = PythonPackageManager()
            py_mgr.install_packages(PYTHON_PACKAGES)
            
            print("\n✓ セットアップ完了 (GPUなし)")
            return
        
        driver_status = check_nvidia_driver()
        has_driver = driver_status['installed']
        
        success, _ = run_cmd(['nvcc', '--version'], use_sudo=False, check=False)
        has_cuda = success
        
        print(f"\n現状:")
        print(f"  GPU: ✓ 検出済み")
        print(f"  ドライバ: {'✓ インストール済み' if has_driver else '✗ 未インストール'}")
        print(f"  CUDA: {'✓ インストール済み' if has_cuda else '✗ 未インストール'}")
        
        # すでに完全インストール済み
        if has_driver and has_cuda:
            print("\n✓ ドライバとCUDAがインストール済み")
            
            print("\n" + "█" * 70)
            print("ステップ 2: システムツールをインストール")
            print("█" * 70)
            linux_installer.install_system_tools(SYSTEM_TOOLS)
            
            print("\n" + "█" * 70)
            print("ステップ 3: Pythonパッケージをインストール")
            print("█" * 70)
            py_mgr = PythonPackageManager()
            py_mgr.install_packages(PYTHON_PACKAGES)
            
            print("\n" + "█" * 70)
            print("ステップ 4: GPU Burnをインストール")
            print("█" * 70)
            if gpu_info['compute_capabilities']:
                cc = gpu_info['compute_capabilities'][0]
                linux_installer.install_gpu_burn(compute_capability=cc)
            else:
                linux_installer.install_gpu_burn()
            
            print("\n✓ Linux セットアップ完了!")
            print_linux_summary(gpu_info)
            return
        
        # ドライバインストールが必要
        print("\n" + "█" * 70)
        print("ステップ 2: システムツールをインストール")
        print("█" * 70)
        linux_installer.install_system_tools(SYSTEM_TOOLS)
        
        print("\n" + "█" * 70)
        print("ステップ 3: NVIDIAドライバとCUDAをインストール")
        print("█" * 70)
        
        linux_installer.disable_nouveau()
        
        if package_manager == 'apt-get':
            success = linux_installer.install_nvidia_driver_apt(gpu_info)
        else:  # dnf
            success = linux_installer.install_nvidia_driver_dnf(gpu_info)
        
        if not success:
            print("✗ ドライバインストール失敗")
            return
        
        linux_installer.create_auto_start()
        
        print("\n" + "!" * 70)
        print("ドライバインストール完了!")
        print("システムは15秒後に自動再起動します...")
        print("再起動後、プログラムは自動継続してGPU Burnをインストールします")
        print("!" * 70)
        
        for i in range(15, 0, -1):
            print(f"\r再起動カウントダウン: {i} 秒...", end='', flush=True)
            time.sleep(1)
        print("\n")
        
        run_cmd(['reboot'], use_sudo=True)
        return
    
    # ==========================================
    # 再起動後: Pythonパッケージとツール
    # ==========================================
    else:
        print("\n" + "█" * 70)
        print("ステップ 4: 再起動後の継続セットアップ")
        print("█" * 70)
        
        linux_installer.remove_auto_start()
        
        gpu_info = check_gpu()
        driver_status = check_nvidia_driver()
        
        if not driver_status['installed']:
            print("✗ 再起動後もドライバが検出されません")
            return
        
        success, output = run_cmd(['nvcc', '--version'], use_sudo=False, check=False)
        if success:
            print("\n✓ CUDA Toolkit検証成功:")
            for line in output.split('\n'):
                if line.strip():
                    print(f"  {line}")
        
        print("\n" + "█" * 70)
        print("ステップ 5: Pythonパッケージをインストール")
        print("█" * 70)
        py_mgr = PythonPackageManager()
        py_mgr.install_packages(PYTHON_PACKAGES)
        
        print("\n" + "█" * 70)
        print("ステップ 6: GPU Burnをインストール")
        print("█" * 70)
        
        if gpu_info['has_gpu'] and gpu_info['compute_capabilities']:
            cc = gpu_info['compute_capabilities'][0]
            linux_installer.install_gpu_burn(compute_capability=cc)
        elif gpu_info['has_gpu']:
            linux_installer.install_gpu_burn()
        
        print("\n✓ Linux セットアップ完全完了!")
        print_linux_summary(gpu_info)


def run_windows_setup():
    """Windows完全セットアップフロー"""
    from win_install import WindowsInstaller
    
    print("\n" + "=" * 70)
    print(" " * 20 + "Windows セットアップ")
    print("=" * 70)
    
    is_server = 'server' in platform.platform().lower()
    print(f"Windows タイプ: {'Server' if is_server else 'Client (Windows 11/10)'}")
    
    # 再起動後の継続実行かチェック
    is_auto_continue = os.path.exists(WINDOWS_FLAG_FILE)
    
    if is_auto_continue:
        print("\n🔄 再起動後の自動継続を検出\n")
    
    win_installer = WindowsInstaller()
    
    # ==========================================
    # 初回実行: Chocolateyインストール
    # ==========================================
    if not is_auto_continue:
        print("\n" + "█" * 70)
        print("ステップ 1: GPU環境をチェック")
        print("█" * 70)
        
        gpu_info = check_gpu()
        
        if not gpu_info['has_gpu']:
            print("\n✗ NVIDIA GPUが検出されませんでした")
            print("   GPUなしでシステムツールとPythonパッケージのみインストールします")
        else:
            print(f"\n✓ {len(gpu_info['gpu_names'])} 個のGPUを検出")
        
        # Chocolateyチェック
        if not win_installer.has_choco:
            print("\n" + "█" * 70)
            print("ステップ 2: Chocolateyパッケージマネージャーをインストール")
            print("█" * 70)
            
            if win_installer.install_chocolatey():
                # 再起動して継続
                return
            else:
                print("✗ Chocolateyインストール失敗")
                return
        
        # Chocolateyが既にある場合
        print("\n✓ Chocolateyインストール済み")
        
        print("\n" + "█" * 70)
        print("ステップ 2: システムツールをインストール")
        print("█" * 70)
        win_installer.install_system_tools(WINDOWS_TOOLS)
        
        print("\n" + "█" * 70)
        print("ステップ 3: Pythonパッケージをインストール")
        print("█" * 70)
        py_mgr = PythonPackageManager()
        py_mgr.install_packages(PYTHON_PACKAGES)
        
        # GPUがある場合のみドライバとCUDAをインストール
        if gpu_info['has_gpu']:
            print("\n" + "█" * 70)
            print("ステップ 4: NVIDIAドライバをチェック")
            print("█" * 70)
            
            success, _ = run_cmd(['nvidia-smi'], check=False)
            if not success:
                print("\nNVIDIAドライバをインストール...")
                win_installer.install_nvidia_driver()
            else:
                print("✓ NVIDIAドライバインストール済み")
            
            print("\n" + "█" * 70)
            print("ステップ 5: CUDA Toolkitをチェック")
            print("█" * 70)
            
            success, _ = run_cmd(['nvcc', '--version'], check=False)
            if not success:
                print("\nCUDA Toolkitをインストール...")
                win_installer.install_cuda()
            else:
                print("✓ CUDA Toolkitインストール済み")
        
        print("\n✓ Windows セットアップ完了!")
        print_windows_summary(gpu_info)
        return
    
    # ==========================================
    # 再起動後: 全セットアップ
    # ==========================================
    else:
        print("\n" + "█" * 70)
        print("ステップ 2: 再起動後の継続セットアップ")
        print("█" * 70)
        
        win_installer.remove_auto_start()
        
        # Chocolateyを再確認
        win_installer.has_choco = win_installer._check_chocolatey()
        
        if not win_installer.has_choco:
            print("✗ Chocolateyがまだ使用できません")
            print("   PowerShellを再起動してから再度実行してください")
            return
        
        print("✓ Chocolatey準備完了")
        
        print("\n" + "█" * 70)
        print("ステップ 3: システムツールをインストール")
        print("█" * 70)
        win_installer.install_system_tools(WINDOWS_TOOLS)
        
        print("\n" + "█" * 70)
        print("ステップ 4: Pythonパッケージをインストール")
        print("█" * 70)
        py_mgr = PythonPackageManager()
        py_mgr.install_packages(PYTHON_PACKAGES)
        
        gpu_info = check_gpu()
        
        if gpu_info['has_gpu']:
            print("\n" + "█" * 70)
            print("ステップ 5: NVIDIAドライバをインストール")
            print("█" * 70)
            
            success, _ = run_cmd(['nvidia-smi'], check=False)
            if not success:
                win_installer.install_nvidia_driver()
            else:
                print("✓ NVIDIAドライバインストール済み")
            
            print("\n" + "█" * 70)
            print("ステップ 6: CUDA Toolkitをインストール")
            print("█" * 70)
            
            success, _ = run_cmd(['nvcc', '--version'], check=False)
            if not success:
                win_installer.install_cuda()
            else:
                print("✓ CUDA Toolkitインストール済み")
        
        print("\n✓ Windows セットアップ完全完了!")
        print_windows_summary(gpu_info)


def print_linux_summary(gpu_info):
    """Linuxセットアップサマリーを表示"""
    print("\n" + "=" * 70)
    print("セットアップサマリー")
    print("=" * 70)
    
    print("\n✓ インストール済み:")
    print(f"  • {len(SYSTEM_TOOLS)} 個のシステムツール")
    print(f"  • {len(PYTHON_PACKAGES)} 個のPythonパッケージ")
    
    if gpu_info['has_gpu']:
        print(f"  • NVIDIAドライバとCUDA Toolkit")
        print(f"  • GPU Burnストレステストツール")
        print(f"\n✓ 検出されたGPU:")
        for i, (gpu_name, cc) in enumerate(zip(gpu_info['gpu_names'], gpu_info['compute_capabilities']), 1):
            print(f"    GPU {i}: {gpu_name} (CC: {cc})")
    
    print("\n" + "=" * 70)
    print("📋 インストール検証")
    print("=" * 70)
    
    # Python バージョンを表示
    success, output = run_cmd(['python3', '--version'], check=False, silent=True)
    if success:
        print(f"✓ Python: {output.strip()}")
    
    # Git バージョンを表示
    success, output = run_cmd(['git', '--version'], check=False, silent=True)
    if success:
        print(f"✓ Git: {output.strip()}")
    
    # GCC バージョンを表示
    success, output = run_cmd(['gcc', '--version'], check=False, silent=True)
    if success:
        # 最初の行だけ取得
        first_line = output.strip().split('\n')[0]
        print(f"✓ GCC: {first_line}")
    
    # Pip バージョンを表示
    success, output = run_cmd(['pip3', '--version'], check=False, silent=True)
    if success:
        print(f"✓ Pip: {output.strip()}")
    
    if gpu_info['has_gpu']:
        print("\n" + "=" * 70)
        print("🎮 GPU環境検証")
        print("=" * 70)
        
        # nvidia-smi
        success, output = run_cmd(['nvidia-smi', '--version'], check=False, silent=True)
        if success:
            version_line = output.strip().split('\n')[0] if output else "インストール済み"
            print(f"✓ NVIDIA Driver: {version_line}")
        else:
            print("✗ NVIDIA Driver: 未インストール")
        
        # nvcc
        success, output = run_cmd(['nvcc', '--version'], check=False, silent=True)
        if success:
            # "Cuda compilation tools, release 12.x" の行を抽出
            for line in output.split('\n'):
                if 'release' in line.lower():
                    print(f"✓ CUDA: {line.strip()}")
                    break
        else:
            print("✗ CUDA: 未インストール")
        
        # GPU Burn の存在確認
        if os.path.exists(os.path.join(GPU_BURN_PATH, 'gpu_burn')):
            print(f"✓ GPU Burn: {GPU_BURN_PATH}/gpu_burn")
            print("\n  使用例:")
            print(f"    cd {GPU_BURN_PATH}")
            print("    ./gpu_burn 60    # 60秒ストレステスト")
    
    print("=" * 70)


def print_windows_summary(gpu_info):
    """Windowsセットアップサマリーを表示"""
    print("\n" + "=" * 70)
    print("セットアップサマリー")
    print("=" * 70)
    
    is_server = 'server' in platform.platform().lower()
    tool_count = len(WINDOWS_TOOLS['common']) + len(WINDOWS_TOOLS['server' if is_server else 'windows11'])
    
    print("\n✓ インストール済み:")
    print(f"  • {tool_count} 個のシステムツール")
    print(f"  • {len(PYTHON_PACKAGES)} 個のPythonパッケージ")
    
    if gpu_info['has_gpu']:
        print(f"  • NVIDIAドライバとCUDA Toolkit")
        print(f"\n✓ 検出されたGPU:")
        for i, (gpu_name, cc) in enumerate(zip(gpu_info['gpu_names'], gpu_info['compute_capabilities']), 1):
            print(f"    GPU {i}: {gpu_name} (CC: {cc})")
    
    print("\n" + "=" * 70)
    print("📋 インストール検証")
    print("=" * 70)
    
    # Python バージョンを表示
    success, output = run_cmd(['python', '--version'], check=False, silent=True)
    if success:
        print(f"✓ Python: {output.strip()}")
    
    # Git バージョンを表示
    success, output = run_cmd(['git', '--version'], check=False, silent=True)
    if success:
        print(f"✓ Git: {output.strip()}")
    
    # Pip バージョンを表示
    success, output = run_cmd(['pip', '--version'], check=False, silent=True)
    if success:
        print(f"✓ Pip: {output.strip()}")
    
    if gpu_info['has_gpu']:
        print("\n" + "=" * 70)
        print("🎮 GPU環境検証")
        print("=" * 70)
        
        # nvidia-smi
        success, output = run_cmd(['nvidia-smi', '--version'], check=False, silent=True)
        if success:
            version_line = output.strip().split('\n')[0] if output else "インストール済み"
            print(f"✓ NVIDIA Driver: {version_line}")
        else:
            print("✗ NVIDIA Driver: 未インストール")
        
        # nvcc
        success, output = run_cmd(['nvcc', '--version'], check=False, silent=True)
        if success:
            # "Cuda compilation tools, release 12.x" の行を抽出
            for line in output.split('\n'):
                if 'release' in line.lower():
                    print(f"✓ CUDA: {line.strip()}")
                    break
        else:
            print("✗ CUDA: 未インストール")
    
    print("=" * 70)


def main():
    """メインプログラム - OSを検出して適切なセットアップを実行"""
    
    print("\n" + "=" * 70)
    print(" " * 15 + "自動化環境構成ツール")
    print("=" * 70)
    
    os_type = platform.system().lower()
    
    print(f"\n検出されたOS: {platform.system()} {platform.release()}")
    print(f"Python バージョン: {sys.version.split()[0]}")
    
    if os_type == 'linux':
        run_linux_setup()
    elif os_type == 'windows':
        run_windows_setup()
    else:
        print(f"\n✗ サポートされていないOS: {platform.system()}")
        print("   このツールはLinuxとWindowsのみサポートしています")


if __name__ == "__main__":
    main()