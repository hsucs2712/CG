#!/usr/bin/env python3
"""
Linux システムインストーラー
"""

import os
import sys
import subprocess
from typing import Dict
from run_cmd import run_cmd
from list import (
    AUTO_START_SERVICE, AUTO_START_SCRIPT, SCRIPT_PATH,
    GPU_BURN_REPO, GPU_BURN_PATH
)


class LinuxInstaller:
    """Linux システムインストーラークラス"""
    
    def __init__(self, package_manager: str):
        self.package_manager = package_manager
    
    def update_system(self) -> bool:
        """システムパッケージリストを更新"""
        print("\n" + "=" * 70)
        print("システムパッケージリストを更新")
        print("=" * 70)
        
        if self.package_manager == 'apt-get':
            success, _ = run_cmd(['apt-get', 'update'], use_sudo=True)
            if success:
                print("✓ システム更新完了 (APT)")
                return True
        elif self.package_manager == 'dnf':
            run_cmd(['dnf', 'check-update'], use_sudo=True, check=False)
            print("✓ システム更新完了 (DNF)")
            return True
        
        print("⚠ システムを更新できません")
        return False
    
    def install_system_tools(self, tools) -> bool:
        """システムツールをインストール(既存のものは更新のみ)"""
        print("\n" + "=" * 70)
        print("システムツールをチェック・インストール")
        print("=" * 70)
        
        self.update_system()
        
        # 既にインストールされているツールをチェック
        installed_tools = []
        missing_tools = []
        
        for tool in tools:
            # which コマンドでツールの存在をチェック
            success, _ = run_cmd(['which', tool], use_sudo=False, check=False, silent=True)
            if success:
                installed_tools.append(tool)
            else:
                missing_tools.append(tool)
        
        if installed_tools:
            print(f"\n✓ 既にインストール済み ({len(installed_tools)} 個):")
            for tool in installed_tools[:5]:  # 最初の5個だけ表示
                print(f"  • {tool}")
            if len(installed_tools) > 5:
                print(f"  ... 他 {len(installed_tools) - 5} 個")
        
        if missing_tools:
            print(f"\n📥 新規インストールが必要 ({len(missing_tools)} 個):")
            for tool in missing_tools:
                print(f"  • {tool}")
            
            if self.package_manager == 'apt-get':
                print(f"\nAPTで {len(missing_tools)} 個のツールをインストール...")
                success, _ = run_cmd(['apt-get', 'install', '-y'] + missing_tools, use_sudo=True)
                if success:
                    print("✓ 新規ツールのインストール完了")
                    run_cmd(['apt-get', 'update'], use_sudo=True)
                    return True
            
            elif self.package_manager == 'dnf':
                print(f"\nDNFで {len(missing_tools)} 個のツールをインストール...")
                success, _ = run_cmd(['dnf', 'install', '-y'] + missing_tools, use_sudo=True)
                if success:
                    print("✓ 新規ツールのインストール完了")
                    return True
        else:
            print("\n✓ すべてのシステムツールがインストール済み")
            return True
        
        print("✗ システムツールのインストール失敗")
        return False
    
    def disable_nouveau(self) -> bool:
        """nouveauドライバを無効化してinitramfsを更新"""
        print("\n" + "=" * 70)
        print("Nouveauオープンソースドライバを無効化")
        print("=" * 70)
        
        blacklist_file = "/etc/modprobe.d/blacklist-nouveau.conf"
        blacklist_content = """# Blacklist nouveau driver
blacklist nouveau
options nouveau modeset=0
"""
        
        try:
            if os.path.exists(blacklist_file):
                print(f"✓ {blacklist_file} が存在します")
            else:
                print(f"{blacklist_file}を作成...")
                with open(blacklist_file, 'w') as f:
                    f.write(blacklist_content)
                print(f"✓ blacklist設定を作成しました")
            
            print("\ninitramfsを更新...")
            
            if self.package_manager == 'apt-get':
                success, _ = run_cmd(['update-initramfs', '-u'], use_sudo=True)
                if success:
                    print("✓ initramfs更新完了 (update-initramfs)")
                else:
                    print("⚠ initramfs更新失敗")
                    
            elif self.package_manager == 'dnf':
                success, _ = run_cmd(['dracut', '--force'], use_sudo=True)
                if success:
                    print("✓ initramfs更新完了 (dracut)")
                else:
                    print("⚠ initramfs更新失敗")
            
            print("\n⚠ 重要: 再起動後にnouveauが無効化されます")
            return True
            
        except Exception as e:
            print(f"✗ nouveauの無効化失敗: {e}")
            return False
    
    def remove_existing_nvidia_driver(self) -> bool:
        """既存のNVIDIAドライバを削除"""
        print("\n既存のNVIDIAドライバをチェックして削除...")
        
        if self.package_manager == 'apt-get':
            success, output = run_cmd(['dpkg', '-l'], use_sudo=False, check=False)
            if success and 'nvidia' in output.lower():
                print("既存のNVIDIAパッケージを検出、削除準備...")
                run_cmd(['apt-get', 'remove', '--purge', '-y', 'nvidia-*'], use_sudo=True, check=False)
                run_cmd(['apt-get', 'autoremove', '-y'], use_sudo=True, check=False)
                print("✓ 旧ドライバを削除しました")
            else:
                print("✓ 既存のNVIDIAドライバはありません")
                
        elif self.package_manager == 'dnf':
            success, output = run_cmd(['dnf', 'list', 'installed'], use_sudo=False, check=False)
            if success and 'nvidia' in output.lower():
                print("既存のNVIDIAパッケージを検出、削除準備...")
                run_cmd(['dnf', 'remove', '-y', 'nvidia-*'], use_sudo=True, check=False)
                print("✓ 旧ドライバを削除しました")
            else:
                print("✓ 既存のNVIDIAドライバはありません")
        
        return True
    
    def install_nvidia_driver_apt(self, gpu_info: Dict) -> bool:
        """APT: network repoを使用してNVIDIAドライバとCUDAをインストール"""
        print("\n" + "=" * 70)
        print("APT: NVIDIAドライバとCUDA Toolkitをインストール")
        print("=" * 70)
        
        # 1. NVIDIA公式repositoryを追加
        print("\n【ステップ 1】NVIDIA Network Repositoryを追加...")
        
        run_cmd(['apt-get', 'install', '-y', 'software-properties-common', 'wget'], use_sudo=True)
        
        cuda_keyring = "cuda-keyring_1.1-1_all.deb"
        
        print("CUDA Repository設定をダウンロード...")
        run_cmd(['wget', 'https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb'], 
               check=False)
        
        if os.path.exists(cuda_keyring):
            run_cmd(['dpkg', '-i', cuda_keyring], use_sudo=True)
            print("✓ CUDA Repositoryを追加しました")
        else:
            print("⚠ Repository keyringのダウンロード失敗、代替案を試します...")
            run_cmd(['add-apt-repository', '-y', 'ppa:graphics-drivers/ppa'], use_sudo=True)
        
        # 2. パッケージデータベースを更新
        print("\n【ステップ 2】パッケージデータベースを更新...")
        run_cmd(['apt-get', 'update'], use_sudo=True)
        
        # 3. 旧ドライバを削除
        print("\n【ステップ 3】既存のNVIDIAドライバを削除...")
        self.remove_existing_nvidia_driver()
        
        # 4. ドライバをインストール
        print("\n【ステップ 4】NVIDIAドライバをインストール...")
        
        success, output = run_cmd(['ubuntu-drivers', 'devices'], use_sudo=True, check=False)
        
        if success and 'recommended' in output:
            print("ubuntu-driversで推奨ドライバを自動インストール...")
            success, _ = run_cmd(['ubuntu-drivers', 'autoinstall'], use_sudo=True, check=False)
        else:
            print("最新ドライババージョンを手動インストール...")
            drivers = ['nvidia-driver-550', 'nvidia-driver-545', 'nvidia-driver-535']
            for driver in drivers:
                print(f"{driver}のインストールを試行...")
                success, _ = run_cmd(['apt-get', 'install', '-y', driver], use_sudo=True, check=False)
                if success:
                    break
        
        if success:
            print("✓ NVIDIAドライバのインストール成功")
        else:
            print("✗ NVIDIAドライバのインストール失敗")
            return False
        
        # 5. CUDA Toolkitをインストール
        print("\n【ステップ 5】CUDA Toolkitをインストール...")
        
        cuda_packages = ['cuda-toolkit-12-6', 'cuda-toolkit-12-5', 'cuda-toolkit']
        
        for pkg in cuda_packages:
            print(f"{pkg}のインストールを試行...")
            success, _ = run_cmd(['apt-get', 'install', '-y', pkg], use_sudo=True, check=False)
            if success:
                print(f"✓ {pkg} インストール成功")
                break
        
        if not success:
            print("✗ CUDA Toolkitのインストール失敗")
            return False
        
        # 6. 完全なシステム更新
        print("\n【ステップ 6】完全なシステム更新を実行...")
        run_cmd(['apt-get', 'update'], use_sudo=True)
        run_cmd(['apt-get', 'upgrade', '-y'], use_sudo=True)
        run_cmd(['apt-get', 'dist-upgrade', '-y'], use_sudo=True)
        print("✓ システム更新完了 (apt update + upgrade + dist-upgrade)")
        
        return True
    
    def install_nvidia_driver_dnf(self, gpu_info: Dict) -> bool:
        """DNF: network repoを使用してNVIDIAドライバとCUDAをインストール"""
        print("\n" + "=" * 70)
        print("DNF: NVIDIAドライバとCUDA Toolkitをインストール")
        print("=" * 70)
        
        # 1. NVIDIA公式repositoryを追加
        print("\n【ステップ 1】NVIDIA Network Repositoryを追加...")
        
        nvidia_repo = "https://developer.download.nvidia.com/compute/cuda/repos/rhel9/x86_64/cuda-rhel9.repo"
        
        success, _ = run_cmd(['dnf', 'config-manager', '--add-repo', nvidia_repo], 
                            use_sudo=True, check=False)
        if success:
            print("✓ NVIDIA Repositoryを追加しました")
        else:
            print("⚠ Repositoryの追加失敗、手動ダウンロードを試行...")
            run_cmd(['wget', '-O', '/etc/yum.repos.d/cuda-rhel9.repo', nvidia_repo], 
                   use_sudo=True, check=False)
        
        # 2. キャッシュをクリアして更新
        print("\n【ステップ 2】パッケージデータベースを更新...")
        run_cmd(['dnf', 'clean', 'all'], use_sudo=True)
        run_cmd(['dnf', 'makecache'], use_sudo=True)
        
        # 3. NVIDIAドライバをインストール
        print("\n【ステップ 3】NVIDIAドライバをインストール...")
        
        driver_package = 'nvidia-driver:latest-dkms'
        
        success, _ = run_cmd(['dnf', 'module', 'install', '-y', driver_package], 
                            use_sudo=True, check=False)
        
        if not success:
            print("モジュールインストール失敗、直接インストールを試行...")
            success, _ = run_cmd(['dnf', 'install', '-y', 'nvidia-driver', 'nvidia-settings'], 
                                use_sudo=True, check=False)
        
        if success:
            print("✓ NVIDIAドライバのインストール成功")
        else:
            print("✗ NVIDIAドライバのインストール失敗")
            return False
        
        # 4. CUDA Toolkitをインストール
        print("\n【ステップ 4】CUDA Toolkitをインストール...")
        
        success, _ = run_cmd(['dnf', 'install', '-y', 'cuda-toolkit'], use_sudo=True, check=False)
        
        if not success:
            print("cuda-toolkit-12-xのインストールを試行...")
            success, _ = run_cmd(['dnf', 'install', '-y', 'cuda-toolkit-12-*'], 
                                use_sudo=True, check=False)
        
        if success:
            print("✓ CUDA Toolkitのインストール成功")
        else:
            print("✗ CUDA Toolkitのインストール失敗")
            return False
        
        # 5. 完全なシステム更新
        print("\n【ステップ 5】完全なシステム更新を実行...")
        run_cmd(['dnf', 'upgrade', '-y'], use_sudo=True)
        print("✓ システム更新完了 (dnf upgrade)")
        
        return True
    
    def create_auto_start(self) -> bool:
        """Linux 自動起動サービスを作成"""
        print("\nLinux 自動起動サービスを設定...")
        
        work_dir = os.path.dirname(SCRIPT_PATH)
        
        script_content = f"""#!/bin/bash
# CUDA インストール自動継続スクリプト
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
            print(f"✓ 実行スクリプトを作成: {AUTO_START_SCRIPT}")
            print(f"  使用: python3")
        except Exception as e:
            print(f"✗ スクリプト作成失敗: {e}")
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
            print(f"✗ サービス作成失敗: {e}")
            return False
        
        success, _ = run_cmd(['systemctl', 'daemon-reload'], use_sudo=True)
        if not success:
            return False
        
        success, _ = run_cmd(['systemctl', 'enable', 'cuda-setup.service'], use_sudo=True)
        if success:
            print("✓ 自動起動サービスを有効化しました")
            return True
        return False
    
    def remove_auto_start(self) -> bool:
        """Linux 自動起動サービスを削除"""
        print("\nLinux 自動起動サービスを削除...")
        
        run_cmd(['systemctl', 'disable', 'cuda-setup.service'], use_sudo=True, check=False)
        run_cmd(['systemctl', 'stop', 'cuda-setup.service'], use_sudo=True, check=False)
        
        try:
            if os.path.exists(AUTO_START_SERVICE):
                os.remove(AUTO_START_SERVICE)
            if os.path.exists(AUTO_START_SCRIPT):
                os.remove(AUTO_START_SCRIPT)
            run_cmd(['systemctl', 'daemon-reload'], use_sudo=True)
            print("✓ 自動起動機能を削除しました")
            return True
        except Exception as e:
            print(f"⚠ ファイル削除時にエラー: {e}")
            return False
    
    def install_gpu_burn(self, compute_capability: str = None) -> bool:
        """GPU Burnをダウンロードしてコンパイル"""
        print("\n" + "=" * 70)
        print("【GPU ステップ 3】GPU Burn ストレステストツールをインストール")
        print("=" * 70)
        
        if os.path.exists(GPU_BURN_PATH):
            print(f"✓ GPU Burn ディレクトリが存在: {GPU_BURN_PATH}")
            if os.path.exists(os.path.join(GPU_BURN_PATH, 'gpu_burn')):
                print("✓ GPU Burn はコンパイル済み")
                return True
            else:
                print("⚠ 再コンパイルが必要")
        else:
            print(f"\nGPU Burn repositoryをクローン...")
            print(f"ソース: {GPU_BURN_REPO}")
            success, _ = run_cmd(['git', 'clone', GPU_BURN_REPO, GPU_BURN_PATH], check=False)
            
            if not success:
                print("✗ クローン失敗")
                return False
            
            print("✓ クローン成功")
        
        print(f"\nGPU Burnをコンパイル...")
        
        if compute_capability:
            print(f"Compute Capabilityを使用: {compute_capability}")
            make_cmd = ['make', f'COMPUTE={compute_capability.replace(".", "")}']
        else:
            print("デフォルトのCompute Capabilityを使用")
            make_cmd = ['make']
        
        original_dir = os.getcwd()
        try:
            os.chdir(GPU_BURN_PATH)
            
            cuda_paths = ['/usr/local/cuda', '/usr/local/cuda-12', '/usr/local/cuda-11', '/usr']
            cuda_path = None
            for path in cuda_paths:
                nvcc_path = os.path.join(path, 'bin', 'nvcc') if path != '/usr' else '/usr/bin/nvcc'
                if os.path.exists(nvcc_path):
                    cuda_path = path
                    break
            
            if cuda_path:
                print(f"CUDAパスを使用: {cuda_path}")
                make_cmd.append(f'CUDAPATH={cuda_path}')
            
            success, output = run_cmd(make_cmd, check=False)
            
            if success and os.path.exists('gpu_burn'):
                print("✓ GPU Burn コンパイル成功")
                print(f"\n実行ファイルの場所: {os.path.join(GPU_BURN_PATH, 'gpu_burn')}")
                print("\n" + "=" * 70)
                print("使用方法:")
                print("=" * 70)
                print(f"cd {GPU_BURN_PATH}")
                print("./gpu_burn 60       # 60秒テスト")
                print("./gpu_burn 3600     # 1時間テスト")
                print("./gpu_burn -d 60    # 倍精度でテスト")
                print("./gpu_burn -l       # すべてのGPUをリスト")
                print("./gpu_burn -i 0     # GPU 0のみテスト")
                print("=" * 70)
                return True
            else:
                print(f"✗ GPU Burn コンパイル失敗")
                if output:
                    print(f"エラーメッセージ: {output}")
                return False
                
        finally:
            os.chdir(original_dir)