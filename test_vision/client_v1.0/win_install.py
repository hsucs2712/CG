#!/usr/bin/env python3
"""
Windows システムインストーラー
"""

import os
import sys
import subprocess
import platform
import time
from run_cmd import run_cmd
from list import (
    WINDOWS_STARTUP_SCRIPT, WINDOWS_FLAG_FILE, SCRIPT_PATH
)


class WindowsInstaller:
    """Windows システムインストーラークラス"""
    
    def __init__(self):
        self.has_choco = self._check_chocolatey()
    
    def _check_chocolatey(self) -> bool:
        """Chocolateyがインストールされているかチェック"""
        try:
            subprocess.run(['choco', '--version'], 
                         capture_output=True, check=True)
            return True
        except:
            return False
    
    def update_system(self) -> bool:
        """Chocolateyを更新"""
        print("\n" + "=" * 70)
        print("Chocolateyを更新")
        print("=" * 70)
        
        if not self.has_choco:
            print("⚠ Chocolateyが未インストール")
            return False
        
        success, _ = run_cmd(['choco', 'upgrade', 'chocolatey', '-y'])
        if success:
            print("✓ Chocolatey更新完了")
            return True
        return False
    
    def install_system_tools(self, tools: dict) -> bool:
        """Windowsシステムツールをインストール(既存のものは更新のみ)"""
        print("\n" + "=" * 70)
        print("システムツールをチェック・インストール")
        print("=" * 70)
        
        if not self.has_choco:
            print("✗ Chocolateyが未インストール、継続できません")
            return False
        
        is_server = 'server' in platform.platform().lower()
        
        # すべてのツールリストを作成
        all_tools = tools['common'].copy()
        if is_server:
            all_tools.extend(tools['server'])
        else:
            all_tools.extend(tools['windows11'])
        
        # 既にインストールされているツールをチェック
        print("\nインストール状況をチェック...")
        installed_tools = []
        missing_tools = []
        
        for tool in all_tools:
            # choco list でインストール状況を確認
            success, output = run_cmd(['choco', 'list', '--local-only', tool, '--exact'], 
                                     check=False, silent=True)
            if success and '1 packages installed' in output:
                installed_tools.append(tool)
            else:
                missing_tools.append(tool)
        
        if installed_tools:
            print(f"\n✓ 既にインストール済み ({len(installed_tools)} 個):")
            for tool in installed_tools[:5]:  # 最初の5個だけ表示
                print(f"  • {tool}")
            if len(installed_tools) > 5:
                print(f"  ... 他 {len(installed_tools) - 5} 個")
            
            # インストール済みツールを更新
            print(f"\n🔄 既存ツールを更新中...")
            for tool in installed_tools:
                print(f"  {tool} を更新...")
                run_cmd(['choco', 'upgrade', tool, '-y'], check=False, silent=True)
            print("✓ 既存ツールの更新完了")
        
        if missing_tools:
            print(f"\n📥 新規インストールが必要 ({len(missing_tools)} 個):")
            for tool in missing_tools:
                print(f"  • {tool}")
            
            print(f"\n新規ツールをインストール中...")
            for tool in missing_tools:
                print(f"  {tool} をインストール...")
                run_cmd(['choco', 'install', tool, '-y'], check=False, silent=True)
            print("✓ 新規ツールのインストール完了")
        else:
            print("\n✓ すべてのシステムツールがインストール済み")
        
        print("\n✓ システムツールのセットアップ完了")
        return True
    
    def install_chocolatey(self) -> bool:
        """Chocolateyパッケージマネージャーをインストール"""
        print("\n" + "=" * 70)
        print("Chocolateyパッケージマネージャーをインストール")
        print("=" * 70)
        
        try:
            cmd = (
                "Set-ExecutionPolicy Bypass -Scope Process -Force; "
                "[System.Net.ServicePointManager]::SecurityProtocol = "
                "[System.Net.ServicePointManager]::SecurityProtocol -bor 3072; "
                "iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))"
            )
            
            print("Chocolateyインストールスクリプトを実行...")
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
                capture_output=True,
                text=True,
                check=True
            )
            
            print("✓ Chocolateyインストール成功")
            print("\n⚠ 重要: PowerShell/コマンドプロンプトを再起動しないとchocoが使えません")
            
            # Windows自動再起動を設定
            self.create_auto_start()
            
            print("\nシステムは10秒後に自動再起動します...")
            for i in range(10, 0, -1):
                print(f"\r再起動カウントダウン: {i} 秒...", end='', flush=True)
                time.sleep(1)
            print("\n")
            
            subprocess.run(['shutdown', '/r', '/t', '0'], check=False)
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"✗ Chocolateyインストール失敗: {e.stderr}")
            return False
        except Exception as e:
            print(f"✗ インストールプロセスでエラー: {e}")
            return False
    
    def create_auto_start(self) -> bool:
        """Windows 自動起動スクリプトを作成"""
        print("\nWindows 自動起動を設定...")
        
        work_dir = os.path.dirname(SCRIPT_PATH)
        
        # フラグファイルを作成
        try:
            with open(WINDOWS_FLAG_FILE, 'w') as f:
                f.write('restart')
            print(f"✓ フラグファイルを作成: {WINDOWS_FLAG_FILE}")
        except Exception as e:
            print(f"✗ フラグファイル作成失敗: {e}")
            return False
        
        # 起動バッチファイルを作成
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
            print(f"✓ 起動スクリプトを作成: {WINDOWS_STARTUP_SCRIPT}")
            return True
        except Exception as e:
            print(f"✗ 起動スクリプト作成失敗: {e}")
            return False
    
    def remove_auto_start(self) -> bool:
        """Windows 自動起動を削除"""
        print("\nWindows 自動起動を削除...")
        
        try:
            if os.path.exists(WINDOWS_STARTUP_SCRIPT):
                os.remove(WINDOWS_STARTUP_SCRIPT)
                print(f"✓ 起動スクリプトを削除: {WINDOWS_STARTUP_SCRIPT}")
            
            if os.path.exists(WINDOWS_FLAG_FILE):
                os.remove(WINDOWS_FLAG_FILE)
                print(f"✓ フラグファイルを削除: {WINDOWS_FLAG_FILE}")
            
            print("✓ 自動起動機能を削除しました")
            return True
        except Exception as e:
            print(f"⚠ ファイル削除時にエラー: {e}")
            return False
    
    def install_nvidia_driver(self) -> bool:
        """Windows: ChocolateyでNVIDIA表示カードドライバをインストール"""
        print("\n" + "=" * 70)
        print("Windows: NVIDIA表示カードドライバをインストール")
        print("=" * 70)

        if not self.has_choco:
            print("✗ インストール不可: Chocolateyが未インストール")
            return False

        print("\nChocolateyでNVIDIA表示カードドライバをインストール...")
        success, output = run_cmd(['choco', 'install', 'nvidia-display-driver', '-y'], check=False)

        if success:
            print("✓ NVIDIA表示カードドライバのインストール成功")
            return True
        else:
            print("✗ NVIDIA Driverインストール失敗")
            print(f"エラー: {output}")
            print("\n手動ダウンロード:")
            print("https://www.nvidia.com/Download/index.aspx")
            return False
    
    def install_cuda(self) -> bool:
        """Windows: ChocolateyでCUDA Toolkitをインストール"""
        print("\n" + "=" * 70)
        print("Windows: CUDA Toolkitをインストール")
        print("=" * 70)
        
        if not self.has_choco:
            print("✗ Chocolateyが未インストール、継続できません")
            return False
        
        print("\nChocolateyでCUDAをインストール...")
        success, output = run_cmd(['choco', 'install', 'cuda', '-y'], check=False)
        
        if success:
            print("✓ CUDA Toolkitのインストール成功")
            
            # インストール検証
            success, output = run_cmd(['nvcc', '--version'], use_sudo=False, check=False)
            if success:
                print("\n✓ CUDA検証成功:")
                for line in output.split('\n'):
                    if line.strip():
                        print(f"  {line}")
            return True
        else:
            print(f"✗ CUDAインストール失敗")
            print(f"エラー: {output}")
            
            print("\n手動インストールを推奨:")
            print("1. NVIDIA公式サイトからダウンロード: https://developer.nvidia.com/cuda-downloads")
            print("2. Windowsバージョンを選択してインストール")
            return False