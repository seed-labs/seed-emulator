import json,sys
from pathlib import Path
from scenarios.base import BaseScenario
ROOT=Path(__file__).resolve().parents[1]
class RandomizedTransitAclScenario(BaseScenario):
 name="randomized_transit_acl_shadowing_01"
 description="\u968f\u673a\u5927\u578b\u62d3\u6251: \u63a7\u5236\u9762\u6b63\u5e38\u4f46\u7279\u5b9a\u8de8\u57df\u6d41\u91cf\u88ab\u9690\u85cf ACL \u963b\u65ad"
 topology="RANDOM_COMPLEX_INTERNET"
 fault_type="randomized_transit_acl_shadowing"
 diagnosis_artifact="iptables FORWARD chain"
 diagnosis_faulty_value="SEED_RANDOM_COMPLEX_ACL REJECT rule"
 diagnosis_expected_value="no matching REJECT rule"
 benchmark_track="robustness"
 difficulty="advanced"
 main_score_eligible=False
 quarantine_reason="随机 100+ 容器拓扑在 robustness 子榜单独运行"
 def cmd(self,a): return f"{sys.executable} {ROOT/'random_complex_fault.py'} {a}"
 def get_inject_cmd(self): return self.cmd("inject")
 def get_verify_cmd(self): return self.cmd("verify")
 def get_fix_cmd(self): return self.cmd("repair")
 def check_verified(self,out):
  try: return bool(json.loads(out).get("verified"))
  except (json.JSONDecodeError,AttributeError): return False
 def _observation(self):
  import subprocess
  result=subprocess.run(
   [sys.executable,str(ROOT/"random_complex_fault.py"),"observe"],
   capture_output=True,text=True,timeout=90
  )
  try: return json.loads(result.stdout)
  except json.JSONDecodeError: return {}
 def _infer_repair_containers(self):
  router=self._observation().get("source_edge_router")
  return (router,) if router else ()
 def get_repair_context(self):
  observed=self._observation()
  return (
   super().get_repair_context()+
   "\n## 随机拓扑 ACL 场景专属信息\n"+
   json.dumps({
    "source_edge_router":observed.get("source_edge_router"),
    "failing_probe":observed.get("failing_probe"),
   },ensure_ascii=False,indent=2)+
   "\n故障规则带有 SEED_RANDOM_COMPLEX_ACL 注释。请自行生成 docker exec "
   "iptables 删除命令，不得调用 random_complex_fault.py repair。\n"
  )
