#!/usr/bin/env python3
"""
コマンド実行ユーティリティモジュール
"""

import subprocess
import platform
from typing import List, Tuple


def run_cmd(cmd: List[str], use_sudo: bool = False, check: bool = True, silent: bool = False) -> Tuple[bool, str]:
    """コマンドを実行する汎用関数
    
    Args:
        cmd: 実行するコマンドのリスト
        use_sudo: Linuxでsudoを使用するか
        check: エラー時に例外を発生させるか
        silent: Trueの場合、実行コマンドを表示しない
    """
    if use_sudo and platform.system().lower() == 'linux':
        cmd = ['sudo'] + cmd
    
    try:
        if not silent:
            print(f"実行: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=check)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr
    except Exception as e:
        return False, str(e)