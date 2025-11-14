#!/usr/bin/env python3

import subprocess
import sys
import os
import platform
import json
from typing import Dict, List, Tuple, Optional
import pkg_resources
from packaging import version

class SystemPackageManager:
    """系統套件管理器 - 處理系統級別的工具安裝"""
    
    def __init__(self):
        self.os_type = platform.system().lower()
        self.package_manager = self._detect_package_manager()
    
    def _detect_package_manager(self) -> Optional[str]:
        """偵測系統套件管理器"""
        if self.os_type == 'linux':
            # 檢查常見的 Linux 套件管理器
            managers = {
                'apt-get': ['apt-get', '--version'],
                'yum': ['yum', '--version'],
                'dnf': ['dnf', '--version'],
                'pacman': ['pacman', '--version'],
                'zypper': ['zypper', '--version']
            }
            
            for manager, cmd in managers.items():
                try:
                    subprocess.run(cmd, capture_output=True, check=True)
                    return manager
                except:
                    continue
        
        elif self.os_type == 'darwin':  # macOS
            try:
                subprocess.run(['brew', '--version'], capture_output=True, check=True)
                return 'brew'
            except:
                return None
        
        elif self.os_type == 'windows':
            # 檢查 chocolatey 或 winget
            try:
                subprocess.run(['choco', '--version'], capture_output=True, check=True)
                return 'choco'
            except:
                try:
                    subprocess.run(['winget', '--version'], capture_output=True, check=True)
                    return 'winget'
                except:
                    return None
        
        return None
    
    def _run_command(self, command: List[str], use_sudo: bool = False) -> Tuple[bool, str]:
        """執行系統命令"""
        if use_sudo and self.os_type in ['linux', 'darwin']:
            command = ['sudo'] + command
        
        try:
            print(f"執行命令: {' '.join(command)}")
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, e.stderr
        except Exception as e:
            return False, str(e)
    
    def install_system_package(self, package_name: str, custom_command: List[str] = None) -> bool:
        """安裝系統套件"""
        if custom_command:
            print(f"\n使用自訂命令安裝 {package_name}...")
            success, output = self._run_command(custom_command, use_sudo=True)
        elif not self.package_manager:
            print(f"✗ 無法偵測套件管理器,無法自動安裝 {package_name}")
            return False
        else:
            print(f"\n使用 {self.package_manager} 安裝 {package_name}...")
            
            # 根據不同的套件管理器建立安裝命令
            if self.package_manager == 'apt-get':
                # 先更新套件列表
                print("更新套件列表...")
                self._run_command(['sudo', 'apt-get', 'update'], use_sudo=False)
                command = ['apt-get', 'install', '-y', package_name]
            
            elif self.package_manager == 'yum':
                command = ['yum', 'install', '-y', package_name]
            
            elif self.package_manager == 'dnf':
                command = ['dnf', 'install', '-y', package_name]
            
            elif self.package_manager == 'pacman':
                command = ['pacman', '-S', '--noconfirm', package_name]
            
            elif self.package_manager == 'brew':
                command = ['brew', 'install', package_name]
            
            elif self.package_manager == 'choco':
                command = ['choco', 'install', package_name, '-y']
            
            elif self.package_manager == 'winget':
                command = ['winget', 'install', package_name]
            
            else:
                print(f"✗ 不支援的套件管理器: {self.package_manager}")
                return False
            
            success, output = self._run_command(command, use_sudo=(self.package_manager not in ['brew', 'choco', 'winget']))
        
        if success:
            print(f"✓ {package_name} 安裝成功")
        else:
            print(f"✗ {package_name} 安裝失敗:")
            print(output)
        
        return success
    
    def install_cuda_toolkit(self, version: str = "12.3") -> bool:
        """安裝 CUDA Toolkit"""
        print(f"\n準備安裝 CUDA Toolkit {version}...")
        
        if self.os_type == 'linux':
            # Ubuntu/Debian 安裝方式
            if self.package_manager == 'apt-get':
                print("為 Ubuntu/Debian 系統安裝 CUDA...")
                print("\n注意: 這將添加 NVIDIA 的官方軟體源")
                
                # 下載並安裝 CUDA keyring
                commands = [
                    ['wget', 'https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb'],
                    ['dpkg', '-i', 'cuda-keyring_1.1-1_all.deb'],
                    ['apt-get', 'update'],
                    ['apt-get', 'install', '-y', 'cuda-toolkit']
                ]
                
                for cmd in commands:
                    success, output = self._run_command(cmd, use_sudo=True)
                    if not success:
                        print(f"✗ 命令執行失敗: {' '.join(cmd)}")
                        print(output)
                        return False
                
                return True
            
            # RHEL/CentOS 安裝方式
            elif self.package_manager in ['yum', 'dnf']:
                print("為 RHEL/CentOS 系統安裝 CUDA...")
                commands = [
                    ['dnf', 'config-manager', '--add-repo', 'https://developer.download.nvidia.com/compute/cuda/repos/rhel8/x86_64/cuda-rhel8.repo'] if self.package_manager == 'dnf' else ['yum-config-manager', '--add-repo', 'https://developer.download.nvidia.com/compute/cuda/repos/rhel8/x86_64/cuda-rhel8.repo'],
                    [self.package_manager, 'clean', 'all'],
                    [self.package_manager, 'install', '-y', 'cuda-toolkit']
                ]
                
                for cmd in commands:
                    success, output = self._run_command(cmd, use_sudo=True)
                    if not success:
                        return False
                
                return True
        
        elif self.os_type == 'darwin':
            print("✗ macOS 不支援 CUDA Toolkit")
            print("請使用 Metal 或其他替代方案")
            return False
        
        elif self.os_type == 'windows':
            print("Windows 系統請從以下網址手動下載安裝:")
            print("https://developer.nvidia.com/cuda-downloads")
            return False
        
        print("✗ 無法為此系統自動安裝 CUDA")
        return False


