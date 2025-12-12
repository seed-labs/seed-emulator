
---

# 一、脚本内容逐项解释

## 1. kernel.pid_max = 4194303

这是 系统允许的最大 PID 数量。

Linux 每个进程都有一个 PID。默认通常是 4194304 或更低（如 32768、65536）。

你设置为：

```
4194303 （靠近 Linux 最大允许值）
```

➤ 作用：  
 允许系统同时创建更多的进程（包括容器、线程）。

---

## 2. /etc/security/limits.conf 参数解释

这些是 用户级别的资源限制，由 PAM（Pluggable Authentication Modules）管理。

在容器、Docker、大量并发服务时非常重要。

---

### nofile（打开文件数限制）

```
* soft nofile 1048576
* hard nofile 1048576
```

- soft = 当前生效的限制
- hard = 最大允许限制（soft 不能超过 hard）
- nofile = 最大文件描述符数量（含 socket、pipe）

➤ 作用：允许每个用户打开 最多 1,048,576 个文件/socket  
 Docker、大量容器、大量网络连接必须调大这个值。

---

### 📌 nproc（最大进程数限制）

```
* soft nproc unlimited
* hard nproc unlimited
```

➤ 作用：允许用户创建 无限数量的线程 / 进程

如果 nproc 不够，Docker 会报：

```
Fork failed: resource temporarily unavailable
```

---

### 📌 root 用户的设置

```
root soft nofile 1048576
root hard nofile 1048576
root soft nproc unlimited
root hard nproc unlimited
```

和上面一样，但专门针对 root 用户。

因为 Docker daemon 以 root 运行，所以 root 的限制尤其关键。

---

# ✅ 二、如何检查这些参数是否生效？

---

# 1️⃣ 检查 pid_max

```
cat /proc/sys/kernel/pid_max
```

应该看到：

```
4194303
```

---

# 2️⃣ 检查当前会话文件描述符限制（nofile）

```
ulimit -n
ulimit -Hn
```

期望输出：

```
1048576
```

⚠️ 注意：  
 如果你用的是 SSH 或 login shell，需要重新登录一次才会生效。

---

# 3️⃣ 检查当前会话最大进程数（nproc）

```
ulimit -u
ulimit -Hu
```

期望输出：

```
unlimited
```

---

# 4️⃣ 检查系统级 FD 使用情况

查看总 FD 使用情况：

```
cat /proc/sys/fs/file-nr
```

会输出 3 个数字，例如：

```
51200   0   1048576
```

解释：

| 字段  | 含义           |
|-----|--------------|
| 第1列 | 已分配但未使用的 FD  |
| 第2列 | 已分配且正在使用的 FD |
| 第3列 | 最大可用 FD（系统级） |

最大值可以查看：

```
cat /proc/sys/fs/file-max
```

---

# 5️⃣ 检查每个进程打开的 FD

例如查看 Docker 进程：

```
pidof dockerd | xargs -I{} ls /proc/{}/fd | wc -l
```

---

# 6️⃣ 检查 nproc 使用情况

```
ps -eLf | wc -l
```

查看线程/进程总数。

---

# 7️⃣ 检查 PAM 是否生效

```
grep pam_limits.so /etc/pam.d/*
```

在 Ubuntu 默认是生效的。

---

# 8️⃣ 检查 limits.conf 是否正确写入

```
grep -E "nofile|nproc" /etc/security/limits.conf
```

---

# ⚠️ 是否要重启？

| 参数                          | 是否要重启                    |
|-----------------------------|--------------------------|
| pid_max                     | 不需要，马上生效                 |
| limits.conf（nofile / nproc） | ⚠️ 需要重登 或重启所有服务          |
| Docker 守护进程需要重新启动           | systemctl restart docker |

如果你要确保所有服务应用最新限制，建议最终重启：

```
reboot
```