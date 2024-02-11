# Set up Docker Hub Proxies

If you are in Mainland China, you may not be able to directly fetch the docker images 
used by the emulator. To solve this problem, you need to set up proxies. 


1. Add the pip proxy:
  
  ```bash
  pip install --upgrade pip
  pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
  ```

2. Add the dockerhub proxy:

  - Open the `daemon.json` file
  ```bash
  sudo vim /etc/docker/daemon.json
  ```

  - Add the following entries. These proxies worked when we wrote this document, but 
    there is no guarantee. You can search for working proxies if the situations have changed. 

  ```python
  {
    "registry-mirrors": [
        "https://docker.mirrors.ustc.edu.cn",
        "https://dockerproxy.com",
        "https://hub-mirror.c.163.com",
        "https://mirror.baidubce.com",
        "https://ccr.ccs.tencentyun.com"
    ]
  }
  ```

  - Restart docker 
  ```bash
  sudo systemctl daemon-reload
  sudo systemctl restart docker
  ```