class PythonPackageManager:
    """Python 套件管理器"""
    
    def __init__(self):
        self.installed_packages = self._get_installed_packages()
    
    def _get_installed_packages(self) -> Dict[str, str]:
        """獲取已安裝套件列表"""
        packages = {}
        for dist in pkg_resources.working_set:
            packages[dist.project_name.lower()] = dist.version
        return packages
    
    def _run_command(self, command: List[str], check: bool = True) -> Tuple[bool, str]:
        """執行系統命令"""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=check
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, e.stderr
        except Exception as e:
            return False, str(e)
    
    def check_package_version(self, package_name: str, required_version: str = None) -> Dict:
        """檢查套件版本"""
        package_lower = package_name.lower()
        installed_version = self.installed_packages.get(package_lower)
        
        result = {
            'package': package_name,
            'installed': installed_version,
            'required': required_version,
            'status': 'not_installed'
        }
        
        if installed_version:
            result['status'] = 'installed'
            if required_version:
                try:
                    if version.parse(installed_version) >= version.parse(required_version):
                        result['status'] = 'up_to_date'
                    else:
                        result['status'] = 'outdated'
                except:
                    result['status'] = 'version_check_failed'
        
        return result
    
    def install_package(self, package_name: str, version_spec: str = None, upgrade: bool = False) -> bool:
        """安裝或升級 Python 套件"""
        print(f"\n{'升級' if upgrade else '安裝'} {package_name}...")
        
        if version_spec:
            package_spec = f"{package_name}{version_spec}"
        else:
            package_spec = package_name
        
        command = [sys.executable, "-m", "pip", "install"]
        if upgrade:
            command.append("--upgrade")
        command.append(package_spec)
        
        success, output = self._run_command(command, check=False)
        
        if success:
            print(f"✓ {package_name} 安裝成功")
            self.installed_packages = self._get_installed_packages()
        else:
            print(f"✗ {package_name} 安裝失敗: {output}")
        
        return success
    
    def process_requirements(self, requirements: Dict[str, str], auto_install: bool = False):
        """處理需求套件列表"""
        print("=" * 60)
        print("檢查 Python 套件需求")
        print("=" * 60)
        
        to_install = []
        to_upgrade = []
        
        for package, required_version in requirements.items():
            status = self.check_package_version(package, required_version)
            
            print(f"\n套件: {status['package']}")
            print(f"  要求版本: {status['required'] or '任意版本'}")
            print(f"  已安裝版本: {status['installed'] or '未安裝'}")
            print(f"  狀態: {status['status']}")
            
            if status['status'] == 'not_installed':
                to_install.append((package, required_version))
            elif status['status'] == 'outdated':
                to_upgrade.append((package, required_version))
        
        if to_install or to_upgrade:
            print("\n" + "=" * 60)
            if not auto_install:
                response = input(f"\n是否安裝/升級所需 Python 套件? (y/n): ")
                if response.lower() != 'y':
                    print("取消安裝")
                    return
            
            for package, req_version in to_install:
                version_spec = f">={req_version}" if req_version else None
                self.install_package(package, version_spec)
            
            for package, req_version in to_upgrade:
                version_spec = f">={req_version}" if req_version else None
                self.install_package(package, version_spec, upgrade=True)
        else:
            print("\n✓ 所有 Python 套件都已安裝且版本正確")


