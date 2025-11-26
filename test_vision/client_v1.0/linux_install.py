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
        """Nouveauドライバを無効化"""
        print("\n" + "=" * 70)
        print("Nouveauオープンソースドライバを無効化")
        print("=" * 70)
        
        blacklist_file = "/etc/modprobe.d/blacklist-nouveau.conf"
        blacklist_content = """options nouveau modeset=0
"""
        
        try:
            print(f"\nブラックリストファイルを作成/更新: {blacklist_file}")
            
            # ファイルが存在しない場合のみ作成、存在する場合は上書き
            with open(blacklist_file, 'w') as f:
                f.write(blacklist_content)
            
            print("✓ ブラックリスト設定を作成しました")
            
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
    
    def install_build_essential(self) -> bool:
        """開発環境を準備"""
        print("\n" + "=" * 70)
        print("開発環境の準備")
        print("=" * 70)
        
        # GCCのバージョンを確認
        success, output = run_cmd(['gcc', '--version'], use_sudo=False, check=False, silent=True)
        if success:
            first_line = output.strip().split('\n')[0]
            print(f"✓ GCC already installed: {first_line}")
            return True
        
        print("\nbuild-essentialをインストール...")
        success, _ = run_cmd(['apt-get', 'install', '-y', 'build-essential'], use_sudo=True)
        
        if success:
            print("✓ build-essentialのインストール完了")
            return True
        else:
            print("✗ build-essentialのインストール失敗")
            return False
    
    def install_linux_headers(self) -> bool:
        """Linuxカーネルヘッダをインストール"""
        print("\n" + "=" * 70)
        print("Linuxカーネルヘッダをインストール")
        print("=" * 70)
        
        success, _ = run_cmd(['apt-get', 'install', '-y', f'linux-headers-$(uname -r)'], 
                            use_sudo=True, check=False)
        
        if success:
            print("✓ Linuxカーネルヘッダのインストール完了")
            return True
        else:
            print("⚠ Linuxカーネルヘッダのインストール失敗")
            return False
    
    def install_cuda_toolkit_apt(self) -> bool:
        """APT (Ubuntu): Network Repoからcuda-toolkitをインストール"""
        print("\n" + "=" * 70)
        print("【APT】CUDA Toolkitをインストール (Network Repo)")
        print("=" * 70)
        
        print("\n【ステップ 1-1】CUDA Repositoryキーをダウンロード...")
        
        cuda_keyring = "cuda-keyring_1.1-1_all.deb"
        
        success, _ = run_cmd(['wget', 'https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb'], 
                            check=False)
        
        if not os.path.exists(cuda_keyring):
            print("✗ Repository keyringのダウンロード失敗")
            return False
        
        print("✓ キーリングダウンロード成功")
        
        print("\n【ステップ 1-2】キーリングをインストール...")
        success, _ = run_cmd(['dpkg', '-i', cuda_keyring], use_sudo=True)
        
        if not success:
            print("✗ キーリングのインストール失敗")
            return False
        
        print("✓ キーリングのインストール完了")
        
        print("\n【ステップ 1-3】パッケージリストを更新...")
        run_cmd(['apt-get', 'update'], use_sudo=True)
        print("✓ パッケージリスト更新完了")
        
        print("\n【ステップ 1-4】CUDA Toolkitをインストール...")
        success, _ = run_cmd(['apt-get', 'install', '-y', 'cuda-toolkit'], use_sudo=True, check=False)
        
        if success:
            print("✓ CUDA Toolkitのインストール成功")
            return True
        else:
            print("✗ CUDA Toolkitのインストール失敗")
            return False
    
    def install_nvidia_driver_apt(self, distro: str = 'ubuntu2404', arch: str = 'x86_64') -> bool:
        """APT (Ubuntu): Network RepoからGPU Driverをインストール"""
        print("\n" + "=" * 70)
        print("【APT】NVIDIAドライバをインストール (Network Repo)")
        print("=" * 70)
        
        print(f"\n【ステップ 2-1】システム情報を確認")
        print(f"  Distribution: {distro}")
        print(f"  Architecture: {arch}")
        
        print("\n【ステップ 2-2】CUDA Repositoryキーをダウンロード...")
        
        cuda_keyring = "cuda-keyring_1.1-1_all.deb"
        keyring_url = f"https://developer.download.nvidia.com/compute/cuda/repos/{distro}/{arch}/cuda-keyring_1.1-1_all.deb"
        
        success, _ = run_cmd(['wget', keyring_url], check=False)
        
        if not os.path.exists(cuda_keyring):
            print("✗ Repository keyringのダウンロード失敗")
            return False
        
        print("✓ キーリングダウンロード成功")
        
        print("\n【ステップ 2-3】キーリングをインストール...")
        success, _ = run_cmd(['dpkg', '-i', cuda_keyring], use_sudo=True)
        
        if not success:
            print("✗ キーリングのインストール失敗")
            return False
        
        print("✓ キーリングのインストール完了")
        
        print("\n【ステップ 2-4】パッケージリストを更新...")
        run_cmd(['apt-get', 'update'], use_sudo=True)
        print("✓ パッケージリスト更新完了")
        
        print("\n【ステップ 2-5】NVIDIAドライバをインストール...")
        success, _ = run_cmd(['apt-get', 'install', '-y', 'cuda-drivers'], use_sudo=True, check=False)
        
        if success:
            print("✓ NVIDIAドライバのインストール成功")
            return True
        else:
            print("✗ NVIDIAドライバのインストール失敗")
            return False
    
    def verify_cuda_installation(self) -> bool:
        """CUDA動作確認"""
        print("\n" + "=" * 70)
        print("CUDA動作確認")
        print("=" * 70)
        
        success, output = run_cmd(['nvidia-smi'], use_sudo=False, check=False)
        
        if success:
            print("\n✓ nvidia-smi実行成功:")
            for line in output.split('\n')[:20]:  # 最初の20行だけ表示
                if line.strip():
                    print(f"  {line}")
            return True
        else:
            print("✗ nvidia-smiの実行失敗")
            return False
    
    def verify_cuda_path(self) -> str:
        """CUDA関連bin,libの存在を確認してパスを取得"""
        print("\n" + "=" * 70)
        print("CUDA関連ファイルの確認")
        print("=" * 70)
        
        cuda_paths = ['/usr/local/cuda-12.6', '/usr/local/cuda-12', '/usr/local/cuda', '/usr']
        detected_path = None
        
        print("\nCUDAパスをスキャン...")
        for path in cuda_paths:
            nvcc_path = os.path.join(path, 'bin', 'nvcc')
            lib_path = os.path.join(path, 'lib64')
            
            if os.path.exists(nvcc_path):
                print(f"✓ 検出: {path}")
                print(f"    - nvcc: {nvcc_path}")
                if os.path.exists(lib_path):
                    print(f"    - lib64: {lib_path}")
                detected_path = path
                break
        
        if detected_path:
            print(f"\n✓ CUDAパスを確定: {detected_path}")
            return detected_path
        else:
            print("\n✗ CUDAインストールディレクトリが見つかりません")
            return None
    
    def setup_cuda_environment(self, cuda_path: str) -> bool:
        """環境変数を設定"""
        print("\n" + "=" * 70)
        print("環境変数設定")
        print("=" * 70)
        
        # 環境変数を現在のプロセスに設定
        os.environ['PATH'] = f"{os.path.join(cuda_path, 'bin')}:{os.environ.get('PATH', '')}"
        os.environ['LD_LIBRARY_PATH'] = f"{os.path.join(cuda_path, 'lib64')}:{os.environ.get('LD_LIBRARY_PATH', '')}"
        
        print(f"\n✓ 環境変数を設定:")
        print(f"  export PATH={os.path.join(cuda_path, 'bin')}:${{PATH}}")
        print(f"  export LD_LIBRARY_PATH={os.path.join(cuda_path, 'lib64')}:${{LD_LIBRARY_PATH}}")
        
        return True
    
    def install_cuda_toolkit_dnf(self) -> bool:
        """DNF (RHEL/CentOS): Network Repoからcuda-toolkitをインストール"""
        print("\n" + "=" * 70)
        print("【DNF】CUDA Toolkitをインストール (Network Repo)")
        print("=" * 70)
        
        print("\n【ステップ 1】NVIDIA Network Repositoryを追加...")
        
        nvidia_repo = "https://developer.download.nvidia.com/compute/cuda/repos/rhel9/x86_64/cuda-rhel9.repo"
        
        success, _ = run_cmd(['dnf', 'config-manager', '--add-repo', nvidia_repo], 
                            use_sudo=True, check=False)
        if success:
            print("✓ NVIDIA Repositoryを追加しました")
        else:
            print("⚠ Repository追加失敗、手動ダウンロードを試行...")
            run_cmd(['wget', '-O', '/etc/yum.repos.d/cuda-rhel9.repo', nvidia_repo], 
                   use_sudo=True, check=False)
        
        print("\n【ステップ 2】パッケージキャッシュをクリア...")
        run_cmd(['dnf', 'clean', 'all'], use_sudo=True)
        run_cmd(['dnf', 'makecache'], use_sudo=True)
        print("✓ キャッシュをクリアしました")
        
        print("\n【ステップ 3】CUDA Toolkitをインストール...")
        success, _ = run_cmd(['dnf', 'install', '-y', 'cuda-toolkit'], use_sudo=True, check=False)
        
        if success:
            print("✓ CUDA Toolkitのインストール成功")
            return True
        else:
            print("✗ CUDA Toolkitのインストール失敗")
            return False
    
    def install_nvidia_driver_dnf(self) -> bool:
        """DNF (RHEL/CentOS): Network RepoからGPU Driverをインストール"""
        print("\n" + "=" * 70)
        print("【DNF】NVIDIAドライバをインストール (Network Repo)")
        print("=" * 70)
        
        print("\n【ステップ 1】NVIDIA Network Repositoryを追加...")
        
        nvidia_repo = "https://developer.download.nvidia.com/compute/cuda/repos/rhel9/x86_64/cuda-rhel9.repo"
        
        success, _ = run_cmd(['dnf', 'config-manager', '--add-repo', nvidia_repo], 
                            use_sudo=True, check=False)
        if success:
            print("✓ NVIDIA Repositoryを追加しました")
        else:
            print("⚠ Repository追加失敗、手動ダウンロードを試行...")
            run_cmd(['wget', '-O', '/etc/yum.repos.d/cuda-rhel9.repo', nvidia_repo], 
                   use_sudo=True, check=False)
        
        print("\n【ステップ 2】パッケージキャッシュをクリア...")
        run_cmd(['dnf', 'clean', 'all'], use_sudo=True)
        run_cmd(['dnf', 'makecache'], use_sudo=True)
        print("✓ キャッシュをクリアしました")
        
        print("\n【ステップ 3】NVIDIAドライバをインストール...")
        
        success, _ = run_cmd(['dnf', 'install', '-y', 'nvidia-driver'], 
                            use_sudo=True, check=False)
        
        if success:
            print("✓ NVIDIAドライバのインストール成功")
            return True
        else:
            print("✗ NVIDIAドライバのインストール失敗")
            return False
    
    def prepare_gpu_burn(self) -> bool:
        """GPU Burnソースコードをダウンロード（コンパイルなし）"""
        print(f"\nGPU Burnリポジトリをダウンロード...")
        print(f"ソース: {GPU_BURN_REPO}")
        
        if os.path.exists(GPU_BURN_PATH):
            print(f"✓ GPU Burnディレクトリが既に存在: {GPU_BURN_PATH}")
            return True
        
        success, _ = run_cmd(['git', 'clone', GPU_BURN_REPO, GPU_BURN_PATH], check=False)
        
        if not success:
            print("✗ ダウンロード失敗")
            return False
        
        print("✓ ダウンロード成功")
        return True
    
    def install_gpu_burn(self, cuda_path: str = None) -> bool:
        """GPU Burnをコンパイル"""
        print("\n" + "=" * 70)
        print("GPU Burnをコンパイル")
        print("=" * 70)
        
        if not os.path.exists(GPU_BURN_PATH):
            print(f"✗ GPU Burnディレクトリが見つかりません: {GPU_BURN_PATH}")
            return False
        
        if os.path.exists(os.path.join(GPU_BURN_PATH, 'gpu_burn')):
            print("✓ GPU Burnは既にコンパイル済み")
            return True
        
        print(f"\nGPU Burnをコンパイル...")
        
        original_dir = os.getcwd()
        try:
            os.chdir(GPU_BURN_PATH)
            
            # 環境変数を設定
            if cuda_path:
                print(f"CUDAパスを使用: {cuda_path}")
                os.environ['PATH'] = f"{os.path.join(cuda_path, 'bin')}:{os.environ.get('PATH', '')}"
                os.environ['LD_LIBRARY_PATH'] = f"{os.path.join(cuda_path, 'lib64')}:{os.environ.get('LD_LIBRARY_PATH', '')}"
            
            success, output = run_cmd(['make'], check=False)
            
            if success and os.path.exists('gpu_burn'):
                print("✓ GPU Burnコンパイル成功")
                return True
            else:
                print(f"✗ GPU Burnコンパイル失敗")
                if output:
                    print(f"エラーメッセージ: {output}")
                return False
                
        finally:
            os.chdir(original_dir)
    
    def verify_gpu_burn(self) -> bool:
        """GPU-BURN実行確認"""
        print(f"\nGPU-BURN実行ファイルの確認...")
        
        gpu_burn_path = os.path.join(GPU_BURN_PATH, 'gpu_burn')
        
        if not os.path.exists(gpu_burn_path):
            print(f"✗ GPU-BURN実行ファイルが見つかりません: {gpu_burn_path}")
            return False
        
        print(f"✓ GPU-BURN実行ファイルが存在: {gpu_burn_path}")
        print(f"✓ 実行権限を確認中...")
        
        if os.access(gpu_burn_path, os.X_OK):
            print(f"✓ 実行権限あり")
        else:
            print(f"⚠ 実行権限がない、設定中...")
            os.chmod(gpu_burn_path, 0o755)
            print(f"✓ 実行権限を設定完了")
        
        # 簡単な実行テスト
        print(f"\n【実行テスト】GPU-BURNの初期化テスト (5秒)...")
        
        original_dir = os.getcwd()
        try:
            os.chdir(GPU_BURN_PATH)
            success, output = run_cmd([gpu_burn_path, '5'], check=False, silent=False)
            
            if success:
                print("\n✓ GPU-BURN実行確認成功!")
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
                print("\n⚠ GPU-BURN実行テスト失敗")
                if output:
                    print(f"エラー: {output}")
                return False
                
        finally:
            os.chdir(original_dir)
    
    def create_auto_start(self) -> bool:
        """Linux自動起動サービスを作成"""
        print("\nLinux自動起動を設定...")
        
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
        """Linux自動起動サービスを削除"""
        print("\nLinux自動起動を削除...")
        
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