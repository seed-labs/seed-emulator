#!/usr/bin/env python3
"""
BIRD 故障注入器 - 修复版。
"""

import subprocess
import time
import re
from typing import List, Dict, Optional


class BirdFaultInjector:
    """BIRD 故障注入器。"""

    def __init__(self):
        self.containers = self._get_running_containers()

    def _get_running_containers(self) -> List[str]:
        try:
            result = subprocess.run(
                ['docker', 'ps', '--format', '{{.Names}}'],
                capture_output=True, text=True, timeout=10
            )
            return [line.strip().strip("'").strip('"')
                    for line in result.stdout.strip().split('\n') if line.strip()]
        except:
            return []

    def _exec(self, cmd: str) -> str:
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            return r.stdout + r.stderr
        except Exception as e:
            return f"Error: {e}"

    def inject_wrong_asn(self, asn: int = 2, wrong_asn: int = 999) -> Dict:
        """注入错误 ASN 故障。"""
        print(f"\n[FAULT] Injecting wrong_asn: AS{asn} -> AS{wrong_asn}")

        # 找到所有路由器
        target_containers = [c for c in self.containers if re.match(rf'as{asn}brd-', c)]

        if not target_containers:
            return {"success": False, "error": f"Router for AS{asn} not found"}

        print(f"  Found {len(target_containers)} routers for AS{asn}")

        # 修改每个路由器
        for container in target_containers:
            print(f"  Processing: {container}")

            # 使用 sed 替换 ASN
            self._exec(f"docker exec {container} sed -i 's/as {asn};/as {wrong_asn};/g' /etc/bird/bird.conf")

            # 重载 BIRD 配置
            self._exec(f"docker exec {container} birdc configure")

            print(f"  ✓ Modified {container}")

        # 验证注入
        time.sleep(2)
        verify_container = target_containers[0]
        bgp_status = self._exec(f"docker exec {verify_container} birdc show protocols")

        injection_success = "Bad peer AS" in bgp_status

        return {
            "success": injection_success,
            "containers_modified": target_containers,
            "verification": "Bad peer AS detected" if injection_success else "Injection may have failed",
        }


def demo():
    """演示。"""
    injector = BirdFaultInjector()
    print(f"Found {len(injector.containers)} containers")

    result = injector.inject_wrong_asn(2, 999)
    print(f"\nResult: {result}")


if __name__ == "__main__":
    demo()