class SystemToolsChecker:
    """系統工具檢查器"""
    
    def __init__(self):
        self.system_manager = SystemPackageManager()
    
    def _run_command(self, command: List[str]) -> Tuple[bool, str]:
        """執行系統命令"""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )
            return True, result.stdout
        except:
            return False, ""
    
    def check_tool(self, tool_name: str, check_command: List[str]) -> Dict:
        """檢查單一工具"""
        success, output = self._run_command(check_command)
        return {
            'name': tool_name,
            'installed': success,
            'version': output.split('\n')[0] if success else None
        }
    
    def check_cuda_toolkit(self) -> Dict:
        """檢查 CUDA Toolkit"""
        result = self.check_tool('CUDA Toolkit', ['nvcc', '--version'])
        
        if result['installed']:
            # 從輸出中提取版本號
            success, output = self._run_command(['nvcc', '--version'])
            for line in output.split('\n'):
                if 'release' in line.lower():
                    result['version'] = line.strip()
                    break
        
        return result
    
    def check_all_tools(self) -> Dict[str, Dict]:
        """檢查所有系統工具"""
        tools = {
            'git': ['git', '--version'],
            'gcc': ['gcc', '--version'],
            'g++': ['g++', '--version'],
            'make': ['make', '--version'],
            'cmake': ['cmake', '--version'],
            'wget': ['wget', '--version'],
            'curl': ['curl', '--version'],
        }
        
        results = {}
        print("\n" + "=" * 60)
        print("檢查系統工具")
        print("=" * 60)
        
        for tool_name, command in tools.items():
            result = self.check_tool(tool_name, command)
            results[tool_name] = result
            
            if result['installed']:
                print(f"✓ {tool_name}: {result['version']}")
            else:
                print(f"✗ {tool_name}: 未安裝")
        
        # 檢查 CUDA
        print()
        cuda_result = self.check_cuda_toolkit()
        results['cuda'] = cuda_result
        
        if cuda_result['installed']:
            print(f"✓ CUDA Toolkit: {cuda_result['version']}")
        else:
            print(f"✗ CUDA Toolkit: 未安裝")
        
        return results
    
    def install_missing_tools(self, tools_status: Dict[str, Dict], auto_install: bool = False):
        """安裝缺少的工具"""
        missing_tools = [name for name, status in tools_status.items() 
                        if not status['installed'] and name != 'cuda']
        
        if not missing_tools:
            print("\n✓ 所有系統工具都已安裝")
            return
        
        print("\n" + "=" * 60)
        print(f"發現 {len(missing_tools)} 個未安裝的工具:")
        for tool in missing_tools:
            print(f"  - {tool}")
        
        if not auto_install:
            response = input("\n是否安裝缺少的系統工具? (y/n): ")
            if response.lower() != 'y':
                print("取消安裝")
                return
        
        # 套件名稱映射 (有些工具的套件名稱不同)
        package_mapping = {
            'gcc': 'gcc',
            'g++': 'g++',
            'make': 'make',
            'cmake': 'cmake',
            'git': 'git',
            'wget': 'wget',
            'curl': 'curl',
        }
        
        for tool in missing_tools:
            package_name = package_mapping.get(tool, tool)
            self.system_manager.install_system_package(package_name)
        
        # 處理 CUDA
        if not tools_status.get('cuda', {}).get('installed'):
            print("\n" + "=" * 60)
            response = input("\n是否安裝 CUDA Toolkit? (y/n): ")
            if response.lower() == 'y':
                self.system_manager.install_cuda_toolkit()


def main():
    """主程式"""
    print("=" * 60)
    print("系統環境檢查與安裝工具")
    print("=" * 60)
    print(f"作業系統: {platform.system()} {platform.release()}")
    print(f"Python 版本: {sys.version}")
    
    # 初始化管理器
    py_manager = PythonPackageManager()
    tools_checker = SystemToolsChecker()
    
    # 定義 Python 套件需求
    python_requirements = {
        'numpy': '1.21.0',
        'pandas': '1.3.0',
        'torch': '2.0.0',
        'scikit-learn': '1.0.0',
        'matplotlib': '3.4.0',
    }
    
    # 1. 檢查並安裝 Python 套件
    py_manager.process_requirements(python_requirements, auto_install=False)
    
    # 2. 檢查系統工具
    tools_status = tools_checker.check_all_tools()
    
    # 3. 安裝缺少的系統工具
    tools_checker.install_missing_tools(tools_status, auto_install=False)
    
    # 總結
    print("\n" + "=" * 60)
    print("檢查完成!")
    print("=" * 60)


if __name__ == "__main__":
    # 確保有必要的套件
    try:
        import pkg_resources
        from packaging import version
    except ImportError:
        print("安裝必要的套件...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "packaging"])
        import pkg_resources
        from packaging import version
    
    main()