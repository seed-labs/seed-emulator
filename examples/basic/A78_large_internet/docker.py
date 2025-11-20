import psutil
import subprocess
import time
import os
from datetime import datetime
import signal
import sys
import json

class DockerCommandMonitor:
    def __init__(self, command_idx, interval=1, batch_size=50, parallel_jobs=8):
        """
        初始化Docker命令监控器
        :param command_idx: 命令编号（1或2）
        :param interval: 监控间隔（秒）
        :param batch_size: xargs的-n参数
        :param parallel_jobs: xargs的-P参数
        """
        
        self.batch_size = batch_size
        self.parallel_jobs = parallel_jobs
        self.interval = interval
        
        self.compose_file = "docker-compose.yml" 

        # 构建 'config' 命令
        config_cmd = f"docker compose -f {self.compose_file} config --services"

        # 1. 构建 'build' 命令
        build_xargs = f"xargs -n {self.batch_size} -P {self.parallel_jobs}"
        build_suffix = f"docker compose -f {self.compose_file} build --progress=plain"
        
        # 2. 构建 'up' 命令
        up_xargs = f"xargs -n {self.batch_size} -P {self.parallel_jobs}"
        up_suffix = f"docker compose -f {self.compose_file} up -d"

        self.commands = {
            1: f"export DOCKER_BUILDKIT=0; {config_cmd} | {build_xargs} {build_suffix}",
            2: f"export DOCKER_BUILDKIT=0; {config_cmd} | {up_xargs} {up_suffix}"
        } 
        
        if command_idx not in self.commands:
            raise ValueError(f"命令编号无效，只能是1或2（1=build，2=up）")
            
        self.command = self.commands[command_idx]
        self.command_name = "build" if command_idx == 1 else "up"
        self.process = None
        self.running = False
        self.output_dir = os.path.join(os.getcwd(), "output")
        
        # 生成监控日志文件名
        params_str = f"n{self.batch_size}_p{self.parallel_jobs}_i{self.interval}"
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_filename = f"docker_{self.command_name}_{params_str}_{timestamp}.log"
        self.log_path = os.path.join(os.getcwd(), self.log_filename)
        
        # 生成命令输出日志文件名 (用于保存原来的终端输出)
        self.cmd_output_filename = f"docker_cmd_output_{params_str}_{timestamp}.log"
        self.cmd_output_path = os.path.join(os.getcwd(), self.cmd_output_filename)

        self._write_log_header()

    def _write_log_header(self):
        """写入日志头部，包含参数信息"""
        with open(self.log_path, 'w', encoding='utf-8') as f:
            f.write("--- 监控任务开始 ---\n")
            f.write(f"任务类型: {self.command_name}\n")
            f.write(f"监控间隔: {self.interval}s\n")
            f.write(f"统计周期: 300s (5分钟)\n")
            f.write(f"批次大小 (-n): {self.batch_size}\n")
            f.write(f"并行作业 (-P): {self.parallel_jobs}\n")
            f.write(f"完整命令: {self.command}\n")
            f.write(f"命令输出日志: {self.cmd_output_filename}\n") # 记录输出去哪了
            f.write("----------------------------------\n\n")
            
            # CSV 头部，增加了一列用于备注信息 (Stats)
            f.write("时间,主进程ID,总CPU使用率(%),总内存占用(MB),系统内存使用率(%),统计信息\n")

    def _get_process_resources(self, pid):
        """获取进程及其子进程的总资源占用"""
        try:
            main_process = psutil.Process(pid)
            all_processes = [main_process] + main_process.children(recursive=True)
            
            total_cpu = 0.0
            total_memory = 0.0
            
            for p in all_processes:
                try:
                    total_cpu += p.cpu_percent(interval=0.01)
                    total_memory += p.memory_info().rss / (1024 **2)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            sys_mem_percent = psutil.virtual_memory().percent
            return total_cpu, total_memory, sys_mem_percent
        
        except psutil.NoSuchProcess:
            return 0.0, 0.0, psutil.virtual_memory().percent
        except Exception as e:
            # 静默处理资源获取错误，避免刷屏
            return 0.0, 0.0, psutil.virtual_memory().percent

    def _get_docker_count(self):
        """执行docker命令统计数量"""
        try:
            count_cmd = ""
            count_name = ""
            
            if self.command_name == "build":
                # 统计所有镜像数量 (包括中间层，如果只想统计最终镜像可去掉-a)
                count_cmd = "docker images -q | wc -l"
                count_name = "Docker Images Count"
            else: # up
                # 统计运行中的容器数量
                count_cmd = "docker ps -q | wc -l"
                count_name = "Running Containers Count"

            # 执行命令
            result = subprocess.run(count_cmd, shell=True, capture_output=True, text=True)
            count = result.stdout.strip()
            return f"{count_name}: {count}"
        except Exception as e:
            return f"Stat Error: {str(e)}"

    def _monitor_loop(self):
        """监控循环"""
        last_stat_time = 0
        stat_interval = 300  # 5分钟 = 300秒

        while self.running and self.process.poll() is None:
            current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            pid = self.process.pid
            
            # 1. 获取资源数据 (根据 interval 频率)
            cpu, mem, sys_mem = self._get_process_resources(pid)
            
            # 2. 检查是否需要执行 5分钟一次的统计
            stat_info = ""
            current_ts = time.time()
            if current_ts - last_stat_time >= stat_interval:
                stat_info = self._get_docker_count()
                last_stat_time = current_ts
            
            # 3. 写入日志
            with open(self.log_path, 'a', encoding='utf-8') as f:
                # 如果有统计信息，这一行的最后一列会有内容，否则为空
                f.write(f"{current_time_str},{pid},{cpu:.2f},{mem:.2f},{sys_mem:.2f},{stat_info}\n")
            
            time.sleep(self.interval)

    def _verify_build_success(self):
        """验证所有带 'build' 标签的服务是否都已生成镜像"""
        # 注意：验证过程的输出我们仍然打印到终端，因为这通常是在结束时运行一次，不影响运行时的I/O
        print("开始从 config --json 获取应构建的镜像列表...")
        try:
            config_cmd = ["docker", "compose", "-f", self.compose_file, "config", "--format", "json"]
            result = subprocess.run(config_cmd, cwd=self.output_dir, capture_output=True, text=True, encoding='utf-8', check=True)
            config_data = json.loads(result.stdout)
            
            project_name = config_data.get("name")
            if not project_name:
                project_name = os.path.basename(self.output_dir)

            images_cmd = ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"]
            result = subprocess.run(images_cmd, capture_output=True, text=True, encoding='utf-8', check=True)
            available_images = set(result.stdout.strip().split("\n"))
            
            services = config_data.get("services", {})
            if not services:
                return True

            missing_services = []
            checked_count = 0

            for service_name, service_data in services.items():
                if "build" in service_data:
                    checked_count += 1
                    if "image" in service_data:
                        image_name = service_data.get("image")
                        if ":" not in image_name: image_name += ":latest"
                        if image_name not in available_images:
                            missing_services.append(f"服务 '{service_name}' (期望: {image_name})")
                        continue

                    candidates = [
                        f"{project_name}-{service_name}:latest", 
                        f"{project_name}_{service_name}:latest"
                    ]
                    if not any(cand in available_images for cand in candidates):
                         missing_services.append(f"服务 '{service_name}' (期望: {candidates[0]} 或 {candidates[1]})")

            if checked_count == 0: return True

            if not missing_services:
                print(f"✅ 验证成功：所有 {checked_count} 个应构建的镜像均已在本地找到。")
                return True
            else:
                print(f"❌ 验证失败：以下 {len(missing_services)} 个服务的镜像在本地未找到：")
                for msg in missing_services[:10]:
                    print(f"  - {msg}")
                if len(missing_services) > 10:
                    print(f"  ... 以及其他 {len(missing_services) - 10} 个")
                return False

        except Exception as e:
            print(f"验证错误: {e}")
            return False

    def start(self):
        """启动命令并监控"""
        if not os.path.exists(self.output_dir):
            print(f"错误：output目录不存在（路径：{self.output_dir}）")
            return
        
        if not os.path.exists(os.path.join(self.output_dir, self.compose_file)):
             print(f"错误：在 output 目录中未找到 {self.compose_file}")
             return
        
        print("=================================================")
        print(f"正在后台执行命令...") 
        print(f"任务类型: {self.command_name}")
        print(f"监控日志: {self.log_path}")
        print(f"命令输出日志: {self.cmd_output_path}") # 提示用户输出去哪了
        print("终端将不再显示命令输出，以减少I/O。")
        print("=================================================")
        
        start_time = time.time()
        
        # 打开一个文件用于保存命令输出
        with open(self.cmd_output_path, 'w') as cmd_out_file:
            # 记录开始时间
            cmd_out_file.write(f"Command started at {datetime.now()}\n")
            cmd_out_file.write(f"Command: {self.command}\n\n")
            cmd_out_file.flush()

            # --- 核心修改：stdout/stderr 重定向到文件 ---
            self.process = subprocess.Popen(
                self.command,
                shell=True,
                cwd=self.output_dir,
                stdout=cmd_out_file,  # 不再是 sys.stdout
                stderr=cmd_out_file,  # 不再是 sys.stderr
                text=True,
                preexec_fn=os.setsid
            )
            
            self.running = True
            # 立即执行一次统计作为初始状态
            with open(self.log_path, 'a', encoding='utf-8') as f:
                init_stat = self._get_docker_count()
                f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]},{self.process.pid},0.00,0.00,0.00,{init_stat} (Initial)\n")

            self._monitor_loop() # 开始循环监控
            
            self.process.wait() # 等待命令结束

            # 记录结束时间
            cmd_out_file.write(f"\nCommand finished at {datetime.now()} with return code {self.process.returncode}\n")

        
        end_time = time.time()
        
        # 总结部分
        main_return_code = self.process.returncode
        verification_passed = None
        
        if self.command_name == "build":
            print("\n任务结束，正在验证结果...")
            if main_return_code == 0:
                verification_passed = self._verify_build_success()
            else:
                verification_passed = False
        
        duration = int(end_time - start_time)
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        seconds = duration % 60
        
        print("\n-------------------------------------")
        print("执行结束。")
        print(f"主命令返回码：{self.process.returncode}")
        if verification_passed is not None:
            status_text = "成功 ✅" if verification_passed else "失败 ❌"
            print(f"镜像构建验证：{status_text}")
        print(f"Total runtime: {hours}h {minutes}m {seconds}s")
        print("=================================================")
        
        # 将总结写入监控日志
        try:
            with open(self.log_path, 'a', encoding='utf-8') as f:
                f.write("\n\n--- 监控任务结束 ---\n")
                f.write(f"主命令返回码: {self.process.returncode}\n")
                if verification_passed is not None:
                    status_text = "成功 ✅" if verification_passed else "失败 ❌"
                    f.write(f"镜像构建验证: {status_text}\n")
                f.write(f"Total runtime: {hours}h {minutes}m {seconds}s\n")
                f.write("----------------------------------\n")
        except Exception as e:
            pass

    def stop(self):
        """强制停止"""
        self.running = False
        if self.process and self.process.poll() is None:
            print("\n强制终止命令...")
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            except Exception:
                pass


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("用法：python test.py <命令编号> <监控间隔秒数> <批次大小n> <并行作业P>")
        print("1 = build, 2 = up")
        sys.exit(1)
    
    try:
        command_idx = int(sys.argv[1])
        interval = float(sys.argv[2])
        batch_size = int(sys.argv[3])
        parallel_jobs = int(sys.argv[4])
        if batch_size <= 0: batch_size = 50
        if parallel_jobs <= 0: parallel_jobs = 8
    except ValueError:
        print("错误：参数必须是数字")
        sys.exit(1)
    
    monitor = None
    try:
        monitor = DockerCommandMonitor(command_idx, interval, batch_size, parallel_jobs)
        monitor.start()
    except KeyboardInterrupt:
        if monitor:
            monitor.stop()
        print("\n监控已停止")
    except Exception as e:
        print(f"执行失败：{e}")
        if monitor:
            monitor.stop()