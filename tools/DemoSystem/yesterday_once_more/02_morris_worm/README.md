请先在主机`/etc/seedemu/seedemu.conf`中配置如下信息，请根据实际情况填写。

```yaml
condaPath: /home/cy/miniconda3/condabin/conda # conda 路径 (which conda)

demoSystem:
  envName: seedpy310 # demoSystem 需要使用到的 conda 环境名称 
  hostProjectPath: /home/cy/projects/debug/seed-emulator/tools/DemoSystem # DemoSystem 的项目根目录