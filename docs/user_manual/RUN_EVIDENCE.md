# Seed-Agent Runtime Evidence (2026-03-02)

This page records closed-loop runtime checks from real local runs.
All records below are from local runtime databases and generated artifacts.

---

## 1) Mission State Machine Evidence

Runtime DB:

- `subrepos/seed-agent/.seed-agent-runtime/task_sessions.db`

Session:

- `session_id`: `3a99db6b-25d6-4b9e-b27a-e89e55a6e036`
- `task_id`: `RS_B29_FAULT_IMPACT_ABLATION`
- `policy_profile`: `net_ops`

Observed transitions (Asia/Shanghai):

1. `2026-03-02 15:34:19` `begin` -> `status=awaiting_confirmation`
2. `2026-03-02 15:34:19` `execute_begin`
3. `2026-03-02 15:34:51` `execute_end` -> `status=ok`, `job_status=succeeded`

This confirms the expected gate-and-execute control loop:

- `awaiting_confirmation` (HITL gate active)
- approved execution
- terminal `ok`

---

## 2) SeedOps Job Evidence

SeedOps DB:

- `mcp-server/.seedops/seedops.db`

Recent succeeded jobs (Asia/Shanghai):

1. `job_id=218810af-bb3b-4d86-a79d-2072477c3a16`  
   `name=seedagent_fallback` `status=succeeded`  
   `created=2026-03-02 17:16:51` `finished=2026-03-02 17:16:52`
2. `job_id=bd14eaed-2c11-4798-955e-6bcd8585bdf4`  
   `name=seedagent_fallback` `status=succeeded`  
   `created=2026-03-02 15:34:51` `finished=2026-03-02 15:34:51`

---

## 3) Artifact Evidence Files

For `job_id=218810af-bb3b-4d86-a79d-2072477c3a16`:

- `mcp-server/.seedops/workspaces/38611584-5428-4812-8c97-51dc25bd7c5e/artifacts/218810af-bb3b-4d86-a79d-2072477c3a16/refresh.json`
- `mcp-server/.seedops/workspaces/38611584-5428-4812-8c97-51dc25bd7c5e/artifacts/218810af-bb3b-4d86-a79d-2072477c3a16/evidence.json`

Observed from `refresh.json`:

- `containers_seen=8`
- `nodes_parsed=7`
- `missing_containers=0`
- roles include `Route Server`, `BorderRouter`, `Host`

Observed from `evidence.json`:

- `counts.total=3`
- `counts.ok=3`
- `counts.fail=0`
- includes runtime command outputs: route tables, BGP protocol/routes, interfaces, process list

For `job_id=bd14eaed-2c11-4798-955e-6bcd8585bdf4`:

- `mcp-server/.seedops/workspaces/d6ad2fa6-b1b7-4836-9968-0e8ab9e40ff9/artifacts/bd14eaed-2c11-4798-955e-6bcd8585bdf4/refresh.json`
- `mcp-server/.seedops/workspaces/d6ad2fa6-b1b7-4836-9968-0e8ab9e40ff9/artifacts/bd14eaed-2c11-4798-955e-6bcd8585bdf4/evidence.json`

---

## 4) Quick Verification Commands

Show gate -> execute -> success:

```bash
sqlite3 subrepos/seed-agent/.seed-agent-runtime/task_sessions.db \
"select id,session_id,event,datetime(replace(substr(ts,1,19),'T',' '), '+8 hours') as ts_cst,payload \
from task_decisions \
where session_id='3a99db6b-25d6-4b9e-b27a-e89e55a6e036' \
order by id;"
```

Show succeeded jobs:

```bash
sqlite3 mcp-server/.seedops/seedops.db \
"select job_id,name,status,datetime(created_at,'unixepoch','+8 hours') as created_cst,datetime(finished_at,'unixepoch','+8 hours') as finished_cst \
from jobs \
where job_id in ('218810af-bb3b-4d86-a79d-2072477c3a16','bd14eaed-2c11-4798-955e-6bcd8585bdf4') \
order by created_at desc;"
```

Show artifact paths:

```bash
sqlite3 mcp-server/.seedops/seedops.db \
"select job_id,name,size_bytes,path \
from artifacts \
where job_id in ('218810af-bb3b-4d86-a79d-2072477c3a16','bd14eaed-2c11-4798-955e-6bcd8585bdf4') \
order by job_id,name;"
```
