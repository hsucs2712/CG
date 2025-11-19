#!/usr/bin/env python3
"""
インストールパッケージ・ツールのリスト定義
"""

import os

# スクリプトパス
SCRIPT_PATH = os.path.abspath(__file__)

# 自動起動スクリプトパス (Linux)
AUTO_START_SERVICE = "/etc/systemd/system/cuda-setup.service"
AUTO_START_SCRIPT = "/usr/local/bin/cuda-setup-continue.sh"

# Windows 自動起動パス
WINDOWS_STARTUP_SCRIPT = os.path.join(
    os.environ.get('APPDATA', 'C:\\'), 
    'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup', 
    'cuda-setup-continue.bat'
)
WINDOWS_FLAG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 
    '.restart_flag'
)

# GPU Burn 関連設定
GPU_BURN_REPO = "https://github.com/wilicc/gpu-burn.git"
GPU_BURN_PATH = os.path.join(os.path.dirname(SCRIPT_PATH), 'gpu-burn')

# Python パッケージ要件 (形式: 'パッケージ名': 'バージョン')
PYTHON_PACKAGES = {
    'requests': '',
    'psutil': '',          # ローカルシステム情報
    'rich': '',            # ターミナル美化出力
    'matplotlib': '',
    'tkiner':'',
    'packaging': '',       # バージョン比較
}

# システムツール要件 (Linux)
SYSTEM_TOOLS = [
    'git',
    'gcc',
    'g++',
    'make',
    'cmake',
    'wget',
    'curl',
    'build-essential',
    'python3-pip',         # pip サポート
]

# Windows システムツール (11 と Server 区分)
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