# 区块连测试说明
## 测试环境

- ubuntu24.04 server
- cpu：AMD EPYC 9654 96-Core Processor， 256G Mem
- python env： conda activate seedpy310
## 网络设置（防止 ping 报错 no buffer space  available）
执行 [max_net_setting.sh](./max_net_setting.sh)
```
./max_net_setting.sh
```

## 后台持续交易100亿次（1000个账户）间隔0.5S
执行 [send_rand_tx.py](./send_rand_tx.py)
```
./send_rand_tx.py
```
## 测试block数量，内存使用和cpu使用率(10s检测一次)
执行 [check_block_cpu_mem.py](./check_block_cpu_mem.py)
```
Usage: python3 check_block_cpu_mem.py <rpc_url>
Example: python3 check_blosck_cpu_mem.py http://ip:8545
```
## block内存测试日志转excel
将上面测试block内存的log文件转换为excel
执行 [log2excel.py](./log2excel.py)
```
Usage: python3 log_to_excel.py input.log
```

## 测试block生成间隔
执行 [block_monitor.py](./block_monitor.py)
```
usage: block_monitor.py [-h] --node NODE [--interval INTERVAL] [--threshold THRESHOLD]
```
**参数说明**
- --interval 为每次get_block的间隔，默认5s，建议设置为1
- --threshold 为block间隔的警告时间。默认20S，超过20s会写入日志
**推荐**
```
python3 block_monitor.py --node http://10.164.0.84:8545 --threshold 20 --interval  1
```


## 定时交易检测receipt是否成功
执行 [web3_raw_tx.py](./web3_raw_tx.py)

```
python3 web3_raw_tx.py
```
程序自动每60s自动发一次交易并写入日志