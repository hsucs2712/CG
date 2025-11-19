#!/usr/bin/env python3
"""
GPU検出モジュール
"""

import platform
from typing import Dict
from run_cmd import run_cmd


# GPU Compute Capability マッピングテーブル
GPU_COMPUTE_CAPABILITY = {
    # RTX 40 シリーズ
    'rtx 4090': '8.9',
    'rtx 4080': '8.9',
    'rtx 4070': '8.9',
    'rtx 4060': '8.9',
    
    # RTX 30 シリーズ  
    'rtx 3090': '8.6',
    'rtx 3080': '8.6',
    'rtx 3070': '8.6',
    'rtx 3060': '8.6',
    
    # RTX 20 シリーズ
    'rtx 2080': '7.5',
    'rtx 2070': '7.5',
    'rtx 2060': '7.5',
    
    # GTX 10 シリーズ
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
    
    # デフォルト値
    'default': '7.5'
}


def get_compute_capability(gpu_name: str) -> str:
    """GPU名からCompute Capabilityを取得"""
    gpu_name_lower = gpu_name.lower()
    
    for key, cc in GPU_COMPUTE_CAPABILITY.items():
        if key in gpu_name_lower:
            return cc
    
    print(f"    ⚠ Compute Capabilityを特定できません。デフォルト値を使用: {GPU_COMPUTE_CAPABILITY['default']}")
    return GPU_COMPUTE_CAPABILITY['default']


def check_gpu() -> Dict:
    """NVIDIA GPUをチェック"""
    print("\n" + "=" * 70)
    print("【GPU】NVIDIA GPUハードウェアをチェック")
    print("=" * 70)
    
    os_type = platform.system().lower()
    
    if os_type == 'linux':
        success, output = run_cmd(['lspci'], use_sudo=False, check=False)
    elif os_type == 'windows':
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
                if os_type == 'linux' and ':' in line:
                    parts = line.split(':', 2)
                    if len(parts) >= 3:
                        gpu_name = parts[2].strip().replace('NVIDIA Corporation', '').strip()
                        result['gpu_names'].append(gpu_name)
                        cc = get_compute_capability(gpu_name)
                        result['compute_capabilities'].append(cc)
                elif os_type == 'windows':
                    gpu_name = line.strip()
                    if gpu_name and gpu_name != 'Name':
                        result['gpu_names'].append(gpu_name)
                        cc = get_compute_capability(gpu_name)
                        result['compute_capabilities'].append(cc)
    
    if result['has_gpu']:
        print(f"✓ {len(result['gpu_names'])} 個のNVIDIA GPUを検出:")
        for i, (gpu_name, cc) in enumerate(zip(result['gpu_names'], result['compute_capabilities']), 1):
            print(f"  GPU {i}: {gpu_name}")
            print(f"         Compute Capability: {cc}")
    else:
        print("✗ NVIDIA GPUが検出されませんでした")
    
    return result


def check_nvidia_driver() -> Dict:
    """NVIDIAドライバをチェック"""
    print("\n" + "=" * 70)
    print("【GPU ステップ 1】NVIDIAドライバをチェック")
    print("=" * 70)
    
    success, output = run_cmd(['nvidia-smi'], use_sudo=False, check=False)
    
    if success:
        print("✓ NVIDIAドライバがインストール済み")
        for line in output.split('\n')[:10]:
            if line.strip():
                print(f"  {line}")
        return {'installed': True}
    else:
        print("✗ NVIDIAドライバが未インストール")
        return {'installed': False}