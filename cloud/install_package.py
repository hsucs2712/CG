import subprocess
import sys
import os

CORE_PACKAGES =[
    'pip',
    'os',
    'requests',
]

REQUIRED_PACKAGTE = [
    'fastapi==0.104.1',
    'uvicorn[standard]==0.24.0',
    'pydantic[email]==2.5.0',
    'python-multipart==0.0.6',
    'motor==3.3.2',  # MongoDB 異步驅動
    'pymongo==4.6.1' , # MongoDB 驅動
    'dnspython==2.4.2',  # MongoDB DNS 支援
]

VERSION = "Cloud service 1.0.0"

def update_core_packages():
   pass

def self_check_package_versionupdate():
   pass