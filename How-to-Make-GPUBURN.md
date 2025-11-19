# Documents
- [NVIDIA CUDA Installation Guide for Linux](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/index.html#post-installation-actions)
- [NVIDIA Linux Driver Download](https://www.nvidia.com/en-us/drivers/details/239784/)  
- [Driver Installation Guide](https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/index.html#ubuntu)  
- [ubuntuにCUDA、nvidiaドライバをインストールするメモ](https://qiita.com/porizou1/items/74d8264d6381ee2941bd)

# Oracle OCI上でCompute Instance を作成
- Image Ubuntu 24.04
- Shape VM.GPU.A10.1



# Nouveau の無効化
```
sudo gedit /etc/modprobe.d/blacklist-nouveau.conf
```
## nouveauの設定ファイルを新規作成して以下を記入して保存する
blacklist-nouveau.conf    
``` 
options nouveau modeset=0
```
保存したら以下を実行
```
sudo update-initramfs -u
```



# 開発環境の準備
```
    6  gcc --version
    7  sudo apt install build-essential
```  

# Network Repoからcuda-toolkitをインストール
```
   11  wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb  
   12  sudo dpkg -i cuda-keyring_1.1-1_all.deb  
   13  sudo apt-get update  
   14  sudo apt-get install cuda-toolkit  
   16  sudo reboot  
```

# Network repoからGPU Driverをインストール 
```
   17  sudo apt install linux-headers-$(uname -r)  
   18  export distro=ubuntu2404   
   19  export arch=arm64  
   20  echo $distro  
   22  echo $arch  
   23  wget https://developer.download.nvidia.com/compute/cuda/repos/$distro/$arch/cuda-keyring_1.1-1_all.deb  
   24  sudo dpkg -i cuda-keyring_1.1-1_all.deb  
   25  sudo apt update  
   27  sudo apt install cuda-drivers  
   28  sudo reboot  
```

# CUDA動作確認
```
   29  nvidia-smi  
```

# CUDA関連bin,libの存在確認
```
   31  cd /usr/local  
```

# 環境変数設定  
```
   33  export PATH=/usr/local/cuda-12.6/bin${PATH:+:${PATH}}   
   34  export LD_LIBRARY_PATH=/usr/local/cuda-12.6/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}     
```

# GPU-BURNをmake&run
```
   54  git clone https://github.com/wilicc/gpu-burn.git  
   56  cd gpu-burn/  
   59  make  
   61  ./gpu_burn -l  
   62  ./gpu_burn -d 30  
   63  nvidia-smi  
```